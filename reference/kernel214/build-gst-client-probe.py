from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;root=Path('/home/cy122/x2pro-linux/libcamera214-root');private=Path('/mnt/e/edk2-samurai-out/kernel214')
source=here/'gst-default-camera-probe.c';shutil.copyfile(source,root/'private'/source.name)
p=subprocess.run(['chroot',str(root),'/usr/bin/pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-1.0'],capture_output=True,text=True,timeout=15);assert p.returncode==0
p=subprocess.run(['chroot',str(root),'/usr/bin/cc','-O2','-Wall','-Wextra','-Werror','/private/'+source.name,*p.stdout.split(),'-o','/private/gst-default-camera-probe'],capture_output=True,timeout=120);(private/'gst-probe-compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'probes/gst-default-camera-probe';assert not target.exists();shutil.copyfile(root/'private/gst-default-camera-probe',target)
report=dict(stage=214,finite_gstreamer_apps_only_client_built=True,headless=True,no_saved_scene_or_external_illumination=True,frames_requested=6,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),no_image_statistics_claim_from_unsynchronised_gst_buffer=True)
(here/'gst-client-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
