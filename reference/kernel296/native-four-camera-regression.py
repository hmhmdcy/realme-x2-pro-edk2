
from pathlib import Path
import json,os,pwd,re,resource,signal,subprocess,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai/k296-four-camera-regression-r1');assert not root.exists();root.mkdir(mode=0o700)
state=dict(stage=296,state='preflight',terminal=False,pid=os.getpid(),runs=[])
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def faults(b):return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def runtime():
 result={}
 for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
  found=[p for p in Path('/sys/bus/i2c/drivers',driver).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
  assert len(found)==1,driver
  result[driver]=(found[0]/'power/runtime_status').read_text().strip()
 return result

def rails():
 result={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-','cam-tele-','cam-main-')):result[name]={n:(p/n).read_text().strip() for n in ['state','num_users']}
 return result
def clocks():
 data=Path('/sys/kernel/debug/clk/clk_summary').read_text()
 return {name:int(next(l.split()[1] for l in data.splitlines() if l.split() and l.split()[0]==name)) for name in ['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']}
save();before=subprocess.check_output(['dmesg']);assert not any(faults(before).values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k296-work/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#296 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k296+'
assert all(v=='suspended' for v in runtime().values())
u=pwd.getpwuid(10000)
def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name)
ids=dict(main='/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10',front='/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10',wide='/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10',tele='/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d')
try:
 pattern=['front','main','wide','tele','main','front','tele','wide']*2+['main','main']
 for index,which in enumerate(pattern):
  interrupted=index==16;state.update(state='interrupting-main' if interrupted else 'capture-'+which,leg=index);save()
  start=time.monotonic();p=subprocess.Popen(['cam','-c',ids[which],'--capture='+('10000' if interrupted else '12')],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  state.update(child_pid=p.pid,child_start_ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  forced=False;requested=False
  try:
   stdout,stderr=p.communicate(timeout=3 if interrupted else 20)
  except subprocess.TimeoutExpired:
   if interrupted:requested=True;p.send_signal(signal.SIGINT)
   else:forced=True;p.terminate()
   try:stdout,stderr=p.communicate(timeout=8)
   except subprocess.TimeoutExpired:forced=True;p.kill();stdout,stderr=p.communicate(timeout=3)
  (root/(str(index)+'-stdout-private.log')).write_bytes(stdout);(root/(str(index)+'-stderr-private.log')).write_bytes(stderr)
  seq=[int(v) for v in re.findall(rb'seq:\s*(\d+)',stdout)]
  end=time.monotonic()+3
  while not all(v=='suspended' for v in runtime().values()) and time.monotonic()<end:time.sleep(.1)
  after=subprocess.check_output(['dmesg']);delta={k:v-faults(before)[k] for k,v in faults(after).items()}
  row=dict(leg=index,camera=which,frames=len(seq),monotonic_sequence=bool(seq) and all(b>a for a,b in zip(seq,seq[1:])),exit=p.returncode,
   interrupted=interrupted,sigint_requested=requested,forced=forced,seconds=round(time.monotonic()-start,3),runtime_after=runtime(),rails_after=rails(),mclks_after=clocks(),fault_delta=delta,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
  row['passed']=row['monotonic_sequence'] and (len(seq)>=12 if interrupted else len(seq)==12) and p.returncode==0 and not forced and (requested if interrupted else True) and not any(delta.values()) and row['taint']==0 and all(v=='suspended' for v in row['runtime_after'].values()) and all(v['state']=='disabled' and v['num_users']=='0' for v in row['rails_after'].values()) and not any(row['mclks_after'].values())
  state['runs'].append(row);save()
  if not row['passed']:break
 report=dict(stage=296,legs=state['runs'],passed=len(state['runs'])==18 and all(r['passed'] for r in state['runs']),
  frames=sum(r['frames'] for r in state['runs']),independent_standard_cam_processes=True,front_and_three_rear_cameras=True,
  sigint_and_same_camera_reopen_exercised=len(state['runs'])==18,no_user_space_service_restart=True)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');state.update(state='terminal',terminal=True,exit_code=0 if report['passed'] else 1);save();print(json.dumps(report))
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
