"""One-time transformation of 313 to the 315 dual-output candidate."""
from pathlib import Path
P=Path(__file__).resolve().parent/'pipeline/camss_vfe.cpp'
s=P.read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,old[:100]
 s=s.replace(old,new)
def function(begin,end,text):
 global s
 a=s.index(begin);b=s.index(end,a)
 s=s[:a]+text+'\n\n'+s[b:]
replace('/* Experimental inline CAMSS handler. Manual, single processed stream only. */',
        '/* CAMSS hardware processing with optional zero-copy RAW capture. */')
replace('#include "libcamera/internal/camera.h"','#include "libcamera/internal/bayer_format.h"\n#include "libcamera/internal/camera.h"')
replace('\tvoid imageReady(FrameBuffer *buffer);','''
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
''')
replace('std::unique_ptr<V4L2VideoDevice> image_, params_, stats_;','std::unique_ptr<V4L2VideoDevice> image_, params_, stats_, raw_;')
replace('V4L2Subdevice *pix_ = nullptr;', 'V4L2Subdevice *pix_ = nullptr, *rdi_ = nullptr;')
replace('std::vector<MediaLink *> path_;', 'std::vector<MediaLink *> path_, rawPath_;')
replace('\tStream stream_;','\tStream stream_, rawStream_;')
replace('\tV4L2SubdeviceFormat sensorFormat_;','\tV4L2SubdeviceFormat sensorFormat_;\n bool raw_ = false, processed_ = false;')
# Discover an RDI connected to the same CSID as the selected PIX, by topology
# and packed RAW10 capabilities rather than board node names.
replace('\tpix_ = subdevs_.at(endpoint.pix).get();','''
 pix_ = subdevs_.at(endpoint.pix).get();
 MediaLink *pixInput = path_[path_.size() - 2];
 MediaEntity *csid = pixInput->source()->entity();
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
''')
replace('pix_->frameStart.connect(this, &CamssVfeData::frameStart);','pix_->frameStartTimestamp.connect(this, &CamssVfeData::pixFrameStart);')
replace('\t/* Exclusive candidate: deactivate competing routes touching this path. */', '''
 std::vector<MediaLink *> routes = path_;
 if (rawEnabled_) routes.insert(routes.end(), rawPath_.begin(), rawPath_.end());
 /* Exclusive camera: deactivate competing routes touching the selected paths. */''')
# Modify only configurePath loops; the discovery loops above stay unchanged.
a=s.index('int CamssVfeData::configurePath');b=s.index('CameraConfiguration::Status',a)
part=s[a:b].replace('for (MediaLink *link : path_)','for (MediaLink *link : routes)').replace('std::find(path_.begin(), path_.end(), link) != path_.end()', 'std::find(routes.begin(), routes.end(), link) != routes.end()')
# Preserve ordered propagation on the PIX route, then propagate its CSID format
# into the selected RDI. The RAW format cannot go through the PIX compose.
part=part.replace('\tfor (MediaLink *link : routes) {\n\t\tMediaEntity *source', '\tfor (MediaLink *link : path_) {\n\t\tMediaEntity *source')
part=part.replace('\tRectangle compose(output);', '''
 if (rawEnabled_) {
  MediaLink *link = rawPath_.front();
  ret = subdevs_.at(link->source()->entity())->getFormat(link->source()->index(), &format);
  if (!ret) ret = rdi_->setFormat(link->sink()->index(), &format);
  if (ret || format.size != requested.size) return ret ? ret : -EINVAL;
 }
 Rectangle compose(output);''')
