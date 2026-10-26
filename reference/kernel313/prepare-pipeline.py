"""Use standard lens lifetime/acknowledgement and frame-owned AF observations."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
def edit(before,after):
    p=HERE/'pipeline/camss_vfe.cpp';s=p.read_text()
    if s.count(before)!=1:raise RuntimeError((before[:90],s.count(before)))
    p.write_text(s.replace(before,after))
edit('#include <chrono>','#include <chrono>\n#include <time.h>\n#include "hardware_focus.h"\n#include "libcamera/internal/camera_lens.h"')
edit('\tvoid expired();','\tvoid expired();\n\tbool lensActive_=false;\n\tControlInfoMap lensControls_;\n\tstd::string lensModel_;')
edit('ret = d->ipa_->init(IPASettings{ "", d->sensor_->model() }, info, d->sensor_->controls(), &d->controlInfo_);',
     'const std::string profile=d->ipa_->configurationFile(d->sensor_->model()+".yaml");\n ret = d->ipa_->init(IPASettings{ profile, d->sensor_->model() }, info, d->sensor_->controls(), d->lensControls_, d->lensModel_, &d->controlInfo_);')
edit('''	if (!sensor_)
		return -ENODEV;''','''	if (!sensor_)
		return -ENODEV;
 if (CameraLens *lens=sensor_->focusLens()) {
  lensControls_=lens->controls();lensModel_=lens->model();lens->close();
 }''')
edit(''' d->running_ = true;
 for (auto *device''',''' if (d->controlInfo_.find(&controls::AfMode)!=d->controlInfo_.end()) {
  CameraLens *lens=d->sensor_->focusLens();
  if (!lens) {ret=-ENODEV;goto error;}
  ret=lens->open();if (ret) goto error;d->lensActive_=true;
 }
 d->running_ = true;
 for (auto *device''')
edit('''	d->sensorContextHealthy_ = false;
	d->sensorUpdates_.clear();''','''	d->sensorContextHealthy_ = false;
	d->sensorUpdates_.clear();''')
edit('''	d->ipaMapped_ = false;
	d->pendingStats_.clear();''','''	d->lensActive_=false;
 if (CameraLens *lens=d->sensor_->focusLens()) lens->close();
	d->ipaMapped_ = false;
	d->pendingStats_.clear();''')
edit('''	sensorContexts_.erase(sequence);
	request->_d()->metadata().set(controls::SensorTimestamp''',''' if (lensActive_) {
  const auto score=measureFrameFocus(buffer,stream_.configuration());
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
	request->_d()->metadata().set(controls::SensorTimestamp''')
print('Prepared lens lifetime and per-frame focus measurement / acknowledged moves.')
