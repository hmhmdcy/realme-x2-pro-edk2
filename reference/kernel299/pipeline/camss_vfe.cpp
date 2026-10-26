/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Experimental inline CAMSS handler. Manual, single processed stream only. */

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <deque>
#include <map>
#include <queue>
#include <set>
#include <unordered_map>

#include <linux/media-bus-format.h>
#include <linux/qcom-camss-config.h>

#include <libcamera/base/file.h>
#include <libcamera/base/log.h>
#include <libcamera/base/timer.h>
#include <libcamera/base/utils.h>
#include <libcamera/control_ids.h>
#include <libcamera/formats.h>

#include "libcamera/internal/camera.h"
#include "libcamera/internal/camera_sensor.h"
#include "libcamera/internal/device_enumerator.h"
#include "libcamera/internal/framebuffer.h"
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/media_device.h"
#include "libcamera/internal/pipeline_handler.h"
#include "libcamera/internal/request.h"
#include "libcamera/internal/v4l2_subdevice.h"
#include "libcamera/internal/v4l2_videodevice.h"
#include "libcamera/internal/yaml_parser.h"

#include "parameter_encoder.h"

namespace libcamera {

LOG_DEFINE_CATEGORY(CamssVfe)

class CamssVfePipeline;

class CamssVfeData : public Camera::Private
{
public:
	struct Endpoint {
		MediaEntity *image;
		MediaEntity *params;
		MediaEntity *stats;
		MediaEntity *pix;
	};
	CamssVfeData(CamssVfePipeline *pipe, std::shared_ptr<MediaDevice> media);
	int init(MediaEntity *sensor, const Endpoint &endpoint);
	int configurePath(const V4L2SubdeviceFormat &sensorFormat, const Size &output);
	void restoreLinks();
	int loadProfile();
	void imageReady(FrameBuffer *buffer);
	void statsReady(FrameBuffer *buffer);
	void paramsReady(FrameBuffer *buffer);
	void frameStart(uint32_t sequence);
	void expired();
	void finish(uint32_t sequence, bool paired);
	CamssVfePipeline *handler();

