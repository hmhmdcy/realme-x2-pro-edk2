"""Build the full-feature opt-in profile separately from the first candidate."""
from pathlib import Path
import concurrent.futures,hashlib,json,shlex,shutil,subprocess
R=Path(__file__).parent;ROOT=R.parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel262')
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire262'
base=W/'pipewire-1.6.9';source=W/'pipewire-profile';assert not source.exists()
shutil.copytree(base,source)
recipe=ROOT/'linux-port/packages/gst-plugin-pipewire'
shutil.copyfile(P/'source/pool-lock-fix.patch',recipe/'0001-defer-pool-buffer-recycle.patch')
q=subprocess.run(['patch','--batch','--forward','-p1','-i',str(recipe/'0002-camera-copy-profile.patch')],cwd=source,capture_output=True)
(P/'profile-patch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
build=W/'profile-build';build.mkdir()
(build/'config.h').write_text('#define PACKAGE "pipewire"\n#define PACKAGE_VERSION "1.6.9"\n#define HAVE_GSTREAMER_DEVICE_PROVIDER 1\n#define HAVE_GSTREAMER_DMA_DRM 1\n#define HAVE_GSTREAMER_SHM_ALLOCATOR 1\n')
pc=['gstreamer-1.0','gstreamer-base-1.0','gstreamer-video-1.0','gstreamer-audio-1.0','gstreamer-net-1.0','gstreamer-allocators-1.0']
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
flags=shlex.split(inside(['pkg-config','--cflags',*pc]).stdout.decode())
libs=shlex.split(inside(['pkg-config','--libs',*pc]).stdout.decode())
common=['cc','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-I/work/pipewire262/profile-build','-I/work/pipewire262/pipewire-profile/src','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',*flags]
def compile_one(p):
 obj=build/(p.stem+'.o');q=inside([*common,'-c','/'+str(p.relative_to(SDK)),'-o','/'+str(obj.relative_to(SDK))])
 (P/('profile-'+p.stem+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,p.name
 return '/'+str(obj.relative_to(SDK))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:objects=list(pool.map(compile_one,sorted((source/'src/gst').glob('*.c'))))
binary=build/'libgstpipewire.so'
q=inside(['cc','-shared',*objects,'-L/work/pipewire262/sdk/usr/lib','-lpipewire-0.3','-lm',*libs,'-o','/'+str(binary.relative_to(SDK))]);assert q.returncode==0,q.stderr.decode()
q=inside(['strip','--strip-unneeded','/'+str(binary.relative_to(SDK))]);assert q.returncode==0
shutil.copyfile(binary,P/'libgstpipewire-profile.so')
inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'source/pipewire-1.6.9.tar.gz',P/'source/pipewire-dev-1.6.9-r0.apk',P/'source/pipewire-libs-1.6.9-r0.apk',recipe/'0001-defer-pool-buffer-recycle.patch',recipe/'0002-camera-copy-profile.patch']}
report=dict(stage=262,compiled=True,candidate_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),inputs=inputs,shm_allocator_enabled=True,copy_opt_in='SAMURAI_CAMERA_COPY=1',upstream_default_preserved=True,system_not_deployed=True)
(R/'profile-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
sha512=[hashlib.sha512(p.read_bytes()).hexdigest()+'  '+name for p,name in [(P/'source/pipewire-1.6.9.tar.gz','pipewire-1.6.9.tar.gz'),(recipe/'0001-defer-pool-buffer-recycle.patch','0001-defer-pool-buffer-recycle.patch'),(recipe/'0002-camera-copy-profile.patch','0002-camera-copy-profile.patch')]]
apkbuild=recipe/'APKBUILD';text=apkbuild.read_text();assert 'sha512sums=' not in text
apkbuild.write_text(text+'\nsha512sums="\n'+'\n'.join(sha512)+'\n"\n')
(recipe/'source-lock.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='inputs'}))
