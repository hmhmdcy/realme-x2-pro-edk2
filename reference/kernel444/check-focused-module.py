"""Compare separate and combined calls on the actual IPA6, including GTM history."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed'] and build['private_ipa_version']==6
prefix=(HERE.parent/'kernel431/ipa-contract.cpp').read_text().split(' uint32_t bytes=0;')[0]
prefix=prefix.replace('#include <cassert>','#include <cassert>\n#include <array>\n#include <cstdlib>\n#include <ctime>')
prefix=prefix.replace('constexpr uint32_t used=','constexpr uint32_t baseUsed=').replace('used-sizeof(*envelope)','baseUsed-sizeof(*envelope)')
prefix=prefix.replace('info.outputSize=Size(4608,3456);','info.outputSize=Size(4608,std::stoul(getenv("CONTRACT_HEIGHT")));')
prefix=prefix.replace('for(auto &bin:hist->bins)bin=3888;', 'for(auto &bin:hist->bins)bin=(info.outputSize.width/2)*(info.outputSize.height/2)/1024;')
body=(HERE.parent/'kernel435/gtm-contract-body.cpp').read_text()
old=' auto prepare=[&](uint32_t sof,uint64_t token){return ipa->prepareIpeParameters(1,sof,token,&packet,&revision,&fresh);};'
replacement='''
 const bool combined=std::string(getenv("COMBINED_FOCUS"))=="1";
 std::ofstream snapshot(argv[4],std::ios::binary);assert(snapshot.good());
 ControlList focusControls(controls::controls);ipa::camss::LensMove lastMove{};
 bool lastPrepared=false;int lastFocusStatus=0;
 auto focused=[&](uint64_t epoch,uint32_t sof,uint64_t token,const ControlList &focus){
  ControlList metadata(controls::controls);ipa::camss::LensMove move{};
  bool prepared=false;int32_t toneStatus=0;packet.clear();revision=0;fresh=false;
  timespec clock{};assert(!clock_gettime(CLOCK_MONOTONIC,&clock));
  const uint64_t captured=uint64_t(clock.tv_sec)*1000000000+clock.tv_nsec;
  int focusStatus;
  if(combined)focusStatus=ipa->prepareFocusedIpe(epoch,sof,token,focus,true,321,captured,
    ipa::camss::SensorContext{true,500,32,0},&metadata,&move,&prepared,&toneStatus,&packet,&revision,&fresh);
  else {
   focusStatus=ipa->processFocus(epoch,sof,focus,true,321,captured,ipa::camss::SensorContext{true,500,32,0},&metadata,&move);
   if(!move.valid){prepared=true;toneStatus=ipa->prepareIpeParameters(epoch,sof,token,&packet,&revision,&fresh);}
  }
  const std::array<uint64_t,15> header{epoch,sof,token,uint64_t(int64_t(focusStatus)),uint64_t(int64_t(toneStatus)),
   prepared,revision,fresh,packet.size(),uint64_t(int64_t(metadata.get(controls::FocusFoM).value_or(-1))),
   uint64_t(int64_t(metadata.get(controls::AfState).value_or(-1))),uint64_t(int64_t(metadata.get(controls::AfMode).value_or(-1))),
   move.valid,move.serial,uint64_t(int64_t(move.position))};
  snapshot.write(reinterpret_cast<const char*>(header.data()),sizeof header);
  snapshot.write(reinterpret_cast<const char*>(packet.data()),packet.size());assert(snapshot.good());
  lastMove=move;lastPrepared=prepared;lastFocusStatus=focusStatus;
  return int(toneStatus);
 };
 auto prepare=[&](uint32_t sof,uint64_t token){
  int ret=focused(1,sof,token,focusControls);assert(!lastFocusStatus&&lastPrepared&&!lastMove.valid);return ret;
 };
'''
assert body.count(old)==1;body=body.replace(old,replacement)
marker=' ipa->stop();assert(!ipa->start(2,start,&converted));'
extra='''
 // A real AF trigger creates a move. Neither path prepares tone before ACK.
 ControlList trigger(controls::controls);trigger.set(controls::AfTrigger,controls::AfTriggerStart);
 assert(!focused(1,100,UINT64_MAX,trigger));assert(!lastFocusStatus&&lastMove.valid&&!lastPrepared&&packet.empty()&&!revision&&!fresh);
 ipa->lensPositionApplied(1,lastMove.serial,-EIO,0);
 assert(focused(1,101,UINT64_MAX,focusControls)==-ESTALE&&lastPrepared&&!lastMove.valid);
 ipa->stop();
 assert(focused(1,102,0,focusControls)==-ESTALE&&lastFocusStatus==-ESTALE);
 assert(!ipa->start(2,start,&converted));
 assert(focused(1,103,0,focusControls)==-ESTALE&&lastFocusStatus==-ESTALE);
'''
assert body.count(marker)==1;body=body.replace(marker,extra)
body=body.replace(' std::cout<<"GTM_IPA_CONTRACT', ' snapshot.close();assert(snapshot.good());\n std::cout<<"GTM_IPA_CONTRACT')
source=prefix+body
if (P/'focused-contract-build.log').exists() and not (P/'focused-module-zero-timestamp-rejected.cpp').exists():shutil.copyfile(HERE/'focused-module.cpp',P/'focused-module-zero-timestamp-rejected.cpp')
(HERE/'focused-module.cpp').write_text(source)
W='/private/camss444-focused';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True);(work/'contract.cpp').write_text(source)
shutil.copyfile(P.parent/'kernel443/factory-s5kgw1-private.yaml',work/'factory.yaml')
T='/work/libcamera/src/libcamera-v0.7.2';rows=[]
attempt=1
while (P/f'focused-contract-r{attempt}-build.log').exists():attempt+=1
with storage.sdk_candidate():
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 q=subprocess.run(['chroot',str(storage.SDK),*env,T+'/output/src/apps/ipa-verify/ipa_verify',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True)
 (P/'signature-check.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/contract.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/contract'],capture_output=True)
 (P/f'focused-contract-r{attempt}-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2300:]
 for height in [3456,2592]:
  results=[]
  for combined in [False,True]:
   label=f'r{attempt}-'+str(height)+'-'+('combined' if combined else 'separate');dest=W+'/'+label+'.bin'
   q=subprocess.run(['chroot',str(storage.SDK),*env,'CONTRACT_HEIGHT='+str(height),'COMBINED_FOCUS='+str(int(combined)),W+'/contract',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/factory.yaml','factory',dest],capture_output=True,timeout=45)
   (P/(label+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(label,q.returncode,q.stderr.decode()[-2500:])
   data=(work/(label+'.bin')).read_bytes();(P/(label+'-contract-private.bin')).write_bytes(data);results.append(data)
  assert results[0]==results[1]
  at=0;count=0
  while at<len(results[0]):
   header=struct.unpack_from('<15Q',results[0],at);length=header[8];assert length in [0,6008];at+=120+length;count+=1
  assert at==len(results[0]) and count>0
  rows.append(dict(height=height,compared_calls=count,return_metadata_lens_move_tone_status_revision_fresh_and_packet_bytes_equal=True,passed=True))
r=dict(stage=444,attempt=attempt,actual_arm64_ipa6=True,actual_module_sha256=hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest(),signature_verified=True,werror_build=True,
 rows=rows,gtm_bootstrap_ack_missing_lux_failure_success_and_restart_history_retained=True,
 lens_move_defers_tone_until_host_ack=True,stopped_and_stale_epoch_statuses_equal=True,synthetic_statistics_not_hardware=True,phone_accessed=False,passed=True)
(HERE/'focused-module-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
