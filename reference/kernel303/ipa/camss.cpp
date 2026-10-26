/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CAMSS inline hardware IPA: explicit manual tuning and validated BHIST. */
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>
#include <linux/videodev2.h>
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
#include "../libipa/camera_sensor_helper.h"
#include "hardware_agc.h"

namespace libcamera::ipa::camss {

LOG_DEFINE_CATEGORY(IPACamss)

class IPACamss final : public IPACamssInterface
{
public:
	int init(const IPASettings &settings, const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls) override;
	int configure(const IPACameraSensorInfo &sensorInfo, const Size &input, const ControlInfoMap &sensorControls, const std::string &profilePath, ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration) override;
	int mapBuffers(const std::vector<IPABuffer> &parameters, const std::vector<IPABuffer> &statistics) override;
	void unmapBuffers(const std::vector<uint32_t> &ids) override;
	int start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;
	int convertControls(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;
	void stop() override;
	int prepareParameters(uint64_t epoch, uint32_t id, uint32_t *bytesused) override;
	void parametersApplied(uint64_t epoch, uint32_t firstSof) override;
	void processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused, const SensorContext &sensorContext) override;
private:
 int describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &controls, ControlInfoMap *ipaControls);
 int translate(const ControlList &controls, bool startup, ControlList *sensorControls);
 std::unique_ptr<CameraSensorHelper> helper_;
 std::unique_ptr<HardwareAgc> agc_;
 bool automatic_ = false;
 uint32_t revision_ = 0;
 std::optional<AutoSensorUpdate> awaiting_;
 bool autoAvailable_ = false;
 ControlInfoMap sensorControls_;
 double lineUs_ = 0;
 int32_t minLines_ = 0, maxLines_ = 0, minGainCode_ = 0, maxGainCode_ = 0;
 int32_t minExposure_ = 0, maxExposure_ = 0;
 double minGain_ = 1, maxGain_ = 1;
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

int IPACamss::describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)
{
 if (!helper_ || !ipaControls || !info.pixelRate || !info.minLineLength ||
     info.minLineLength != info.maxLineLength) return -EINVAL;
 auto exposure = sensorControls.find(V4L2_CID_EXPOSURE);
 auto gain = sensorControls.find(V4L2_CID_ANALOGUE_GAIN);
 if (exposure == sensorControls.end() || gain == sensorControls.end()) return -ENOTSUP;
 const ControlInfo &e = exposure->second, &g = gain->second;
 minLines_ = e.min().get<int32_t>(); maxLines_ = e.max().get<int32_t>();
 minGainCode_ = g.min().get<int32_t>(); maxGainCode_ = g.max().get<int32_t>();
 lineUs_ = double(info.minLineLength) * 1000000 / info.pixelRate;
 if (minLines_ <= 0 || maxLines_ < minLines_ || minGainCode_ < 0 || maxGainCode_ < minGainCode_ ||
     !std::isfinite(lineUs_) || lineUs_ <= 0 || maxLines_ * lineUs_ > std::numeric_limits<int32_t>::max()) return -ERANGE;
 minExposure_ = std::lround(minLines_ * lineUs_); maxExposure_ = std::lround(maxLines_ * lineUs_);
 minGain_ = helper_->gain(minGainCode_); maxGain_ = helper_->gain(maxGainCode_);
 if (!std::isfinite(minGain_) || !std::isfinite(maxGain_) || minGain_ <= 0 || maxGain_ < minGain_) return -ERANGE;
 sensorControls_ = sensorControls;
 *ipaControls = ControlInfoMap({
  { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) },
  { &controls::ExposureTimeMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::ExposureTimeModeManual)}) },
  { &controls::AnalogueGainMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::AnalogueGainModeManual)}) },
  { &controls::ExposureTime, ControlInfo(minExposure_, maxExposure_, int32_t(std::lround(e.def().get<int32_t>() * lineUs_))) },
  { &controls::AnalogueGain, ControlInfo(float(minGain_), float(maxGain_), float(helper_->gain(g.def().get<int32_t>()))) }
 }, controls::controls);
 return 0;
}

int IPACamss::init(const IPASettings &settings, const IPACameraSensorInfo &info,
 const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)
{
 if (running_) return -EBUSY;
 model_ = settings.sensorModel;
 if (info.model != model_ || !settings.configurationFile.empty()) return -EINVAL;
 helper_ = CameraSensorHelperFactoryBase::create(model_);
 if (!helper_) return -ENOTSUP;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 configured_ = false;
 agc_.reset(); autoAvailable_ = false;
 LOG(IPACamss, Info) << "IPA init pid=" << getpid() << " model=" << model_;
 return 0;
}

