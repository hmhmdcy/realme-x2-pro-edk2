"""Couple the optional full CCM tree to acknowledged WB/CCT revisions."""
from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
OLD=SDK/'work/libcamera332-cct-built';NEW=SDK/'work/libcamera335-ccm-built';SRC='src/libcamera-v0.7.2'
assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
tree=NEW/SRC;changed=[]
def edit(name,a,b):
 p=tree/name;s=p.read_text();assert a in s,(name,a);p.write_text(s.replace(a,b));changed.append(name)
for area,names in [('libipa',['colour_correction.cpp','colour_correction.h']),('camss-vfe',['colour_correction_profile.cpp','colour_correction_profile.h'])]:
 for name in names:
  source=HERE.parent/'kernel333/libipa'/name if area=='libipa' else HERE/'ipa'/name
  dest=tree/'src/ipa'/area/name;shutil.copyfile(source,dest);changed.append(str(dest.relative_to(tree)))
edit('src/ipa/libipa/meson.build',"    'awb_colour_temperature.cpp',","    'awb_colour_temperature.cpp',\n    'colour_correction.cpp',")
edit('src/ipa/camss-vfe/meson.build',"'white_balance_reference.cpp']","'white_balance_reference.cpp', 'colour_correction_profile.cpp']")
edit('src/ipa/camss-vfe/parameter_encoder.h','const camss_params_lsc *lsc = nullptr);','const camss_params_lsc *lsc = nullptr,\n\t\t     const camss_params_color_correct *ccm = nullptr);')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','const camss_params_lsc *lsc)','const camss_params_lsc *lsc, const camss_params_color_correct *ccm)')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','(lsc ? sizeof(*lsc) : 0);','(lsc ? sizeof(*lsc) : 0) + (ccm ? sizeof(*ccm) : 0);')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','\t*bytesused = params.bytesused();',''' if (ccm) {
  auto block = params.block<CamssBlocks::ColorCorrect>();
  block.setEnabled(true);
  std::memcpy(&block->a, &ccm->a, sizeof(*ccm) - sizeof(ccm->header));
 }
\t*bytesused = params.bytesused();''')
p='src/ipa/camss-vfe/camss.cpp'
edit(p,'#include "white_balance_reference.h"','#include "white_balance_reference.h"\n#include "colour_correction_profile.h"')
edit(p,'colourTemperature, estimatedColourTemperature; };','colourTemperature, estimatedColourTemperature; std::optional<ColourCorrectionState> colourCorrection; };')
edit(p,' std::optional<int32_t> colourTemperature_;',''' std::optional<int32_t> colourTemperature_;
 std::optional<ColourCorrectionProfile> colourCorrection_;
 std::optional<ColourMatrix> manualMatrix_;
 int selectColourCorrection(double red, double blue, std::optional<int32_t> temperature,
                            const std::optional<ColourMatrix> &manualMatrix,
                            const ColourCorrectionState *fallback,
                            std::optional<ColourCorrectionState> *state) const;''')
edit(p,'profile_ = { 0, 1.0 }; lensShading_.reset(); whiteBalance_.reset(); colourTemperature_.reset();','profile_ = { 0, 1.0 }; lensShading_.reset(); whiteBalance_.reset(); colourTemperature_.reset(); colourCorrection_.reset(); manualMatrix_.reset();')
needle='  ret=configureAutofocus(tuning["autofocus"].isEmpty()?(*root)["autofocus"]:tuning["autofocus"],ipaControls);'
edit(p,needle,'''  ret=ColourCorrectionProfile::configure(tuning["colour_correction"],&colourCorrection_);
  if (ret) return ret;
  if (colourCorrection_) {
   ControlInfoMap::Map map;
   for (const auto &[id,value]:*ipaControls) map.emplace(id,value);
   const std::array<float,9> minimum{colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum(),colourCorrection_->minimum()};
   const std::array<float,9> maximum{colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum(),colourCorrection_->maximum()};
   const std::array<float,9> identity{1,0,0,0,1,0,0,0,1};
   map[&controls::ColourCorrectionMatrix]=ControlInfo(ControlValue(Span<const float,9>(minimum)),ControlValue(Span<const float,9>(maximum)),ControlValue(Span<const float,9>(identity)));
   *ipaControls=ControlInfoMap(std::move(map),controls::controls);
  }