	std::shared_ptr<MediaDevice> media_;
	std::unique_ptr<CameraSensor> sensor_;
	std::unique_ptr<V4L2VideoDevice> image_, params_, stats_;
	std::map<MediaEntity *, std::unique_ptr<V4L2Subdevice>> subdevs_;
	V4L2Subdevice *pix_ = nullptr;
	std::vector<MediaLink *> path_;
	std::vector<std::pair<MediaLink *, bool>> changedLinks_;
	Stream stream_;
	Size input_;
	V4L2SubdeviceFormat configuredFormat_;
	std::vector<std::unique_ptr<FrameBuffer>> paramsBuffers_, statsBuffers_;
	std::map<FrameBuffer *, std::unique_ptr<MappedFrameBuffer>> maps_;
	ipa::camss::ResidualBlackProfile profile_{ 0, 1.0 };
	bool running_ = false;
	bool paramsApplied_ = false;
	uint32_t firstParamSof_ = 0;
	uint64_t epoch_ = 0;
	std::map<uint32_t, FrameBuffer *> images_;
	struct Histogram {
		uint64_t population;
		uint64_t weightedSum;
	};
	std::map<uint32_t, Histogram> histograms_;
	std::deque<uint32_t> histogramOrder_;
	Timer deadline_;
};

class CamssVfeConfiguration : public CameraConfiguration
{
public:
	explicit CamssVfeConfiguration(CamssVfeData *data) : data_(data) {}
	Status validate() override;
	V4L2SubdeviceFormat sensorFormat_;
private:
	CamssVfeData *data_;
};

class CamssVfePipeline : public PipelineHandler
{
public:
	explicit CamssVfePipeline(CameraManager *manager) : PipelineHandler(manager, 4) {}
	bool match(DeviceEnumerator *enumerator) override;
	std::unique_ptr<CameraConfiguration> generateConfiguration(Camera *camera,
					Span<const StreamRole> roles) override;
	int configure(Camera *camera, CameraConfiguration *config) override;
	int exportFrameBuffers(Camera *camera, Stream *stream,
		std::vector<std::unique_ptr<FrameBuffer>> *buffers) override;
	int start(Camera *camera, const ControlList *controls) override;
	void stopDevice(Camera *camera) override;
	int queueRequestDevice(Camera *camera, Request *request) override;
	CamssVfeData *active_ = nullptr;
private:
	void releaseDevice(Camera *camera) override;
	CamssVfeData *configured_ = nullptr;
	CamssVfeData *data(Camera *camera) { return static_cast<CamssVfeData *>(camera->_d()); }
};

CamssVfeData::CamssVfeData(CamssVfePipeline *pipe, std::shared_ptr<MediaDevice> media)
	: Camera::Private(pipe), media_(std::move(media))
{
	deadline_.timeout.connect(this, &CamssVfeData::expired);
}

CamssVfePipeline *CamssVfeData::handler()
{
	return static_cast<CamssVfePipeline *>(pipe());
}

int CamssVfeData::init(MediaEntity *sensor, const Endpoint &endpoint)
{
	/* Traverse to the already capability-checked PIX output, never an RDI. */
	std::queue<MediaEntity *> todo;
	std::map<MediaEntity *, MediaLink *> parents;
	std::set<MediaEntity *> visited{ sensor };
	todo.push(sensor);
	while (!todo.empty() && !visited.count(endpoint.image)) {
		MediaEntity *entity = todo.front();
		todo.pop();
		for (const MediaPad *pad : entity->pads()) {
			if (!(pad->flags() & MEDIA_PAD_FL_SOURCE))
				continue;
			for (MediaLink *link : pad->links()) {
				MediaEntity *next = link->sink()->entity();
				if (next->type() == MediaEntity::Type::V4L2VideoDevice && next != endpoint.image)
					continue;
				if (!visited.insert(next).second)
					continue;
				parents[next] = link;
				todo.push(next);
			}
		}
	}
	if (!visited.count(endpoint.image))
		return -ENOLINK;
	for (MediaEntity *entity = endpoint.image; entity != sensor;) {
		MediaLink *link = parents.at(entity);
		path_.push_back(link);
		entity = link->source()->entity();
	}
	std::reverse(path_.begin(), path_.end());
	if (path_.back()->source()->entity() != endpoint.pix)
		return -ENOLINK;

	sensor_ = CameraSensorFactoryBase::create(sensor);
	if (!sensor_)
		return -ENODEV;
	for (MediaLink *link : path_) {
		MediaEntity *entity = link->source()->entity();
		if (entity == sensor || subdevs_.count(entity))
			continue;
		auto dev = std::make_unique<V4L2Subdevice>(entity);
		int ret = dev->open();
		if (ret)
			return ret;
		subdevs_[entity] = std::move(dev);
	}
	pix_ = subdevs_.at(endpoint.pix).get();
	image_ = std::make_unique<V4L2VideoDevice>(endpoint.image);
	params_ = std::make_unique<V4L2VideoDevice>(endpoint.params);
	stats_ = std::make_unique<V4L2VideoDevice>(endpoint.stats);
	for (auto *dev : { image_.get(), params_.get(), stats_.get() }) {
		int ret = dev->open();
		if (ret)
			return ret;
	}
	image_->bufferReady.connect(this, &CamssVfeData::imageReady);
	params_->bufferReady.connect(this, &CamssVfeData::paramsReady);
	stats_->bufferReady.connect(this, &CamssVfeData::statsReady);
	pix_->frameStart.connect(this, &CamssVfeData::frameStart);
	properties_ = sensor_->properties();
	controlInfo_ = ControlInfoMap({ { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) } }, controls::controls);
	return 0;
}

