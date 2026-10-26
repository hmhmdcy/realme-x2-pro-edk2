"""Bind selected stock DS4 coefficients through typed IPA parameters."""
from pathlib import Path
import hashlib,json,shutil,struct,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2'
def edit(rel,a,b):
 p=tree/rel;t=p.read_text()
 if a not in t:assert b in t;return
 assert t.count(a)==1,(rel,a,t.count(a));p.write_text(t.replace(a,b))
pipe='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';ipa='src/ipa/camss-vfe/'
if '--resume-encoding-calls' not in sys.argv:
 edit(pipe,'PendingFrame{buffer,raw,ife,false,!raw,false}','PendingFrame{buffer,raw,ife,nullptr,false,!raw,false}')
 edit(pipe,'if(d->coarseEnabled_)d->coarse_->releaseBuffers();d->coarseBuffers_.clear();','if(d->coarseEnabled_)d->coarse_->releaseBuffers();\n d->coarseBuffers_.clear();')
 edit(pipe,'bool coarseEnabled_ = false;','bool coarseEnabled_ = false, coarseRequested_ = false;')
 edit(pipe,'bool(coarse_ && ipe_ && processedEnabled_ && output==Size(640,480))','bool(coarseRequested_ && coarse_ && ipe_ && processedEnabled_ && output==Size(640,480))')
 edit(pipe,'d->rawEnabled_ = cfg->raw_;d->processedEnabled_ = cfg->processed_;','d->rawEnabled_ = cfg->raw_;d->processedEnabled_ = cfg->processed_;d->coarseRequested_=false;')
 edit(pipe,'ret = configureIPA(d);\n if (ret) { d->restoreLinks(); return ret; }','''ret = configureIPA(d);
  if (ret) { d->restoreLinks(); return ret; }
  if(d->sensorConfiguration_.pd10) {
   if(!d->coarse_ || !d->ipe_ || !d->processedEnabled_ || d->output_!=Size(640,480)){d->restoreLinks();return -ENOTSUP;}
   d->coarseRequested_=true;ret=d->configurePath(cfg->sensorFormat_,d->output_);
   if(ret){d->restoreLinks();return ret;}
  }''')
 edit(pipe,'if (ret) goto error;\n\n d->requests_.clear();','if (ret) goto error;\n if(d->sensorConfiguration_.pd10!=d->coarseEnabled_){ret=-ENOTSUP;goto error;}\n\n d->requests_.clear();')
 edit(pipe,'createIPA<ipa::camss::IPAProxyCamss>(3, 3)','createIPA<ipa::camss::IPAProxyCamss>(4, 4)')
 edit('include/libcamera/ipa/camss.mojom','uint32 gainDelay;','uint32 gainDelay;\n bool pd10;')
 inc=tree/'include/linux';inc.mkdir(exist_ok=True)
 shutil.copyfile(tree.parents[2]/'source354/include/uapi/linux/qcom-camss-config.h',inc/'qcom-camss-config.h')
 edit(ipa+'params.h','\tIfeGamma,','\tIfeGamma,\n IfeDs4,')
 edit(ipa+'params.h','CAMSS_DEFINE_BLOCK_TYPE(IfeGamma, ife_gamma, IFE_GAMMA);','CAMSS_DEFINE_BLOCK_TYPE(IfeGamma, ife_gamma, IFE_GAMMA);\nCAMSS_DEFINE_BLOCK_TYPE(IfeDs4, ife_ds4, IFE_DS4);')
 edit(ipa+'parameter_encoder.h','const camss_params_ife_gamma *gamma = nullptr);','const camss_params_ife_gamma *gamma = nullptr,\n                     const camss_params_ife_ds4 *ds4 = nullptr);')
 edit(ipa+'parameter_encoder.cpp','const camss_params_ife_gamma *gamma)','const camss_params_ife_gamma *gamma, const camss_params_ife_ds4 *ds4)')
 edit(ipa+'parameter_encoder.cpp','(gamma ? sizeof(*gamma) : 0);','(gamma ? sizeof(*gamma) : 0) + (ds4 ? sizeof(*ds4) : 0);')
 edit(ipa+'parameter_encoder.cpp','\tCamssParams params(output);',''' if(ds4) {
   unsigned sum=0;for(uint16_t c:ds4->coefficient){if(c>256)return -ERANGE;sum+=c;}
   if(ds4->reserved || sum<256 || sum>512)return -ERANGE;
  }
  CamssParams params(output);''')
 edit(ipa+'parameter_encoder.cpp','\t*bytesused = params.bytesused();',''' if(ds4) {
   auto block=params.block<CamssBlocks::IfeDs4>();
   /* DS4 enable follows stream lifetime; this block requires zero flags. */
   std::copy(std::begin(ds4->coefficient),std::end(ds4->coefficient),block->coefficient);
  }
  *bytesused = params.bytesused();''')
 edit(ipa+'camss.cpp','\tstd::optional<qcom_ipe_a5_frame_params> pendingTone_, committedTone_;','\tstd::optional<qcom_ipe_a5_frame_params> pendingTone_, committedTone_;\n std::optional<camss_params_ife_ds4> ds4_;')
 edit(ipa+'camss.cpp','profile_ = { 0, 1.0 }; gamma_.reset();','profile_ = { 0, 1.0 }; ds4_.reset(); gamma_.reset();')
 edit(ipa+'camss.cpp','const ValueNode &tuning=*selected;','''const ValueNode &tuning=*selected;
   const auto &coarse=tuning["ife_ds4"];
   if(!coarse.isEmpty()) {
    if(!coarse.isList() || coarse.asList().size()!=3)return -EINVAL;
    camss_params_ife_ds4 config{};unsigned i=0,sum=0;
    for(const auto &node:coarse.asList()) {
     auto c=node.get<uint16_t>();if(!c || *c>256)return -ERANGE;
     config.coefficient[i++]=*c;sum+=*c;
    }
    if(sum<256 || sum>512)return -ERANGE;
    ds4_=config;
   }''')
 edit(ipa+'camss.cpp',' input_ = input; configured_ = true;',' sensorConfiguration->pd10=bool(ds4_ && ipeTone_);\n input_ = input; configured_ = true;')
 edit(ipa+'camss.cpp','sizeof(camss_params_ife_gamma)> packet;','sizeof(camss_params_ife_gamma) + sizeof(camss_params_ife_ds4)> packet;')
