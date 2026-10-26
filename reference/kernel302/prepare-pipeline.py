"""Use existing DelayedControls with per-SOF snapshots and standard IPA conversion."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300'
s=(OLD/'pipeline/camss_vfe.cpp').read_text()
s=s.replace('#include <linux/media-bus-format.h>','#include <linux/media-bus-format.h>\n#include <linux/videodev2.h>\n#include <optional>\n#include <limits>')
s=s.replace('#include "libcamera/internal/device_enumerator.h"','#include "libcamera/internal/device_enumerator.h"\n#include "libcamera/internal/delayed_controls.h"')
anchor='\tbool ipaMapped_ = false;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
 ipa::camss::SensorControlConfiguration sensorConfiguration_{};
 ipa::camss::SensorContext startupSensor_{};
 std::unique_ptr<DelayedControls> delayedControls_;
 struct SensorUpdate { ControlList controls; uint32_t source; };
 std::deque<SensorUpdate> sensorUpdates_;
 std::map<uint32_t, ipa::camss::SensorContext> sensorContexts_;
 std::optional<uint32_t> lastSof_;
 bool sensorContextHealthy_ = false;
''')
s=s.replace('\tbool match(DeviceEnumerator *enumerator) override;','\tbool match(DeviceEnumerator *enumerator) override;\n\tint initIPA(CamssVfeData *data);')
anchor='int CamssVfeData::init(MediaEntity *sensor, const Endpoint &endpoint)';assert s.count(anchor)==1
s=s.replace(anchor,'''int CamssVfePipeline::initIPA(CamssVfeData *d)
{
 if (d->ipaInitialized_) return 0;
 IPACameraSensorInfo info;
 int ret = d->sensor_->sensorInfo(&info);
 if (ret) return ret;
 d->ipa_ = createIPA<ipa::camss::IPAProxyCamss>(0, 0);
 if (!d->ipa_) return -ENOENT;
 ret = d->ipa_->init(IPASettings{ "", d->sensor_->model() }, info, d->sensor_->controls(), &d->controlInfo_);
 if (ret) { d->ipa_.reset(); return ret; }
 d->ipa_->statsProcessed.connect(d, &CamssVfeData::statsProcessed);
 d->ipaInitialized_ = true;
 return 0;
}

'''+anchor)
s=s.replace('\tcontrolInfo_ = ControlInfoMap({ { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) } }, controls::controls);\n\treturn 0;','\treturn handler()->initIPA(this);')
a=s.index(' if (!d->ipa_) {',s.index('int CamssVfePipeline::start('));b=s.index(' ret = d->image_->importBuffers',a)
s=s[:a]+''' ret = initIPA(d);
 if (ret) goto error;
 {
  const char *profile = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
  IPACameraSensorInfo info;
  ret = d->sensor_->sensorInfo(&info);
  if (ret) goto error;
  ret = d->ipa_->configure(info, d->input_, d->sensor_->controls(), profile ? profile : "", &d->controlInfo_, &d->sensorConfiguration_);
  if (ret) goto error;
 }
'''+s[b:]
anchor='  ret = d->ipa_->start(d->epoch_, controls ? *controls : empty);';assert s.count(anchor)==1
s=s.replace(anchor,'''  ControlList initial(d->sensor_->controls());
  ret = d->ipa_->start(d->epoch_, controls ? *controls : empty, &initial);''')
anchor='  if (ret) goto error;\n }\n for (auto &buffer : d->paramsBuffers_)';assert s.count(anchor)==1
s=s.replace(anchor,'''  if (ret) goto error;
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
 for (auto &buffer : d->paramsBuffers_)''')
anchor='\td->running_ = false;\n\td->deadline_.stop();';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\td->sensorContextHealthy_ = false;\n\td->sensorUpdates_.clear();')
anchor='\td->paramsApplied_ = false;\n\td->restoreLinks();';assert s.count(anchor)==1
s=s.replace(anchor,'\td->paramsApplied_ = false;\n\td->delayedControls_.reset(); d->sensorContexts_.clear(); d->lastSof_.reset();\n\td->restoreLinks();')
a=s.index('int CamssVfePipeline::queueRequestDevice(');b=s.index('void CamssVfeData::paramsReady',a)
s=s[:a]+'''int CamssVfePipeline::queueRequestDevice(Camera *camera, Request *request)
{
 auto *d = data(camera);
 FrameBuffer *buffer = request->findBuffer(&d->stream_);
 if (!buffer) return -EINVAL;
 ControlList sensorControls(d->sensor_->controls());
 if (!request->controls().empty()) {
  if (!d->delayedControls_ || !d->sensorContextHealthy_) return -ENOTSUP;
  if (d->sensorUpdates_.size() >= 8) return -ENOSPC;
  int ret = d->ipa_->convertControls(d->epoch_, request->controls(), &sensorControls);
  if (ret) return ret;
 }
 int ret = d->image_->queueBuffer(buffer);
 if (!ret && !sensorControls.empty())
  d->sensorUpdates_.push_back({ std::move(sensorControls), request->sequence() });
 return ret;
}

'''+s[b:]
a=s.index('void CamssVfeData::frameStart(');b=s.index('void CamssVfeData::imageReady(',a)
s=s[:a]+'''void CamssVfeData::frameStart(uint32_t sequence)
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
  if (!sensorUpdates_.empty()) {
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

'''+s[b:]
anchor='  if (!pending.submitted) ready.push_back(id);';assert s.count(anchor)==1
s=s.replace(anchor,'  if (!pending.submitted && lastSof_ && static_cast<int32_t>(*lastSof_ - pending.sof) >= 0) ready.push_back(id);')
anchor='  ipa_->processStats(epoch_, it->second.sof, id, it->second.buffer->metadata().planes()[0].bytesused);';assert s.count(anchor)==1
s=s.replace(anchor,'''  const uint32_t sof = it->second.sof;
  auto known = sensorContexts_.find(sof);
  const ipa::camss::SensorContext context = known != sensorContexts_.end() ? known->second : ipa::camss::SensorContext{};
  ipa_->processStats(epoch_, sof, id, it->second.buffer->metadata().planes()[0].bytesused, context);''')
anchor='\timages_.erase(it);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\tsensorContexts_.erase(sequence);')
(HERE/'pipeline/camss_vfe.cpp').write_text(s)
print('Prepared302 pipeline; no generic helper/API, kernel or DT changes.')