void CamssVfeData::restoreLinks()
{
	for (auto it = changedLinks_.rbegin(); it != changedLinks_.rend(); ++it) {
		int ret = it->first->setEnabled(it->second);
		if (ret)
			LOG(CamssVfe, Error) << "Restore link failed: " << ret;
	}
	changedLinks_.clear();
}

int CamssVfeData::configurePath(const V4L2SubdeviceFormat &requested, const Size &output)
{
	restoreLinks();
	auto change = [&](MediaLink *link, bool enabled) {
		bool old = link->flags() & MEDIA_LNK_FL_ENABLED;
		if (old == enabled)
			return 0;
		int ret = link->setEnabled(enabled);
		if (!ret)
			changedLinks_.emplace_back(link, old);
		return ret;
	};
	/* Exclusive candidate: deactivate competing routes touching this path. */
	std::set<MediaEntity *> used;
	for (MediaLink *link : path_) {
		used.insert(link->source()->entity());
		used.insert(link->sink()->entity());
	}
	for (MediaEntity *entity : used) {
		for (const MediaPad *pad : entity->pads()) {
			for (MediaLink *link : pad->links()) {
				if (link->flags() & MEDIA_LNK_FL_IMMUTABLE ||
				    std::find(path_.begin(), path_.end(), link) != path_.end())
					continue;
				int ret = change(link, false);
				if (ret)
					return ret;
			}
		}
	}
	for (MediaLink *link : path_) {
		int ret = change(link, true);
		if (ret)
			return ret;
	}
	V4L2SubdeviceFormat format = requested;
	int ret = sensor_->setFormat(&format);
	if (ret || format.code != requested.code || format.size != requested.size)
		return ret ? ret : -EINVAL;
	input_ = format.size;
	for (MediaLink *link : path_) {
		MediaEntity *source = link->source()->entity();
		if (source != sensor_->entity()) {
			ret = subdevs_.at(source)->getFormat(link->source()->index(), &format);
			if (ret)
				return ret;
		}
		MediaEntity *sink = link->sink()->entity();
		if (sink->type() != MediaEntity::Type::V4L2Subdevice)
			break;
		ret = subdevs_.at(sink)->setFormat(link->sink()->index(), &format);
		if (ret)
			return ret;
	}
	Rectangle compose(output);
	ret = pix_->setSelection(0, V4L2_SEL_TGT_COMPOSE, &compose);
	if (ret || compose != Rectangle(output))
		return ret ? ret : -EINVAL;
	return 0;
}

int CamssVfeData::loadProfile()
{
	profile_ = { 0, 1.0 };
	/* Explicit selection only; never infer the physical module from sensor ID. */
	const char *path = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
	if (!path)
		return 0;
	File file(path);
	if (!file.open(File::OpenModeFlag::ReadOnly))
		return file.error();
	auto root = YamlParser::parse(file);
	if (!root || (*root)["version"].get<unsigned int>().value_or(0) != 1 ||
	    (*root)["sensor_model"].get<std::string>().value_or("") != sensor_->model())
		return -EINVAL;
	auto subtraction = (*root)["residual_black_subtraction"].get<uint16_t>();
	auto normalization = (*root)["range_normalization"].get<double>();
	if (!subtraction || !normalization)
		return -EINVAL;
	profile_ = { *subtraction, *normalization };
	return 0;
}

