from pathlib import Path
import json, shutil
import storage

HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
for name in ['hardware_agc.cpp','hardware_agc.h','exposure_program.cpp','exposure_program.h']:
    shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name)
changed=[]
def edit(name,old,new):
    p=tree/name;s=p.read_text();assert old in s,(name,old);p.write_text(s.replace(old,new));changed.append(name)
cam='src/ipa/camss-vfe/camss.cpp'
edit(cam,'afEnabled_=false;af_.cancel();frameLength_=info.minFrameLength;', '''afEnabled_=false;af_.cancel();frameLength_=info.minFrameLength;
 /* These drivers reset VBLANK to its default when selecting a mode. Their
  * exposure control maximum already includes the integration-time margin. */
 if (auto blanking=sensorControls.find(V4L2_CID_VBLANK);blanking!=sensorControls.end()) {
  int32_t lines=blanking->second.def().get<int32_t>();
  if(lines<0 || uint64_t(input.height)+lines>UINT32_MAX)return -ERANGE;
  frameLength_=input.height+lines;
 }''')
edit(cam,'ret = candidate->initialise(agc, lineUs_, minLines_, maxLines_, minGain_, maxGain_, helper_.get());',
 '''ret = candidate->initialise(agc, lineUs_, minLines_, maxLines_, minGain_, maxGain_, helper_.get(),
    tuning["exposure_program"], std::llround(frameLength_*lineUs_*1000), minGainCode_, maxGainCode_);''')
edit(cam,'   agc_ = std::move(candidate);\n   autoAvailable_ = true;', '''   agc_ = std::move(candidate);
   autoAvailable_ = true;''')
needle='''   map[&controls::AnalogueGainMode] = ControlInfo(std::vector<ControlValue>{
    int32_t(controls::AnalogueGainModeAuto), int32_t(controls::AnalogueGainModeManual)}, int32_t(controls::AnalogueGainModeAuto));'''
edit(cam,needle,needle+'''
   map[&controls::ExposureValue] = ControlInfo(-8.0f, 8.0f, 0.0f);
   if (agc_->hasExposureProgram()) {
    map[&controls::AeFlickerMode] = ControlInfo(std::vector<ControlValue>{
     int32_t(controls::FlickerOff),int32_t(controls::FlickerManual)},int32_t(controls::FlickerOff));
    map[&controls::AeFlickerPeriod] = ControlInfo(int32_t(0),int32_t(INT32_MAX),int32_t(0));
   }''')
edit(cam,' if (!sensorControls) return -EINVAL;\n ControlList translated(sensorControls_);', ''' if (!sensorControls) return -EINVAL;
 if (agc_) {int ret=agc_->validateControls(controls);if(ret)return ret;}
 else for(const auto &[id,value]:controls)if(HardwareAgc::algorithmControl(id))return -ENOTSUP;
 ControlList translated(sensorControls_);''')
edit(cam,' for (const auto &[id, value] : controls) {\n  if (id==libcamera::controls::AfMode.id()',
 ''' for (const auto &[id, value] : controls) {
  if (HardwareAgc::algorithmControl(id)) continue;
  if (id==libcamera::controls::AfMode.id()''')
edit(cam,'if (id != libcamera::controls::ColourCorrectionMatrix.id() &&',
 'if (!HardwareAgc::algorithmControl(id) && id != libcamera::controls::ColourCorrectionMatrix.id() &&')
needle=''' if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue && temperature == current.colourTemperature && manualMatrix == manualMatrix_ && sameColourCorrection(current.colourCorrection,selected) && sameLensShading(current.lensShading,selectedLsc)) return 0;
 if (ispRevision_ >= UINT32_MAX-1) return -EOVERFLOW;'''
edit(cam,needle,''' const bool unchanged=enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue && temperature == current.colourTemperature && manualMatrix == manualMatrix_ && sameColourCorrection(current.colourCorrection,selected) && sameLensShading(current.lensShading,selectedLsc);
 if (!unchanged && ispRevision_ >= UINT32_MAX-1) return -EOVERFLOW;
 if (agc_) {ret=agc_->applyControls(controls);if(ret)return ret;}
 if (unchanged) return 0;''')
edit(cam,' if (agc_) agc_->resetFrameCount();',' if (agc_) {ret=agc_->resetControls();if(ret)return ret;ret=agc_->applyControls(controls);if(ret)return ret;}')
edit(cam,' metadata->set(controls::AnalogueGain,float(helper_->gain(sensorContext.gainCode)));',
 ' metadata->set(controls::AnalogueGain,float(helper_->gain(sensorContext.gainCode)));\n if (agc_) agc_->metadata(metadata);')
pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
old='request->controls().contains(controls::ColourCorrectionMatrix.id());'
new='request->controls().contains(controls::ColourCorrectionMatrix.id()) || request->controls().contains(controls::ExposureValue.id()) || request->controls().contains(controls::AeFlickerMode.id()) || request->controls().contains(controls::AeFlickerPeriod.id());'
edit(pipeline,old,new)
edit(pipeline,'Runtime WB control failed: ','Runtime algorithm control failed: ')
edit(pipeline,'"WB request epoch="','"Algorithm request epoch="')
baseline=tree.parents[2]/'libcamera342-r27-built/src/libcamera-v0.7.2'
assert baseline.exists()
all_changed=[str(p.relative_to(tree)) for area in ['src/ipa/camss-vfe','src/ipa/libipa','src/libcamera/pipeline/camss-vfe'] for p in (tree/area).glob('*') if p.is_file() and (not (baseline/p.relative_to(tree)).exists() or p.read_bytes()!=(baseline/p.relative_to(tree)).read_bytes())]
(HERE/'source-state.json').write_text(json.dumps(dict(stage=359,source=str(tree),baseline=str(baseline),baseline_installed_package_stage=342,
    changed=sorted(all_changed),preparation_metadata_shadowing_error_repaired_without_recopying_source=True,installed=False),indent=2)+'\n')
print('Connected selected exposure policy, sensor budget, and SOF-ordered EV/manual-flicker controls.')