int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input,
 const ControlInfoMap &sensorControls, const std::string &profilePath,
 ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration)
{
 if (running_) return -EBUSY;
 configured_ = false;
 agc_.reset(); autoAvailable_ = false;
 if (!sensorConfiguration) return -EINVAL;
 *sensorConfiguration = {};
 if (info.model != model_ || info.outputSize != input || info.bitsPerPixel != 10 ||
     input.width < 4 || input.height < 2 || ((input.width | input.height) & 1)) return -EINVAL;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 profile_ = { 0, 1.0 };
 if (!profilePath.empty()) {
  File file(profilePath);
  if (!file.open(File::OpenModeFlag::ReadOnly)) return file.error();
  auto root = YamlParser::parse(file);
  if (!root || (*root)["version"].get<unsigned int>().value_or(0) != 1 ||
      (*root)["sensor_model"].get<std::string>().value_or("") != model_) return -EINVAL;
  auto subtraction = (*root)["residual_black_subtraction"].get<uint16_t>();
  auto normalization = (*root)["range_normalization"].get<double>();
  if (!subtraction || !normalization) return -EINVAL;
  profile_ = { *subtraction, *normalization };
  const auto &timing = (*root)["sensor_controls"];
  if (!timing.isEmpty()) {
   if (!timing.isDictionary()) return -EINVAL;
   if (timing["width"].get<unsigned int>().value_or(0) != input.width ||
       timing["height"].get<unsigned int>().value_or(0) != input.height ||
       timing["pixel_rate"].get<unsigned int>().value_or(0) != info.pixelRate ||
       timing["line_length"].get<unsigned int>().value_or(0) != info.minLineLength ||
       timing["frame_length"].get<unsigned int>().value_or(0) != info.minFrameLength) return -EINVAL;
   auto exposureDelay = timing["exposure_delay"].get<unsigned int>();
   auto gainDelay = timing["gain_delay"].get<unsigned int>();
   if (!exposureDelay || !gainDelay || *exposureDelay != *gainDelay ||
       !*exposureDelay || *exposureDelay > 4) return -EINVAL;
   *sensorConfiguration = { true, *exposureDelay, *gainDelay };
  }
  const auto &agc = (*root)["agc"];
  if (!agc.isEmpty()) {
   if (!sensorConfiguration->enabled || !agc.isDictionary()) return -EINVAL;
   auto candidate = std::make_unique<HardwareAgc>();
   ret = candidate->initialise(agc, lineUs_, minLines_, maxLines_, minGain_, maxGain_, helper_.get());
   if (ret) return ret;
   agc_ = std::move(candidate);
   autoAvailable_ = true;
   ControlInfoMap::Map map;
   for (const auto &[id, value] : *ipaControls) map.emplace(id, value);
   map[&controls::ExposureTimeMode] = ControlInfo(std::vector<ControlValue>{
    int32_t(controls::ExposureTimeModeAuto), int32_t(controls::ExposureTimeModeManual)}, int32_t(controls::ExposureTimeModeManual));
   map[&controls::AnalogueGainMode] = ControlInfo(std::vector<ControlValue>{
    int32_t(controls::AnalogueGainModeAuto), int32_t(controls::AnalogueGainModeManual)}, int32_t(controls::AnalogueGainModeManual));
   *ipaControls = ControlInfoMap(std::move(map), controls::controls);
  }
 }
 input_ = input; configured_ = true;
 LOG(IPACamss, Info) << "Sensor configuration model=" << model_ << " pixel-rate=" << info.pixelRate
  << " line-length=" << info.minLineLength << " frame-length=" << info.minFrameLength
  << " delayed-controls=" << sensorConfiguration->enabled;
 return 0;
}

