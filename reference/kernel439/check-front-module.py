from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss439-module';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
original=(HERE.parent/'kernel431/ipa-contract.cpp').read_text();prefix=original.split(' uint32_t bytes=0;')[0].replace('constexpr uint32_t used=','constexpr uint32_t baseUsed=').replace('used-sizeof(*envelope)','baseUsed-sizeof(*envelope)')
prefix=prefix.replace('#include <memory>','#include <memory>\n#include <array>').replace('ipa::camss::Statistics result{}; unsigned calls=0;','ipa::camss::Statistics result{}; ControlList metadata{controls::controls}; unsigned calls=0;').replace('const ControlList &){result=s;++calls;}','const ControlList &m){result=s;metadata=m;++calls;}')
prefix=prefix.replace('"s5kgw1"','"imx471"').replace('Size(4608,3456)','Size(2304,1728)').replace('"lc898219xi"','""')
prefix=prefix.replace('info.pixelRate=1920000000;info.minLineLength=info.maxLineLength=17824;info.minFrameLength=3584;', 'info.pixelRate=326400000;info.minLineLength=info.maxLineLength=2560;info.minFrameLength=2124;')
prefix=prefix.replace('int32_t(3576)','int32_t(2116)').replace('int32_t(32),int32_t(512),int32_t(32)','int32_t(0),int32_t(960),int32_t(0)')
prefix=prefix.replace('bin=3888','bin=972')
prefix=prefix.replace('start.set(controls::ColourGains,{1.f,1.f});','start.set(controls::ColourGains,{1.f,1.f});start.set(controls::ColourTemperature,3000);')
(work/'module.cpp').write_text(prefix+(HERE/'front-module-body.cpp').read_text());shutil.copyfile(P/'factory-imx471-private.yaml',work/'factory.yaml')
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include',W+'/module.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/module'],capture_output=True)
 (P/'front-module-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base',W+'/module',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/factory.yaml','factory',W+'/unused.bin'],capture_output=True,timeout=40)
 (P/'front-module-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.returncode,(q.stdout+q.stderr).decode()[-4000:]);print(q.stdout.decode(),flush=True)
r={'stage':439,'passed':True,'actual_arm64_ipa_dso':True,'ipa_sha256':hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest(),'future_cct_and_manual_controls_wait_for_physical_gtm_ack':True,'observed_frame_colour_owned_before_later_control_request':True,'failed_ipe_does_not_commit_math':True,'disabled_gtm_and_absent_ife_ccm_verified':True,'synthetic_statistics_and_gtm_receipts':True,'phone_changed':False}
(HERE/'front-module-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
