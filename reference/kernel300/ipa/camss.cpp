/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CAMSS inline hardware IPA: explicit manual tuning and validated BHIST. */
#include <array>
#include <cerrno>
#include <cstring>
#include <map>
#include <optional>
#include <unistd.h>

#include <linux/qcom-camss-config.h>
#include <libcamera/base/file.h>
#include <libcamera/base/log.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
#include <libcamera/ipa/ipa_module_info.h>
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/yaml_parser.h"
#include "parameter_encoder.h"

namespace libcamera::ipa::camss {

LOG_DEFINE_CATEGORY(IPACamss)

class IPACamss final : public IPACamssInterface
{
public:
	int init(const IPASettings &settings) override;
	int configure(const IPACameraSensorInfo &sensorInfo, const Size &input) override;
	int mapBuffers(const std::vector<IPABuffer> &parameters, const std::vector<IPABuffer> &statistics) override;
	void unmapBuffers(const std::vector<uint32_t> &ids) override;
	int start(uint64_t epoch, const ControlList &controls) override;
	void stop() override;
	int prepareParameters(uint64_t epoch, uint32_t id, uint32_t *bytesused) override;
	void parametersApplied(uint64_t epoch, uint32_t firstSof) override;
	void processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused) override;
private:
	struct Buffer {
		bool parameters;
		std::unique_ptr<MappedFrameBuffer> memory;
	};
	std::map<uint32_t, Buffer> buffers_;
	ResidualBlackProfile profile_{ 0, 1.0 };
	std::string model_;
	Size input_;
	bool configured_ = false, running_ = false, applied_ = false, effective_ = false;
	uint64_t epoch_ = 0;
	uint32_t firstSof_ = 0;
	std::optional<uint32_t> lastStats_;
	double red_ = 1, blue_ = 1;
};

int IPACamss::init(const IPASettings &settings)
{
	if (running_)
		return -EBUSY;
	model_ = settings.sensorModel;
	configured_ = false;
	profile_ = { 0, 1.0 };
	if (!settings.configurationFile.empty()) {
		File file(settings.configurationFile);
		if (!file.open(File::OpenModeFlag::ReadOnly))
			return file.error();
		auto root = YamlParser::parse(file);
		if (!root || (*root)["version"].get<unsigned int>().value_or(0) != 1 ||
		    (*root)["sensor_model"].get<std::string>().value_or("") != model_)
			return -EINVAL;
		auto subtraction = (*root)["residual_black_subtraction"].get<uint16_t>();
		auto normalization = (*root)["range_normalization"].get<double>();
		if (!subtraction || !normalization)
			return -EINVAL;
		profile_ = { *subtraction, *normalization };
	}
	LOG(IPACamss, Info) << "IPA init pid=" << getpid() << " model=" << model_;
	return 0;
}

int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input)
{
	if (running_)
		return -EBUSY;
	if (info.model != model_ || info.outputSize != input || info.bitsPerPixel != 10 ||
	    input.width < 4 || input.height < 2 || ((input.width | input.height) & 1))
		return -EINVAL;
	input_ = input;
	configured_ = true;
	return 0;
}

int IPACamss::mapBuffers(const std::vector<IPABuffer> &parameters, const std::vector<IPABuffer> &statistics)
{
	if (running_)
		return -EBUSY;
	std::map<uint32_t, Buffer> pending;
	for (bool output : { true, false }) {
		for (const IPABuffer &buffer : output ? parameters : statistics) {
			if (!buffer.id || buffer.planes.size() != 1 ||
			    pending.count(buffer.id) || buffers_.count(buffer.id))
				return -EINVAL;
			FrameBuffer frame(buffer.planes);
			auto mapped = std::make_unique<MappedFrameBuffer>(&frame, output
				? MappedFrameBuffer::MapFlag::ReadWrite : MappedFrameBuffer::MapFlag::Read);
			if (!mapped->isValid())
				return mapped->error();
			const size_t required = sizeof(v4l2_isp_buffer) + (output
				? sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist) : sizeof(camss_stats_bhist));
			if (mapped->planes()[0].size() < required)
				return -ENOSPC;
			pending.emplace(buffer.id, Buffer{ output, std::move(mapped) });
		}
	}
	buffers_.merge(pending);
	return 0;
}

void IPACamss::unmapBuffers(const std::vector<uint32_t> &ids)
{
	/* Pipeline first stops the IPA and all V4L2 queues. */
	if (running_)
		return;
	for (uint32_t id : ids)
		buffers_.erase(id);
}

