/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CAMSS hardware processing with optional zero-copy RAW capture. */

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <time.h>
#include "hardware_focus.h"
#include "libcamera/internal/camera_lens.h"
#include <cmath>
#include <cstring>
#include <deque>
#include <iomanip>
#include <map>
#include <queue>
#include <set>
#include <unordered_map>

#include <linux/media-bus-format.h>
#include <linux/videodev2.h>
#include <optional>
#include <limits>
#include <linux/qcom-camss-config.h>

#include <libcamera/base/log.h>
#include <libcamera/base/timer.h>
#include <libcamera/base/utils.h>
#include <libcamera/control_ids.h>
#include <libcamera/formats.h>

#include "libcamera/internal/bayer_format.h"
#include "libcamera/internal/camera.h"
#include "libcamera/internal/camera_sensor.h"
#include "libcamera/internal/device_enumerator.h"
#include "libcamera/internal/delayed_controls.h"
#include "libcamera/internal/framebuffer.h"
#include "libcamera/internal/media_device.h"
#include "libcamera/internal/pipeline_handler.h"
#include "libcamera/internal/request.h"
#include "libcamera/internal/v4l2_subdevice.h"
#include "libcamera/internal/v4l2_videodevice.h"

#include <libcamera/ipa/camss_ipa_proxy.h>

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
 StreamFormats streamFormats(bool raw);
	void submitStatistics();
	void completeMissingStatistics();
	void statsProcessed(uint64_t epoch, uint32_t sof, uint32_t id,
		const ipa::camss::Statistics &statistics, const ControlList &metadata);

 void imageReady(FrameBuffer *buffer);
 void rawReady(FrameBuffer *buffer);
 void pixFrameStart(uint32_t sequence, uint64_t timestamp);
 void rawFrameStart(uint32_t sequence, uint64_t timestamp);
 void tryComplete(Request *request, bool timeout = false);
 Request *imageRequest(FrameBuffer *buffer);
 struct PendingFrame {
  FrameBuffer *image = nullptr, *raw = nullptr;
  bool imageFinished = false, rawReady = false, failed = false;
 };
 std::map<Request *, PendingFrame> requests_;
 std::map<FrameBuffer *, Request *> internalRequests_;
 std::vector<std::unique_ptr<FrameBuffer>> internalImages_;
 std::queue<FrameBuffer *> freeImages_;
 std::map<uint32_t, uint64_t> pixStarts_, rawStarts_;
 uint64_t framePeriod_ = 0, previousPixStart_ = 0;
 bool rawEnabled_ = false, processedEnabled_ = true;
 Size output_;
 unsigned int outputStride_ = 0;
 V4L2DeviceFormat rawFormat_;

	void statsReady(FrameBuffer *buffer);
	void paramsReady(FrameBuffer *buffer);
	void queueIspUpdate(const ipa::camss::AutoIspUpdate &update);
	struct IspControls { ControlList controls; uint32_t source; };
	std::deque<IspControls> ispControls_;
	std::optional<int64_t> imageSequenceOffset_;
	void frameStart(uint32_t sequence);
	void expired();
	bool lensActive_=false;
	std::string lensModel_;
	void finish(uint32_t sequence, bool paired);
	CamssVfePipeline *handler();

	std::shared_ptr<MediaDevice> media_;
	std::unique_ptr<CameraSensor> sensor_;
	std::unique_ptr<V4L2VideoDevice> image_, params_, stats_, raw_;
	std::map<MediaEntity *, std::unique_ptr<V4L2Subdevice>> subdevs_;
	V4L2Subdevice *pix_ = nullptr, *rdi_ = nullptr;
	std::vector<MediaLink *> path_, rawPath_;
	std::vector<std::pair<MediaLink *, bool>> changedLinks_;
	Stream stream_, rawStream_;
	Size input_;
	V4L2SubdeviceFormat configuredFormat_;
	std::vector<std::unique_ptr<FrameBuffer>> paramsBuffers_, statsBuffers_;
	std::unique_ptr<ipa::camss::IPAProxyCamss> ipa_;
	bool ipaInitialized_ = false;
	std::string ipaProfilePath_;
	bool ipaMapped_ = false;
 ipa::camss::SensorControlConfiguration sensorConfiguration_{};
 ipa::camss::SensorContext startupSensor_{};
 std::unique_ptr<DelayedControls> delayedControls_;
 struct SensorUpdate { ControlList controls; uint32_t source; };
 std::deque<SensorUpdate> sensorUpdates_;
 std::map<uint32_t, ipa::camss::SensorContext> sensorContexts_;
 std::optional<uint32_t> lastSof_;
 bool sensorContextHealthy_ = false;
 bool automatic_ = false;
 uint32_t lastAutoRevision_ = 0;
 std::optional<ipa::camss::AutoSensorUpdate> automaticUpdate_;

	struct PendingStats { uint32_t sof; FrameBuffer *buffer; bool submitted; };
	std::map<uint32_t, PendingStats> pendingStats_;
	std::optional<uint32_t> newestStatsSof_;
	bool running_ = false;
	bool paramsApplied_ = false;
	bool parameterBusy_ = false, ispHealthy_ = true;
	uint32_t parameterRevision_ = 0, lastIspRevision_ = 0;
	uint32_t firstParamSof_ = 0;
	uint64_t epoch_ = 0;
	std::map<uint32_t, FrameBuffer *> images_;
	struct Histogram {
		uint64_t population;
		uint64_t weightedSum;
		ControlList metadata;
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
 bool raw_ = false, processed_ = false;
private:
	CamssVfeData *data_;
};

