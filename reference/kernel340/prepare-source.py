"""Snapshot each runtime CCM proposal together with its WB revision."""
from pathlib import Path
import importlib.util,json,shutil
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage339',HERE.parent/'kernel339/storage.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
OLD=old.candidate();NEW=OLD.parent/'libcamera340-runtime-ccm-built';assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
storage=(HERE.parent/'kernel339/storage.py').read_text().replace('libcamera339-lux-built','libcamera340-runtime-ccm-built');(HERE/'storage.py').write_text(storage)
tree=NEW/'src/libcamera-v0.7.2';changed=[]
def edit(name,a,b):
 p=tree/name;s=p.read_text();assert a in s,(name,a);p.write_text(s.replace(a,b));changed.append(name)
h='src/ipa/camss-vfe/colour_correction_profile.h';p='src/ipa/camss-vfe/colour_correction_profile.cpp';cam='src/ipa/camss-vfe/camss.cpp'
edit(h,'struct ColourCorrectionState {','''struct ColourCorrectionInputs {
 std::optional<float> luxIndex, analogueGain;
 uint32_t statisticsSof;
};
struct ColourCorrectionState {''')
edit(h,'\tColourMatrix effective;','\tColourMatrix effective;\n std::optional<float> aecValue;\n std::optional<int32_t> temperature;\n std::optional<uint32_t> statisticsSof;')
edit(h,'ColourCorrectionState *fallback, ColourCorrectionState *state) const;','ColourCorrectionState *fallback, ColourCorrectionState *state,\n            const ColourCorrectionInputs *runtime = nullptr) const;\n bool runtimeAec() const { return runtimeAec_; }\n bool requiresLux() const { return runtimeAec_ && aecPosition_ == 0; }')
edit(h,'unsigned int level, float kelvin,','unsigned int level, float kelvin, float aecValue,')
edit(h,'\tfloat drcGain_ = 1,',' bool runtimeAec_ = false;\n\tfloat drcGain_ = 1,')
edit(p,'ColourCorrectionState *state) const\n{\n\tif (manualMatrix)','ColourCorrectionState *state, const ColourCorrectionInputs *runtime) const\n{\n\tif (manualMatrix)')
edit(p,'\tif (!kelvin) {',''' std::optional<float> aec = aecValue_;
 if (runtimeAec_) aec = runtime ? (aecPosition_ == 0 ? runtime->luxIndex : runtime->analogueGain) : std::nullopt;
 if (aec && !std::isfinite(*aec)) return -ERANGE;
\tif (!kelvin || !aec) {''')
edit(p,'\tint ret = evaluate(core_, 0, float(*kelvin), &data);\n\treturn ret ? ret : encode(data, state);',''' int ret = evaluate(core_, 0, float(*kelvin), *aec, &data);
 if (ret) return ret;
 ret = encode(data, state);
 if (!ret) {
  state->aecValue = aec; state->temperature = kelvin;
  if (runtimeAec_ && runtime) state->statisticsSof = runtime->statisticsSof;
 }
 return ret;''')
edit(p,'unsigned int level, float kelvin,','unsigned int level, float kelvin, float aecValue,')
edit(p,'evaluate(node.children, level + 1, kelvin, output)','evaluate(node.children, level + 1, kelvin, aecValue, output)')
edit(p,'level == 3 ? aecValue_ : kelvin','level == 3 ? aecValue : kelvin')
edit(p,'\t/* These coordinates are explicit references until their corresponding',''' const auto source = tuning["aec_source"].get<std::string>("reference");
 if (source != "reference" && source != "runtime") return -EINVAL;
 result.runtimeAec_ = source == "runtime";
\t/* DRC, HDR and flash coordinates remain explicit references; the AEC
  * coordinate may come from the per-frame runtime observation. Other''')
edit(p,'\tif (!drc || !ratio || !aecValue || !led ||',' if (result.runtimeAec_ && !aecValue) aecValue = 0.f;\n\tif (!drc || !ratio || !aecValue || !led ||')
edit(p,'result.evaluate(result.core_, 0, 6500, &probe)','result.evaluate(result.core_, 0, 6500, result.aecValue_, &probe)')
edit(cam,'#include <array>','#include <array>\n#include <bit>')
edit(cam,' std::optional<LuxProfile> lux_;',''' std::optional<LuxProfile> lux_;
 std::optional<ColourCorrectionInputs> ccmInputs_;
 std::optional<ColourCorrectionState> pendingColourCorrection_;''')
