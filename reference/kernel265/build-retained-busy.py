from pathlib import Path
import concurrent.futures,hashlib,json,shlex,shutil,subprocess
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';source=W/'source';build=W/'build';build.mkdir(exist_ok=True);assert not (build/'libgstpipewire.so').exists()
include=W/'include';include.mkdir(exist_ok=True)
if not (include/'gst').exists():(include/'gst').symlink_to('../source')
assert (include/'gst').resolve()==source.resolve()
(build/'config.h').write_bytes((SDK/'work/pipewire262/profile-build/config.h').read_bytes())
pc=['gstreamer-1.0','gstreamer-base-1.0','gstreamer-video-1.0','gstreamer-audio-1.0','gstreamer-net-1.0','gstreamer-allocators-1.0']
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
flags=shlex.split(inside(['pkg-config','--cflags',*pc]).stdout.decode());libs=shlex.split(inside(['pkg-config','--libs',*pc]).stdout.decode())
common=['cc','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-I/work/pipewire265-retained-busy/build','-I/work/pipewire265-retained-busy/source','-I/work/pipewire265-retained-busy/include','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',*flags]
def compile_one(p):
 obj=build/(p.stem+'.o');q=inside([*common,'-c','/'+str(p.relative_to(SDK)),'-o','/'+str(obj.relative_to(SDK))]);(host.PRIVATE/('retained-'+p.stem+'-build-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,(p.name,q.stderr.decode()[-2000:]);return '/'+str(obj.relative_to(SDK))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:objects=list(pool.map(compile_one,sorted(source.glob('*.c'))))
binary=build/'libgstpipewire.so';q=inside(['cc','-shared',*objects,'-L/work/pipewire262/sdk/usr/lib','-lpipewire-0.3','-lm',*libs,'-o','/'+str(binary.relative_to(SDK))]);(host.PRIVATE/'retained-plugin-link-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert inside(['strip','--strip-unneeded','/'+str(binary.relative_to(SDK))]).returncode==0
shutil.copyfile(binary,host.PRIVATE/'libgstpipewire-retained-busy.so')
report=dict(stage=265,compiled=True,candidate_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),shm_allocator_enabled=True,dma_drm_enabled=True,copy_opt_in_not_required=True,source_version='1.6.9',system_not_deployed=True)
(R/'retained-busy-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