int IPACamss::start(uint64_t epoch, const ControlList &controls)
{
	if (running_)
		return -EBUSY;
	if (!configured_ || !epoch || epoch <= epoch_)
		return -EINVAL;
	double red = 1, blue = 1;
	for (const auto &[id, value] : controls) {
		if (id != controls::ColourGains.id())
			return -EINVAL;
		if (value.type() != ControlTypeFloat || !value.isArray() || value.numElements() != 2)
			return -EINVAL;
		auto gains = value.get<Span<const float>>();
		if (gains.size() != 2)
			return -EINVAL;
		red = gains[0]; blue = gains[1];
	}
	alignas(8) std::array<uint8_t, sizeof(v4l2_isp_buffer) + sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist)> packet;
	size_t used;
	int ret = encodeParameters(packet, profile_, red, blue, input_, Rectangle(input_), &used);
	if (ret)
		return ret;
	epoch_ = epoch;
	red_ = red; blue_ = blue;
	applied_ = effective_ = false;
	lastStats_.reset();
	running_ = true;
	return 0;
}

void IPACamss::stop()
{
	running_ = false;
	applied_ = effective_ = false;
	lastStats_.reset();
}

int IPACamss::prepareParameters(uint64_t epoch, uint32_t id, uint32_t *bytesused)
{
	if (!bytesused)
		return -EINVAL;
	*bytesused = 0;
	if (!running_ || epoch != epoch_)
		return -ESTALE;
	auto it = buffers_.find(id);
	if (it == buffers_.end() || !it->second.parameters)
		return -ENOENT;
	size_t used;
	int ret = encodeParameters(it->second.memory->planes()[0], profile_, red_, blue_, input_, Rectangle(input_), &used);
	if (!ret)
		*bytesused = used;
	return ret;
}

void IPACamss::parametersApplied(uint64_t epoch, uint32_t firstSof)
{
	if (!running_ || epoch != epoch_ || applied_)
		return;
	firstSof_ = firstSof;
	applied_ = true;
}

void IPACamss::processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused)
{
	Statistics result{};
	ControlList metadata(controls::controls);
	result.status = -ESTALE;
	auto complete = [&]() {
		LOG(IPACamss, Debug) << "IPA stats pid=" << getpid() << " epoch=" << epoch << " sof=" << sof << " status=" << result.status;
		statsProcessed.emit(epoch, sof, id, result, metadata);
	};
	if (!running_ || epoch != epoch_) { complete(); return; }
	auto it = buffers_.find(id);
	if (it == buffers_.end() || it->second.parameters) { result.status = -ENOENT; complete(); return; }
	constexpr size_t expected = sizeof(v4l2_isp_buffer) + sizeof(camss_stats_bhist);
	if (bytesused != expected) { result.status = -EINVAL; complete(); return; }
	if (lastStats_ && static_cast<int32_t>(sof - *lastStats_) <= 0) {
		result.status = sof == *lastStats_ ? -EALREADY : -ERANGE; complete(); return;
	}
	const auto &memory = it->second.memory->planes()[0];
	v4l2_isp_buffer header;
	camss_stats_bhist histogram;
	std::memcpy(&header, memory.data(), sizeof(header));
	std::memcpy(&histogram, memory.data() + sizeof(header), sizeof(histogram));
	if (header.version != V4L2_ISP_VERSION_V1 || header.data_size != sizeof(histogram) ||
	    histogram.header.type != CAMSS_STATS_AEC_BHIST || histogram.header.flags || histogram.header.size != sizeof(histogram)) {
		result.status = -EPROTO; complete(); return;
	}
	for (unsigned int i = 0; i < CAMSS_STATS_BHIST_BINS; ++i) {
		result.population += histogram.bins[i];
		result.weightedSum += uint64_t(i) * histogram.bins[i];
	}
	if (result.population != uint64_t(input_.width / 2) * (input_.height / 2)) {
		result.status = -ENODATA; complete(); return;
	}
	lastStats_ = sof;
	if (applied_ && (effective_ || static_cast<int32_t>(sof - firstSof_) >= 0))
		effective_ = true;
	result.parametersKnown = effective_;
	result.status = 0;
	if (effective_) {
		const std::array<float, 2> gains{ static_cast<float>(red_), static_cast<float>(blue_) };
		metadata.set(controls::ColourGains, Span<const float, 2>(gains));
	}
	complete();
}

} /* namespace libcamera::ipa::camss */

namespace libcamera {
extern "C" {
const IPAModuleInfo ipaModuleInfo = {
	IPA_MODULE_API_VERSION, 0, "camss-vfe", "camss-vfe",
};
IPAInterface *ipaCreate() { return new ipa::camss::IPACamss(); }
}
} /* namespace libcamera */