s=s[:a]+part+s[b:]
function('CameraConfiguration::Status CamssVfeConfiguration::validate()',
         'std::unique_ptr<CameraConfiguration> CamssVfePipeline::generateConfiguration',r'''CameraConfiguration::Status CamssVfeConfiguration::validate()
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
  const Size size = raw ? sensorFormat_.size : cfg.size.expandedTo(Size(16,16)).boundedTo(sensorFormat_.size).alignedDownTo(2,2);
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
}''')
function('std::unique_ptr<CameraConfiguration> CamssVfePipeline::generateConfiguration(',
         'int CamssVfePipeline::configure(',r'''std::unique_ptr<CameraConfiguration> CamssVfePipeline::generateConfiguration(
 Camera *camera, Span<const StreamRole> roles)
{
 auto *d = data(camera);
 auto config = std::make_unique<CamssVfeConfiguration>(d);
 if (roles.size() > 2) return nullptr;
 for (StreamRole role : roles) {
  StreamConfiguration cfg;
  if (role == StreamRole::Raw) {
   if (!d->raw_) return nullptr;
   cfg.pixelFormat = formats::SRGGB10_CSI2P;
   cfg.size = d->sensor_->resolution();
  } else {cfg.pixelFormat=formats::NV12;cfg.size=Size(640,480);}
  config->addConfiguration(cfg);
 }
 if (!roles.empty() && config->validate() == CameraConfiguration::Invalid) return nullptr;
 return config;
}''')
replace('\tint ret = d->configurePath(cfg->sensorFormat_, cfg->at(0).size);','''
 d->rawEnabled_ = cfg->raw_;d->processedEnabled_ = cfg->processed_;
 d->output_ = Size(640,480);
 for (auto &stream : *cfg) if (stream.pixelFormat == formats::NV12) d->output_ = stream.size;
 int ret = d->configurePath(cfg->sensorFormat_, d->output_);''')
replace('\tformat.size = cfg->at(0).size;', '\tformat.size = d->output_;')
replace('format.size != cfg->at(0).size', 'format.size != d->output_')
replace(' ret = initIPA(d);\n if (ret) { d->restoreLinks(); return ret; }', ' d->outputStride_=format.planes[0].bpl;\n ret = initIPA(d);\n if (ret) { d->restoreLinks(); return ret; }')
replace('\tcfg->at(0).setStream(&d->stream_);','''
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
 }''')
replace('return data(camera)->image_->exportBuffers(stream->configuration().bufferCount, buffers);', '''
 auto *d = data(camera);
 return (stream == &d->rawStream_ ? d->raw_ : d->image_)->exportBuffers(stream->configuration().bufferCount, buffers);''')
s=s.replace('d->stream_.configuration().size', 'd->output_')
replace('  configured_ = d;\n }\n active_ = d;', '''
  if (d->rawEnabled_) {ret=d->raw_->setFormat(&d->rawFormat_);if(ret){d->restoreLinks();return ret;}}
  configured_ = d;
 }
 active_ = d;''')
replace(' ret = d->image_->importBuffers(d->stream_.configuration().bufferCount);\n if (ret) goto error;', '''
 d->requests_.clear();d->internalRequests_.clear();d->pixStarts_.clear();d->rawStarts_.clear();
 d->framePeriod_=d->previousPixStart_=0;
 if (d->processedEnabled_) ret=d->image_->importBuffers(d->stream_.configuration().bufferCount);
 else {
  ret=d->image_->allocateBuffers(4,&d->internalImages_);
  if (ret >= 4) {for(auto &buffer:d->internalImages_) d->freeImages_.push(buffer.get());ret=0;}
  else ret=ret<0?ret:-ENOMEM;
 }
 if (ret) goto error;
 if (d->rawEnabled_) {ret=d->raw_->importBuffers(d->rawStream_.configuration().bufferCount);if(ret)goto error;}''')
replace(' if (d->controlInfo_.find(&controls::AfMode)!=d->controlInfo_.end()) {','''
 if (d->rawEnabled_) {ret=d->rdi_->setFrameStartEnabled(true);if(ret)goto error;}
 if (d->controlInfo_.find(&controls::AfMode)!=d->controlInfo_.end()) {''')
replace(' return 0;\nerror:\n stopDevice(camera);','''
 if (d->rawEnabled_) {ret=d->raw_->streamOn();if(ret)goto error;}
 return 0;
error:
 stopDevice(camera);''')
replace('\td->image_->streamOff();','\tif (d->rawEnabled_) d->raw_->streamOff();\n\td->image_->streamOff();')
replace('\td->pix_->setFrameStartEnabled(false);','\td->pix_->setFrameStartEnabled(false);\n if (d->rawEnabled_) d->rdi_->setFrameStartEnabled(false);')
replace('\td->histograms_.clear();\n\td->histogramOrder_.clear();','''
 while (!d->requests_.empty()) d->tryComplete(d->requests_.begin()->first,true);
 d->histograms_.clear();
 d->histogramOrder_.clear();''')
