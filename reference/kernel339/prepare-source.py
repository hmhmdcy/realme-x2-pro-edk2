from pathlib import Path
import json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;OLD=storage.SDK/'work/libcamera335-ccm-built';NEW=storage.candidate()
assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=NEW/'src/libcamera-v0.7.2';changed=[]
def edit(name,a,b):
 p=tree/name;s=p.read_text();assert a in s,(name,a);p.write_text(s.replace(a,b));changed.append(name)
for name in ['aec_lux.cpp','aec_lux.h','aec_bayer_luma.cpp','aec_bayer_luma.h']:
 shutil.copyfile(HERE.parent/'kernel337/libipa'/name,tree/'src/ipa/libipa'/name);changed.append('src/ipa/libipa/'+name)
for name in ['lux_profile.cpp','lux_profile.h']:
 shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name);changed.append('src/ipa/camss-vfe/'+name)
edit('src/ipa/libipa/meson.build',"    'colour_correction.cpp',","    'colour_correction.cpp',\n    'aec_lux.cpp',\n    'aec_bayer_luma.cpp',")
edit('src/ipa/camss-vfe/meson.build',"'colour_correction_profile.cpp']","'colour_correction_profile.cpp', 'lux_profile.cpp']")
edit('include/libcamera/ipa/camss.mojom','\tarray<double> rgbMeans;','\tarray<double> rgbMeans;\n\tbool luxValid;\n\tfloat exposureIndex;\n\tfloat luxLuma;\n\tfloat luxIndex;')
p='src/ipa/camss-vfe/camss.cpp'
edit(p,'#include "colour_correction_profile.h"','#include "colour_correction_profile.h"\n#include "lux_profile.h"')
edit(p,' std::optional<ColourMatrix> manualMatrix_;',' std::optional<ColourMatrix> manualMatrix_;\n std::optional<LuxProfile> lux_;')
edit(p,'colourCorrection_.reset(); manualMatrix_.reset();','colourCorrection_.reset(); manualMatrix_.reset(); lux_.reset();')
edit(p,'  ret=ColourCorrectionProfile::configure(tuning["colour_correction"],&colourCorrection_);','  ret=LuxProfile::configure(tuning["aec_lux"],&lux_);\n  if (ret) return ret;\n  ret=ColourCorrectionProfile::configure(tuning["colour_correction"],&colourCorrection_);')
edit(p,' if (agc_) agc_->resetFrameCount();',' if (agc_) agc_->resetFrameCount();\n if (lux_) lux_->reset();')
edit(p,'\trunning_ = false;af_.cancel();initialAfTrigger_.reset();','\trunning_ = false;af_.cancel();initialAfTrigger_.reset();\n if (lux_) lux_->reset();')
needle=' if (af_.state()!=ipa::ContrastAf::State::Scanning && automatic_ && effective_ && result.sensorControlsKnown &&'
edit(p,needle,''' if (lux_ && result.parametersKnown && result.sensorControlsKnown && result.rgbPresent) {
  LuxResult observation;
  const uint64_t exposureNs=std::llround(sensorContext.exposureLines * lineUs_ * 1000);
  result.luxValid=lux_->calculate(parsed.grid,float(helper_->gain(sensorContext.gainCode)),exposureNs,
                                float(context->second.red),float(context->second.blue),&observation);
  if (result.luxValid) {
   result.exposureIndex=observation.exposureIndex;result.luxLuma=observation.luma;result.luxIndex=observation.index;
   LOG(IPACamss,Info)<<"LUX epoch="<<epoch<<" sof="<<sof<<" revision="<<result.ispRevision
    <<" lines="<<sensorContext.exposureLines<<" gain-code="<<sensorContext.gainCode
    <<" exposure-ns="<<exposureNs<<" analogue-gain="<<float(helper_->gain(sensorContext.gainCode))
    <<" red="<<float(context->second.red)<<" blue="<<float(context->second.blue)
    <<" exposure-index="<<result.exposureIndex<<" luma="<<result.luxLuma<<" index="<<result.luxIndex;
  }
 }
'''+needle)
for name in sorted(set(changed)):
 relative=Path('libipa' if '/libipa/' in name else 'framework' if '/include/' in '/'+name else 'ipa')/Path(name).name
 (HERE/relative).parent.mkdir(exist_ok=True);shutil.copyfile(tree/name,HERE/relative)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=339,source=str(tree),baseline=str(OLD/'src/libcamera-v0.7.2'),changed_sources=sorted(set(changed)),installed=False,optional_runtime_lux=True,default_profiles_changed=False,physical_mode_factory_binding_verified=False,public_lux_control_used=False,source_requires_build_image_mounted=True),indent=2)+'\n')
print('Prepared optional runtime Bayer/exposure/lux path on E-drive source; no defaults changed.')
