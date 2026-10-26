"""Build the candidate in a fresh output tree, preserving all deployed outputs."""
from pathlib import Path
import hashlib,json,os,resource,shutil,subprocess,sys,time,traceback
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel272')
W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera272-build-r1')
attempt=int(sys.argv[1]) if len(sys.argv)>1 else 1
assert attempt in [1,2,3]
os.umask(0o077)
if attempt==1:
 B.mkdir(mode=0o700)
 shutil.copyfile('/home/cy122/x2pro-linux/camera269-full-build-r1/.config',B/'.config')
 subprocess.run([str(W/'scripts/config'),'--file',str(B/'.config'),'--module','VIDEO_S5KGW1',
  '--set-str','LOCALVERSION','-rmx1931-samurai-k272','--disable','LOCALVERSION_AUTO',
  '--set-str','INITRAMFS_SOURCE',''],check=True)
else:
 old=json.loads((P/'driver-build-state-private.json').read_text())
 assert old['terminal'] and old['state']=='failed'
 shutil.copyfile(P/'driver-build-state-private.json',P/('driver-build-r'+str(attempt-1)+'-state-private.json'))
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
 KBUILD_BUILD_VERSION='272',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai')
base=['make','-C',str(W),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
 'LD=aarch64-linux-gnu-ld --no-keep-memory','-j3']
state=dict(stage=272,attempt=attempt,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],state='running',terminal=False,steps=[])
def save():(P/'driver-build-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def limit():resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
save()
try:
 steps=[('configure',['olddefconfig']),('prepare',['modules_prepare']),
                   ('sensor',['W=1','drivers/media/i2c/s5kgw1.o']),
                   ('board',['qcom/sm8150-samurai.dtb'])]
 if attempt>1:steps=steps[2:]
 for name,args in steps:
  with (B/(name+'-r'+str(attempt)+'-private.log')).open('xb') as log:
   start=time.monotonic();child=subprocess.Popen(base+args,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
   state.update(step=name,child_pid=child.pid,child_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
   ret=child.wait()
  state['steps'].append(dict(name=name,exit=ret,seconds=round(time.monotonic()-start,2)));save()
  assert ret==0,'Inspect this build log; phone and existing build outputs unchanged'
 diagnostics=[l for l in (B/('sensor-r'+str(attempt)+'-private.log')).read_text().splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
 assert not diagnostics,diagnostics
 report=dict(stage=272,attempt=attempt,steps=state['steps'],sensor_w1_diagnostics=0,
  object_sha256=hashlib.sha256((B/'drivers/media/i2c/s5kgw1.o').read_bytes()).hexdigest(),
  dtb_sha256=hashlib.sha256((B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()).hexdigest(),
  normal_kconfig_enabled='CONFIG_VIDEO_S5KGW1=m' in (B/'.config').read_text(),
  existing_builds_unchanged=True,object_and_dtb_compile_only=True,module_and_hardware_not_verified=True,phone_unchanged=True)
 (R/'driver-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report,indent=2))
except BaseException:
 (P/'driver-build-failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
