"""Build a private ARM64 GStreamer candidate from pinned upstream sources."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
R=Path(__file__).parent
P=Path('/mnt/e/edk2-samurai-out/kernel262')
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
W=SDK/'work/pipewire262';source=W/'pipewire-1.6.9';prefix=W/'sdk'
assert source.is_dir() and not prefix.exists()
for apk in (W/'inputs').glob('*.apk'):
 result=subprocess.run(['chroot',str(SDK),'apk','verify','/'+str(apk.relative_to(SDK))],capture_output=True)
 assert result.returncode==0
 with tarfile.open(apk,'r:gz') as a:
  members=[m for m in a.getmembers() if m.name.startswith(('usr/include/','usr/lib/libpipewire','usr/lib/pkgconfig/'))]
  a.extractall(prefix,members=members,filter='data')
patch=P/'source/pool-lock-fix.patch'
q=subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch)],cwd=source,capture_output=True)
(P/'plugin-patch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
config='''#define PACKAGE "pipewire"
#define PACKAGE_VERSION "1.6.9-k262-test"
#define HAVE_GSTREAMER_DEVICE_PROVIDER 1
#define HAVE_GSTREAMER_DMA_DRM 1
#define HAVE_GSTREAMER_VIDEO_DMA_DRM_CAPS 1
'''
(W/'config.h').write_text(config)
script='''set -eu
cd /work/pipewire262
cc -shared -fPIC -O2 -Wall -Wextra -Wno-unused-parameter \
 -I. -Ipipewire-1.6.9/src -Isdk/usr/include/pipewire-0.3 -Isdk/usr/include/spa-0.2 \
 $(pkg-config --cflags gstreamer-1.0 gstreamer-base-1.0 gstreamer-video-1.0 gstreamer-audio-1.0 gstreamer-net-1.0 gstreamer-allocators-1.0) \
 pipewire-1.6.9/src/gst/*.c \
 -Lsdk/usr/lib -lpipewire-0.3 -lm \
 $(pkg-config --libs gstreamer-1.0 gstreamer-base-1.0 gstreamer-video-1.0 gstreamer-audio-1.0 gstreamer-net-1.0 gstreamer-allocators-1.0) \
 -o libgstpipewire.so
'''
(W/'build.sh').write_text(script)
q=subprocess.run(['chroot',str(SDK),'/bin/sh','/work/pipewire262/build.sh'],capture_output=True)
(P/'plugin-build-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'See private plugin build log'
shutil.copyfile(W/'libgstpipewire.so',P/'libgstpipewire-candidate.so')
report=dict(stage=262,upstream='1.6.9',lock_order_patch='30ff8da174121567c06a576bf2a83e71779ee991',candidate_sha256=hashlib.sha256((W/'libgstpipewire.so').read_bytes()).hexdigest(),compiled=True,system_not_deployed=True)
(R/'plugin-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