CameraConfiguration::Status CamssVfeConfiguration::validate()
{
	if (config_.empty())
		return Invalid;
	Status status = Valid;
	if (config_.size() > 1) {
		config_.resize(1);
		status = Adjusted;
	}
	auto &cfg = config_[0];
	if (orientation != data_->sensor_->mountingOrientation()) {
		orientation = data_->sensor_->mountingOrientation();
		status = Adjusted;
	}
	if (cfg.pixelFormat != formats::NV12) {
		cfg.pixelFormat = formats::NV12;
		status = Adjusted;
	}
	/* Only Bayer10 modes currently verified by this inline backend. */
	const std::array<unsigned int, 4> codes{ MEDIA_BUS_FMT_SRGGB10_1X10,
		MEDIA_BUS_FMT_SGRBG10_1X10, MEDIA_BUS_FMT_SGBRG10_1X10, MEDIA_BUS_FMT_SBGGR10_1X10 };
	sensorFormat_ = data_->sensor_->getFormat(codes, cfg.size);
	if (!sensorFormat_.code || sensorFormat_.size.width > 8192 ||
	    sensorFormat_.size.height > 16384)
		return Invalid;
	const Size requested = cfg.size;
	cfg.size.expandTo(Size(16, 16)).boundTo(sensorFormat_.size).alignDownTo(2, 2);
	if (cfg.size != requested)
		status = Adjusted;
	V4L2DeviceFormat format;
	format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
	format.size = cfg.size;
	if (data_->image_->tryFormat(&format) || format.size != cfg.size)
		return Invalid;
	cfg.stride = format.planes[0].bpl;
	cfg.frameSize = 0;
	for (unsigned int i = 0; i < format.planesCount; ++i)
		cfg.frameSize += format.planes[i].size;
	if (cfg.bufferCount != 4) {
		cfg.bufferCount = 4;
		status = Adjusted;
	}
	cfg.colorSpace = ColorSpace::Sycc;
	return status;
}

std::unique_ptr<CameraConfiguration> CamssVfePipeline::generateConfiguration(
	Camera *camera, Span<const StreamRole> roles)
{
	auto config = std::make_unique<CamssVfeConfiguration>(data(camera));
	if (roles.empty())
		return config;
	if (roles.size() != 1 || roles[0] == StreamRole::Raw)
		return nullptr;
	StreamConfiguration cfg;
	cfg.pixelFormat = formats::NV12;
	cfg.size = Size(640, 480);
	config->addConfiguration(cfg);
	if (config->validate() == CameraConfiguration::Invalid)
		return nullptr;
	return config;
}

int CamssVfePipeline::configure(Camera *camera, CameraConfiguration *configuration)
{
	auto *d = data(camera);
	if (active_)
		return -EBUSY;
	if (configured_ && configured_ != d)
		configured_->restoreLinks();
	configured_ = nullptr;
	auto *cfg = static_cast<CamssVfeConfiguration *>(configuration);
	int ret = d->configurePath(cfg->sensorFormat_, cfg->at(0).size);
	if (ret) {
		d->restoreLinks();
		return ret;
	}
	V4L2DeviceFormat format;
	format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
	format.size = cfg->at(0).size;
	ret = d->image_->setFormat(&format);
	if (ret || format.size != cfg->at(0).size || format.fourcc != V4L2PixelFormat(V4L2_PIX_FMT_NV12)) {
		d->restoreLinks();
		return ret ? ret : -EINVAL;
	}
	cfg->at(0).setStream(&d->stream_);
	d->configuredFormat_ = cfg->sensorFormat_;
	configured_ = d;
	return 0;
}

void CamssVfePipeline::releaseDevice(Camera *camera)
{
	if (configured_ == data(camera)) {
		configured_->restoreLinks();
		configured_ = nullptr;
	}
	data(camera)->configuredFormat_.code = 0;
}

int CamssVfePipeline::exportFrameBuffers(Camera *camera, Stream *stream,
	std::vector<std::unique_ptr<FrameBuffer>> *buffers)
{
	return data(camera)->image_->exportBuffers(stream->configuration().bufferCount, buffers);
}