edit(cam,'std::optional<ColourCorrectionState> *state) const;','std::optional<ColourCorrectionState> *state,\n                            const ColourCorrectionInputs *runtime = nullptr) const;')
edit(cam,'std::optional<ColourCorrectionState> *state) const\n{','std::optional<ColourCorrectionState> *state, const ColourCorrectionInputs *runtime) const\n{')
edit(cam,'colourCorrection_->select(temperature,manualMatrix,fallback,&result)','colourCorrection_->select(temperature,manualMatrix,fallback,&result,runtime)')
# Hardware equality includes offsets and qfactor; changes below quantization
# do not enqueue another kernel packet just to replace bookkeeping.
needle='int IPACamss::applyIspControls('
s=(tree/cam).read_text();at=s.index(needle);s=s[:at]+'''static bool sameColourCorrection(const std::optional<ColourCorrectionState> &a,
                                 const std::optional<ColourCorrectionState> &b)
{
 if (bool(a) != bool(b)) return false;
 if (!a) return true;
 const auto &x=a->parameters, &y=b->parameters;
 return x.a==y.a && x.b==y.b && x.c==y.c && x.k==y.k && x.qfactor==y.qfactor;
}

'''+s[at:];(tree/cam).write_text(s);changed.append(cam)
edit(cam,'manualMatrix,current.colourCorrection ? &*current.colourCorrection : nullptr,&selected);','manualMatrix,current.colourCorrection ? &*current.colourCorrection : nullptr,&selected,ccmInputs_ ? &*ccmInputs_ : nullptr);')
edit(cam,'&& manualMatrix == manualMatrix_) return 0;','&& manualMatrix == manualMatrix_ && sameColourCorrection(current.colourCorrection,selected)) return 0;')
edit(cam,' pendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, red, blue };',' pendingColourCorrection_ = selected;\n pendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, red, blue };')
edit(cam,' if (lux_) lux_->reset();',' if (lux_) lux_->reset();\n ccmInputs_.reset();pendingColourCorrection_.reset();')
edit(cam,'  ret=configureAutofocus(tuning["autofocus"]','  if (colourCorrection_ && colourCorrection_->requiresLux() && !lux_) return -EINVAL;\n  ret=configureAutofocus(tuning["autofocus"]')
edit(cam,' ret=selectColourCorrection(red,blue,colourTemperature_,manualMatrix_,fallback,&selected);',''' if (revision) selected=pendingColourCorrection_;
 else ret=selectColourCorrection(red,blue,colourTemperature_,manualMatrix_,fallback,&selected);''')
edit(cam,'if (pendingWhiteBalance_ && pendingWhiteBalance_->revision == revision) pendingWhiteBalance_.reset();','''if (pendingWhiteBalance_ && pendingWhiteBalance_->revision == revision) {
  pendingWhiteBalance_.reset();pendingColourCorrection_.reset();
 }
 ccmInputs_.reset();''')
# AWB decides the proposed gains; one subsequent transaction snapshots both
# those gains and the CCM selected from this frame's runtime observation.
edit(cam,'\tif (af_.state()!=ipa::ContrastAf::State::Scanning && awbEnabled_ && effective_',''' double proposedRed=result.parametersKnown ? context->second.sourceRed : red_;
 double proposedBlue=result.parametersKnown ? context->second.sourceBlue : blue_;
 bool whiteBalanceChanged=false;
\tif (af_.state()!=ipa::ContrastAf::State::Scanning && awbEnabled_ && effective_''')
edit(cam,'\t\t\t\tpendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, awb.red, awb.blue };\n\t\t\t\tresult.ispUpdate = *pendingWhiteBalance_;','\t\t\t\tproposedRed=awb.red;proposedBlue=awb.blue;whiteBalanceChanged=true;')
needle=' if (af_.state()!=ipa::ContrastAf::State::Scanning && automatic_ && effective_ && result.sensorControlsKnown &&'
edit(cam,needle,''' if (result.parametersKnown && context==std::prev(parameterHistory_.end()) && result.sensorControlsKnown) {
  ccmInputs_=ColourCorrectionInputs{ result.luxValid ? std::optional<float>(result.luxIndex) : std::nullopt,
                                   float(helper_->gain(sensorContext.gainCode)),sof };
 }
 if (af_.state()!=ipa::ContrastAf::State::Scanning && result.parametersKnown && context==std::prev(parameterHistory_.end()) &&
     !pendingWhiteBalance_ && preparedParameters_.empty() && ispRevision_<UINT32_MAX-1 &&
     (whiteBalanceChanged || (colourCorrection_ && colourCorrection_->runtimeAec()))) {
  std::optional<ColourCorrectionState> selected;
  int ret=selectColourCorrection(proposedRed,proposedBlue,colourTemperature_,manualMatrix_,
                                context->second.colourCorrection ? &*context->second.colourCorrection : nullptr,
                                &selected,ccmInputs_ ? &*ccmInputs_ : nullptr);
  if (ret) LOG(IPACamss,Error)<<"Runtime CCM selection failed: "<<ret;
  else if (whiteBalanceChanged || !sameColourCorrection(selected,context->second.colourCorrection)) {
   pendingColourCorrection_=selected;
   pendingWhiteBalance_=AutoIspUpdate{ true,++ispRevision_,proposedRed,proposedBlue };
   result.ispUpdate=*pendingWhiteBalance_;
   if (selected && selected->aecValue) {
    LOG(IPACamss,Info)<<"CCM_PROPOSE epoch="<<epoch<<" statistics-sof="<<selected->statisticsSof.value_or(sof)
     <<" revision="<<ispRevision_<<" aec-bits="<<std::bit_cast<uint32_t>(*selected->aecValue)
     <<" kelvin="<<selected->temperature.value_or(0);
   }
  }
 }
'''+needle)
for name in sorted(set(changed)):
 dest=HERE/'ipa'/Path(name).name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(tree/name,dest)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=340,source=str(tree),baseline=str(OLD/'src/libcamera-v0.7.2'),changed_sources=sorted(set(changed)),installed=False,kernel_board_sensor_changes=False,default_profiles_changed=False,runtime_ccm_aec_optional=True,frozen_per_revision_ccm=True,factory_mode_supplier_binding_verified=False),indent=2)+'\n')
for filename in ['build-candidate.py']:
 (HERE/filename).write_text((HERE.parent/'kernel339'/filename).read_text().replace('stage=339','stage=340'))
print('Prepared optional runtime AEC CCM selection and frozen ISP transaction snapshots.')