class CamssVfePipeline : public PipelineHandler
{
public:
	explicit CamssVfePipeline(CameraManager *manager) : PipelineHandler(manager, 4) {}
	bool match(DeviceEnumerator *enumerator) override;
	int initIPA(CamssVfeData *data);
	int configureIPA(CamssVfeData *data);
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

int CamssVfePipeline::initIPA(CamssVfeData *d)
{
 if (d->ipaInitialized_) return 0;
 IPACameraSensorInfo info;
 int ret = d->sensor_->sensorInfo(&info);
 if (ret) return ret;
 d->ipa_ = createIPA<ipa::camss::IPAProxyCamss>(0, 0);
 if (!d->ipa_) return -ENOENT;
 const std::string profile=d->ipa_->configurationFile(d->sensor_->model()+".yaml");
 CameraLens *lens=d->sensor_->focusLens();
 const ControlInfoMap lensControls=lens?lens->controls():ControlInfoMap{};
 ret = d->ipa_->init(IPASettings{ profile, d->sensor_->model() }, info, d->sensor_->controls(), lensControls, d->lensModel_, &d->controlInfo_);
 if (ret) { d->ipa_.reset(); return ret; }
 d->ipa_->statsProcessed.connect(d, &CamssVfeData::statsProcessed);
 d->ipaInitialized_ = true;
 return 0;
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
 if (CameraLens *lens=sensor_->focusLens()) {
  lensModel_=lens->model();lens->close();
 }
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
 MediaLink *pixInput = path_[path_.size() - 2];
 MediaEntity *csid = pixInput->source()->entity();
 /* Shared input lifetime is handled by the matched CAMSS driver. This
  * single-VC path needs no userspace routing API; the V4L2 core may hide
  * CAP_STREAMS even when the driver's internal streams ops are active. */
 for (const MediaPad *pad : csid->pads()) {
  if (!(pad->flags() & MEDIA_PAD_FL_SOURCE) || raw_) continue;
  for (MediaLink *input : pad->links()) {
   MediaEntity *entity = input->sink()->entity();
   if (entity == endpoint.pix || entity->type() != MediaEntity::Type::V4L2Subdevice) continue;
   for (const MediaPad *output : entity->pads()) {
    if (!(output->flags() & MEDIA_PAD_FL_SOURCE)) continue;
    for (MediaLink *link : output->links()) {
     MediaEntity *video = link->sink()->entity();
     if (video->type() != MediaEntity::Type::V4L2VideoDevice) continue;
     auto device = std::make_unique<V4L2VideoDevice>(video);
     if (device->open() || !device->formats().count(V4L2PixelFormat(V4L2_PIX_FMT_SRGGB10P))) continue;
     auto subdev = std::make_unique<V4L2Subdevice>(entity);
     if (subdev->open() || !subdev->supportsFrameStartEvent()) continue;
     rawPath_ = {input, link};
     rdi_ = subdev.get();subdevs_[entity] = std::move(subdev);
     raw_ = std::move(device);
     break;
    }
    if (raw_) break;
   }
   if (raw_) break;
  }
 }
 if (raw_) {
  raw_->bufferReady.connect(this, &CamssVfeData::rawReady);
  rdi_->frameStartTimestamp.connect(this, &CamssVfeData::rawFrameStart);
 }

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
	pix_->frameStartTimestamp.connect(this, &CamssVfeData::pixFrameStart);
	properties_ = sensor_->properties();
	return handler()->initIPA(this);
}

int CamssVfePipeline::configureIPA(CamssVfeData *d)
{
 int ret = initIPA(d);
 if (ret) return ret;
 IPACameraSensorInfo info;
 ret = d->sensor_->sensorInfo(&info);
 if (ret) return ret;
 return d->ipa_->configure(info, d->input_, d->sensor_->controls(), d->ipaProfilePath_,
                          &d->controlInfo_, &d->sensorConfiguration_);
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

 std::vector<MediaLink *> routes = path_;
 if (rawEnabled_) routes.insert(routes.end(), rawPath_.begin(), rawPath_.end());
 /* Exclusive camera: deactivate competing routes touching the selected paths. */
	std::set<MediaEntity *> used;
	for (MediaLink *link : routes) {
		used.insert(link->source()->entity());
		used.insert(link->sink()->entity());
	}
	for (MediaEntity *entity : used) {
		for (const MediaPad *pad : entity->pads()) {
			for (MediaLink *link : pad->links()) {
				if (link->flags() & MEDIA_LNK_FL_IMMUTABLE ||
				    std::find(routes.begin(), routes.end(), link) != routes.end())
					continue;
				int ret = change(link, false);
				if (ret)
					return ret;
			}
		}
	}
	for (MediaLink *link : routes) {
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

 if (rawEnabled_) {
  MediaLink *link = rawPath_.front();
  ret = subdevs_.at(link->source()->entity())->getFormat(link->source()->index(), &format);
  if (!ret) ret = rdi_->setFormat(link->sink()->index(), &format);
  if (ret || format.size != requested.size) return ret ? ret : -EINVAL;
 }
 Rectangle compose(output);
	ret = pix_->setSelection(0, V4L2_SEL_TGT_COMPOSE, &compose);
	if (ret || compose != Rectangle(output))
		return ret ? ret : -EINVAL;
	return 0;
}


StreamFormats CamssVfeData::streamFormats(bool raw)
{
 std::map<PixelFormat,std::vector<SizeRange>> formats;
 const auto video=image_->formats();
 auto nv12=video.find(V4L2PixelFormat(V4L2_PIX_FMT_NV12));
 for (unsigned int code:sensor_->mbusCodes()) {
  BayerFormat bayer=BayerFormat::fromMbusCode(code);
  if (!bayer.isValid() || bayer.bitDepth!=10) continue;
  bayer.packing=BayerFormat::Packing::CSI2;
  for (const Size &size:sensor_->sizes(code)) {
   if (raw) {formats[bayer.toPixelFormat()].emplace_back(size);continue;}
   if (nv12==video.end()) continue;
   V4L2SubdeviceFormat trial{code,size,{}};
   if (pix_->setFormat(0,&trial,V4L2Subdevice::TryFormat)) continue;
   for (const SizeRange &range:nv12->second) {
    Rectangle minimum(range.min),maximum(range.max);
    if (pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&minimum,V4L2Subdevice::TryFormat) ||
        pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&maximum,V4L2Subdevice::TryFormat)) continue;
    formats[libcamera::formats::NV12].emplace_back(minimum.size(),maximum.size(),range.hStep,range.vStep);
   }
  }
 }
 if (!raw) {
  auto &ranges=formats[libcamera::formats::NV12];
  if (ranges.size()>1) {
   /* StreamFormats accepts one continuous range per pixel format. Publish
    * advisory bounds across sensor modes; validate() still asks the selected
    * mode's TRY compose for the exact scaling/alignment constraints. */
   SizeRange bounds=ranges.front();
   for (const SizeRange &range:ranges) {
    bounds.min.width=std::min(bounds.min.width,range.min.width);
    bounds.min.height=std::min(bounds.min.height,range.min.height);
    bounds.max.width=std::max(bounds.max.width,range.max.width);
    bounds.max.height=std::max(bounds.max.height,range.max.height);
   }
   ranges={bounds};
  }
 }
 return StreamFormats(formats);
}

