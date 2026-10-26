"""Build a real libcamera application and a separate test-only state fixture."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss299-application';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'pipeline-smoke.cpp',stage/'pipeline-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/candidate278-r24/usr/include/libcamera','/private/camss299-application/pipeline-smoke.cpp',
 '-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib','-lcamera','-lcamera-base','-pthread',
 '-o','/private/camss299-application/pipeline-smoke'],capture_output=True,timeout=180)
(host.PRIVATE/'inline-smoke-compile-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stderr.decode()
shutil.copyfile(stage/'pipeline-smoke',host.PRIVATE/'pipeline-smoke-aarch64-private')
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'pipeline-fixture.c'),
 '-o',str(host.PRIVATE/'pipeline-fixture-aarch64-private')],capture_output=True,timeout=120)
(host.PRIVATE/'inline-fixture-compile-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stderr.decode()
wrong=subprocess.run(['qemu-aarch64',str(host.PRIVATE/'pipeline-fixture-aarch64-private'),'/dev/media0','/tmp/never-executed'],capture_output=True,timeout=10)
assert wrong.returncode==3
report=dict(stage=299,application_public_libcamera_api_compile_pass=True,fixture_strict_static_compile_pass=True,fixture_wrong_kernel_guard_pass=True,
 application_source_sha256=hashlib.sha256((stage/'pipeline-smoke.cpp').read_bytes()).hexdigest(),fixture_source_sha256=hashlib.sha256((HERE/'pipeline-fixture.c').read_bytes()).hexdigest(),
 planned_restart_epochs=3,minimum_images_per_epoch=24,start_wb_is_scene_estimate_only=True,never_installs_or_replaces_system_library=True,
 binaries={n:dict(bytes=(host.PRIVATE/n).stat().st_size,sha256=hashlib.sha256((host.PRIVATE/n).read_bytes()).hexdigest()) for n in ['pipeline-smoke-aarch64-private','pipeline-fixture-aarch64-private']})
(HERE/'inline-smoke-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