int CamssVfePipeline::start(Camera *camera, const ControlList *controls)
{
	auto *d = data(camera);
	if (active_)
		return -EBUSY;
	if (!d->configuredFormat_.code)
		return -EPIPE;
	/* Per-frame controls await the IPA/context integration, never silently ignored. */
	double red = 1.0, blue = 1.0;
	if (controls) {
		for (const auto &[id, value] : *controls) {
			if (id != controls::ColourGains.id())
				return -EINVAL;
			auto gains = value.get<Span<const float>>();
			if (gains.size() != 2)
				return -EINVAL;
			red = gains[0]; blue = gains[1];
		}
	}
	int ret = d->loadProfile();
	if (ret)
		return ret;
	if (configured_ != d) {
		if (configured_)
			configured_->restoreLinks();
		configured_ = nullptr;
		ret = d->configurePath(d->configuredFormat_, d->stream_.configuration().size);
		V4L2DeviceFormat format;
		format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
		format.size = d->stream_.configuration().size;
		if (!ret)
			ret = d->image_->setFormat(&format);
		if (ret || format.size != d->stream_.configuration().size) {
			d->restoreLinks();
			return ret ? ret : -EINVAL;
		}
		configured_ = d;
	}
	active_ = d;
	++d->epoch_;
	d->paramsApplied_ = false;
	d->images_.clear(); d->histograms_.clear(); d->histogramOrder_.clear();
	ret = d->image_->importBuffers(d->stream_.configuration().bufferCount);
	if (ret)
		goto error;
	ret = d->params_->allocateBuffers(1, &d->paramsBuffers_);
	if (ret < 1) {
		ret = ret < 0 ? ret : -ENOMEM;
		goto error;
	}
	ret = d->stats_->allocateBuffers(4, &d->statsBuffers_);
	if (ret < 3) {
		ret = ret < 0 ? ret : -ENOMEM;
		goto error;
	}
	for (auto &buffer : d->paramsBuffers_) {
		auto mapped = std::make_unique<MappedFrameBuffer>(buffer.get(), MappedFrameBuffer::MapFlag::ReadWrite);
		if (!mapped->isValid()) { ret = mapped->error(); goto error; }
		size_t used;
		ret = ipa::camss::encodeParameters(mapped->planes()[0], d->profile_, red, blue,
						 d->input_, Rectangle(d->input_), &used);
		if (ret)
			goto error;
		auto &metadata = buffer->_d()->metadata();
		metadata.status = FrameMetadata::FrameSuccess;
		metadata.sequence = 0;
		metadata.timestamp = 0;
		metadata.planes()[0].bytesused = used;
		d->maps_[buffer.get()] = std::move(mapped);
		ret = d->params_->queueBuffer(buffer.get());
		if (ret)
			goto error;
	}
	for (auto &buffer : d->statsBuffers_) {
		auto mapped = std::make_unique<MappedFrameBuffer>(buffer.get(), MappedFrameBuffer::MapFlag::Read);
		if (!mapped->isValid()) { ret = mapped->error(); goto error; }
		d->maps_[buffer.get()] = std::move(mapped);
		ret = d->stats_->queueBuffer(buffer.get());
		if (ret)
			goto error;
	}
	ret = d->pix_->setFrameStartEnabled(true);
	if (ret)
		goto error;
	d->running_ = true;
	for (auto *dev : { d->stats_.get(), d->params_.get(), d->image_.get() }) {
		ret = dev->streamOn();
		if (ret)
			goto error;
	}
	return 0;
error:
	stopDevice(camera);
	return ret;
}

void CamssVfePipeline::stopDevice(Camera *camera)
{
	auto *d = data(camera);
	d->running_ = false;
	d->deadline_.stop();
	/* streamOff callbacks finish every queued application buffer once. */
	d->image_->streamOff();
	d->params_->streamOff();
	d->stats_->streamOff();
	d->pix_->setFrameStartEnabled(false);
	while (!d->images_.empty())
		d->finish(d->images_.begin()->first, false);
	d->histograms_.clear();
	d->histogramOrder_.clear();
	d->maps_.clear();
	d->params_->releaseBuffers(); d->stats_->releaseBuffers(); d->image_->releaseBuffers();
	d->paramsBuffers_.clear(); d->statsBuffers_.clear();
	d->paramsApplied_ = false;
	d->restoreLinks();
	if (active_ == d)
		active_ = nullptr;
	if (configured_ == d)
		configured_ = nullptr;
}