int IPACamss::translate(const ControlList &controls, bool startup, ControlList *sensorControls)
{
 if (!sensorControls) return -EINVAL;
 ControlList translated(sensorControls_);
 for (const auto &[id, value] : controls) {
  if (id == controls::ColourGains.id() && startup) continue;
  if (id == controls::ExposureTimeMode.id() || id == controls::AnalogueGainMode.id()) {
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   const int32_t wanted = id == controls::ExposureTimeMode.id() ? int32_t(controls::ExposureTimeModeManual) : int32_t(controls::AnalogueGainModeManual);
   if (!startup && value.get<int32_t>() != wanted) return -ENOTSUP;
   const int32_t autoMode = id == controls::ExposureTimeMode.id() ? int32_t(controls::ExposureTimeModeAuto) : int32_t(controls::AnalogueGainModeAuto);
   if (startup && value.get<int32_t>() != wanted && value.get<int32_t>() != autoMode) return -ENOTSUP;
   continue;
  }
  if (id == controls::ExposureTime.id()) {
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   int32_t time = value.get<int32_t>();
   if (time < minExposure_ || time > maxExposure_) return -ERANGE;
   int32_t lines = std::clamp<int64_t>(std::llround(time / lineUs_), minLines_, maxLines_);
   translated.set(V4L2_CID_EXPOSURE, lines);
  } else if (id == controls::AnalogueGain.id()) {
   if (value.type() != ControlTypeFloat || value.isArray()) return -EINVAL;
   float gain = value.get<float>();
   if (!std::isfinite(gain) || gain < minGain_ || gain > maxGain_) return -ERANGE;
   int32_t code = std::clamp<int64_t>(helper_->gainCode(gain), minGainCode_, maxGainCode_);
   translated.set(V4L2_CID_ANALOGUE_GAIN, code);
  } else return -EINVAL;
 }
 *sensorControls = translated;
 return 0;
}

int IPACamss::convertControls(uint64_t epoch, const ControlList &controls, ControlList *sensorControls)
{
 if (!running_ || epoch != epoch_) return -ESTALE;
 if (automatic_ && !controls.empty()) return -ENOTSUP;
 return translate(controls, false, sensorControls);
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

int IPACamss::start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls)
{
	if (running_)
		return -EBUSY;
	if (!configured_ || !epoch || epoch <= epoch_)
		return -EINVAL;
 if (!sensorControls) return -EINVAL;
 ControlList initial(sensorControls_);
 int translated = translate(controls, true, &initial);
 if (translated) return translated;
 const int32_t exposureMode = controls.get(controls::ExposureTimeMode).value_or(controls::ExposureTimeModeManual);
 const int32_t gainMode = controls.get(controls::AnalogueGainMode).value_or(controls::AnalogueGainModeManual);
 const bool automatic = exposureMode == controls::ExposureTimeModeAuto && gainMode == controls::AnalogueGainModeAuto;
 const bool manual = exposureMode == controls::ExposureTimeModeManual && gainMode == controls::AnalogueGainModeManual;
 if ((!automatic && !manual) || (automatic && !autoAvailable_)) return -ENOTSUP;
	double red = 1, blue = 1;
	for (const auto &[id, value] : controls) {
		if (id != controls::ColourGains.id())
			continue;
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
 *sensorControls = initial;
 automatic_ = automatic;
 revision_ = 0;
 awaiting_.reset();
 if (agc_) agc_->resetFrameCount();
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
 automatic_ = false; awaiting_.reset();
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

void IPACamss::processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused, const SensorContext &sensorContext)
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
 if (sensorContext.valid && sensorContext.exposureLines >= uint32_t(minLines_) &&
     sensorContext.exposureLines <= uint32_t(maxLines_) && sensorContext.gainCode >= uint32_t(minGainCode_) &&
     sensorContext.gainCode <= uint32_t(maxGainCode_)) {
  result.sensorControlsKnown = true;
  metadata.set(controls::ExposureTimeMode, int32_t(automatic_ ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual));
  metadata.set(controls::AnalogueGainMode, int32_t(automatic_ ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual));
  metadata.set(controls::ExposureTime, int32_t(std::lround(sensorContext.exposureLines * lineUs_)));
  metadata.set(controls::AnalogueGain, float(helper_->gain(sensorContext.gainCode)));
 }
 if (automatic_ && effective_ && result.sensorControlsKnown &&
     (!awaiting_ || (sensorContext.source == awaiting_->revision &&
      sensorContext.exposureLines == awaiting_->exposureLines && sensorContext.gainCode == awaiting_->gainCode))) {
  awaiting_.reset();
  uint32_t lines, code;
  if (!agc_->calculate(histogram.bins, sensorContext.exposureLines, sensorContext.gainCode, &lines, &code) &&
      (lines != sensorContext.exposureLines || code != sensorContext.gainCode) && revision_ < UINT32_MAX - 1) {
   result.automaticUpdate = { true, ++revision_, lines, code };
   awaiting_ = result.automaticUpdate;
  }
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
