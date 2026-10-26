from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;root=Path('/home/cy122/x2pro-linux/libcamera214-root');private=Path('/mnt/e/edk2-samurai-out/kernel222')
target=root/'private/request-gap-probe222.cpp';assert not target.exists();shutil.copyfile(here/'request-gap-probe.cpp',target)
command=['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate220/usr/include/libcamera','/private/request-gap-probe222.cpp','-L/candidate220/usr/lib','-Wl,-rpath-link,/candidate220/usr/lib','-lcamera','-lcamera-base','-o','/private/request-gap-probe222']
p=subprocess.run(command,capture_output=True,timeout=150);(private/'gap-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'request-gap-probe';shutil.copyfile(root/'private/request-gap-probe222',target)
r=dict(stage=222,metadata_only_probe_built=True,public_libcamera_api_only=True,pixel_buffers_never_mapped=True,request_count=16,request_gap_milliseconds=500,source_sha256=hashlib.sha256((here/'request-gap-probe.cpp').read_bytes()).hexdigest(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size)
(here/'gap-probe-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
