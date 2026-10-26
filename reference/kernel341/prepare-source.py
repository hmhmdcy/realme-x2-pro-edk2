from pathlib import Path
import importlib.util,json,shutil
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage340',HERE.parent/'kernel340/storage.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
OLD=old.candidate();NEW=OLD.parent/'libcamera341-dynamic-lsc-built';assert not NEW.exists();shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
(HERE/'storage.py').write_text((HERE.parent/'kernel340/storage.py').read_text().replace('libcamera340-runtime-ccm-built','libcamera341-dynamic-lsc-built'))
tree=NEW/'src/libcamera-v0.7.2';changed=[]
def edit(name,a,b):
 p=tree/name;s=p.read_text();assert a in s,(name,a);p.write_text(s.replace(a,b));changed.append(name)
for area,names in [('libipa',['tuning_interpolation.h']),('camss-vfe',['dynamic_lens_shading.cpp','dynamic_lens_shading.h'])]:
 for name in names:
  source=HERE/('ipa' if area=='camss-vfe' else area)/name;dest=tree/'src/ipa'/area/name;shutil.copyfile(source,dest);changed.append(str(dest.relative_to(tree)))
name='src/ipa/libipa/colour_correction.cpp';s=(tree/name).read_text();a=s.index('/* Preserve the pinned');b=s.index('} /* namespace */',a);s=s[:a]+s[b:];s=s.replace('#include "colour_correction.h"','#include "colour_correction.h"\n#include "tuning_interpolation.h"').replace('interpolateValue(','interpolateTuningFloat(');(tree/name).write_text(s);changed.append(name)
edit('src/ipa/libipa/lens_shading.h','bool lscCalibrationFactors(','''bool interpolateLscMesh(const LscMesh &first,const LscMesh &second,float weight,LscMesh *result);

bool lscCalibrationFactors(''')
edit('src/ipa/libipa/lens_shading.cpp','#include "lens_shading.h"','#include "lens_shading.h"\n#include "tuning_interpolation.h"')
edit('src/ipa/libipa/lens_shading.cpp','bool lscCalibrationFactors(','''bool interpolateLscMesh(const LscMesh &first,const LscMesh &second,float weight,LscMesh *result)
{
 if(!result||!std::isfinite(weight)||weight<0||weight>1)return false;
 LscMesh output;
 for(unsigned c=0;c<LscChannels;c++)for(unsigned i=0;i<LscPoints;i++){
  float a=first[c][i],b=second[c][i];if(!positive(a)||!positive(b))return false;
  if(weight==0)output[c][i]=a;
  else if(weight==1)output[c][i]=b;
  else {
   if(a>=2147483648.0f||b>=2147483648.0f)return false;
   output[c][i]=interpolateTuningFloat(a,b,weight);
  }
  if(!positive(output[c][i]))return false;
 }
 *result=output;return true;
}

bool lscCalibrationFactors(''')
h='src/ipa/camss-vfe/lens_shading.h';p='src/ipa/camss-vfe/lens_shading.cpp'
edit(h,'#include <libcamera/geometry.h>','#include <libcamera/geometry.h>\n#include "../libipa/lsc_resample.h"')
edit(h,'/* Static mode tuning.','''int readLensShadingMesh(const ValueNode &value,LscMesh *mesh);
int readLensShadingMapping(const ValueNode &tuning,LscMapping *mapping);
int encodeLensShading(const LscMesh &source,const Size &input,const LscMapping &mapping,camss_params_lsc *parameters);

/* Static mode tuning.''')
edit(p,'static int readMesh(','int readLensShadingMesh(');edit(p,'readMesh(','readLensShadingMesh(')
s=(tree/p).read_text();start=s.index('\tLscPackedMesh packed;');end=s.index('\n} /* namespace libcamera',start)
encoding=s[start:end];encoding=encoding.replace('\t*parameters = result;','\t*parameters = result;')
s=s[:start]+''' camss_params_lsc encoded;
 int ret=encodeLensShading(source,input,mapping,&encoded);
 if(!ret)*parameters=encoded;
 return ret;
}

int readLensShadingMapping(const ValueNode &tuning,LscMapping *mapping)
{
 if(!mapping)return -EINVAL;
 return readPair(tuning["source_span"],&mapping->sourceSpanX,&mapping->sourceSpanY)||
        readPair(tuning["first_quad"],&mapping->firstX,&mapping->firstY)||
        readPair(tuning["quad_step"],&mapping->stepX,&mapping->stepY)?-EINVAL:0;
}

int encodeLensShading(const LscMesh &source,const Size &input,const LscMapping &mapping,camss_params_lsc *parameters)
{
 if(!parameters)return -EINVAL;
 LscGrid grid;LscMesh resampled;
 if(!lscGridForSize(input.width,input.height,&grid))return -EINVAL;
'''+encoding+s[end:]
(tree/p).write_text(s);changed.append(p)
edit('src/ipa/camss-vfe/meson.build',"'lux_profile.cpp']","'lux_profile.cpp', 'dynamic_lens_shading.cpp']")
cam='src/ipa/camss-vfe/camss.cpp'
edit(cam,'#include "lens_shading.h"','#include "lens_shading.h"\n#include "dynamic_lens_shading.h"')
edit(cam,'std::optional<ColourCorrectionState> colourCorrection; };','std::optional<ColourCorrectionState> colourCorrection; std::optional<DynamicLscState> lensShading; };')
edit(cam,' std::optional<ColourCorrectionState> pendingColourCorrection_;',''' std::optional<ColourCorrectionState> pendingColourCorrection_;
 std::optional<DynamicLensShading> dynamicLensShading_;
 std::optional<DynamicLscState> pendingLensShading_;
 int selectLensShading(double red,double blue,std::optional<int32_t> temperature,
                      const DynamicLscState *fallback,std::optional<DynamicLscState> *state,
                      const ColourCorrectionInputs *runtime=nullptr) const;''')
