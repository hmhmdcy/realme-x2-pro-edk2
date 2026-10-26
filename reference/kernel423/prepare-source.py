"""Connect native IPA tone calculations to owned observations and media requests."""
from pathlib import Path
import json,shutil,sys
import storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();old=new.parent/'libcamera422-tmc-ltm'
assert json.loads((HERE.parent/'kernel422/documentation-validation.json').read_text())['passed']
if new.exists():
    assert sys.argv[1:]==['--resume-preparation'] and not (HERE/'source-state.json').exists(),'Inspect existing candidate rather than resetting it'
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2'
baseline=old/'src/libcamera-v0.7.2'
for name in ['src/ipa/camss-vfe/meson.build','include/libcamera/ipa/camss.mojom','src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']:
    shutil.copyfile(baseline/name,tree/name)
def replace(text,a,b):
    assert text.count(a)==1,(a,text.count(a));return text.replace(a,b)
for n in ['ipe_tone_profile.h','ipe_tone_profile.cpp']:
    shutil.copyfile(HERE/n,tree/'src/ipa/camss-vfe'/n)
shutil.copyfile(HERE.parent/'kernel350/libipa/gamma_segments.h',tree/'src/ipa/libipa/gamma_segments.h')
path=tree/'src/ipa/camss-vfe/meson.build';text=path.read_text();text=replace(text,"['camss.cpp',","['camss.cpp', 'ipe_tone_profile.cpp',");path.write_text(text)
path=tree/'include/libcamera/ipa/camss.mojom';text=path.read_text();text=replace(text,'\t[async] frameProcessed(',
    '\tprepareIpeParameters(uint64 epoch, uint32 sof, uint64 token) => (int32 ret, array<uint8> parameters, uint64 revision, bool fresh);\n\t[async] frameProcessed(');path.write_text(text)
path=tree/'src/ipa/camss-vfe/camss.cpp';text=path.read_text()
text=replace(text,'#include "ipe_frame_history.h"','#include "ipe_frame_history.h"\n#include "ipe_numeric_history.h"\n#include "ipe_tone_profile.h"')
text=replace(text,'\tvoid frameProcessed(', '\tint prepareIpeParameters(uint64_t epoch, uint32_t sof, uint64_t token, std::vector<uint8_t> *parameters, uint64_t *revision, bool *fresh) override;\n\tvoid frameProcessed(')
text=replace(text,'\tIpeFrameHistory ipeHistory_;','\tIpeFrameHistory ipeHistory_;\n\tstd::optional<IpeToneProfile> ipeTone_;\n\tIpeNumericHistory<IpeToneState> numericHistory_;\n\tstd::optional<qcom_ipe_a5_frame_params> pendingTone_, committedTone_;')
assert text.count('agc_.reset(); awb_.reset(); autoAvailable_ = false;')==2
text=text.replace('agc_.reset(); awb_.reset(); autoAvailable_ = false;','agc_.reset(); awb_.reset(); ipeTone_.reset(); autoAvailable_ = false;')
text=replace(text,'ret=LuxProfile::configure(tuning["aec_lux"],&lux_);\n  if (ret) return ret;',
    'ret=LuxProfile::configure(tuning["aec_lux"],&lux_);\n  if (ret) return ret;\n  ret=IpeToneProfile::configure(tuning["ipe_tone"], gamma_ ? &*gamma_ : nullptr, &ipeTone_);\n  if(ret || (ipeTone_ && !lux_)) return ret ? ret : -EINVAL;')
text=replace(text,'if (!ipeHistory_.start(epoch)) return -EINVAL;',
    'if (!ipeHistory_.start(epoch)) return -EINVAL;\n if(!numericHistory_.start(epoch)){ipeHistory_.stop();return -EINVAL;}\n pendingTone_.reset();committedTone_.reset();')
text=replace(text,' ipeHistory_.stop();',' LOG(IPACamss,Info)<<"IPE_TONE_STOP epoch="<<epoch_<<" revision="<<numericHistory_.revision()<<" pending="<<numericHistory_.busy();\n numericHistory_.stop();pendingTone_.reset();committedTone_.reset();\n ipeHistory_.stop();')
text=replace(text,'const int result = ipeHistory_.resolve(epoch, sof, token, success);',
    'const int result = ipeHistory_.resolve(epoch, sof, token, success);\n\tif(numericHistory_.pending() && numericHistory_.pending()->token==token) {\n\t\tconst int numeric=numericHistory_.resolve(epoch,sof,token,success && result>=0);\n\t\tif(numeric==1 && pendingTone_) committedTone_=pendingTone_;\n\t\tif(numeric>=0) pendingTone_.reset();\n\t\tLOG(IPACamss,Info)<<"IPE_TONE_RECEIPT epoch="<<epoch<<" sof="<<sof<<" token="<<token<<" success="<<success<<" result="<<numeric<<" revision="<<numericHistory_.revision();\n\t}')
text=replace(text,'void IPACamss::frameProcessed(', (HERE/'ipa-tone-method.cpp').read_text()+'\nvoid IPACamss::frameProcessed(')
text=replace(text,'IPA_MODULE_API_VERSION, 2, "camss-vfe", "camss-vfe"','IPA_MODULE_API_VERSION, 3, "camss-vfe", "camss-vfe"');path.write_text(text)
path=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';text=path.read_text()
text=replace(text,'createIPA<ipa::camss::IPAProxyCamss>(this, 2, 2)','createIPA<ipa::camss::IPAProxyCamss>(this, 3, 3)') if 'createIPA<ipa::camss::IPAProxyCamss>(this, 2, 2)' in text else text
line=next(l for l in text.splitlines() if 'createIPA<' in l)
if '(2, 2)' in line:text=replace(text,line,line.replace('(2, 2)','(3, 3)'))
assert '(3, 3)' in next(l for l in text.splitlines() if 'createIPA<' in l)
text=replace(text,'  int ret=ipe_->queue(buffer,output);','''  const uint64_t toneEpoch=epoch_;std::vector<uint8_t> tone;uint64_t toneRevision=0;bool toneFresh=false;
  const uint64_t toneToken=requests_.at(request).ipeToken;
  int ret=ipa_->prepareIpeParameters(toneEpoch,sequence,toneToken,&tone,&toneRevision,&toneFresh);
  if(!running_ || epoch_!=toneEpoch || !requests_.count(request))return;
  qcom_ipe_a5_frame_params packet{};
  if(!ret && !tone.empty()) {
   if(tone.size()!=sizeof packet)ret=-EINVAL;
   else std::memcpy(&packet,tone.data(),sizeof packet);
  }
  if(!ret)ret=ipe_->queue(buffer,output,tone.empty()?nullptr:&packet);
  LOG(CamssVfe,Info)<<"IPE_TONE_QUEUE epoch="<<toneEpoch<<" sof="<<sequence<<" token="<<toneToken
   <<" revision="<<toneRevision<<" fresh="<<toneFresh<<" bytes="<<tone.size()<<" result="<<ret;''')
path.write_text(text)
report=dict(stage=423,source=str(tree),baseline_stage=422,private_ipa_version=3,
    actual_ipa_calls_numeric_primitives=True,same_frame_media_request_parameters=True,
    numeric_history_single_pending_final_receipt=True,source_prepared=True,build_pending=True,
    factory_profiles_not_yet_enabled=True,kernel_unchanged=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