'''+needle)
edit(p,'  if (id == controls::ColourTemperature.id()) {','''  if (id == controls::ColourCorrectionMatrix.id()) {
   if (!colourCorrection_) return -ENOTSUP;
   if (value.type()!=ControlTypeFloat || !value.isArray() || value.numElements()!=9) return -EINVAL;
   ColourCorrectionState check;
   int status=colourCorrection_->manual(value.get<Span<const float>>(),&check);
   if (status) return status;
   continue;
  }
  if (id == controls::ColourTemperature.id()) {''')
edit(p,'if (id != libcamera::controls::ColourTemperature.id() &&','if (id != libcamera::controls::ColourCorrectionMatrix.id() && id != libcamera::controls::ColourTemperature.id() &&')
needle='int IPACamss::applyIspControls('
s=(tree/p).read_text();at=s.index(needle)
s=s[:at]+'''int IPACamss::selectColourCorrection(double red, double blue, std::optional<int32_t> temperature,
 const std::optional<ColourMatrix> &manualMatrix, const ColourCorrectionState *fallback,
 std::optional<ColourCorrectionState> *state) const
{
 state->reset();
 if (!colourCorrection_) return 0;
 double effectiveRed, effectiveBlue;
 int ret=effectiveColourGains(profile_,red,blue,&effectiveRed,&effectiveBlue);
 if (ret) return ret;
 if (!temperature && whiteBalance_) temperature=whiteBalance_->temperature(effectiveRed,effectiveBlue);
 ColourCorrectionState result;
 ret=colourCorrection_->select(temperature,manualMatrix,fallback,&result);
 if (!ret) *state=result;
 return ret;
}

'''+s[at:];(tree/p).write_text(s)
edit(p,' if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue && temperature == current.colourTemperature) return 0;',''' auto manualMatrix=manualMatrix_;
 if (enabled) manualMatrix.reset();
 else if (auto requested=controls.get(libcamera::controls::ColourCorrectionMatrix)) {
  ColourMatrix matrix;std::copy(requested->begin(),requested->end(),matrix.begin());manualMatrix=matrix;
 } else if (controls.contains(libcamera::controls::ColourTemperature.id()) || controls.contains(libcamera::controls::ColourGains.id())) manualMatrix.reset();
 std::optional<ColourCorrectionState> selected;
 ret=selectColourCorrection(red,blue,temperature,manualMatrix,current.colourCorrection ? &*current.colourCorrection : nullptr,&selected);
 if (ret) return ret;
 if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue && temperature == current.colourTemperature && manualMatrix == manualMatrix_) return 0;''')
edit(p,'awbEnabled_ = enabled; colourTemperature_ = temperature;','awbEnabled_ = enabled; colourTemperature_ = temperature; manualMatrix_ = manualMatrix;')
edit(p,' metadata->set(controls::AwbLocked,false);',''' if (context->second.colourCorrection)
  metadata->set(controls::ColourCorrectionMatrix,Span<const float,9>(context->second.colourCorrection->effective));
 metadata->set(controls::AwbLocked,false);''')
edit(p,'+ sizeof(camss_params_lsc)> packet;','+ sizeof(camss_params_lsc) + sizeof(camss_params_color_correct)> packet;')
edit(p,'\tsize_t used;\n\tint ret = encodeParameters(packet,',''' std::optional<ColourMatrix> manualMatrix;
 if (!awbEnabled) if (auto requested=controls.get(libcamera::controls::ColourCorrectionMatrix)) {
  ColourMatrix matrix;std::copy(requested->begin(),requested->end(),matrix.begin());manualMatrix=matrix;
 }
 std::optional<ColourCorrectionState> selected;
 int ret=selectColourCorrection(red,blue,temperature,manualMatrix,nullptr,&selected);
 if (ret) return ret;
 camss_params_color_correct ccm{};
 if (selected) {
  const auto &params=selected->parameters;
  std::copy(params.a.begin(),params.a.end(),ccm.a);std::copy(params.b.begin(),params.b.end(),ccm.b);
  std::copy(params.c.begin(),params.c.end(),ccm.c);std::copy(params.k.begin(),params.k.end(),ccm.k);ccm.qfactor=params.qfactor;
 }
