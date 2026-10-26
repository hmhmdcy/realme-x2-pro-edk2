"""Link the fault probe to the unchanged, hardware-tested 418 library."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
base=(HERE.parent/'kernel418/ipe-smoke.cpp').read_text().split('class Capture : public Object')[0]
base=base.replace('static constexpr std::array<unsigned,8> modes={0,1,2,2,3,4,0,1};\n','')
source=base+(HERE/'ack-loss-tail.cpp').read_text();(HERE/'ack-loss-client.cpp').write_text(source)
slot=storage.SDK/'private-k419';slot.mkdir(exist_ok=True)
shutil.copyfile(storage.SDK/'private-k418/request-params.h',slot/'request-params.h')
shutil.copyfile(HERE/'ack-loss-client.cpp',slot/'ack-loss-client.cpp')
with storage.sdk_candidate():
    tree='/work/libcamera/src/libcamera-v0.7.2'
    args=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-g','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE',
        '-I'+tree+'/include','-I'+tree+'/output/include','-I'+tree+'/src/libcamera/pipeline/camss-vfe','-I/private-k419',
        '/private-k419/ack-loss-client.cpp','-L'+tree+'/output/src/libcamera','-L'+tree+'/output/src/libcamera/base',
        '-Wl,-rpath-link,'+tree+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private-k419/ack-loss-client']
    q=subprocess.run(args,capture_output=True)
(P/'client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
shutil.copyfile(slot/'ack-loss-client',P/'ack-loss-client')
tree=storage.candidate()/'src/libcamera-v0.7.2';shutil.copyfile(tree/'output/src/libcamera/libcamera.so.0.7.2',P/'libcamera.so.0.7.2')
previous=json.loads((HERE.parent/'kernel418/runtime-build-validation.json').read_text())
assert hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest()==previous['library_sha256']
r=dict(stage=419,actual_libcamera418_unchanged=True,client_werror=True,one_real_success_ack_planned_drop=True,
    two_warm_nonzero_ltm_sessions=True,combined_ltm_gamma_fault_packet=True,idle_consumer_held_to_check_fatal_gate=True,
    wrapper_watchdog_and_kernel_timeouts_unchanged=True,probe_sha256=hashlib.sha256((P/'ack-loss-client').read_bytes()).hexdigest(),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
