"""Move policy/statistics out of the tested299 handler into a generated IPA proxy."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel299/pipeline/camss_vfe.cpp').read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,old[:120]
 s=s.replace(old,new)
def section(start,end,new):
 global s
 a=s.index(start);b=s.index(end,a);s=s[:a]+new+s[b:]
replace('#include "parameter_encoder.h"','#include <libcamera/ipa/camss_ipa_proxy.h>')
for line in ['#include <libcamera/base/file.h>\n','#include "libcamera/internal/mapped_framebuffer.h"\n','#include "libcamera/internal/yaml_parser.h"\n']:
 replace(line,'')
replace('\tint loadProfile();','\tvoid submitStatistics();\n\tvoid statsProcessed(uint64_t epoch, uint32_t sof, uint32_t id,\n\t\tconst ipa::camss::Statistics &statistics, const ControlList &metadata);')
replace('\tstd::map<FrameBuffer *, std::unique_ptr<MappedFrameBuffer>> maps_;\n\tipa::camss::ResidualBlackProfile profile_{ 0, 1.0 };', '''\tstd::unique_ptr<ipa::camss::IPAProxyCamss> ipa_;
\tbool ipaInitialized_ = false;
\tstd::string ipaProfilePath_;
\tbool ipaMapped_ = false;
\tstruct PendingStats { uint32_t sof; FrameBuffer *buffer; bool submitted; };
\tstd::map<uint32_t, PendingStats> pendingStats_;''')
replace('\t\tuint64_t weightedSum;','\t\tuint64_t weightedSum;\n\t\tControlList metadata;')
section('int CamssVfeData::loadProfile()','CameraConfiguration::Status CamssVfeConfiguration::validate()','')
replace('\tdata(camera)->configuredFormat_.code = 0;', '\tauto *d = data(camera);\n\td->ipa_.reset();\n\td->ipaInitialized_ = false;\n\td->ipaProfilePath_.clear();\n\td->configuredFormat_.code = 0;')
section('int CamssVfePipeline::start(','void CamssVfePipeline::stopDevice(',r'''int CamssVfePipeline::start(Camera *camera, const ControlList *controls)
{
 auto *d = data(camera);
 if (active_) return -EBUSY;
 if (!d->configuredFormat_.code) return -EPIPE;
 int ret;
 if (configured_ != d) {
  if (configured_) configured_->restoreLinks();
  configured_ = nullptr;
  ret = d->configurePath(d->configuredFormat_, d->stream_.configuration().size);
  V4L2DeviceFormat format;
  format.fourcc = V4L2PixelFormat(V4L2_PIX_FMT_NV12);
  format.size = d->stream_.configuration().size;
  if (!ret) ret = d->image_->setFormat(&format);
  if (ret || format.size != d->stream_.configuration().size) {
   d->restoreLinks(); return ret ? ret : -EINVAL;
  }
  configured_ = d;
 }
 active_ = d;
 ++d->epoch_;
 d->paramsApplied_ = false;
 d->images_.clear(); d->histograms_.clear(); d->histogramOrder_.clear(); d->pendingStats_.clear();
 if (!d->ipa_) {
  d->ipa_ = createIPA<ipa::camss::IPAProxyCamss>(0, 0);
  if (!d->ipa_) { ret = -ENOENT; goto error; }
  d->ipa_->statsProcessed.connect(d, &CamssVfeData::statsProcessed);
 }
 {
  const char *profile = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
  const std::string profilePath = profile ? profile : "";
  if (d->ipaInitialized_ && profilePath != d->ipaProfilePath_) { ret = -EINVAL; goto error; }
  if (!d->ipaInitialized_) {
   ret = d->ipa_->init(IPASettings{ profilePath, d->sensor_->model() });
   if (ret) { d->ipa_.reset(); goto error; }
   d->ipaInitialized_ = true;
   d->ipaProfilePath_ = profilePath;
  }
  IPACameraSensorInfo info;
  ret = d->sensor_->sensorInfo(&info);
  if (ret) goto error;
  ret = d->ipa_->configure(info, d->input_);
  if (ret) goto error;
 }
 ret = d->image_->importBuffers(d->stream_.configuration().bufferCount);
 if (ret) goto error;
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
  ret = d->ipa_->start(d->epoch_, controls ? *controls : empty);
  if (ret) goto error;
 }
 for (auto &buffer : d->paramsBuffers_) {
  uint32_t used = 0;
  ret = d->ipa_->prepareParameters(d->epoch_, buffer->cookie(), &used);
  if (ret) goto error;
  auto &metadata = buffer->_d()->metadata();
  metadata.status = FrameMetadata::FrameSuccess; metadata.sequence = 0; metadata.timestamp = 0;
  metadata.planes()[0].bytesused = used;
  ret = d->params_->queueBuffer(buffer.get());
  if (ret) goto error;
 }
 for (auto &buffer : d->statsBuffers_) {
  ret = d->stats_->queueBuffer(buffer.get());
  if (ret) goto error;
 }
 ret = d->pix_->setFrameStartEnabled(true);
 if (ret) goto error;
 d->running_ = true;
 for (auto *device : { d->stats_.get(), d->params_.get(), d->image_.get() }) {
  ret = device->streamOn();
  if (ret) goto error;
 }
 return 0;
error:
 stopDevice(camera);
 return ret;
}

''')
replace('\td->maps_.clear();', '''\tif (d->ipa_) {
\t\td->ipa_->stop();
\t\tif (d->ipaMapped_) {
\t\t\tstd::vector<uint32_t> ids;
\t\t\tfor (auto &buffer : d->paramsBuffers_) ids.push_back(buffer->cookie());
\t\t\tfor (auto &buffer : d->statsBuffers_) ids.push_back(buffer->cookie());
\t\t\td->ipa_->unmapBuffers(ids);
\t\t}
\t}
\td->ipaMapped_ = false;
\td->pendingStats_.clear();''')
replace('\tfirstParamSof_ = buffer->_d()->kernelSequence();','\tfirstParamSof_ = buffer->_d()->kernelSequence();\n\tipa_->parametersApplied(epoch_, firstParamSof_);\n\tsubmitStatistics();')
section('void CamssVfeData::statsReady(','void CamssVfeData::finish(',r'''void CamssVfeData::statsReady(FrameBuffer *buffer)
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
 submitStatistics();
}

void CamssVfeData::submitStatistics()
{
 if (!running_ || !paramsApplied_) return;
 /* No iterators cross a proxy call: a direct module may return immediately. */
 std::vector<uint32_t> ready;
 for (const auto &[id, pending] : pendingStats_)
  if (!pending.submitted) ready.push_back(id);
 for (uint32_t id : ready) {
  auto it = pendingStats_.find(id);
  if (it == pendingStats_.end()) continue;
  it->second.submitted = true;
  ipa_->processStats(epoch_, it->second.sof, id, it->second.buffer->metadata().planes()[0].bytesused);
 }
}

void CamssVfeData::statsProcessed(uint64_t epoch, uint32_t sof, uint32_t id,
 const ipa::camss::Statistics &statistics, const ControlList &metadata)
{
 if (!running_ || epoch != epoch_) return;
 auto it = pendingStats_.find(id);
 if (it == pendingStats_.end() || !it->second.submitted || it->second.sof != sof) return;
 FrameBuffer *buffer = it->second.buffer;
 pendingStats_.erase(it);
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
}

''')
replace('\t\tconst Histogram &h = histograms_.at(sequence);','\t\tconst Histogram &h = histograms_.at(sequence);\n\t\trequest->_d()->metadata().merge(h.metadata);')
dest=HERE/'pipeline/camss_vfe.cpp';dest.parent.mkdir(exist_ok=True)
if dest.exists():assert dest.read_text()==s, 'Existing generated handler differs; preserve and inspect before regeneration'
else:dest.write_text(s)
(HERE/'pipeline/meson.build').write_text("# SPDX-License-Identifier: CC0-1.0\nlibcamera_internal_sources += files('camss_vfe.cpp')\n")
assert 'encodeParameters' not in s and 'MappedFrameBuffer' not in s and 'camss_stats_bhist' not in s and 'YamlParser' not in s
print('Prepared online handler using standard generated IPA proxy; no tuning or histogram parser remains in handler.')