edit(cam,'profile_ = { 0, 1.0 }; lensShading_.reset();','profile_ = { 0, 1.0 }; lensShading_.reset(); dynamicLensShading_.reset();')
edit(cam,'  ret=configureLensShading(tuning["lens_shading"],input,&lensShading_);','''  ret=DynamicLensShading::configure(tuning["lens_shading"],input,&dynamicLensShading_);
  if(ret)return ret;
  if(tuning["lens_shading"]["mode"].get<std::string>("static")!="dynamic")
   ret=configureLensShading(tuning["lens_shading"],input,&lensShading_);''')
edit(cam,'  if (colourCorrection_ && colourCorrection_->requiresLux() && !lux_) return -EINVAL;','  if (((colourCorrection_ && colourCorrection_->requiresLux()) || (dynamicLensShading_ && dynamicLensShading_->requiresLux())) && !lux_) return -EINVAL;')
needle='static bool sameColourCorrection('
s=(tree/cam).read_text();at=s.index(needle);s=s[:at]+'''int IPACamss::selectLensShading(double red,double blue,std::optional<int32_t> temperature,
 const DynamicLscState *fallback,std::optional<DynamicLscState> *state,const ColourCorrectionInputs *runtime) const
{
 state->reset();if(!dynamicLensShading_)return 0;
 double effectiveRed,effectiveBlue;int ret=effectiveColourGains(profile_,red,blue,&effectiveRed,&effectiveBlue);if(ret)return ret;
 if(!temperature&&whiteBalance_)temperature=whiteBalance_->temperature(effectiveRed,effectiveBlue);
 DynamicLscState result;ret=dynamicLensShading_->select(temperature,runtime,fallback,&result);
 if(!ret)*state=result;return ret;
}

static bool sameLensShading(const std::optional<DynamicLscState> &a,const std::optional<DynamicLscState> &b)
{
 if(bool(a)!=bool(b))return false;
 return !a||!std::memcmp(&a->parameters,&b->parameters,sizeof(a->parameters));
}

'''+s[at:];(tree/cam).write_text(s);changed.append(cam)
edit(cam,' if (enabled == current.awbEnabled',''' std::optional<DynamicLscState> selectedLsc;
 ret=selectLensShading(red,blue,temperature,current.lensShading?&*current.lensShading:nullptr,&selectedLsc,ccmInputs_?&*ccmInputs_:nullptr);
 if(ret)return ret;
 if (enabled == current.awbEnabled''')
edit(cam,'&& sameColourCorrection(current.colourCorrection,selected)) return 0;','&& sameColourCorrection(current.colourCorrection,selected) && sameLensShading(current.lensShading,selectedLsc)) return 0;')
edit(cam,' pendingColourCorrection_ = selected;',' pendingLensShading_=selectedLsc;\n pendingColourCorrection_ = selected;')
edit(cam,'ccmInputs_.reset();pendingColourCorrection_.reset();','ccmInputs_.reset();pendingColourCorrection_.reset();pendingLensShading_.reset();')
# Startup preflight and startup parameter encoding must both begin with unity
# while the dynamic profile has no measured AEC coordinate.
a=' int ret=selectColourCorrection(red,blue,temperature,manualMatrix,nullptr,&selected);\n if (ret) return ret;'
b=a+'''\n std::optional<DynamicLscState> selectedLsc;
 ret=selectLensShading(red,blue,temperature,nullptr,&selectedLsc);if(ret)return ret;'''