edit(ipa+'camss.cpp','selected ? &ccm : nullptr, gamma_?&*gamma_:nullptr);','selected ? &ccm : nullptr, gamma_?&*gamma_:nullptr,ds4_?&*ds4_:nullptr);')
edit(ipa+'camss.cpp','revision==0&&gamma_?&*gamma_:nullptr);','revision==0&&gamma_?&*gamma_:nullptr,ds4_?&*ds4_:nullptr);')
edit(ipa+'camss.cpp','IPA_MODULE_API_VERSION, 3,','IPA_MODULE_API_VERSION, 4,')
raw=(P.parent/'kernel428/params-s5kgw1-private.bin').read_bytes();assert len(raw)==56
coefficients=struct.unpack_from('<3H',raw,48)
profile=(P.parent/'kernel423/factory-s5kgw1-private.yaml').read_text();assert profile.count('  ipe_tone:')==2
assert profile.split('  ipe_tone:',1)[0].count('- match:')==1 and '    height: 3456' in profile.split('  ipe_tone:',1)[0]
profile=profile.replace('  ipe_tone:','  ife_ds4:\n'+''.join('  - '+str(c)+'\n' for c in coefficients)+'  ipe_tone:',1)
(P/'factory-s5kgw1-private.yaml').write_text(profile)
state=json.loads((HERE/'source-state.json').read_text());names=[r['path'] for r in state['source_hashes']]+['include/libcamera/ipa/camss.mojom','include/linux/qcom-camss-config.h']+[ipa+n for n in ['params.h','parameter_encoder.h','parameter_encoder.cpp','camss.cpp']]
state.update(private_ipa_version=4,ipa_mathematics_unchanged=True,typed_profile_ds4_parameters=True,source_hashes=[dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()) for n in names])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=431,selected_oem_ds4_source_stage=428,private_profile_coefficients_bound=True,private_ipa_version=4,passed=True)))