\tsize_t used;
\tret = encodeParameters(packet,''')
edit(p,'&used, lensShading_ ? &*lensShading_ : nullptr);','&used, lensShading_ ? &*lensShading_ : nullptr, selected ? &ccm : nullptr);')
edit(p,'awbEnabled_ = awbEnabled; colourTemperature_ = temperature;','awbEnabled_ = awbEnabled; colourTemperature_ = temperature; manualMatrix_ = manualMatrix;')
edit(p,'awbEnabled_ = false; colourTemperature_.reset(); pendingWhiteBalance_.reset();','awbEnabled_ = false; colourTemperature_.reset(); manualMatrix_.reset(); pendingWhiteBalance_.reset();')
edit(p,'\tsize_t used;\n\tret = encodeParameters(it->second.memory', ''' std::optional<ColourCorrectionState> selected;
 const ColourCorrectionState *fallback=nullptr;
 if (!parameterHistory_.empty() && parameterHistory_.rbegin()->second.colourCorrection) fallback=&*parameterHistory_.rbegin()->second.colourCorrection;
 ret=selectColourCorrection(red,blue,colourTemperature_,manualMatrix_,fallback,&selected);
 if (ret) return ret;
 camss_params_color_correct ccm{};
 if (selected) {
  const auto &params=selected->parameters;
  std::copy(params.a.begin(),params.a.end(),ccm.a);std::copy(params.b.begin(),params.b.end(),ccm.b);
  std::copy(params.c.begin(),params.c.end(),ccm.c);std::copy(params.k.begin(),params.k.end(),ccm.k);ccm.qfactor=params.qfactor;
 }
\tsize_t used;
\tret = encodeParameters(it->second.memory''')
edit(p,'&used, revision==0 && lensShading_ ? &*lensShading_ : nullptr);','&used, revision==0 && lensShading_ ? &*lensShading_ : nullptr, selected ? &ccm : nullptr);')
edit(p,'whiteBalance_->temperature(effectiveRed,effectiveBlue) : std::nullopt };','whiteBalance_->temperature(effectiveRed,effectiveBlue) : std::nullopt, selected };')
edit(p,'\tmetadata.set(controls::AwbLocked, false);',''' if (result.parametersKnown && context->second.colourCorrection)
  metadata.set(controls::ColourCorrectionMatrix,Span<const float,9>(context->second.colourCorrection->effective));
\tmetadata.set(controls::AwbLocked, false);''')
edit('src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','request->controls().contains(controls::ColourTemperature.id())','request->controls().contains(controls::ColourTemperature.id()) || request->controls().contains(controls::ColourCorrectionMatrix.id())')
for name in sorted(set(changed)):
 relative=Path('libipa' if '/libipa/' in name else 'framework' if '/pipeline/' in name else 'ipa')/Path(name).name
 (HERE/relative).parent.mkdir(exist_ok=True);shutil.copyfile(tree/name,HERE/relative)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=335,source=str(tree),baseline=str(OLD/SRC),installed=False,changed_sources=sorted(set(changed)),default_profiles_changed=False,ccm_cct_coupled=True,aec_drc_hdr_led_reference_inputs=True,kernel_source_changes=False),indent=2)+'\n')
print('Prepared optional full-tree CCM coupling; deployed defaults unchanged.')