edit(cam,a,b)
edit(cam,'&used, lensShading_ ? &*lensShading_ : nullptr, selected ? &ccm : nullptr);','&used, selectedLsc?&selectedLsc->parameters:lensShading_?&*lensShading_:nullptr, selected ? &ccm : nullptr);')
a=' else ret=selectColourCorrection(red,blue,colourTemperature_,manualMatrix_,fallback,&selected);\n if (ret) return ret;'
b=a+'''\n std::optional<DynamicLscState> selectedLsc;
 if(revision)selectedLsc=pendingLensShading_;
 else {ret=selectLensShading(red,blue,colourTemperature_,nullptr,&selectedLsc);if(ret)return ret;}
 const camss_params_lsc *uploadLsc=revision==0&&lensShading_?&*lensShading_:nullptr;
 if(selectedLsc && (revision==0 || parameterHistory_.empty() || !sameLensShading(selectedLsc,parameterHistory_.rbegin()->second.lensShading)))uploadLsc=&selectedLsc->parameters;'''
edit(cam,a,b)
edit(cam,'&used, revision==0 && lensShading_ ? &*lensShading_ : nullptr, selected ? &ccm : nullptr);','&used, uploadLsc, selected ? &ccm : nullptr);')
edit(cam,'std::nullopt, selected };','std::nullopt, selected, selectedLsc };')
edit(cam,'pendingWhiteBalance_.reset();pendingColourCorrection_.reset();','pendingWhiteBalance_.reset();pendingColourCorrection_.reset();pendingLensShading_.reset();')
a=' const auto &ccm=parameterHistory_.at(firstSof).colourCorrection;'
b=''' const auto &lsc=parameterHistory_.at(firstSof).lensShading;
 if(lsc)LOG(IPACamss,Info)<<"LSC_APPLIED epoch="<<epoch<<" revision="<<revision<<" first-sof="<<firstSof
  <<" statistics-sof="<<lsc->statisticsSof.value_or(firstSof)<<" aec-bits="<<std::bit_cast<uint32_t>(lsc->aecValue.value_or(0))
  <<" kelvin="<<lsc->temperature.value_or(0)<<" mesh-trace="<<lensShadingTrace(lsc->parameters);
'''+a
edit(cam,a,b)
edit(cam,'     (whiteBalanceChanged || (colourCorrection_ && colourCorrection_->runtimeAec()))) {','     (whiteBalanceChanged || (colourCorrection_ && colourCorrection_->runtimeAec()) || dynamicLensShading_)) {')
a='  if (ret) LOG(IPACamss,Error)<<"Runtime CCM selection failed: "<<ret;'
b='''  std::optional<DynamicLscState> selectedLsc;
  if(!ret)ret=selectLensShading(proposedRed,proposedBlue,colourTemperature_,context->second.lensShading?&*context->second.lensShading:nullptr,&selectedLsc,ccmInputs_?&*ccmInputs_:nullptr);
'''+a
edit(cam,a,b)
edit(cam,'else if (whiteBalanceChanged || !sameColourCorrection(selected,context->second.colourCorrection)) {','else if (whiteBalanceChanged || !sameColourCorrection(selected,context->second.colourCorrection) || !sameLensShading(selectedLsc,context->second.lensShading)) {')
edit(cam,'   pendingColourCorrection_=selected;','   pendingLensShading_=selectedLsc;\n   pendingColourCorrection_=selected;')
for name in sorted(set(changed)):
 destination=HERE/('libipa' if '/libipa/' in name else 'ipa')/Path(name).name;destination.parent.mkdir(exist_ok=True);shutil.copyfile(tree/name,destination)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=341,source=str(tree),baseline=str(OLD/'src/libcamera-v0.7.2'),changed_sources=sorted(set(changed)),installed=False,kernel_board_sensor_changes=False,default_profiles_changed=False,dynamic_lsc_full_core_tree=True,explicit_single_golden_unit_pair=True,factory_mode_supplier_binding_verified=False),indent=2)+'\n')
(HERE/'build-candidate.py').write_text((HERE.parent/'kernel340/build-candidate.py').read_text().replace('stage=340','stage=341'))
print('Prepared dynamic LSC selection and coalesced frozen WB/CCM/LSC revisions.')
