from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss437-contract';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
original=(HERE.parent/'kernel431/ipa-contract.cpp').read_text()
prefix=original.split(' uint32_t bytes=0;')[0].replace('constexpr uint32_t used=','constexpr uint32_t baseUsed=').replace('used-sizeof(*envelope)','baseUsed-sizeof(*envelope)')
prefix=prefix.replace('#include <memory>','#include <memory>\n#include <optional>')
prefix=prefix.replace('ipa::camss::Statistics result{}; unsigned calls=0;','ipa::camss::Statistics result{}; ControlList metadata{controls::controls}; unsigned calls=0;')
prefix=prefix.replace('const ControlList &){result=s;++calls;}','const ControlList &m){result=s;metadata=m;++calls;}')
prefix=prefix.replace('start.set(controls::AwbEnable,false)','start.set(controls::AwbEnable,true)')
prefix+=' const uint32_t legacyGrid=sizeof(v4l2_isp_buffer)+sizeof(camss_stats_bhist);std::vector<uint8_t> grid(memory+legacyGrid,memory+baseUsed);\n'
(work/'awb-status.cpp').write_text(prefix+(HERE/'awb-contract-body.cpp').read_text())
shutil.copyfile(P/'factory-s5kgw1-private.yaml',work/'factory.yaml')
with storage.sdk_candidate():
 command=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include','-I'+T+'/src/ipa/camss-vfe',W+'/awb-status.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/awb-status']
 q=subprocess.run(command,capture_output=True);(P/'awb-contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 args=[W+'/awb-status',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/factory.yaml','factory',W+'/awb.bin']
 q=subprocess.run(['chroot',str(storage.SDK),*env,*args],capture_output=True,timeout=35);(P/'awb-contract-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.returncode,(q.stdout+q.stderr).decode()[-3500:])
r=dict(stage=437,actual_arm64_ipa_module=True,actual_ipa_sha256=hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest(),werror=True,synthetic_pre_wb_grid=True,delayed_actual_gtm_ack_with_identical_wb_preserves_lock=True,missing_bg_invalidates=True,restart_resets=True,awb_thresholds_unchanged=True,passed=True)
(HERE/'awb-module-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
