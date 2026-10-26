"""Refresh libcamera's media topology cache after the legacy test restored links externally."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,resource,select,signal,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k264-policy-refresh';assert not out.exists();out.mkdir()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
receipt=json.loads((root/'k264-services/summary.json').read_text());items=receipt['new_processes'];old=next(x for x in items if x['name']=='wireplumber');pw=next(x for x in items if x['name']=='pipewire')
def identity(pid):return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
assert identity(old['pid'])==old['start_ticks'] and identity(pw['pid'])==pw['start_ticks']
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
env=json.loads((root/'k264-services/environments-before-private.json').read_text())['wireplumber'];env.pop('PIPEWIRE_NOTIFICATION_FD',None)
user=pwd.getpwuid(10000)
def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
(out/'state-private.json').write_text(json.dumps(dict(phase='stopping-verified-policy',terminal=False)))
fd=os.pidfd_open(old['pid']);assert identity(old['pid'])==old['start_ticks'];signal.pidfd_send_signal(fd,signal.SIGTERM);assert select.select([fd],[],[],8)[0];os.close(fd)
with (out/'wireplumber-private.log').open('xb') as log:
 p=subprocess.Popen(['/usr/bin/wireplumber'],env=env,preexec_fn=demote,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  assert p.poll() is None
  if any(l.split()[-1]=='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' for l in Path('/proc',str(p.pid),'maps').read_text().splitlines()):break
  time.sleep(.1)
 else:raise AssertionError('Camera backend not enumerated')
new=dict(name='wireplumber',pid=p.pid,start_ticks=identity(p.pid));assert identity(pw['pid'])==pw['start_ticks']
current=dict(stage=264,new_processes=[pw,new]);(root/'k264-services-current-private.json').write_text(json.dumps(current,indent=2)+'\n')
report=dict(stage=264,reason='Legacy test externally restored media links while libcamera cached their changed state',policy_manager_reenumerated=True,old_policy_pid=old['pid'],new_policy=new,pipewire_identity_unchanged=True,no_forced_kill=True,taint=0)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'state-private.json').write_text(json.dumps(dict(phase='verified',terminal=True)));print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=30,check=False);(host.PRIVATE/'policy-refresh-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'Inspect refresh state; never replay it blindly'
d=json.loads(r.stdout);(Path(__file__).parent/'policy-refresh-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
