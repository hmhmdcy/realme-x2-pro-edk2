"""Reject zero-ref resurrection; narrow v3 to the independent Busy lifetime fix."""
from pathlib import Path
import difflib,hashlib,json,os,resource,shlex,shutil,subprocess
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy';work=W/'v3';assert not work.exists();work.mkdir()
def inside(args,**kw):return subprocess.run(['chroot',str(SDK),*args],capture_output=True,**kw)
pkgs=['gstreamer-1.0','gstreamer-base-1.0','gstreamer-video-1.0','gstreamer-audio-1.0','gstreamer-net-1.0','gstreamer-allocators-1.0']
flags=shlex.split(inside(['pkg-config','--cflags',*pkgs]).stdout.decode());libs=shlex.split(inside(['pkg-config','--libs',*pkgs]).stdout.decode())
(work/'dispose-race-test.c').write_bytes((R/'dispose-race-test.c').read_bytes())
q=inside(['cc','-O1','-g','-Wall','-Wextra','-Werror','/work/pipewire265-retained-busy/v3/dispose-race-test.c',*flags,*libs,'-pthread','-o','/work/pipewire265-retained-busy/v3/dispose-race-test']);assert q.returncode==0,q.stderr.decode()
def limit():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
env=os.environ.copy();env.update(GST_PLUGIN_PATH='',GST_PLUGIN_SYSTEM_PATH='',GST_REGISTRY='/tmp/k265-dispose-unit-registry.bin')
q=inside(['/work/pipewire265-retained-busy/v3/dispose-race-test'],env=env,preexec_fn=limit,timeout=20);assert q.returncode==0,(q.stdout+q.stderr).decode()
n=inside(['/work/pipewire265-retained-busy/v3/dispose-race-test','unsafe-pin'],env=env,preexec_fn=limit,timeout=20);assert n.returncode!=0
(host.PRIVATE/'dispose-race-positive-private.log').write_bytes(q.stdout+q.stderr);(host.PRIVATE/'dispose-race-negative-private.log').write_bytes(n.stdout+n.stderr)
report=dict(stage=265,arm64_real_gstreamer=True,positive=json.loads(q.stdout),temporary_pin_frees_while_dispose_callback_live_negative_detected=True,negative_exit=n.returncode,phone_failure_same_cause_not_yet_proven=True)
(R/'dispose-race-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
source=work/'source';shutil.copytree(W/'source',source);p=source/'gstpipewiresrc.c';s=p.read_text()
needle='  /* Pin across flush-start: downstream may synchronously drop its last ref. */\n  GstBuffer *buf = gst_buffer_ref (data->buf);';assert s.count(needle)==1;s=s.replace(needle,'  GstBuffer *buf = data->buf;')
needle='  /* Retired frames release their own Busy loan when the last Gst ref dies. */\n  gst_buffer_unref (buf);\n';assert s.count(needle)==1;s=s.replace(needle,'');p.write_text(s)
# No on_remove_buffer changes remain relative to the trusted r1 source.
original=SDK/'work/pipewire262/pipewire-profile/src/gst'
a=s.index('static void\non_remove_buffer (');b=s.index('\nstatic const char * const transform_map',a)
old=(original/'gstpipewiresrc.c').read_text();x=old.index('static void\non_remove_buffer (');y=old.index('\nstatic const char * const transform_map',x)
assert s[a:b]==old[x:y]
patch=''
for name in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']:
 patch+=''.join(difflib.unified_diff((original/name).read_text().splitlines(True),(source/name).read_text().splitlines(True),fromfile='a/src/gst/'+name,tofile='b/src/gst/'+name))
(R/'gst-retained-busy-v3-candidate.patch').write_text(patch)
common=['cc','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-I/work/pipewire265-retained-busy/build-v2','-I/work/pipewire265-retained-busy/v3/source','-I/work/pipewire265-retained-busy/include','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',*flags]
q=inside([*common,'-c','/work/pipewire265-retained-busy/v3/source/gstpipewiresrc.c','-o','/work/pipewire265-retained-busy/v3/gstpipewiresrc.o']);(host.PRIVATE/'v3-source-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
objects=['/'+str(p.relative_to(SDK)) for p in sorted((W/'build-v2').glob('*.o')) if p.name!='gstpipewiresrc.o']
objects.append('/work/pipewire265-retained-busy/v3/gstpipewiresrc.o')
binary=work/'libgstpipewire.so'
q=inside(['cc','-shared',*objects,'-L/work/pipewire265-retained-busy/core-map-lookup','-lpipewire-0.3','-lm',*libs,'-o','/work/pipewire265-retained-busy/v3/libgstpipewire.so']);assert q.returncode==0,q.stderr.decode()
assert inside(['strip','--strip-unneeded','/work/pipewire265-retained-busy/v3/libgstpipewire.so']).returncode==0
shutil.copyfile(binary,host.PRIVATE/'libgstpipewire-retained-busy-v3.so')
report=dict(stage=265,compiled=True,plugin_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),src_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),on_remove_unchanged_from_r1=True,temporary_zero_ref_pin_removed=True,busy_helpers_identical_to_real_imported_map_unit=True,system_not_deployed=True)
assert (source/'gstpipewirepool.c').read_bytes()==(W/'source/gstpipewirepool.c').read_bytes()
(R/'retained-busy-v3-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