CameraConfiguration::Status CamssVfeConfiguration::validate()
{
 if (config_.empty() || config_.size() > 2) return Invalid;
 Status status = Valid;
 raw_ = processed_ = false;
 Size desired;
 for (auto &cfg : config_) {
  bool raw = BayerFormat::fromPixelFormat(cfg.pixelFormat).isValid();
  if (raw ? (raw_ || !data_->raw_) : processed_) return Invalid;
  if (raw) { raw_ = true; desired = cfg.size; }
  else { processed_ = true; if (desired.isNull()) desired = cfg.size; }
 }
 if (orientation != data_->sensor_->mountingOrientation()) {
  orientation = data_->sensor_->mountingOrientation(); status = Adjusted;
 }
 const std::array<unsigned int, 4> codes{MEDIA_BUS_FMT_SRGGB10_1X10,
  MEDIA_BUS_FMT_SGRBG10_1X10, MEDIA_BUS_FMT_SGBRG10_1X10, MEDIA_BUS_FMT_SBGGR10_1X10};
 if (sensorConfig && (!sensorConfig->isValid() || sensorConfig->bitDepth != 10)) return Invalid;
 sensorFormat_ = data_->sensor_->getFormat(codes, sensorConfig ? sensorConfig->outputSize : desired);
 if (sensorConfig && sensorFormat_.size != sensorConfig->outputSize) return Invalid;
 if (!sensorFormat_.code || sensorFormat_.size.width > 8192 || sensorFormat_.size.height > 16384) return Invalid;
 BayerFormat bayer = BayerFormat::fromMbusCode(sensorFormat_.code);
 bayer.packing = BayerFormat::Packing::CSI2;
 for (auto &cfg : config_) {
  const bool raw = BayerFormat::fromPixelFormat(cfg.pixelFormat).isValid();
  const PixelFormat pixel = raw ? bayer.toPixelFormat() : formats::NV12;
  Size size = sensorFormat_.size;
  if (!raw) {
   V4L2SubdeviceFormat trial = sensorFormat_;
   if (data_->pix_->setFormat(0,&trial,V4L2Subdevice::TryFormat)) return Invalid;
   Rectangle compose(cfg.size);
   if (data_->pix_->setSelection(0,V4L2_SEL_TGT_COMPOSE,&compose,V4L2Subdevice::TryFormat)) return Invalid;
   size=compose.size();
  }
  if (cfg.pixelFormat != pixel || cfg.size != size) status = Adjusted;
  cfg.pixelFormat = pixel; cfg.size = size;
  V4L2DeviceFormat format;
  format.fourcc = raw ? bayer.toV4L2PixelFormat() : V4L2PixelFormat(V4L2_PIX_FMT_NV12);
  format.size = size;
  if ((raw ? data_->raw_ : data_->image_)->tryFormat(&format) || format.size != size) return Invalid;
  cfg.stride = format.planes[0].bpl; cfg.frameSize = 0;
  for (unsigned int i=0;i<format.planesCount;++i) cfg.frameSize += format.planes[i].size;
  if (cfg.bufferCount != 4) {cfg.bufferCount=4;status=Adjusted;}
  cfg.colorSpace = raw ? ColorSpace::Raw : ColorSpace::Sycc;
 }
 return status;
}

std::unique_ptr<CameraConfiguration> CamssVfePipeline::generateConfiguration(
 Camera *camera, Span<const StreamRole> roles)
{
 auto *d = data(camera);
 auto config = std::make_unique<CamssVfeConfiguration>(d);
 if (roles.size() > 2) return nullptr;
 for (StreamRole role : roles) {
  StreamConfiguration cfg(d->streamFormats(role==StreamRole::Raw));
  if (role == StreamRole::Raw) {
   if (!d->raw_) return nullptr;
   cfg.pixelFormat = formats::SRGGB10_CSI2P;
   cfg.size = d->sensor_->resolution();
  } else {cfg.pixelFormat=formats::NV12;cfg.size=Size(640,480);}
  config->addConfiguration(cfg);
 }
 if (!roles.empty() && config->validate() == CameraConfiguration::Invalid) return nullptr;
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

 d->rawEnabled_ = cfg->raw_;d->processedEnabled_ = cfg->processed_;
 d->output_ = Size(640,480);
 for (auto &stream : *cfg) if (stream.pixelFormat == formats::NV12) d->output_ = stream.size;
 int ret = d->configurePath(cfg->sensorFormat_, d->output_);
	if (ret) {
		d->restoreLinks();
		return ret;
	}
	V4L2DeviceFormat format;
	format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
	format.size = d->output_;
	ret = d->image_->setFormat(&format);
	if (ret || format.size != d->output_ || format.fourcc != V4L2PixelFormat(V4L2_PIX_FMT_NV12)) {
		d->restoreLinks();
		return ret ? ret : -EINVAL;
	}
 d->outputStride_=format.planes[0].bpl;
 ret = initIPA(d);
 if (ret) { d->restoreLinks(); return ret; }
 const char *profile = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
 d->ipaProfilePath_ = profile ? profile : d->ipa_->configurationFile(d->sensor_->model()+".yaml");
 ret = configureIPA(d);
 if (ret) { d->restoreLinks(); return ret; }

 for (auto &stream : *cfg) {
  if (stream.pixelFormat == formats::NV12) stream.setStream(&d->stream_);
  else {
   d->rawFormat_ = {};
   d->rawFormat_.fourcc = BayerFormat::fromPixelFormat(stream.pixelFormat).toV4L2PixelFormat();
   d->rawFormat_.size = stream.size;
   ret = d->raw_->setFormat(&d->rawFormat_);
   if (ret || d->rawFormat_.size != stream.size) {d->restoreLinks();return ret ? ret : -EINVAL;}
   stream.setStream(&d->rawStream_);
  }
 }
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
	auto *d = data(camera);
	d->ipa_.reset();
	d->ipaInitialized_ = false;
	d->ipaProfilePath_.clear();
	d->configuredFormat_.code = 0;
}

int CamssVfePipeline::exportFrameBuffers(Camera *camera, Stream *stream,
	std::vector<std::unique_ptr<FrameBuffer>> *buffers)
{
	
 auto *d = data(camera);
 return (stream == &d->rawStream_ ? d->raw_ : d->image_)->exportBuffers(stream->configuration().bufferCount, buffers);
}

