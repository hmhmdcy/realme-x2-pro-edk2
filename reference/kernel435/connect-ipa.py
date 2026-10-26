"""Bind real GTM receipts to immutable TMC objects and IPE success history."""
from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';D=T/'src/ipa/camss-vfe';p=D/'camss.cpp';t=p.read_text()
shutil.copyfile(HERE/'ife_gtm_history.h',D/'ife_gtm_history.h')
def replace(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
replace('#include "ipe_tone_profile.h"','#include "ipe_tone_profile.h"\n#include "ife_gtm_history.h"')
replace(' int describeSensor(',''' using GtmHistory=IfeGtmHistory<IpeToneState>;
 GtmHistory gtmHistory_;
 std::optional<GtmHistory::Version> proposedGtm_;
 std::map<uint64_t,GtmHistory::Pointer> frameGtms_;
 bool tracksGtm() const { return ipeTone_ && ipeTone_->tracksGtm(); }
 void commitParameters(uint64_t epoch,uint32_t firstSof,uint32_t revision);
 int describeSensor(''')
replace(' pendingTone_.reset();committedTone_.reset();',' pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();')
replace(' numericHistory_.stop();pendingTone_.reset();committedTone_.reset();',' numericHistory_.stop();pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();')
# Real receipt commits all blocks in the serialized packet. DQ is submission only.
replace('void IPACamss::parametersApplied(uint64_t epoch, uint32_t firstSof, uint32_t revision)\n{','''void IPACamss::parametersApplied(uint64_t epoch,uint32_t firstSof,uint32_t revision)
{
 if(!running_ || epoch!=epoch_)return;
 if(tracksGtm()) {
  LOG(IPACamss,Info)<<"IFE_PARAMS_SUBMITTED epoch="<<epoch<<" revision="<<revision<<" reported-sof="<<firstSof;
  return;
 }
 commitParameters(epoch,firstSof,revision);
}
void IPACamss::commitParameters(uint64_t epoch, uint32_t firstSof, uint32_t revision)
{''')
needle='''	size_t used;
	ret = encodeParameters(it->second.memory->planes()[0]'''
replace(needle,''' GtmHistory::Pointer gtmUpload;
 if(tracksGtm()) {
  GtmHistory::Version version;
  if(proposedGtm_)version=*proposedGtm_;
  else if(gtmHistory_.active())version=*gtmHistory_.active();
  /* Bootstrap is explicit disabled GTM until real statistics generate TMC. */
  ret=gtmHistory_.stage(version,revision,&gtmUpload);if(ret)return ret;
 }
	size_t used;
	ret = encodeParameters(it->second.memory->planes()[0]''')
replace('revision==0&&gamma_?&*gamma_:nullptr,ds4_?&*ds4_:nullptr);','revision==0&&gamma_?&*gamma_:nullptr,ds4_?&*ds4_:nullptr,gtmUpload?&gtmUpload->parameters:nullptr);')
replace('''		*bytesused = used;
	}
	return ret;
}

void IPACamss::parametersApplied''','''		*bytesused = used;
  if(gtmUpload) {
   proposedGtm_.reset();
   LOG(IPACamss,Info)<<"IFE_GTM_QUEUE epoch="<<epoch<<" revision="<<revision<<" cookie="<<gtmUpload->parameters.cookie
    <<" source-sof="<<gtmUpload->sourceSof<<" source-histogram="<<gtmUpload->sourceHistogram<<" ready="<<gtmUpload->ready<<" enabled="<<gtmUpload->parameters.enabled;
  }
	} else if(gtmUpload)gtmHistory_.cancelUnsubmitted(gtmUpload->parameters.cookie);
	return ret;
}

void IPACamss::parametersApplied''')
replace('''	if (result.status) { complete(); return; }
	lastStats_ = sof;''','''	if (result.status) { complete(); return; }
 GtmHistory::Pointer appliedGtm;
 if(tracksGtm()) {
  bool changed=false;
  result.status=parsed.gtm?gtmHistory_.accept(sof,*parsed.gtm,&appliedGtm,&changed):-ENODATA;
  if(result.status){complete();return;}
  if(changed) {
   commitParameters(epoch,sof,appliedGtm->revision);
   LOG(IPACamss,Info)<<"IFE_GTM_APPLIED epoch="<<epoch<<" sof="<<sof<<" cookie="<<appliedGtm->parameters.cookie
    <<" generation="<<parsed.gtm->generation<<" bank="<<parsed.gtm->bank<<" revision="<<appliedGtm->revision
    <<" source-sof="<<appliedGtm->sourceSof<<" source-histogram="<<appliedGtm->sourceHistogram<<" ready="<<appliedGtm->ready;
  }
 }
	lastStats_ = sof;''')
replace('''  observation.epoch=epoch;observation.sof=sof;observation.histogram=parsed.histogram;''','''  observation.epoch=epoch;observation.sof=sof;observation.histogram=parsed.histogram;
  if(appliedGtm){observation.gtmCookie=appliedGtm->parameters.cookie;observation.gtmGeneration=parsed.gtm->generation;}''')
replace('''   result.ipeToken=token;result.ipeHistogramTrace=histogramTrace(observation);''','''   result.ipeToken=token;result.ipeHistogramTrace=histogramTrace(observation);
   if(appliedGtm)frameGtms_[token]=appliedGtm;''')
replace('''    <<" exposure-index="<<observation.exposureIndex<<" gamma-override="<<observation.ifeGammaOverride;''','''    <<" exposure-index="<<observation.exposureIndex<<" gamma-override="<<observation.ifeGammaOverride
    <<" gtm-cookie="<<observation.gtmCookie<<" gtm-generation="<<observation.gtmGeneration;''')
replace('''  } else LOG(IPACamss,Error)<<"IPE observation rejected: "<<status;
 }
 complete();''','''  } else LOG(IPACamss,Error)<<"IPE observation rejected: "<<status;
  if(tracksGtm() && observation.luxValid && af_.state()!=ipa::ContrastAf::State::Scanning &&
     !gtmHistory_.busy() && preparedParameters_.empty() &&
     (!pendingWhiteBalance_ || result.ispUpdate.valid) && ispRevision_<UINT32_MAX-1) {
   GtmHistory::Version version;IpeToneState initial;
   const auto &active=gtmHistory_.active();
   int ret=ipeTone_->prepareGtm(observation,active?active->math:initial,&version.parameters,&version.math);
   if(!ret) {
    version.ready=true;version.sourceSof=sof;version.sourceHistogram=histogramTrace(observation);
    proposedGtm_=version;
    if(!pendingWhiteBalance_) {
     pendingColourCorrection_=context->second.colourCorrection;pendingLensShading_=context->second.lensShading;
     pendingWhiteBalance_=AutoIspUpdate{true,++ispRevision_,context->second.sourceRed,context->second.sourceBlue};
    }
    result.ispUpdate=*pendingWhiteBalance_;
    LOG(IPACamss,Info)<<"IFE_GTM_PROPOSE epoch="<<epoch<<" source-sof="<<sof<<" revision="<<result.ispUpdate.revision
     <<" source-histogram="<<version.sourceHistogram<<" enabled="<<version.parameters.enabled;
   } else LOG(IPACamss,Error)<<"IFE_GTM_REJECT sof="<<sof<<" status="<<ret;
  }
 }
 complete();''')
replace('''	if (!frame || !frame->luxValid || numericHistory_.busy()) {''',''' GtmHistory::Pointer applied;
 if(tracksGtm()) {
  const auto found=frameGtms_.find(token);
  if(!frame || found==frameGtms_.end() || found->second->parameters.cookie!=frame->gtmCookie)return -ENODATA;
  applied=found->second;
  if(!applied->ready) {
   qcom_ipe_a5_frame_params packet;ipeTone_->bootstrap(&packet);
   const auto *p=reinterpret_cast<const uint8_t*>(&packet);parameters->assign(p,p+sizeof packet);
   *revision=numericHistory_.revision();
   LOG(IPACamss,Info)<<"IPE_TONE_BOOTSTRAP sof="<<sof<<" cookie="<<frame->gtmCookie<<" generation="<<frame->gtmGeneration;
   return 0;
  }
 }
	if (!frame || !frame->luxValid || numericHistory_.busy()) {
  /* A held LTM program is valid only for the very same upstream GTM. */
  if(applied && (!committedTone_ || numericHistory_.state().gtmCookie!=frame->gtmCookie))return -EAGAIN;''')
replace('int ret = ipeTone_->calculate(*frame, numericHistory_.state(), &packet, &next);','int ret = ipeTone_->calculate(*frame, numericHistory_.state(), &packet, &next,applied?&applied->math:nullptr);\n if(!ret && applied){next.gtmCookie=frame->gtmCookie;next.gtmGeneration=frame->gtmGeneration;}')
replace('''<< " previous-ltm-lux=" << numericHistory_.state().ltmLuxIndex << " factory=" << ipeTone_->factoryMode();''','''<< " previous-ltm-lux=" << numericHistory_.state().ltmLuxIndex << " factory=" << ipeTone_->factoryMode()
  <<" gtm-cookie="<<next.gtmCookie<<" gtm-generation="<<next.gtmGeneration
  <<" gtm-source-sof="<<(applied?applied->sourceSof:0)<<" gtm-source-histogram="<<(applied?applied->sourceHistogram:0);''')
replace('''		const int numeric=numericHistory_.resolve(epoch,sof,token,success && result>=0);''','''  const uint64_t gtmCookie=numericHistory_.pending()->next.gtmCookie,gtmGeneration=numericHistory_.pending()->next.gtmGeneration;
		const int numeric=numericHistory_.resolve(epoch,sof,token,success && result>=0);''')
replace('''<<" result="<<numeric<<" revision="<<numericHistory_.revision();''','''<<" result="<<numeric<<" revision="<<numericHistory_.revision()
   <<" gtm-cookie="<<gtmCookie<<" gtm-generation="<<gtmGeneration<<" active-ife-cookie="<<(gtmHistory_.active()?gtmHistory_.active()->parameters.cookie:0);''')
replace('''	LOG(IPACamss, Info) << "IPE_RECEIPT epoch="''',''' if(result>=0)frameGtms_.erase(token);
	LOG(IPACamss, Info) << "IPE_RECEIPT epoch="''')
replace('IPA_MODULE_API_VERSION, 4,','IPA_MODULE_API_VERSION, 5,');p.write_text(t)
p=D/'ipe_frame_history.h';raw=p.read_text();assert raw.count('uint64_t epoch = 0, exposureNs = 0, population = 0;')==1;p.write_text(raw.replace('uint64_t epoch = 0, exposureNs = 0, population = 0;','uint64_t epoch = 0, exposureNs = 0, population = 0, gtmCookie = 0, gtmGeneration = 0;'))
p=T/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';raw=p.read_text();assert raw.count('createIPA<ipa::camss::IPAProxyCamss>(4, 4)')==1;p.write_text(raw.replace('createIPA<ipa::camss::IPAProxyCamss>(4, 4)','createIPA<ipa::camss::IPAProxyCamss>(5, 5)').replace('<< " parameters-acknowledged=" << paramsApplied_','<< " parameter-buffer-submitted=" << paramsApplied_'))
files=['src/ipa/camss-vfe/'+n for n in ['camss.cpp','ipe_tone_profile.cpp','ipe_tone_profile.h','ife_gtm_history.h','ipe_frame_history.h','statistics.h','params.h','parameter_encoder.cpp','parameter_encoder.h']]+['src/ipa/libipa/'+n for n in ['gtm_tmc11.cpp','gtm_tmc11.h','meson.build']]+['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','include/linux/qcom-camss-config.h']
r=dict(stage=435,source=str(T),baseline_stage=431,source_prepared=True,source_hashes=[dict(path=n,sha256=hashlib.sha256((T/n).read_bytes()).hexdigest()) for n in files],private_ipa_version=5,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(stage=435,files=len(files),private_ipa_version=5,source_prepared=True)))