int CamssVfePipeline::queueRequestDevice(Camera *camera, Request *request)
{
	auto *d = data(camera);
	if (!request->controls().empty())
		return -EINVAL;
	FrameBuffer *buffer = request->findBuffer(&d->stream_);
	return buffer ? d->image_->queueBuffer(buffer) : -EINVAL;
}

void CamssVfeData::paramsReady(FrameBuffer *buffer)
{
	if (!running_ || buffer->metadata().status != FrameMetadata::FrameSuccess)
		return;
	paramsApplied_ = true;
	firstParamSof_ = buffer->_d()->kernelSequence();
	LOG(CamssVfe, Info) << "Parameters epoch=" << epoch_ << " first-sof=" << firstParamSof_;
}

void CamssVfeData::frameStart(uint32_t sequence)
{
	LOG(CamssVfe, Debug) << "SOF epoch=" << epoch_ << " sequence=" << sequence;
}

void CamssVfeData::imageReady(FrameBuffer *buffer)
{
	if (!running_ || buffer->metadata().status != FrameMetadata::FrameSuccess) {
		Request *request = buffer->request();
		handler()->completeBuffer(request, buffer);
		handler()->completeRequest(request);
		return;
	}
	const uint32_t sequence = buffer->_d()->kernelSequence();
	if (images_.count(sequence)) {
		LOG(CamssVfe, Error) << "Duplicate image SOF " << sequence;
		buffer->_d()->metadata().status = FrameMetadata::FrameError;
		Request *request = buffer->request();
		handler()->completeBuffer(request, buffer);
		handler()->completeRequest(request);
		return;
	}
	images_[sequence] = buffer;
	if (histograms_.count(sequence))
		finish(sequence, true);
	else if (!deadline_.isRunning())
		deadline_.start(std::chrono::milliseconds(250));
}

void CamssVfeData::statsReady(FrameBuffer *buffer)
{
	if (!running_)
		return;
	const uint32_t sequence = buffer->_d()->kernelSequence();
	const auto &memory = maps_.at(buffer)->planes()[0];
	constexpr size_t expected = sizeof(v4l2_isp_buffer) + sizeof(camss_stats_bhist);
	if (buffer->metadata().status == FrameMetadata::FrameSuccess &&
	    buffer->metadata().planes()[0].bytesused == expected && memory.size() >= expected) {
		v4l2_isp_buffer header;
		camss_stats_bhist histogram;
		std::memcpy(&header, memory.data(), sizeof(header));
		std::memcpy(&histogram, memory.data() + sizeof(header), sizeof(histogram));
		if (header.version == V4L2_ISP_VERSION_V1 && header.data_size == sizeof(histogram) &&
		    histogram.header.type == CAMSS_STATS_AEC_BHIST && !histogram.header.flags &&
		    histogram.header.size == sizeof(histogram)) {
			Histogram sample{};
			for (unsigned int i = 0; i < CAMSS_STATS_BHIST_BINS; ++i) {
				sample.population += histogram.bins[i];
				sample.weightedSum += uint64_t(i) * histogram.bins[i];
			}
			/* Exact ROI population is required before using any statistics. */
			if (sample.population == uint64_t(input_.width / 2) * (input_.height / 2) &&
			    std::find(histogramOrder_.begin(), histogramOrder_.end(), sequence) == histogramOrder_.end()) {
				histogramOrder_.push_back(sequence);
				histograms_[sequence] = sample;
				if (images_.count(sequence))
					finish(sequence, true);
			}
		}
	}
	while (histogramOrder_.size() > 32) {
		histograms_.erase(histogramOrder_.front());
		histogramOrder_.pop_front();
	}
	int ret = stats_->queueBuffer(buffer);
	if (ret)
		LOG(CamssVfe, Error) << "Requeue statistics failed: " << ret;
}