int CamssVfePipeline::start(Camera *camera, const ControlList *controls)
{
 auto *d = data(camera);
 if (active_) return -EBUSY;
 if (!d->configuredFormat_.code) return -EPIPE;
 int ret;
 if (configured_ != d) {
  if (configured_) configured_->restoreLinks();
  configured_ = nullptr;
  ret = d->configurePath(d->configuredFormat_, d->output_);
  V4L2DeviceFormat format;
  format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
  format.size = d->output_;
  if (!ret) ret = d->image_->setFormat(&format);
  if (ret || format.size != d->output_) {
   d->restoreLinks(); return ret ? ret : -EINVAL;
  }

  if (d->rawEnabled_) {ret=d->raw_->setFormat(&d->rawFormat_);if(ret){d->restoreLinks();return ret;}}
  configured_ = d;
 }
 active_ = d;
 ++d->epoch_;
 d->paramsApplied_ = false;
 d->images_.clear(); d->histograms_.clear(); d->histogramOrder_.clear(); d->pendingStats_.clear();
 ret = configureIPA(d);
 if (ret) goto error;

 d->requests_.clear();d->internalRequests_.clear();d->pixStarts_.clear();d->rawStarts_.clear();
 d->framePeriod_=d->previousPixStart_=0;
 if (d->processedEnabled_) ret=d->image_->importBuffers(d->stream_.configuration().bufferCount);
 else {
  ret=d->image_->allocateBuffers(4,&d->internalImages_);
  if (ret >= 4) {for(auto &buffer:d->internalImages_) d->freeImages_.push(buffer.get());ret=0;}
  else ret=ret<0?ret:-ENOMEM;
 }
 if (ret) goto error;
 if (d->rawEnabled_) {ret=d->raw_->importBuffers(d->rawStream_.configuration().bufferCount);if(ret)goto error;}
 ret = d->params_->allocateBuffers(1, &d->paramsBuffers_);
 if (ret < 1) { ret = ret < 0 ? ret : -ENOMEM; goto error; }
 ret = d->stats_->allocateBuffers(4, &d->statsBuffers_);
 if (ret < 3) { ret = ret < 0 ? ret : -ENOMEM; goto error; }
 {
  std::vector<IPABuffer> parameters, statistics;
  auto append = [](FrameBuffer *buffer, uint32_t id, std::vector<IPABuffer> &buffers) {
   buffer->setCookie(id);
   auto planes = buffer->planes();
   buffers.emplace_back(id, std::vector<FrameBuffer::Plane>(planes.begin(), planes.end()));
  };
  append(d->paramsBuffers_[0].get(), 1, parameters);
  uint32_t id = 100;
  for (auto &buffer : d->statsBuffers_) append(buffer.get(), id++, statistics);
  ret = d->ipa_->mapBuffers(parameters, statistics);
  if (ret) goto error;
  d->ipaMapped_ = true;
  ControlList empty(libcamera::controls::controls);
  ControlList initial(d->sensor_->controls());
  ret = d->ipa_->start(d->epoch_, controls ? *controls : empty, &initial);
  if (ret) goto error;
  d->automatic_ = (controls ? controls->get(libcamera::controls::ExposureTimeMode) : std::nullopt).value_or(d->controlInfo_.at(&libcamera::controls::ExposureTimeMode).def().get<int32_t>()) == libcamera::controls::ExposureTimeModeAuto;
  d->lastAutoRevision_ = 0; d->automaticUpdate_.reset();
  if (!initial.empty()) {
   ret = d->sensor_->setControls(&initial);
   if (ret) goto error;
  }
  const std::array<uint32_t, 2> ids{ V4L2_CID_EXPOSURE, V4L2_CID_ANALOGUE_GAIN };
  ControlList actual = d->sensor_->getControls(ids);
  if (!actual.contains(V4L2_CID_EXPOSURE) || !actual.contains(V4L2_CID_ANALOGUE_GAIN)) { ret = -EIO; goto error; }
  d->startupSensor_ = { true, uint32_t(actual.get(V4L2_CID_EXPOSURE).get<int32_t>()),
   uint32_t(actual.get(V4L2_CID_ANALOGUE_GAIN).get<int32_t>()), std::numeric_limits<uint32_t>::max() };
  d->sensorUpdates_.clear(); d->sensorContexts_.clear(); d->lastSof_.reset(); d->sensorContextHealthy_ = true;
  if (d->sensorConfiguration_.enabled) {
   const std::unordered_map<uint32_t, DelayedControls::ControlParams> delays{
    { V4L2_CID_EXPOSURE, { d->sensorConfiguration_.exposureDelay, false } },
    { V4L2_CID_ANALOGUE_GAIN, { d->sensorConfiguration_.gainDelay, false } }
   };
   d->delayedControls_ = std::make_unique<DelayedControls>(d->sensor_->device(), delays);
   d->delayedControls_->reset(std::numeric_limits<uint32_t>::max());
  } else d->delayedControls_.reset();
 }
 d->parameterBusy_ = false; d->ispHealthy_ = true;
 d->parameterRevision_ = d->lastIspRevision_ = 0;
 d->ispControls_.clear();
 d->newestStatsSof_.reset();
 d->imageSequenceOffset_.reset();
 for (auto &buffer : d->paramsBuffers_) {
  uint32_t used = 0;
  ret = d->ipa_->prepareParameters(d->epoch_, buffer->cookie(), 0, &used);
  if (ret) goto error;
  auto &metadata = buffer->_d()->metadata();
  metadata.status = FrameMetadata::FrameSuccess; metadata.sequence = 0; metadata.timestamp = 0;
  metadata.planes()[0].bytesused = used;
  ret = d->params_->queueBuffer(buffer.get());
  if (ret) goto error;
  d->parameterBusy_ = true;
 }
 for (auto &buffer : d->statsBuffers_) {
  ret = d->stats_->queueBuffer(buffer.get());
  if (ret) goto error;
 }
 ret = d->pix_->setFrameStartEnabled(true);
 if (ret) goto error;

 if (d->rawEnabled_) {ret=d->rdi_->setFrameStartEnabled(true);if(ret)goto error;}
 if (d->controlInfo_.find(&controls::AfMode)!=d->controlInfo_.end()) {
  CameraLens *lens=d->sensor_->focusLens();
  if (!lens) {ret=-ENODEV;goto error;}
  ret=lens->open();if (ret) goto error;d->lensActive_=true;
 }
 d->running_ = true;
 for (auto *device : { d->stats_.get(), d->params_.get(), d->image_.get() }) {
  ret = device->streamOn();
  if (ret) goto error;
 }

 if (d->rawEnabled_) {ret=d->raw_->streamOn();if(ret)goto error;}
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
	d->sensorContextHealthy_ = false;
	d->sensorUpdates_.clear();
 d->automaticUpdate_.reset(); d->automatic_ = false;
	/* streamOff callbacks finish every queued application buffer once. */
	if (d->rawEnabled_) d->raw_->streamOff();
	d->image_->streamOff();
	d->params_->streamOff();
	d->stats_->streamOff();
	d->pix_->setFrameStartEnabled(false);
 if (d->rawEnabled_) d->rdi_->setFrameStartEnabled(false);
	while (!d->images_.empty())
		d->finish(d->images_.begin()->first, false);

 /* All queues are stopped, including any partially queued request. */
 while (!d->requests_.empty()) {
  auto it=d->requests_.begin();
  it->second.imageFinished=true;it->second.rawReady=true;it->second.failed=true;
  d->tryComplete(it->first,true);
 }
 d->histograms_.clear();
 d->histogramOrder_.clear();
	if (d->ipa_) {
		d->ipa_->stop();
		if (d->ipaMapped_) {
			std::vector<uint32_t> ids;
			for (auto &buffer : d->paramsBuffers_) ids.push_back(buffer->cookie());
			for (auto &buffer : d->statsBuffers_) ids.push_back(buffer->cookie());
			d->ipa_->unmapBuffers(ids);
		}
	}
	d->lensActive_=false;
 if (CameraLens *lens=d->sensor_->focusLens()) lens->close();
	d->ipaMapped_ = false;
	d->pendingStats_.clear();
	d->params_->releaseBuffers(); d->stats_->releaseBuffers(); d->image_->releaseBuffers();

 if (d->rawEnabled_) d->raw_->releaseBuffers();
 d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();
 d->pixStarts_.clear();d->rawStarts_.clear();
 d->paramsBuffers_.clear(); d->statsBuffers_.clear();
	d->paramsApplied_ = false;
	d->delayedControls_.reset(); d->sensorContexts_.clear(); d->lastSof_.reset(); d->ispControls_.clear();
	d->restoreLinks();
	if (active_ == d)
		active_ = nullptr;
	if (configured_ == d)
		configured_ = nullptr;
}

