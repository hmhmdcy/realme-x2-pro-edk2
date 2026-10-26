"""Compile the standard-resource sensor candidate without altering accepted builds."""
from pathlib import Path
import hashlib,json,os,resource,shutil,subprocess,time,traceback
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270')
W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera270-build-r1')
os.umask(0o077);B.mkdir(mode=0o700)
shutil.copyfile('/home/cy122/x2pro-linux/camera269-full-build-r1/.config',B/'.config')
subprocess.run([str(W/'scripts/config'),'--file',str(B/'.config'),'--module','VIDEO_S5K3M5',
 '--set-str','LOCALVERSION','-rmx1931-samurai-k270','--disable','LOCALVERSION_AUTO',
 '--set-str','INITRAMFS_SOURCE',''],check=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
 KBUILD_BUILD_VERSION='270',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai')
base=['make','-C',str(W),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','-j3']
state=dict(stage=270,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],state='running',terminal=False,steps=[])
def save():(P/'telephoto-build-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
save()
try:
 for name,args in [('configure',['olddefconfig']),('prepare',['modules_prepare']),('sensor',['W=1','drivers/media/i2c/s5k3m5.o'])]:
  with (B/(name+'-private.log')).open('xb') as log:
   start=time.monotonic();child=subprocess.Popen(base+args,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
   state.update(step=name,child_pid=child.pid,child_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
   ret=child.wait()
  state['steps'].append(dict(name=name,exit=ret,seconds=round(time.monotonic()-start,2)));save()
  assert ret==0,'Compile failed; inspect the private log; no phone changes'
 diagnostics=[l for l in (B/'sensor-private.log').read_text().splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
 assert not diagnostics,diagnostics
 obj=B/'drivers/media/i2c/s5k3m5.o'
 report=dict(stage=270,steps=state['steps'],sensor_w1_diagnostics=0,object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
  normal_kconfig_enabled='CONFIG_VIDEO_S5K3M5=m' in (B/'.config').read_text(),
  existing_kernel269_outputs_unchanged=True,object_compile_only=True,module_and_hardware_not_verified=True,phone_unchanged=True)
 (R/'telephoto-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report,indent=2))
except BaseException:
 (P/'telephoto-build-failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
