"""Instrument shared-buffer ownership; keep the installed package unchanged."""
from pathlib import Path
import hashlib,json,shlex,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel262')
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire262'
source=W/'ownership-source';build=W/'ownership-build'
assert not source.exists() and not build.exists()
shutil.copytree(W/'pipewire-profile',source);shutil.copytree(W/'profile-build',build)
p=source/'src/gst/gstpipewiresrc.c';s=p.read_text()
needle='  if (!data->queued) {\n    GST_ERROR_OBJECT (pwsrc, "buffer %p was not recycled", data->buf);'
replacement='''  if (!data->queued) {
    struct spa_meta_busy *busy = spa_buffer_find_meta_data(b->buffer, SPA_META_Busy, sizeof(*busy));
    GST_ERROR_OBJECT (pwsrc, "ownership-trace busy=%d refs=%d metas=%u fd=%d", busy ? SPA_ATOMIC_LOAD(busy->count) : -1, GST_MINI_OBJECT_REFCOUNT_VALUE(data->buf), b->buffer->n_metas, (int)b->buffer->datas[0].fd);
    GST_ERROR_OBJECT (pwsrc, "buffer %p was not recycled", data->buf);'''
assert s.count(needle)==1;s=s.replace(needle,replacement);p.write_text(s)
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
pc=['gstreamer-1.0','gstreamer-base-1.0','gstreamer-video-1.0','gstreamer-audio-1.0','gstreamer-net-1.0','gstreamer-allocators-1.0']
cflags=shlex.split(inside(['pkg-config','--cflags',*pc]).stdout.decode());libs=shlex.split(inside(['pkg-config','--libs',*pc]).stdout.decode())
q=inside(['cc','-fPIC','-O2','-I/work/pipewire262/ownership-build','-I/work/pipewire262/ownership-source/src','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',*cflags,'-c','/work/pipewire262/ownership-source/src/gst/gstpipewiresrc.c','-o','/work/pipewire262/ownership-build/gstpipewiresrc.o'])
(P/'ownership-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
objects=['/'+str(p.relative_to(SDK)) for p in sorted(build.glob('*.o'))]
q=inside(['cc','-shared',*objects,'-L/work/pipewire262/sdk/usr/lib','-lpipewire-0.3','-lm',*libs,'-o','/work/pipewire262/ownership-build/libgstpipewire.so']);assert q.returncode==0
shutil.copyfile(build/'libgstpipewire.so',P/'libgstpipewire-ownership.so')
print(json.dumps(dict(stage=262,diagnostic_only=True,installed_plugin_unchanged=True,sha256=hashlib.sha256((build/'libgstpipewire.so').read_bytes()).hexdigest())))