int CamssVfePipeline::queueRequestDevice(Camera *camera, Request *request)
{
 auto *d = data(camera);
 FrameBuffer *buffer = request->findBuffer(&d->stream_);

 FrameBuffer *raw = request->findBuffer(&d->rawStream_);
 if ((d->processedEnabled_ && !buffer) || (d->rawEnabled_ && !raw)) return -EINVAL;
 if (!buffer) {if(d->freeImages_.empty())return -ENOBUFS;buffer=d->freeImages_.front();}
 ControlList sensorControls(d->sensor_->controls());
 if (!request->controls().empty()) {
  int ret = d->ipa_->convertControls(d->epoch_, request->controls(), &sensorControls);
  if (ret) return ret;
 }
 const bool isp = request->controls().contains(controls::AwbEnable.id()) || request->controls().contains(controls::ColourGains.id()) || request->controls().contains(controls::ColourTemperature.id()) || request->controls().contains(controls::ColourCorrectionMatrix.id());
 if (isp && !d->ispHealthy_) return -EPIPE;
 if (!sensorControls.empty() && (!d->delayedControls_ || !d->sensorContextHealthy_)) return -ENOTSUP;
 if ((!sensorControls.empty() && d->sensorUpdates_.size() >= 8) || (isp && d->ispControls_.size() >= 8)) return -ENOSPC;

 d->requests_.emplace(request,CamssVfeData::PendingFrame{buffer,raw,false,!raw,false});
 if (!d->processedEnabled_) {d->freeImages_.pop();d->internalRequests_[buffer]=request;}
 int ret = d->image_->queueBuffer(buffer);
 if (ret) {
  d->requests_.erase(request);
  if(!d->processedEnabled_){d->internalRequests_.erase(buffer);d->freeImages_.push(buffer);}
  return ret;
 }
 if (raw) {
  ret=d->raw_->queueBuffer(raw);
  if(ret){auto &frame=d->requests_.at(request);frame.rawReady=true;frame.failed=true;
   LOG(CamssVfe,Error)<<"RAW queue failed after PIX accepted request: "<<ret;}
 }
 {
  if (!sensorControls.empty()) d->sensorUpdates_.push_back({ std::move(sensorControls), request->sequence() });
  if (isp) { d->ispControls_.push_back({ request->controls(), request->sequence() }); d->submitStatistics(); }
 }
 return 0;
}


Request *CamssVfeData::imageRequest(FrameBuffer *buffer)
{
 auto it=internalRequests_.find(buffer);
 return it==internalRequests_.end()?buffer->request():it->second;
}

void CamssVfeData::pixFrameStart(uint32_t sequence,uint64_t timestamp)
{
 if(!running_)return;
 if(previousPixStart_ && timestamp>previousPixStart_)framePeriod_=timestamp-previousPixStart_;
 previousPixStart_=timestamp;
 pixStarts_[sequence]=timestamp;
 while(pixStarts_.size()>128)pixStarts_.erase(pixStarts_.begin());
 frameStart(sequence);
 std::vector<Request *> pending;
 for(const auto &[request,frame]:requests_)if(frame.imageFinished && frame.rawReady)pending.push_back(request);
 for(Request *request:pending)tryComplete(request);
}

void CamssVfeData::rawFrameStart(uint32_t sequence,uint64_t timestamp)
{
 if(!running_)return;
 rawStarts_[sequence]=timestamp;
 while(rawStarts_.size()>128)rawStarts_.erase(rawStarts_.begin());
 std::vector<Request *> pending;
 for(const auto &[request,frame]:requests_)if(frame.imageFinished && frame.rawReady)pending.push_back(request);
 for(Request *request:pending)tryComplete(request);
}

void CamssVfeData::rawReady(FrameBuffer *buffer)
{
 Request *request=buffer->request();
 auto it=requests_.find(request);
 if(it==requests_.end())return;
 it->second.rawReady=true;
 it->second.failed |= buffer->metadata().status!=FrameMetadata::FrameSuccess;
 tryComplete(request);
}

