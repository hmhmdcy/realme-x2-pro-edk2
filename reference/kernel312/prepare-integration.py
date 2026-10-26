"""Extend the current common backend with standard mode selection/catalogs."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel311'
for name in ['camss.mojom','build-candidate.py','ipa-contract.cpp','test-ipa.py']:
    shutil.copyfile(OLD/name,HERE/name)
for directory in ['ipa','pipeline']:
    (HERE/directory).mkdir(exist_ok=True)
    for p in (OLD/directory).iterdir():
        if p.is_file():shutil.copyfile(p,HERE/directory/p.name)
def edit(name,before,after):
    p=HERE/name;s=p.read_text()
    if s.count(before)!=1:raise RuntimeError((name,before[:80],s.count(before)))
    p.write_text(s.replace(before,after))
edit('pipeline/camss_vfe.cpp','sensorFormat_ = data_->sensor_->getFormat(codes, cfg.size);', '''if (sensorConfig && (!sensorConfig->isValid() || sensorConfig->bitDepth != 10)) return Invalid;
 sensorFormat_ = data_->sensor_->getFormat(codes, sensorConfig ? sensorConfig->outputSize : cfg.size);
 if (sensorConfig && sensorFormat_.size != sensorConfig->outputSize) return Invalid;''')
edit('pipeline/camss_vfe.cpp',''' const char *profile = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
 d->ipaProfilePath_ = profile ? profile : "";''',''' ret = initIPA(d);
 if (ret) { d->restoreLinks(); return ret; }
 const char *profile = utils::secure_getenv("LIBCAMERA_CAMSS_VFE_PROFILE");
 d->ipaProfilePath_ = profile ? profile : d->ipa_->configurationFile(d->sensor_->model()+".yaml");''')
edit('pipeline/camss_vfe.cpp','d->automatic_ = controls && controls->get(libcamera::controls::ExposureTimeMode).value_or(libcamera::controls::ExposureTimeModeManual) == libcamera::controls::ExposureTimeModeAuto;',
     'd->automatic_ = (controls ? controls->get(libcamera::controls::ExposureTimeMode) : std::nullopt).value_or(d->controlInfo_.at(&libcamera::controls::ExposureTimeMode).def().get<int32_t>()) == libcamera::controls::ExposureTimeModeAuto;')
edit('ipa/camss.cpp','''  if (!root || (*root)["version"].get<unsigned int>().value_or(0) != 1 ||
      (*root)["sensor_model"].get<std::string>().value_or("") != model_) return -EINVAL;
  auto subtraction = (*root)["residual_black_subtraction"].get<uint16_t>();''','''  if (!root || (*root)["sensor_model"].get<std::string>().value_or("") != model_) return -EINVAL;
  const unsigned int version=(*root)["version"].get<unsigned int>().value_or(0);
  const ValueNode *selected=root.get();
  if (version==2) {
   const auto &modes=(*root)["modes"];
   if (!modes.isList()) return -EINVAL;
   selected=nullptr;
   for (const auto &mode:modes.asList()) {
    const auto &match=mode["match"];
    if (!mode.isDictionary() || !match.isDictionary()) return -EINVAL;
    if (match["width"].get<unsigned int>().value_or(0)!=input.width ||
        match["height"].get<unsigned int>().value_or(0)!=input.height ||
        match["pixel_rate"].get<unsigned int>().value_or(0)!=info.pixelRate ||
        match["line_length"].get<unsigned int>().value_or(0)!=info.minLineLength ||
        match["frame_length"].get<unsigned int>().value_or(0)!=info.minFrameLength) continue;
    if (selected) return -EINVAL;
    selected=&mode;
   }
   if (!selected) return -ENOTSUP;
  } else if (version!=1) return -EINVAL;
  const ValueNode &tuning=*selected;
  auto subtraction = tuning["residual_black_subtraction"].get<uint16_t>();''')
for field in ['range_normalization','awb','sensor_controls','agc']:
    edit('ipa/camss.cpp','(*root)["'+field+'"]','tuning["'+field+'"]')
edit('ipa/camss.cpp','map[&controls::AwbEnable] = ControlInfo(false, true, false);',
     'map[&controls::AwbEnable] = ControlInfo(false, true, true);')
edit('ipa/camss.cpp','int32_t(controls::ExposureTimeModeAuto), int32_t(controls::ExposureTimeModeManual)}, int32_t(controls::ExposureTimeModeManual));',
     'int32_t(controls::ExposureTimeModeAuto), int32_t(controls::ExposureTimeModeManual)}, int32_t(controls::ExposureTimeModeAuto));')
edit('ipa/camss.cpp','int32_t(controls::AnalogueGainModeAuto), int32_t(controls::AnalogueGainModeManual)}, int32_t(controls::AnalogueGainModeManual));',
     'int32_t(controls::AnalogueGainModeAuto), int32_t(controls::AnalogueGainModeManual)}, int32_t(controls::AnalogueGainModeAuto));')
edit('ipa/camss.cpp','const int32_t exposureMode = controls.get(controls::ExposureTimeMode).value_or(controls::ExposureTimeModeManual);',
     'const int32_t exposureMode = controls.get(controls::ExposureTimeMode).value_or(autoAvailable_ ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual);')
edit('ipa/camss.cpp','const int32_t gainMode = controls.get(controls::AnalogueGainMode).value_or(controls::AnalogueGainModeManual);',
     'const int32_t gainMode = controls.get(controls::AnalogueGainMode).value_or(autoAvailable_ ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual);')
edit('ipa/camss.cpp','const bool awbEnabled = controls.get(controls::AwbEnable).value_or(false);',
     'const bool awbEnabled = controls.get(controls::AwbEnable).value_or(bool(awb_));')
edit('build-candidate.py',"'stage':311","'stage':312")
# The test has several references to the same private stage directory.
p=HERE/'test-ipa.py';p.write_text(p.read_text().replace('camss311-contract','camss312-contract').replace("'stage':311","'stage':312"))
print('Prepared explicit sensorConfig, mode catalogs and standard IPA lookup/default auto controls.')
