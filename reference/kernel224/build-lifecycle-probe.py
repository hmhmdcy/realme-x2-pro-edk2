from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=sdk/'private/raw-lifecycle-probe224.cpp';assert not source.exists();shutil.copyfile(here/'raw-lifecycle-probe.cpp',source)
args=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate224/usr/include/libcamera','/private/raw-lifecycle-probe224.cpp','-L/candidate224/usr/lib','-Wl,-rpath-link,/candidate224/usr/lib','-lcamera','-lcamera-base','-o','/private/raw-lifecycle-probe224']
p=subprocess.run(args,capture_output=True,timeout=160);(private/'lifecycle-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
out=private/'raw-lifecycle-probe';shutil.copyfile(sdk/'private/raw-lifecycle-probe224',out)
r=dict(stage=224,source_sha256=hashlib.sha256((here/'raw-lifecycle-probe.cpp').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size,public_api_only=True,no_pixel_mapping_or_scene_storage=True,same_camera_reconfiguration_and_pending_request_cancellation=True)
(here/'lifecycle-probe-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