void CamssVfeData::tryComplete(Request *request,bool timeout)
{
 auto it=requests_.find(request);
 if(it==requests_.end())return;
 PendingFrame &frame=it->second;
 if(!frame.imageFinished || !frame.rawReady)return;
 if(rawEnabled_ && !frame.failed && running_) {
  const uint32_t imageSof=frame.image->_d()->kernelSequence(),rawSof=frame.raw->_d()->kernelSequence();
  auto pix=pixStarts_.find(imageSof),raw=rawStarts_.find(rawSof);
  if(pix==pixStarts_.end() || raw==rawStarts_.end()) {
   if(!timeout){if(!deadline_.isRunning())deadline_.start(std::chrono::milliseconds(250));return;}
   frame.failed=true;
   LOG(CamssVfe,Warning)<<"Frame sync event missing request="<<request->sequence();
  } else {
   uint64_t delta=pix->second>raw->second?pix->second-raw->second:raw->second-pix->second;
   const uint64_t tolerance=framePeriod_?std::min<uint64_t>(1000000,framePeriod_/8):1000000;
   frame.failed=delta>tolerance;
   LOG(CamssVfe,Info)<<"RawPair request="<<request->sequence()<<" pix-sof="<<imageSof<<" raw-sof="<<rawSof
    <<" pix-start="<<pix->second<<" raw-start="<<raw->second<<" delta-ns="<<delta
    <<" tolerance-ns="<<tolerance<<" matched="<<!frame.failed;
  }
 }
 if(timeout || !running_)frame.failed=true;
 FrameBuffer *image=frame.image,*raw=frame.raw;
 if(frame.failed){image->_d()->metadata().status=FrameMetadata::FrameError;if(raw)raw->_d()->metadata().status=FrameMetadata::FrameError;}
 requests_.erase(it);
 if(processedEnabled_)handler()->completeBuffer(request,image);
 else {internalRequests_.erase(image);freeImages_.push(image);}
 if(raw)handler()->completeBuffer(request,raw);
 handler()->completeRequest(request);
 if(images_.empty() && requests_.empty())deadline_.stop();
}

void CamssVfeData::paramsReady(FrameBuffer *buffer)
{
	if (!running_) return;
	parameterBusy_ = false;
	if (buffer->metadata().status != FrameMetadata::FrameSuccess) {
		ispHealthy_ = false;
		LOG(CamssVfe, Error) << "ISP parameter buffer failed";
		return;
	}
	paramsApplied_ = true;
	firstParamSof_ = buffer->_d()->kernelSequence();
	ipa_->parametersApplied(epoch_, firstParamSof_, parameterRevision_);
	completeMissingStatistics();
	submitStatistics();
	LOG(CamssVfe, Info) << "Parameters epoch=" << epoch_ << " first-sof=" << firstParamSof_ << " revision=" << parameterRevision_;
}

void CamssVfeData::queueIspUpdate(const ipa::camss::AutoIspUpdate &update)
{
	if (!running_ || !ispHealthy_ || !update.valid) return;
	if (parameterBusy_ || update.revision != lastIspRevision_ + 1 ||
	    !std::isfinite(update.red) || !std::isfinite(update.blue) ||
	    update.red < 0 || update.red > 8 || update.blue < 0 || update.blue > 8) {
		ispHealthy_ = false;
		LOG(CamssVfe, Error) << "Rejected ISP gain proposal";
		return;
	}
	FrameBuffer *buffer = paramsBuffers_[0].get();
	parameterBusy_ = true;
	uint32_t used = 0;
	int ret = ipa_->prepareParameters(epoch_, buffer->cookie(), update.revision, &used);
	if (!ret) {
		auto &metadata = buffer->_d()->metadata();
		metadata.status = FrameMetadata::FrameSuccess;
		metadata.planes()[0].bytesused = used;
		ret = params_->queueBuffer(buffer);
	}
	if (ret) {
		parameterBusy_ = false; ispHealthy_ = false;
		LOG(CamssVfe, Error) << "ISP parameter queue failed: " << ret;
		return;
	}
	parameterRevision_ = lastIspRevision_ = update.revision;
	LOG(CamssVfe, Info) << "WB queue epoch=" << epoch_ << " revision=" << update.revision
		<< " red=" << std::setprecision(17) << update.red << " blue=" << update.blue << " precision=17";
}

void CamssVfeData::frameStart(uint32_t sequence)
{
 if (!running_) return;
 LOG(CamssVfe, Debug) << "SOF epoch=" << epoch_ << " sequence=" << sequence;
 if ((!lastSof_ && sequence != 0) || (lastSof_ && sequence != *lastSof_ + 1) ||
     sequence >= uint32_t(std::numeric_limits<int32_t>::max() - 4)) {
  LOG(CamssVfe, Error) << "Sensor context lost SOF continuity at " << sequence;
  sensorContextHealthy_ = false;
 }
 lastSof_ = sequence;
 ipa::camss::SensorContext context = startupSensor_;
 if (delayedControls_ && sensorContextHealthy_) {
  ControlList update(sensor_->controls());
  std::optional<uint32_t> source;
  if (automatic_ && automaticUpdate_) {
   update.set(V4L2_CID_EXPOSURE, int32_t(automaticUpdate_->exposureLines));
   update.set(V4L2_CID_ANALOGUE_GAIN, int32_t(automaticUpdate_->gainCode));
   source = automaticUpdate_->revision;
   automaticUpdate_.reset();
  } else if (!sensorUpdates_.empty()) {
   update = sensorUpdates_.front().controls;
   source = sensorUpdates_.front().source;
   sensorUpdates_.pop_front();
  }
  if (!delayedControls_->push(update, source)) sensorContextHealthy_ = false;
  if (sensorContextHealthy_) {
   delayedControls_->applyControls(sequence);
   uint32_t delay = std::max(sensorConfiguration_.exposureDelay, sensorConfiguration_.gainDelay);
   ControlList expected = delayedControls_->get(sequence + delay);
   const std::array<uint32_t, 2> ids{ V4L2_CID_EXPOSURE, V4L2_CID_ANALOGUE_GAIN };
   ControlList actual = sensor_->getControls(ids);
   for (uint32_t id : ids)
    if (!actual.contains(id) || !expected.contains(id) || actual.get(id) != expected.get(id)) sensorContextHealthy_ = false;
   uint32_t cookie;
   ControlList effective = delayedControls_->get(sequence, &cookie);
   if (!effective.contains(V4L2_CID_EXPOSURE) || !effective.contains(V4L2_CID_ANALOGUE_GAIN)) sensorContextHealthy_ = false;
   else context = { sensorContextHealthy_, uint32_t(effective.get(V4L2_CID_EXPOSURE).get<int32_t>()),
    uint32_t(effective.get(V4L2_CID_ANALOGUE_GAIN).get<int32_t>()), cookie };
  }
 }
 context.valid = sensorContextHealthy_;
 sensorContexts_[sequence] = context;
 while (sensorContexts_.size() > 64) sensorContexts_.erase(sensorContexts_.begin());
 LOG(CamssVfe, Info) << "SensorContext epoch=" << epoch_ << " sof=" << sequence << " valid=" << context.valid
  << " exposure-lines=" << context.exposureLines << " gain-code=" << context.gainCode << " source=" << context.source;
 submitStatistics();
}