replace('\td->paramsBuffers_.clear(); d->statsBuffers_.clear();','''
 if (d->rawEnabled_) d->raw_->releaseBuffers();
 d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();
 d->pixStarts_.clear();d->rawStarts_.clear();
 d->paramsBuffers_.clear(); d->statsBuffers_.clear();''')
replace(' if (!buffer) return -EINVAL;','''
 FrameBuffer *raw = request->findBuffer(&d->rawStream_);
 if ((d->processedEnabled_ && !buffer) || (d->rawEnabled_ && !raw)) return -EINVAL;
 if (!buffer) {if(d->freeImages_.empty())return -ENOBUFS;buffer=d->freeImages_.front();}''')
replace(' int ret = d->image_->queueBuffer(buffer);\n if (!ret) {','''
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
 {''')
replace(' }\n return ret;\n}\n\nvoid CamssVfeData::paramsReady',' }\n return 0;\n}\n\nvoid CamssVfeData::paramsReady')
# Image processing and its statistics remain keyed by the PIX SOF. Keep all
# application buffers until both nodes and the physical-frame check finish.
replace('void CamssVfeData::imageReady(FrameBuffer *buffer)\n{','''
void CamssVfeData::imageReady(FrameBuffer *buffer)
{
 Request *request=imageRequest(buffer);
 if(!request || !requests_.count(request)) return;''')
s=s.replace('''		Request *request = buffer->request();
		handler()->completeBuffer(request, buffer);
		handler()->completeRequest(request);
		return;''','''
  auto &frame=requests_.at(request);frame.imageFinished=true;frame.failed=true;
  tryComplete(request);
  return;''')
# The duplicate-image branch had the same completion block except its local
# declaration was preceded by status assignment. It is replaced independently.
replace('''		Request *request = buffer->request();
		handler()->completeBuffer(request, buffer);
		handler()->completeRequest(request);
		return;''','''
  auto &frame=requests_.at(request);frame.imageFinished=true;frame.failed=true;
  tryComplete(request);
  return;''') if s.count('''		Request *request = buffer->request();
		handler()->completeBuffer(request, buffer);
		handler()->completeRequest(request);
		return;''') else None
s=s.replace('buffer->request()->sequence()', 'request->sequence()')
replace('\tRequest *request = buffer->request();\n\timages_.erase(it);','\tRequest *request = imageRequest(buffer);\n\timages_.erase(it);\n if(!request || !requests_.count(request))return;')
replace('const auto score=measureFrameFocus(buffer,stream_.configuration());','''
  StreamConfiguration focusConfig;focusConfig.pixelFormat=formats::NV12;focusConfig.size=output_;focusConfig.stride=outputStride_;
  const auto score=measureFrameFocus(buffer,focusConfig);''')
replace('''	handler()->completeBuffer(request, buffer);
	handler()->completeRequest(request);
	if (images_.empty())
		deadline_.stop();''','''
 requests_.at(request).imageFinished=true;
 if(buffer->metadata().status!=FrameMetadata::FrameSuccess)requests_.at(request).failed=true;
 tryComplete(request);
 if(images_.empty() && requests_.empty())deadline_.stop();''')
replace('''	while (!images_.empty())
		finish(images_.begin()->first, false);
}''','''
 while (!images_.empty()) finish(images_.begin()->first,false);
 std::vector<Request *> pending;
 for(const auto &[request,frame]:requests_) if(frame.imageFinished && frame.rawReady) pending.push_back(request);
 for(Request *request:pending) tryComplete(request,true);
}''')
replace('std::set<Stream *> streams{ &d->stream_ };','std::set<Stream *> streams{ &d->stream_ };\n   if(d->raw_)streams.insert(&d->rawStream_);')
insert=r'''
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

'''
pos=s.index('void CamssVfeData::paramsReady')
s=s[:pos]+insert+s[pos:]
P.write_text(s)
print('Extended315 pipeline with RAW-only/dual streams and SOF correlation.')
