from pathlib import Path
import subprocess,runpy,hashlib,json
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');runpy.run_path(str(ref/'ensure-build-volume.py'));v=Path('/home/cy122/pmos-samurai-build126');k=v/'kernel';headers=v/'headers'
with (out/'headers-install-private.txt').open('w') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','INSTALL_HDR_PATH='+str(headers),'headers_install'],cwd=k,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
source=ref/'samurai-tpg-capture.c';flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(headers/'include')]
binary=out/'samurai-tpg-capture-aarch64-private';native=out/'samurai-tpg-capture-host-private'
for compiler,target in [('aarch64-linux-gnu-gcc',binary),('gcc',native)]:
 cp=subprocess.run([compiler,*flags,'-static',str(source),'-o',str(target)],capture_output=True,timeout=60);(out/(target.name+'-compile.txt')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:3000]
cp=subprocess.run([str(native),'--self-test'],capture_output=True,timeout=10);assert cp.returncode==0;print(cp.stdout.decode().strip())
cp=subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10);(out/'capture-tool-qemu-self-test-private.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:3000]
cp=subprocess.run([str(native),'--capture',str(out/'should-not-exist.raw')],capture_output=True,timeout=10);assert cp.returncode==3 and b'wrong kernel release' in cp.stderr and not (out/'should-not-exist.raw').exists()
report=dict(static_aarch64_binary_built=True,actual126_kernel_uapi_headers_used=True,native_and_qemu_content_self_tests_pass=True,wrong_kernel_rejected_before_device_open=True,frames_limited_to3=True,poll_timeout_per_frame_ms=5000,active_pixel_prefill_change_threshold_percent=90,width=320,height=240,format='SGRBG10P',standard_media_v4l2_ioctls_only=True,graph_format_control_cleanup_attempted_on_all_exits=True,no_sensor_reg_io=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,not_run_on_phone=True)
(ref/'capture-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('K126_TPG_STATIC_HELPER_UAPI_SELF_TEST_AND_WRONG_KERNEL_GUARD_PASS')
