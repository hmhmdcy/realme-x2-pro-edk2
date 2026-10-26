"""Capture rear frames through the normal libcamera CLI on the inspected boot."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,re,resource,subprocess,time,traceback
os.umask(0o077)
out=Path('/var/lib/samurai/k270-native-rear-r1');out.mkdir(mode=0o700)
state=dict(state='preflight',pid=os.getpid(),terminal=False)
def save():(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def faults(s):return {k:s.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()}
save()
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for p in Path('/proc').glob('[0-9]*'):
  try:assert (p/'comm').read_text().strip() not in ['snapshot','megapixels','cam','gst-launch-1.0'],'Existing camera client'
  except FileNotFoundError:pass
 assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['7-0010','9-0010'])
 assert 'mode: cpu' in Path('/etc/libcamera/configuration.yaml').read_text()
 p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
 raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
 env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
 u=pwd.getpwuid(10000)
 def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.log').write_bytes(before)
 listing=subprocess.run(['cam','--list'],env=env,preexec_fn=demote,capture_output=True,timeout=15)
 (out/'camera-list-private.log').write_bytes(listing.stdout+listing.stderr)
 assert listing.returncode==0
 state.update(state='capturing-rear',camera_id='/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10');save()
 q=subprocess.run(['cam','-c',state['camera_id'],'--capture=24'],env=env,preexec_fn=demote,capture_output=True,timeout=35)
 (out/'stdout-private.log').write_bytes(q.stdout);(out/'stderr-private.log').write_bytes(q.stderr)
 sequences=[int(x) for x in re.findall(r'seq:\s*(\d+)',q.stdout.decode())]
 time.sleep(1)
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.log').write_bytes(after)
 delta={k:v-faults(before)[k] for k,v in faults(after).items()}
 runtime={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','9-0010']}
 rails={}
 for p in Path('/sys/class/regulator').glob('regulator.*'):
  name=(p/'name').read_text().strip()
  if name.startswith(('cam-front-','cam-rear-')):rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users']}
 report=dict(stage=270,camera='rear IMX319',exit=q.returncode,frames=len(sequences),sequences=sequences,
  standard_cam=True,environment_overrides=False,runtime_after=runtime,rails_after=rails,fault_delta=delta,
  taint=int(Path('/proc/sys/kernel/tainted').read_text()),same_boot=True)
 ok=q.returncode==0 and len(sequences)==24 and all(b>a for a,b in zip(sequences,sequences[1:])) and not any(delta.values()) and report['taint']==0 and all(v=='suspended' for v in runtime.values()) and all(v['state']=='disabled' and v['num_users']=='0' for v in rails.values())
 report['passed']=ok;(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=0 if ok else 1);save();print(json.dumps(report))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=60)
(host.PRIVATE/'native-rear-response-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
(Path(__file__).parent/'native-rear-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
