"""Generate runtime WB control support from the retained308 sources."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel308'
for name in ['camss.mojom','ipa-contract.cpp','build-candidate.py']:
    shutil.copyfile(OLD/name,HERE/name)
for directory in ['ipa','pipeline']:
    (HERE/directory).mkdir(exist_ok=True)
    for p in (OLD/directory).iterdir():
        if p.is_file():shutil.copyfile(p,HERE/directory/p.name)
def edit(name,before,after):
    path=HERE/name;text=path.read_text()
    if text.count(before)!=1:raise RuntimeError((name,before[:80],text.count(before)))
    path.write_text(text.replace(before,after))
edit('camss.mojom','\tstop();','\tapplyIspControls(uint64 epoch, libcamera.ControlList controls) => (int32 ret, AutoIspUpdate update);\n\tstop();')
edit('ipa/camss.cpp','\tvoid stop() override;',
     '\tint applyIspControls(uint64_t epoch, const ControlList &controls, AutoIspUpdate *update) override;\n\tvoid stop() override;')
edit('ipa/camss.cpp','struct ParameterContext { uint32_t revision; double red, blue; };',
     'struct ParameterContext { uint32_t revision; double red, blue; bool awbEnabled; };')
edit('ipa/camss.cpp','  if (id == controls::ColourGains.id() && startup) continue;', '''  if (id == controls::ColourGains.id()) {
   if (value.type() != ControlTypeFloat || !value.isArray() || value.numElements() != 2) return -EINVAL;
   for (float gain : value.get<Span<const float>>())
    if (!std::isfinite(gain) || gain < 0 || gain > 8) return -ERANGE;
   continue;
  }''')
edit('ipa/camss.cpp','   if (!startup && value.get<bool>() != awbEnabled_) return -ENOTSUP;',
     '   if (value.get<bool>() && !awb_) return -ENOTSUP;')
edit('ipa/camss.cpp',' if (automatic_ && !controls.empty()) return -ENOTSUP;\n return translate(controls, false, sensorControls);', ''' ControlList sensorOnly(libcamera::controls::controls);
 for (const auto &[id, value] : controls)
  if (id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id()) sensorOnly.set(id,value);
 ControlList ignored(sensorControls_);
 int ret = translate(controls, true, &ignored);
 if (ret) return ret;
 if (automatic_ && !sensorOnly.empty()) return -ENOTSUP;
 return translate(sensorOnly, false, sensorControls);''')
edit('ipa/camss.cpp','int IPACamss::mapBuffers(','''int IPACamss::applyIspControls(uint64_t epoch, const ControlList &controls, AutoIspUpdate *update)
{
 if (!update) return -EINVAL;
 *update = {};
 if (!running_ || epoch != epoch_) return -ESTALE;
 if (pendingWhiteBalance_ || !preparedParameters_.empty() || parameterHistory_.empty()) return -EAGAIN;
 ControlList ignored(sensorControls_);
 int ret = translate(controls, true, &ignored);
 if (ret) return ret;
 const auto &current = parameterHistory_.rbegin()->second;
 const bool enabled = controls.get(libcamera::controls::AwbEnable).value_or(awbEnabled_);
 double red = current.red, blue = current.blue;
 if (!enabled) {
  auto gains = controls.get(libcamera::controls::ColourGains);
  if (gains) { red=(*gains)[0];blue=(*gains)[1]; }
 }
 if (enabled == current.awbEnabled && red == current.red && blue == current.blue) return 0;
 if (ispRevision_ >= UINT32_MAX-1) return -EOVERFLOW;
 awbEnabled_ = enabled;
 if (awb_) awb_->reset();
 pendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, red, blue };
 *update = *pendingWhiteBalance_;
 return 0;
}

int IPACamss::mapBuffers(''')
edit('ipa/camss.cpp','preparedParameters_[revision] = { revision, effectiveRed, effectiveBlue };',
     'preparedParameters_[revision] = { revision, effectiveRed, effectiveBlue, awbEnabled_ };')
edit('ipa/camss.cpp','<< " first-sof=" << firstSof;',
     '<< " first-sof=" << firstSof << " awb=" << parameterHistory_.at(firstSof).awbEnabled;')
edit('ipa/camss.cpp','metadata.set(controls::AwbEnable, awbEnabled_);',
     'metadata.set(controls::AwbEnable, result.parametersKnown && context->second.awbEnabled);\n\tmetadata.set(controls::AwbLocked, false);')
edit('ipa/camss.cpp','if (awbEnabled_ && effective_ && result.rgbPresent && context == std::prev(parameterHistory_.end()) &&',
     'if (awbEnabled_ && effective_ && context->second.awbEnabled && result.rgbPresent && context == std::prev(parameterHistory_.end()) &&')
edit('pipeline/camss_vfe.cpp','\tvoid queueIspUpdate(const ipa::camss::AutoIspUpdate &update);',
     '\tvoid queueIspUpdate(const ipa::camss::AutoIspUpdate &update);\n\tstruct IspControls { ControlList controls; uint32_t source; };\n\tstd::deque<IspControls> ispControls_;')
edit('pipeline/camss_vfe.cpp','d->parameterRevision_ = d->lastIspRevision_ = 0;',
     'd->parameterRevision_ = d->lastIspRevision_ = 0;\n d->ispControls_.clear();')
edit('pipeline/camss_vfe.cpp','d->delayedControls_.reset(); d->sensorContexts_.clear(); d->lastSof_.reset();',
     'd->delayedControls_.reset(); d->sensorContexts_.clear(); d->lastSof_.reset(); d->ispControls_.clear();')
edit('pipeline/camss_vfe.cpp','''  if (!d->delayedControls_ || !d->sensorContextHealthy_) return -ENOTSUP;
  if (d->sensorUpdates_.size() >= 8) return -ENOSPC;
  int ret = d->ipa_->convertControls''','''  int ret = d->ipa_->convertControls''')
edit('pipeline/camss_vfe.cpp',''' int ret = d->image_->queueBuffer(buffer);
 if (!ret && !sensorControls.empty())
  d->sensorUpdates_.push_back({ std::move(sensorControls), request->sequence() });
 return ret;''',''' const bool isp = request->controls().contains(controls::AwbEnable.id()) || request->controls().contains(controls::ColourGains.id());
 if (!sensorControls.empty() && (!d->delayedControls_ || !d->sensorContextHealthy_)) return -ENOTSUP;
 if ((!sensorControls.empty() && d->sensorUpdates_.size() >= 8) || (isp && d->ispControls_.size() >= 8)) return -ENOSPC;
 int ret = d->image_->queueBuffer(buffer);
 if (!ret) {
  if (!sensorControls.empty()) d->sensorUpdates_.push_back({ std::move(sensorControls), request->sequence() });
  if (isp) { d->ispControls_.push_back({ request->controls(), request->sequence() }); d->submitStatistics(); }
 }
 return ret;''')
edit('pipeline/camss_vfe.cpp','update.red < .125 || update.red > 8 || update.blue < .125 || update.blue > 8',
     'update.red < 0 || update.red > 8 || update.blue < 0 || update.blue > 8')
edit('pipeline/camss_vfe.cpp',''' if (!running_ || !paramsApplied_ || parameterBusy_) return;
 /* No iterators''',''' if (!running_ || !paramsApplied_ || parameterBusy_) return;
 while (!ispControls_.empty()) {
  if (std::any_of(pendingStats_.begin(), pendingStats_.end(), [](const auto &entry) { return entry.second.submitted; })) return;
  auto &request = ispControls_.front();
  ipa::camss::AutoIspUpdate update{};
  int ret = ipa_->applyIspControls(epoch_, request.controls, &update);
  if (ret == -EAGAIN) return;
  if (ret) { ispHealthy_=false; LOG(CamssVfe, Error) << "Runtime WB control failed: " << ret; return; }
  LOG(CamssVfe, Info) << "WB request epoch=" << epoch_ << " source=" << request.source << " revision=" << update.revision
   << " awb=" << request.controls.get(controls::AwbEnable).value_or(-1);
  ispControls_.pop_front();
  if (update.valid) { queueIspUpdate(update); return; }
 }
 /* No iterators''')
edit('pipeline/camss_vfe.cpp',''' if (ret) LOG(CamssVfe, Error) << "Requeue IPA statistics failed: " << ret;
}''',''' if (ret) LOG(CamssVfe, Error) << "Requeue IPA statistics failed: " << ret;
 submitStatistics();
}''')
edit('build-candidate.py',"camera307-rgb-kernel",'camera309-link-kernel')
edit('build-candidate.py',"'stage':308","'stage':311")
print('Generated request WB validation, ordered parameter updates and applied-mode history.')
