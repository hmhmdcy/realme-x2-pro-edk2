"""Try actual RAW and ordinary RGB capture on the newly identified rear sensor."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,resource,subprocess,time,traceback
os.umask(0o077);out=Path('/var/lib/samurai/k273-main-capture-r1');out.mkdir(mode=0o700)
state=dict(stage=273,state='preflight',terminal=False,pid=os.getpid(),runs=[])
def save():(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def faults(b):return {k:b.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
def runtime():return {n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['6-0010','7-0010','8-002d','9-0010']}
def rails():
 result={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-','cam-tele-','cam-main-')):result[name]={n:(p/n).read_text().strip() for n in ['state','num_users']}
 return result
save();before=subprocess.check_output(['dmesg']);logger=None
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k273-work/boot-id-private.txt').read_bytes()
 assert not any(faults(before).values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(v=='suspended' for v in runtime().values())
 for p in Path('/proc').glob('[0-9]*'):
  try:assert (p/'comm').read_text().strip() not in ['snapshot','megapixels','cam','gst-launch-1.0']
  except OSError:pass
 u=pwd.getpwuid(10000)
 def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name)
 log=(out/'kernel-follow-private.log').open('xb',buffering=0)
 logger=subprocess.Popen(['dmesg','--follow','--raw'],stdout=log,stderr=subprocess.STDOUT)
 for kind,extra in [('raw',['--stream','role=raw']),('rgb',[])]:
  state['state']='capturing-'+kind;save();start=time.monotonic()
  proc=subprocess.Popen(['cam','-c','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10','--capture=12',*extra],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  state.update(child_pid=proc.pid,child_start_ticks=Path('/proc',str(proc.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
  timeout=False
  try:stdout,stderr=proc.communicate(timeout=30)
  except subprocess.TimeoutExpired:
   timeout=True;proc.terminate()
   try:stdout,stderr=proc.communicate(timeout=8)
   except subprocess.TimeoutExpired:proc.kill();stdout,stderr=proc.communicate(timeout=3)
  (out/(kind+'-stdout-private.log')).write_bytes(stdout);(out/(kind+'-stderr-private.log')).write_bytes(stderr)
  seq=[int(v) for v in re.findall(rb'seq:\s*(\d+)',stdout)]
  time.sleep(1);after=subprocess.check_output(['dmesg']);delta={k:v-faults(before)[k] for k,v in faults(after).items()}
  row=dict(format=kind,exit=proc.returncode,timeout=timeout,frames=len(seq),sequences=seq,seconds=round(time.monotonic()-start,2),
   runtime_after=runtime(),rails_after=rails(),fault_delta=delta,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
  row['passed']=proc.returncode==0 and not timeout and len(seq)==12 and all(b>a for a,b in zip(seq,seq[1:])) and not any(delta.values()) and row['taint']==0 and all(v=='suspended' for v in row['runtime_after'].values()) and all(v['state']=='disabled' and v['num_users']=='0' for v in row['rails_after'].values())
  state['runs'].append(row);save()
  if not row['passed']:break
 report=dict(stage=273,camera='S5KGW1 main',runs=state['runs'],all_passed=len(state['runs'])==2 and all(r['passed'] for r in state['runs']),
  actual_sensor_data=True,test_pattern_not_enabled=True,cpu_software_isp=True,spectra_hardware_isp_not_enabled=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'dmesg-after-private.log').write_bytes(subprocess.check_output(['dmesg']))
 state.update(state='terminal',terminal=True,exit_code=0 if report['all_passed'] else 1);save();print(json.dumps(report))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
finally:
 if logger is not None and logger.poll() is None:logger.terminate();logger.wait(timeout=5)
'''
q=host.ssh('python3 -',input=code.encode(),timeout=90,check=False)
(host.PRIVATE/'main-capture-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.stdout,'Inspect submitted worker and boot; do not repeat this capture directory'
d=json.loads(q.stdout);(R/'main-capture-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
