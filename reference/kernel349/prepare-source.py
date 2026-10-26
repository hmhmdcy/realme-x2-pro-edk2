from pathlib import Path
import importlib.util,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;NEW=storage.candidate();OLD=NEW.parent/'libcamera342-r27-built'
assert OLD.is_dir() and not NEW.exists()
tree=OLD/'src/libcamera-v0.7.2'
for name in ['AGENTS.md','src/AGENTS.md','src/ipa/AGENTS.md','src/ipa/camss-vfe/AGENTS.md','src/ipa/libipa/AGENTS.md']:
 if (tree/name).exists():raise RuntimeError('Read applicable instructions: '+str(tree/name))
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=NEW/'src/libcamera-v0.7.2';changed=[]
def edit(name,a,b):
 p=tree/name;s=p.read_text();assert s.count(a)==1,(name,a);p.write_text(s.replace(a,b))
 if name not in changed:changed.append(name)
for name in ['gamma_curve.h','gamma_curve.cpp']:
 target='src/ipa/libipa/'+name;shutil.copyfile(HERE.parent/'kernel347/libipa'/name,tree/target);changed.append(target)
for source in (HERE/'ipa').glob('*'):
 target='src/ipa/camss-vfe/'+source.name;shutil.copyfile(source,tree/target);changed.append(target)
target='include/linux/qcom-camss-config.h';shutil.copyfile(HERE.parent/'kernel348/kernel/qcom-camss-config.h',tree/target);changed.append(target)
edit('src/ipa/libipa/meson.build',"    'colour_correction.cpp',","    'colour_correction.cpp',\n    'gamma_curve.cpp',")
edit('src/ipa/camss-vfe/meson.build',"'dynamic_lens_shading.cpp']","'dynamic_lens_shading.cpp', 'gamma_profile.cpp']")
edit('src/ipa/camss-vfe/params.h','\tLensShading,','\tLensShading,\n\tIfeGamma,')
edit('src/ipa/camss-vfe/params.h','CAMSS_DEFINE_BLOCK_TYPE(LensShading, lsc, LSC);','CAMSS_DEFINE_BLOCK_TYPE(LensShading, lsc, LSC);\nCAMSS_DEFINE_BLOCK_TYPE(IfeGamma, ife_gamma, IFE_GAMMA);')
edit('src/ipa/camss-vfe/parameter_encoder.h','const camss_params_color_correct *ccm = nullptr);','const camss_params_color_correct *ccm = nullptr,\n                     const camss_params_ife_gamma *gamma = nullptr);')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','const camss_params_lsc *lsc, const camss_params_color_correct *ccm)',
 'const camss_params_lsc *lsc, const camss_params_color_correct *ccm,\n                     const camss_params_ife_gamma *gamma)')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','(ccm ? sizeof(*ccm) : 0);','(ccm ? sizeof(*ccm) : 0) + (gamma ? sizeof(*gamma) : 0);')
edit('src/ipa/camss-vfe/parameter_encoder.cpp','\t*bytesused = params.bytesused();',''' if (gamma) {
  auto block = params.block<CamssBlocks::IfeGamma>();
  block.setEnabled(true);
  std::memcpy(block->segments, gamma->segments, sizeof(gamma->segments));
 }
\t*bytesused = params.bytesused();''')
cam='src/ipa/camss-vfe/camss.cpp'
edit(cam,'#include "lens_shading.h"','#include "lens_shading.h"\n#include "gamma_profile.h"')
edit(cam,'std::optional<DynamicLscState> lensShading; };','std::optional<DynamicLscState> lensShading; bool gammaEnabled; };')
edit(cam,'\tstd::optional<camss_params_lsc> lensShading_;','\tstd::optional<camss_params_lsc> lensShading_;\n std::optional<camss_params_ife_gamma> gamma_;')
edit(cam,'profile_ = { 0, 1.0 }; lensShading_.reset();','profile_ = { 0, 1.0 }; gamma_.reset(); lensShading_.reset();')
edit(cam,'  ret=DynamicLensShading::configure(','''  ret=configureGammaProfile(tuning["gamma"],&gamma_);
  if(ret)return ret;
  ret=DynamicLensShading::configure(''')
edit(cam,'sizeof(camss_params_lsc) + sizeof(camss_params_color_correct)> packet;','sizeof(camss_params_lsc) + sizeof(camss_params_color_correct) + sizeof(camss_params_ife_gamma)> packet;')
edit(cam,'&used, selectedLsc?&selectedLsc->parameters:lensShading_?&*lensShading_:nullptr, selected ? &ccm : nullptr);',
 '&used, selectedLsc?&selectedLsc->parameters:lensShading_?&*lensShading_:nullptr, selected ? &ccm : nullptr, gamma_?&*gamma_:nullptr);')
edit(cam,'&used, uploadLsc, selected ? &ccm : nullptr);','&used, uploadLsc, selected ? &ccm : nullptr, revision==0&&gamma_?&*gamma_:nullptr);')
edit(cam,'std::nullopt, selected, selectedLsc };','std::nullopt, selected, selectedLsc, bool(gamma_) };')
needle='\tLOG(IPACamss, Info) << "ISP applied epoch="'
edit(cam,needle,''' if (revision==0 && parameterHistory_.at(firstSof).gammaEnabled)
  LOG(IPACamss,Info)<<"GAMMA_APPLIED epoch="<<epoch<<" revision="<<revision<<" first-sof="<<firstSof;
'''+needle)
edit(cam,'<< " awb=" << parameterHistory_.at(firstSof).awbEnabled;',
 '<< " awb=" << parameterHistory_.at(firstSof).awbEnabled << " gamma=" << parameterHistory_.at(firstSof).gammaEnabled;')
edit(cam,'<< " parameters-known=" << result.parametersKnown;',
 '<< " parameters-known=" << result.parametersKnown << " gamma=" << (result.parametersKnown && context->second.gammaEnabled);')
# The curve is fixed by configure(), which is forbidden while running. Only
# revision zero uploads it; later WB/CCM/LSC revisions retain its applied state.
edit(cam,'sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist) : sizeof(camss_stats_bhist));',
 'sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist) + (gamma_?sizeof(*gamma_):0) : sizeof(camss_stats_bhist));')
(HERE/'source-state.json').write_text(json.dumps(dict(stage=349,source=str(tree),baseline=str(OLD/'src/libcamera-v0.7.2'),
 changed_sources=changed,installed=False,new_kernel_parameter_type=7,
 static_gamma_upload_startup_only=True,no_ipc_signature_change=True),indent=2)+'\n')
print('Prepared optional static Gamma configuration and native typed encoding; startup upload shares revision0/SOF history.')
