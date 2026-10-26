"""Prepare an isolated r26-derived core/IPA with optional calibrated manual CCT."""
from pathlib import Path
import json, shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
OLD=SDK/'work/libcamera321-lsc-built';NEW=SDK/'work/libcamera330-wb-built';SRC='src/libcamera-v0.7.2'
assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
tree=NEW/SRC
def change(text,old,new):
 assert old in text,old
 return text.replace(old,new)

for name in ['awb_calibration.cpp','awb_calibration.h']:
 (HERE/'libipa').mkdir(exist_ok=True)
 shutil.copyfile(HERE.parent/'kernel329/libipa'/name,HERE/'libipa'/name)
 shutil.copyfile(HERE/'libipa'/name,tree/'src/ipa/libipa'/name)
p=tree/'src/ipa/libipa/meson.build';s=p.read_text()
s=change(s,"    'awb.cpp',","    'awb.cpp',\n    'awb_calibration.cpp',");p.write_text(s)
shutil.copyfile(p,HERE/'libipa/meson.build')
for name in ['white_balance_reference.h','white_balance_reference.cpp']:
 shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name)
p=tree/'src/ipa/camss-vfe/meson.build';s=p.read_text()
s=change(s,"'lens_shading.cpp']","'lens_shading.cpp', 'white_balance_reference.cpp']");p.write_text(s)
shutil.copyfile(p,HERE/'ipa/meson.build')
p=tree/'src/ipa/camss-vfe/camss.cpp';s=p.read_text()
s=change(s,'#include "lens_shading.h"','#include "lens_shading.h"\n#include "white_balance_reference.h"')
s=change(s,'std::optional<camss_params_lsc> lensShading_;','std::optional<camss_params_lsc> lensShading_;\n std::optional<WhiteBalanceReference> whiteBalance_;\n std::optional<int32_t> colourTemperature_;')
s=change(s,'double sourceRed, sourceBlue; };','double sourceRed, sourceBlue; std::optional<int32_t> colourTemperature; };')
s=change(s,'profile_ = { 0, 1.0 }; lensShading_.reset();','profile_ = { 0, 1.0 }; lensShading_.reset(); whiteBalance_.reset(); colourTemperature_.reset();')
needle='  ret=configureLensShading(tuning["lens_shading"],input,&lensShading_);\n  if (ret) return ret;'
s=change(s,needle,needle+'''
  ret=WhiteBalanceReference::configure(tuning["white_balance_reference"],&whiteBalance_);
  if (ret) return ret;
  if (whiteBalance_) {
   ControlInfoMap::Map map;
   for (const auto &[id,value]:*ipaControls) map.emplace(id,value);
   map[&controls::ColourTemperature]=ControlInfo(int32_t(1500),int32_t(12000),int32_t(6500));
   *ipaControls=ControlInfoMap(std::move(map),controls::controls);
  }''')
s=change(s,'<< " lsc=" << bool(lensShading_);','<< " lsc=" << bool(lensShading_) << " white-balance-reference=" << bool(whiteBalance_);')
s=change(s,'  if (id == controls::ColourGains.id()) {','''  if (id == controls::ColourTemperature.id()) {
   if (!whiteBalance_) return -ENOTSUP;
   if (value.type()!=ControlTypeInteger32 || value.isArray()) return -EINVAL;
   if (value.get<int32_t>()<1500 || value.get<int32_t>()>12000) return -ERANGE;
   continue;
  }
  if (id == controls::ColourGains.id()) {''')
s=change(s,'id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id()',
 'id != libcamera::controls::ColourTemperature.id() && id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id()')
old=''' double red = current.sourceRed, blue = current.sourceBlue;
 if (!enabled) {
  auto gains = controls.get(libcamera::controls::ColourGains);
  if (gains) { red=(*gains)[0];blue=(*gains)[1]; }
 }
 if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue) return 0;'''
new=''' double red = current.sourceRed, blue = current.sourceBlue;
 auto temperature = current.colourTemperature;
 if (enabled) temperature.reset();
 else {
  auto gains = controls.get(libcamera::controls::ColourGains);
  auto kelvin = controls.get(libcamera::controls::ColourTemperature);
  if (gains) {
   red=(*gains)[0];blue=(*gains)[1];temperature=kelvin;
  } else if (kelvin) {
   int status=whiteBalance_->gains(*kelvin,&red,&blue);
   if (status) return status;
   temperature=kelvin;
  }
 }
 if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue && temperature == current.colourTemperature) return 0;'''
s=change(s,old,new)
s=change(s,' awbEnabled_ = enabled;',' awbEnabled_ = enabled; colourTemperature_ = temperature;')
needle=' metadata->set(controls::AwbEnable,context->second.awbEnabled);'
s=change(s,needle,needle+'\n if (context->second.colourTemperature) metadata->set(controls::ColourTemperature,*context->second.colourTemperature);')
needle='\talignas(8) std::array<uint8_t,'
at=s.index(needle,s.index('int IPACamss::start('))
s=s[:at]+''' auto temperature = awbEnabled ? std::nullopt : controls.get(libcamera::controls::ColourTemperature);
 if (temperature && !controls.contains(libcamera::controls::ColourGains.id())) {
  int status=whiteBalance_->gains(*temperature,&red,&blue);
  if (status) return status;
 }
'''+s[at:]
s=change(s,'\tawbEnabled_ = awbEnabled;','\tawbEnabled_ = awbEnabled; colourTemperature_ = temperature;')
s=change(s,'\tawbEnabled_ = false; pendingWhiteBalance_.reset();','\tawbEnabled_ = false; colourTemperature_.reset(); pendingWhiteBalance_.reset();')
s=change(s,'{ revision, effectiveRed, effectiveBlue, awbEnabled_, red, blue };','{ revision, effectiveRed, effectiveBlue, awbEnabled_, red, blue, colourTemperature_ };')
needle='\tmetadata.set(controls::AwbEnable, result.parametersKnown && context->second.awbEnabled);'
s=change(s,needle,needle+'\n if (result.parametersKnown && context->second.colourTemperature) metadata.set(controls::ColourTemperature,*context->second.colourTemperature);')
p.write_text(s);shutil.copyfile(p,HERE/'ipa/camss.cpp')
p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';s=p.read_text()
s=change(s,'request->controls().contains(controls::ColourGains.id());','request->controls().contains(controls::ColourGains.id()) || request->controls().contains(controls::ColourTemperature.id());')
p.write_text(s);(HERE/'framework').mkdir();shutil.copyfile(p,HERE/'framework/camss_vfe.cpp')
p=tree/'src/libcamera/control_ids_core.yaml';s=p.read_text()
s=change(s,'  - ColourTemperature:\n      type: int32_t\n      direction: out','  - ColourTemperature:\n      type: int32_t\n      direction: inout')
p.write_text(s);shutil.copyfile(p,HERE/'framework/control_ids_core.yaml')
report=dict(stage=330,source=str(tree),baseline=str(OLD/SRC),installed=False,default_profiles_changed=False,
 wb_calibration_math_stage=329,manual_cct_forward_control_implemented=True,inverse_cct_and_ccm_pending=True)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