void CamssVfeData::finish(uint32_t sequence, bool paired)
{
	auto it = images_.find(sequence);
	if (it == images_.end())
		return;
	FrameBuffer *buffer = it->second;
	Request *request = buffer->request();
	images_.erase(it);
	if (paired) {
		const Histogram &h = histograms_.at(sequence);
		LOG(CamssVfe, Info) << "Pair epoch=" << epoch_ << " sof=" << sequence
			<< " request=" << request->sequence() << " population=" << h.population
			<< " mean=" << double(h.weightedSum) / h.population
			<< " parameters-acknowledged=" << paramsApplied_;
		histograms_.erase(sequence);
	} else {
		LOG(CamssVfe, Warning) << "Image without valid statistics epoch=" << epoch_ << " sof=" << sequence;
	}
	request->_d()->metadata().set(controls::SensorTimestamp, buffer->metadata().timestamp);
	handler()->completeBuffer(request, buffer);
	handler()->completeRequest(request);
	if (images_.empty())
		deadline_.stop();
}

void CamssVfeData::expired()
{
	/* Missing statistics never leave an application request stuck forever. */
	while (!images_.empty())
		finish(images_.begin()->first, false);
}

bool CamssVfePipeline::match(DeviceEnumerator *enumerator)
{
	/* Keep the installed RAW handler as the default while this backend is experimental. */
	const char *enabled = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_ENABLE");
	if (!enabled || std::strcmp(enabled, "1"))
		return false;
	DeviceMatch dm("qcom-camss");
	auto media = acquireMediaDevice(enumerator, dm);
	if (!media)
		return false;
	/* Group by the PIX subdevice's adjacent nodes and metadata FourCCs. */
	std::vector<CamssVfeData::Endpoint> endpoints;
	for (MediaEntity *entity : media->entities()) {
		if (entity->type() != MediaEntity::Type::V4L2Subdevice)
			continue;
		CamssVfeData::Endpoint endpoint{ nullptr, nullptr, nullptr, entity };
		for (const MediaPad *pad : entity->pads()) {
			for (MediaLink *link : pad->links()) {
				MediaEntity *other = link->source()->entity() == entity
					? link->sink()->entity() : link->source()->entity();
				if (other->type() != MediaEntity::Type::V4L2VideoDevice)
					continue;
				V4L2VideoDevice device(other);
				V4L2DeviceFormat format;
				if (device.open() || device.getFormat(&format))
					continue;
				if (format.fourcc == V4L2PixelFormat(V4L2_META_FMT_QCOM_ISP_PARAMS))
					endpoint.params = other;
				else if (format.fourcc == V4L2PixelFormat(V4L2_META_FMT_QCOM_ISP_STATS))
					endpoint.stats = other;
				else if (device.formats().count(V4L2PixelFormat(V4L2_PIX_FMT_NV12)))
					endpoint.image = other;
			}
		}
		if (endpoint.image && endpoint.params && endpoint.stats)
			endpoints.push_back(endpoint);
	}
	bool registered = false;
	for (MediaEntity *entity : media->entities()) {
		if (entity->function() != MEDIA_ENT_F_CAM_SENSOR)
			continue;
		for (const auto &endpoint : endpoints) {
			auto d = std::make_unique<CamssVfeData>(this, media);
			if (d->init(entity, endpoint))
				continue;
			std::set<Stream *> streams{ &d->stream_ };
			std::string id = d->sensor_->id();
			auto camera = Camera::create(std::move(d), id, streams);
			registerCamera(std::move(camera));
			registered = true;
			break;
		}
	}
	return registered;
}

REGISTER_PIPELINE_HANDLER(CamssVfePipeline, "camss-vfe")

} /* namespace libcamera */