void CamssVfeData::imageReady(FrameBuffer *buffer)
{
 Request *request=imageRequest(buffer);
 if(!request || !requests_.count(request)) return;
	if (!running_ || buffer->metadata().status != FrameMetadata::FrameSuccess) {

  auto &frame=requests_.at(request);frame.imageFinished=true;frame.failed=true;
  tryComplete(request);
  return;
	}
	const uint32_t sequence = buffer->_d()->kernelSequence();
	const int64_t offset = int64_t(sequence) - request->sequence();
	if (imageSequenceOffset_ && *imageSequenceOffset_ != offset) {
		LOG(CamssVfe, Info) << "Resynced image/request mapping old=" << *imageSequenceOffset_ << " new=" << offset;
	}
	// A missing image buffer does not invalidate the ISP parameter queue.
	// Pending request controls use the refreshed mapping when they are submitted.
	imageSequenceOffset_ = offset;
	if (images_.count(sequence)) {
		LOG(CamssVfe, Error) << "Duplicate image SOF " << sequence;
		buffer->_d()->metadata().status = FrameMetadata::FrameError;

  auto &frame=requests_.at(request);frame.imageFinished=true;frame.failed=true;
  tryComplete(request);
  return;
	}
	images_[sequence] = buffer;
	if (histograms_.count(sequence))
		finish(sequence, true);
	else {
		completeMissingStatistics();
		if (images_.count(sequence) && !deadline_.isRunning()) deadline_.start(std::chrono::milliseconds(250));
	}
}

void CamssVfeData::statsReady(FrameBuffer *buffer)
{
 if (!running_) return;
 if (buffer->metadata().status != FrameMetadata::FrameSuccess) {
  int ret = stats_->queueBuffer(buffer);
  if (ret) LOG(CamssVfe, Error) << "Requeue error statistics failed: " << ret;
  return;
 }
 uint32_t id = buffer->cookie();
 if (pendingStats_.count(id)) {
  LOG(CamssVfe, Error) << "Duplicate outstanding statistics buffer " << id;
  return;
 }
 pendingStats_.emplace(id, PendingStats{ buffer->_d()->kernelSequence(), buffer, false });
 newestStatsSof_=std::max(newestStatsSof_.value_or(0),buffer->_d()->kernelSequence());
 completeMissingStatistics();
 submitStatistics();
}

void CamssVfeData::completeMissingStatistics()
{
 if (!running_ || !paramsApplied_ || parameterBusy_ || !newestStatsSof_) return;
 std::vector<uint32_t> missing;
 for (const auto &[sequence,buffer]:images_) {
  (void)buffer;
  if (sequence>=*newestStatsSof_ || histograms_.count(sequence)) continue;
  const bool pending=std::any_of(pendingStats_.begin(),pendingStats_.end(),
   [sequence](const auto &entry){return entry.second.sof==sequence;});
  if (!pending) missing.push_back(sequence);
 }
 // Ordered stats buffers have moved past these images; do not wait for a missing packet.
 for (uint32_t sequence:missing) finish(sequence,false);
}

void CamssVfeData::submitStatistics()
{
 if (!running_ || !paramsApplied_ || parameterBusy_) return;
 while (!ispControls_.empty()) {
  // Parameters latch at the following SOF. Do not change an earlier request's image.
  if (!imageSequenceOffset_ || !lastSof_ ||
      int64_t(*lastSof_) + 1 < int64_t(ispControls_.front().source) + *imageSequenceOffset_) break;
  if (std::any_of(pendingStats_.begin(), pendingStats_.end(), [](const auto &entry) { return entry.second.submitted; })) return;
  auto &request = ispControls_.front();
  ipa::camss::AutoIspUpdate update{};
  int ret = ipa_->applyIspControls(epoch_, request.controls, &update);
  if (ret == -EAGAIN) return;
  if (ret) { ispHealthy_=false; LOG(CamssVfe, Error) << "Runtime WB control failed: " << ret; return; }
  LOG(CamssVfe, Info) << "WB request epoch=" << epoch_ << " source=" << request.source << " revision=" << update.revision
   << " awb=" << (request.controls.contains(controls::AwbEnable.id()) ? int(*request.controls.get(controls::AwbEnable)) : -1);
  ispControls_.pop_front();
  if (update.valid) { queueIspUpdate(update); return; }
 }
 /* No iterators cross a proxy call: a direct module may return immediately. */
 std::vector<std::pair<uint32_t, uint32_t>> ready;
 for (const auto &[id, pending] : pendingStats_)
  if (!pending.submitted && lastSof_ && static_cast<int32_t>(*lastSof_ - pending.sof) >= 0) ready.emplace_back(pending.sof, id);
 std::sort(ready.begin(), ready.end());
 for (const auto &[sequence, id] : ready) {
  if (parameterBusy_) return;
  (void)sequence;
  auto it = pendingStats_.find(id);
  if (it == pendingStats_.end()) continue;
  it->second.submitted = true;
  const uint32_t sof = it->second.sof;
  auto known = sensorContexts_.find(sof);
  const ipa::camss::SensorContext context = known != sensorContexts_.end() ? known->second : ipa::camss::SensorContext{};
  ipa_->processStats(epoch_, sof, id, it->second.buffer->metadata().planes()[0].bytesused, context);
 }
}

