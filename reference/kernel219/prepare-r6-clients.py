from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;prior=here.parent/'kernel214';private=Path('/mnt/e/edk2-samurai-out/kernel219');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
code=(prior/'reload-wireplumber.py').read_text()
code=code.replace("here/'package-install-validation.json'","here/'r6-package-install-validation.json'")
code=code.replace('/var/lib/samurai/k214-baseline','/var/lib/samurai/k219-runtime').replace('/var/lib/samurai/k214-package-transaction','/var/lib/samurai/k219-r6-package-transaction').replace('/var/lib/samurai/k214-package-candidates','/var/lib/samurai/k219-r6-package-candidates')
code=code.replace('stage=214','stage=219').replace('new_r5_camera_libraries_loaded','new_r6_camera_libraries_loaded')
compile(code,'reload-wireplumber219','exec');(here/'reload-wireplumber.py').write_text(code)
source=(prior/'gst-default-camera-probe.c').read_text().replace('1920','2296').replace('1088','1728')
(here/'gst-camera219-probe.c').write_text(source);shutil.copyfile(here/'gst-camera219-probe.c',root/'private/gst-camera219-probe.c')
p=subprocess.run(['chroot',str(root),'/usr/bin/pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-1.0'],capture_output=True,text=True,timeout=15);assert p.returncode==0
p=subprocess.run(['chroot',str(root),'/usr/bin/cc','-O2','-Wall','-Wextra','-Werror','/private/gst-camera219-probe.c',*p.stdout.split(),'-o','/private/gst-camera219-probe'],capture_output=True,timeout=120)
(private/'gst-probe-compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'probes/gst-camera219-probe';assert not target.exists();target.parent.mkdir(mode=0o700,exist_ok=True);shutil.copyfile(root/'private/gst-camera219-probe',target)
r=dict(stage=219,finite_standard_gstreamer_client_built=True,width=2296,height=1728,frames_requested=6,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),cpu_pixel_statistics_not_claimed=True)
(here/'gst-client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
