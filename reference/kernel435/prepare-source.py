"""Split upstream TMC/GTM generation from same-frame IPE LTM consumption."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;new=storage.candidate();old=new.parent/'libcamera431-pd10-auto'
assert not new.exists()
for folder in [old,*old.parents]:assert not (folder/'AGENTS.md').exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
T=new/'src/libcamera-v0.7.2';ipa=T/'src/ipa/camss-vfe';lib=T/'src/ipa/libipa'
for directory in [T,ipa,lib,*T.parents,*ipa.parents,*lib.parents]:assert not (directory/'AGENTS.md').exists()
shutil.copyfile(new.parent/'source354/include/uapi/linux/qcom-camss-config.h',T/'include/linux/qcom-camss-config.h')
for name in ['gtm_tmc11.cpp','gtm_tmc11.h']:
 text=(HERE.parent/'kernel432/libipa'/name).read_text().replace('../../kernel412/libipa/tmc11_ltm.h','tmc11_ltm.h');(lib/name).write_text(text)
shutil.copyfile(HERE/'ife_gtm_history.h',ipa/'ife_gtm_history.h')
def edit(p,a,b):
 t=p.read_text();assert t.count(a)==1,(str(p),a,t.count(a));p.write_text(t.replace(a,b))
edit(lib/'meson.build',"    'tmc_runtime.cpp',","    'tmc_runtime.cpp',\n    'gtm_tmc11.cpp',")
h=ipa/'ipe_tone_profile.h';c=ipa/'ipe_tone_profile.cpp'
edit(h,'bool initialized = false, ltmLuxValid = false;','bool initialized = false, ltmLuxValid = false;\n uint64_t gtmCookie = 0, gtmGeneration = 0;')
edit(h,'qcom_ipe_a5_frame_params *parameters, IpeToneState *next) const;','qcom_ipe_a5_frame_params *parameters, IpeToneState *next,\n               const IpeToneState *appliedTmc = nullptr) const;\n int prepareGtm(const IpeFrameObservation &frame, const IpeToneState &history,\n                camss_params_ife_gtm *parameters, IpeToneState *next) const;\n void bootstrap(qcom_ipe_a5_frame_params *packet) const { *packet={};packet->version=1;packet->size=sizeof(*packet);packet->colour=colour_; }\n bool tracksGtm() const { return gtmConfigured_; }')
edit(h,'uint32_t mode_ = 0,','bool gtmConfigured_ = false, gtmEnabled_ = false;\n std::array<float,65> gtmAxis_{};\n std::array<uint32_t,65> gtmDomain_{};\n std::array<float,1024> gtmContrastAxis_{};\n int prepareTmc(const IpeFrameObservation &frame,const IpeToneState &history,IpeToneState *next) const;\n uint32_t mode_ = 0,')
edit(c,'#include "../libipa/gamma_segments.h"','#include "../libipa/gamma_segments.h"\n#include "../libipa/gtm_tmc11.h"')
edit(c,'\t*out = std::move(p); return 0;',''' const auto &gtm=node["ife_gtm"];
 if(!gtm.isEmpty()) {
  auto gtmEnabled=gtm["enabled"].get<bool>();
  if(p.mode_!=0 || !gtm.isDictionary() || !gtmEnabled ||
     gtm["model"].get<std::string>("")!="tmc11-model2" ||
     !gtm["uid"].get<uint32_t>(0) || gtm["manual_curve"].get<uint32_t>(2)>1 || gtm["v2_enable"].get<uint32_t>(2)>1 ||
     !array(gtm["normalized_axis"],&p.gtmAxis_) || !array(gtm["integer_axis"],&p.gtmDomain_) ||
     !array(gtm["contrast_axis"],&p.gtmContrastAxis_))return -EINVAL;
  if(*gtmEnabled != bool(p.tmcEnabled_ && p.tmcUseGtm_))return -ENOTSUP;
  p.gtmConfigured_=true;p.gtmEnabled_=*gtmEnabled;
 }
 *out = std::move(p); return 0;''')
raw=c.read_text();a=raw.index('\t\tTmc11PolicyInput policy{');b=raw.index('\n\t\tuint32_t version =',a)
body=raw[a:b];assert body.endswith('return -EINVAL;')
method='''int IpeToneProfile::prepareTmc(const IpeFrameObservation &frame,const IpeToneState &history,IpeToneState *next) const
{
 IpeToneState state=history;Tmc11GenerationResult adrc;
'''+body+'''
 state.initialized=true;*next=state;return 0;
}
int IpeToneProfile::prepareGtm(const IpeFrameObservation &frame,const IpeToneState &history,
                             camss_params_ife_gtm *parameters,IpeToneState *next) const
{
 if(!parameters || !next || !gtmConfigured_ || !frame.luxValid)return -ENODATA;
 IpeToneState state;int ret=prepareTmc(frame,history,&state);if(ret)return ret;
 camss_params_ife_gtm packet{};
 packet.enabled=gtmEnabled_ && word(state.cache,0)==1 && word(state.cache,4)==1 && word(state.cache,8)==1;
 if(packet.enabled) {
  auto adrc=generated(state.cache);adrc.ltm.percentage=adrc.gtmPercentage;
  std::array<uint64_t,64> lut;
  if(!calculateTmc11Gtm(adrc.pchip,adrc.ltm,gtmAxis_,gtmDomain_,gtmContrastAxis_,adrc.contrastCurve,false,&lut))return -ERANGE;
  for(unsigned i=0;i<64;++i) {
   packet.segments[i].base=lut[i]&0x3ffff;
   uint32_t slope=lut[i]>>32;packet.segments[i].slope=slope&(1u<<25)?int64_t(slope)-(int64_t(1)<<26):slope;
  }
 }
 *parameters=packet;*next=state;return 0;
}
'''
raw=raw[:a]+'''		if(appliedTmc) {
   state.policy=appliedTmc->policy;state.adrc=appliedTmc->adrc;state.cache=appliedTmc->cache;
  } else {int ret=prepareTmc(frame,history,&state);if(ret)return ret;}
'''+raw[b:]
needle='int IpeToneProfile::calculate(';assert raw.count(needle)==1;raw=raw.replace(needle,method+needle)
raw=raw.replace('qcom_ipe_a5_frame_params *parameters, IpeToneState *next) const','qcom_ipe_a5_frame_params *parameters, IpeToneState *next, const IpeToneState *appliedTmc) const');c.write_text(raw)
edit(ipa/'params.h',' IfeDs4,',' IfeDs4,\n IfeGtm,')
edit(ipa/'params.h','CAMSS_DEFINE_BLOCK_TYPE(IfeDs4, ife_ds4, IFE_DS4);','CAMSS_DEFINE_BLOCK_TYPE(IfeDs4, ife_ds4, IFE_DS4);\nCAMSS_DEFINE_BLOCK_TYPE(IfeGtm, ife_gtm, IFE_GTM);')
edit(ipa/'parameter_encoder.h','const camss_params_ife_ds4 *ds4 = nullptr);','const camss_params_ife_ds4 *ds4 = nullptr,\n                     const camss_params_ife_gtm *gtm = nullptr);')
edit(ipa/'parameter_encoder.cpp','const camss_params_ife_ds4 *ds4)','const camss_params_ife_ds4 *ds4, const camss_params_ife_gtm *gtm)')
edit(ipa/'parameter_encoder.cpp','(ds4 ? sizeof(*ds4) : 0);','(ds4 ? sizeof(*ds4) : 0) + (gtm ? sizeof(*gtm) : 0);')
edit(ipa/'parameter_encoder.cpp',' CamssParams params(output);',''' if(gtm) {
  if(!gtm->cookie || gtm->enabled>1 || gtm->reserved || gtm->header.flags)return -EINVAL;
  for(const auto &s:gtm->segments)if(s.base>0x3ffff || s.slope<-(1<<25) || s.slope>=(1<<25))return -ERANGE;
 }
 CamssParams params(output);''')
edit(ipa/'parameter_encoder.cpp',' *bytesused = params.bytesused();',''' if(gtm) {
  auto block=params.block<CamssBlocks::IfeGtm>();
  block->cookie=gtm->cookie;block->enabled=gtm->enabled;block->reserved=0;
  std::copy(std::begin(gtm->segments),std::end(gtm->segments),block->segments);
 }
 *bytesused = params.bytesused();''')
edit(ipa/'statistics.h','#include <span>','#include <span>\n#include <optional>')
edit(ipa/'statistics.h','GridStatistics grid;','GridStatistics grid;\n std::optional<camss_stats_ife_gtm> gtm;')
edit(ipa/'statistics.h','\t\t/* Unknown, structurally valid blocks','''  else if(header.type==CAMSS_STATS_IFE_GTM) {
   if(parsed.gtm || header.size!=sizeof(camss_stats_ife_gtm))return -EPROTO;
   camss_stats_ife_gtm receipt;std::memcpy(&receipt,data.data()+offset,sizeof receipt);
   if(!receipt.cookie || !receipt.generation || receipt.bank>1 || (receipt.status!=1 && receipt.status!=3))return -EPROTO;
   parsed.gtm=receipt;
  }
\t\t/* Unknown, structurally valid blocks''')
r=dict(stage=435,source=str(T),baseline_stage=431,source_prepared=False,profile_phase_prepared=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
