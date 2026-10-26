"""Distinguish the physical sensor/RAW link from dark-scene optical response."""
from pathlib import Path
import ast,json,shlex
import host
R=Path(__file__).resolve().parent
tree=ast.parse((R/'capture-two-rear-jpegs.py').read_text())
remote=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets)))
inner=ast.parse(remote);worker=ast.literal_eval(next(n.value for n in inner.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='worker' for t in n.targets)))
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,sys,time,traceback
os.umask(0o077);worker=sys.stdin.read();root=Path('/var/lib/samurai/k270-telephoto-bars-r1');root.mkdir(mode=0o700)
u=pwd.getpwuid(10000);work=Path(u.pw_dir)/'.local/state/k270-telephoto-bars-r1';work.mkdir(mode=0o700);os.chown(work,u.pw_uid,u.pw_gid)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k270-work/boot-id-private.txt').read_bytes()
sensor=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d')
assert Path('/sys/bus/i2c/devices/8-002d/power/runtime_status').read_text().strip()=='suspended'
before=subprocess.check_output(['dmesg']);pattern=subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl=test_pattern'],text=True);assert 'test_pattern: 0' in pattern
state=dict(state='preflight',terminal=False);(root/'state-private.json').write_text(json.dumps(state))
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
env=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',HOME=u.pw_dir,USER=u.pw_name,GST_DEBUG_NO_COLOR='1');result=None
try:
 subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl=test_pattern=2'],capture_output=True,check=True)
 q=subprocess.run(['python3','-c',worker,'tele-bars','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d',str(work)],env=env,preexec_fn=demote,capture_output=True,timeout=35)
 (root/'stdout-private.json').write_bytes(q.stdout);(root/'stderr-private.log').write_bytes(q.stderr)
 result=dict(exit=q.returncode,photo=json.loads(q.stdout) if q.stdout else None)
finally:
 subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl=test_pattern=0'],capture_output=True,check=True)
 pattern_after=subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl=test_pattern'],text=True);assert 'test_pattern: 0' in pattern_after
 time.sleep(1);after=subprocess.check_output(['dmesg'])
 report=dict(stage=270,**(result or {}),physical_sensor_pattern=2,csid_pattern_not_changed=True,pattern_restored=True,
  runtime_after=Path('/sys/bus/i2c/devices/8-002d/power/runtime_status').read_text().strip(),
  fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
  taint=int(Path('/proc/sys/kernel/tainted').read_text()),optical_image_not_verified_by_pattern=True)
 (root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True);(root/'state-private.json').write_text(json.dumps(state));print(json.dumps(report))
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=worker.encode(),timeout=50,check=False)
(host.PRIVATE/'telephoto-bars-response-private.log').write_bytes(q.stdout+q.stderr)
d=json.loads(q.stdout);photo=d.get('photo')
if photo:photo.pop('path',None);photo.pop('pts',None)
(R/'telephoto-bars-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