void CamssVfeData::statsProcessed(uint64_t epoch, uint32_t sof, uint32_t id,
 const ipa::camss::Statistics &statistics, const ControlList &metadata)
{
 if (!running_ || epoch != epoch_) return;
 auto it = pendingStats_.find(id);
 if (it == pendingStats_.end() || !it->second.submitted || it->second.sof != sof) return;
 FrameBuffer *buffer = it->second.buffer;
 const auto &update = statistics.automaticUpdate;
 if (update.valid && automatic_ && sensorContextHealthy_) {
  const auto &range = sensor_->controls();
  const auto sampled=sensorContexts_.find(sof);
  const auto current=sensorContexts_.find(lastSof_.value_or(0));
  const bool sameContext=sampled!=sensorContexts_.end() && current!=sensorContexts_.end() &&
   sampled->second.valid && current->second.valid &&
   sampled->second.exposureLines==current->second.exposureLines &&
   sampled->second.gainCode==current->second.gainCode && sampled->second.source==current->second.source;
  bool valid = !statistics.status && statistics.parametersKnown && statistics.sensorControlsKnown && delayedControls_ &&
   !automaticUpdate_ && update.revision == lastAutoRevision_ + 1 && update.revision < UINT32_MAX - 1 &&
   lastSof_ && *lastSof_ >= sof && sameContext &&
   update.exposureLines >= uint32_t(range.at(V4L2_CID_EXPOSURE).min().get<int32_t>()) &&
   update.exposureLines <= uint32_t(range.at(V4L2_CID_EXPOSURE).max().get<int32_t>()) &&
   update.gainCode >= uint32_t(range.at(V4L2_CID_ANALOGUE_GAIN).min().get<int32_t>()) &&
   update.gainCode <= uint32_t(range.at(V4L2_CID_ANALOGUE_GAIN).max().get<int32_t>());
  if (valid) {
   automaticUpdate_ = update; lastAutoRevision_ = update.revision;
   LOG(CamssVfe, Info) << "AE update epoch=" << epoch << " stats-sof=" << sof << " revision=" << update.revision
    << " exposure-lines=" << update.exposureLines << " gain-code=" << update.gainCode;
  } else {
   sensorContextHealthy_ = false;
   LOG(CamssVfe, Error) << "Rejected AE update; sensor context invalid until restart";
  }
 }
 pendingStats_.erase(it);
 if (!statistics.status && statistics.parametersKnown) queueIspUpdate(statistics.ispUpdate);
 LOG(CamssVfe, Info) << "WB context epoch=" << epoch << " sof=" << sof << " revision=" << statistics.ispRevision
  << " known=" << statistics.parametersKnown;
 if (!statistics.status && statistics.population == uint64_t(input_.width / 2) * (input_.height / 2)) {
  if (std::find(histogramOrder_.begin(), histogramOrder_.end(), sof) == histogramOrder_.end()) {
   histogramOrder_.push_back(sof);
   histograms_.emplace(sof, Histogram{ statistics.population, statistics.weightedSum, metadata });
   if (images_.count(sof)) finish(sof, true);
  }
 } else {
  LOG(CamssVfe, Warning) << "IPA rejected statistics epoch=" << epoch << " sof=" << sof << " status=" << statistics.status;
 }
 while (histogramOrder_.size() > 32) {
  histograms_.erase(histogramOrder_.front()); histogramOrder_.pop_front();
 }
 int ret = stats_->queueBuffer(buffer);
 if (ret) LOG(CamssVfe, Error) << "Requeue IPA statistics failed: " << ret;
 submitStatistics();
}

void CamssVfeData::finish(uint32_t sequence, bool paired)
{
	auto it = images_.find(sequence);
	if (it == images_.end())
		return;
	FrameBuffer *buffer = it->second;
	Request *request = imageRequest(buffer);
	images_.erase(it);
 if(!request || !requests_.count(request))return;
	if (paired) {
		const Histogram &h = histograms_.at(sequence);
		request->_d()->metadata().merge(h.metadata);
		LOG(CamssVfe, Info) << "Pair epoch=" << epoch_ << " sof=" << sequence
			<< " request=" << request->sequence() << " population=" << h.population
			<< " mean=" << double(h.weightedSum) / h.population
			<< " parameters-acknowledged=" << paramsApplied_;
		histograms_.erase(sequence);
	} else {
		ControlList metadata(controls::controls);
		auto context=sensorContexts_.find(sequence);
		int ret=context==sensorContexts_.end()?-ENODATA:ipa_->frameMetadata(epoch_,sequence,context->second,&metadata);
		if (!ret) {
			request->_d()->metadata().merge(metadata);
			LOG(CamssVfe, Info) << "Image controls recovered epoch=" << epoch_ << " sof=" << sequence << " request=" << request->sequence();
		} else {
			buffer->_d()->metadata().status=FrameMetadata::FrameError;
			LOG(CamssVfe, Warning) << "Image controls unavailable epoch=" << epoch_ << " sof=" << sequence;
		}
	}
 if (lensActive_ && running_) {
  
  StreamConfiguration focusConfig;focusConfig.pixelFormat=formats::NV12;focusConfig.size=output_;focusConfig.stride=outputStride_;
  const auto score=measureFrameFocus(buffer,focusConfig);
  const auto found=sensorContexts_.find(sequence);
  const ipa::camss::SensorContext context=found==sensorContexts_.end()?ipa::camss::SensorContext{}:found->second;
  ControlList metadata(controls::controls);ipa::camss::LensMove move{};
  uint64_t captured=buffer->_d()->timestampMonotonic()?buffer->metadata().timestamp:0;
  int ret=ipa_->processFocus(epoch_,sequence,request->controls(),score.has_value(),score.value_or(0),captured,context,&metadata,&move);
  if (!ret) request->_d()->metadata().merge(metadata);
  else LOG(CamssVfe,Error)<<"Focus frame failed: "<<ret;
  if (move.valid) {
   CameraLens *lens=sensor_->focusLens();
   int result=lens?lens->setFocusPosition(move.position):-ENODEV;
   timespec clock{};uint64_t now=clock_gettime(CLOCK_MONOTONIC,&clock)?0:uint64_t(clock.tv_sec)*1000000000+clock.tv_nsec;
   LOG(CamssVfe,Info)<<"Focus command serial="<<move.serial<<" position="<<move.position<<" result="<<result<<" at="<<now;
   ipa_->lensPositionApplied(epoch_,move.serial,result,now);
  }
 }
	sensorContexts_.erase(sequence);
	request->_d()->metadata().set(controls::SensorTimestamp, buffer->metadata().timestamp);

 requests_.at(request).imageFinished=true;
 if(buffer->metadata().status!=FrameMetadata::FrameSuccess)requests_.at(request).failed=true;
 tryComplete(request);
 if(images_.empty() && requests_.empty())deadline_.stop();
}

void CamssVfeData::expired()
{
	/* Missing statistics never leave an application request stuck forever. */

 while (!images_.empty()) finish(images_.begin()->first,false);
 std::vector<Request *> pending;
 for(const auto &[request,frame]:requests_) if(frame.imageFinished && frame.rawReady) pending.push_back(request);
 for(Request *request:pending) tryComplete(request,true);
}

bool CamssVfePipeline::match(DeviceEnumerator *enumerator)
{
	/* An explicit opt-out retains the generic simple handler for diagnostics. */
	const char *enabled = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_ENABLE");
	if (enabled && !std::strcmp(enabled, "0"))
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
			int ret = d->init(entity, endpoint);
			if (ret) {
				LOG(CamssVfe, Debug) << "Cannot initialize " << entity->name()
					<< " through " << endpoint.pix->name() << ": " << ret;
				continue;
			}
			std::set<Stream *> streams{ &d->stream_ };
   if(d->raw_)streams.insert(&d->rawStream_);
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
