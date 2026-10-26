"""Temporarily load only the fresh-allocation SPA; retain an automatic normal fallback."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'fresh-allocation-build-validation.json').read_text());data=(host.PRIVATE/'libspa-libcamera-fresh-allocation.so').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['spa_sha256']
code=r'''
from pathlib import Path
import hashlib,os,sys
out=Path('/var/lib/samurai/k265-spa-fresh');assert not out.exists();out.mkdir(mode=0o755)
for p in Path('/usr/lib/spa-0.2').iterdir():
 if p.name!='libcamera':(out/p.name).symlink_to(p)
(out/'libcamera').mkdir(mode=0o755);p=out/'libcamera/libspa-libcamera.so';data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()==sys.argv[1];p.write_bytes(data);p.chmod(0o644)
'''
host.ssh('python3 -c '+shlex.quote(code)+' '+proof['spa_sha256'],input=data)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,resource,select,signal,subprocess,sys,time,traceback
os.umask(0o077);root=Path('/var/lib/samurai');proof=json.loads(sys.argv[1]);out=root/'k265-policy-candidate';assert not out.exists();out.mkdir()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k260-work/boot-id-private.txt').read_bytes()
items=json.loads((root/'k264-services-current-private.json').read_text())['new_processes'];old=next(x for x in items if x['name']=='wireplumber');pw=next(x for x in items if x['name']=='pipewire')
def identity(pid):return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
def save(phase,terminal=False):(out/'state-private.json').write_text(json.dumps(dict(stage=265,phase=phase,terminal=terminal)))
assert identity(old['pid'])==old['start_ticks'] and identity(pw['pid'])==pw['start_ticks']
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for path,digest in [('/usr/lib/libpipewire-0.3.so.0.1609.0','870b7077747b14c74f15856a20f6ab93d68fde60703e0c116e2a9a38a8f91416'),('/usr/lib/gstreamer-1.0/libgstpipewire.so','d7a5500688d2881d04bc04c614eb46f00da7070bb96224c7f43f97b3a0e22935')]:assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
candidate='/var/lib/samurai/k265-spa-fresh/libcamera/libspa-libcamera.so';assert hashlib.sha256(Path(candidate).read_bytes()).hexdigest()==proof['spa_sha256']
env=json.loads((root/'k264-services/environments-before-private.json').read_text())['wireplumber'];env.pop('PIPEWIRE_NOTIFICATION_FD',None);assert not any(k in env for k in ['LD_LIBRARY_PATH','LD_PRELOAD','SPA_PLUGIN_DIR'])
(out/'environment-before-private.json').write_text(json.dumps(env,indent=2)+'\n')
user=pwd.getpwuid(10000)
def demote():resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
def stop(pid,ticks):
 fd=os.pidfd_open(pid);assert identity(pid)==ticks;signal.pidfd_send_signal(fd,signal.SIGTERM);assert select.select([fd],[],[],8)[0];os.close(fd)
def start(e,label,expected):
 with (out/(label+'-private.log')).open('xb') as log:p=subprocess.Popen(['/usr/bin/wireplumber'],env=e,preexec_fn=demote,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  if p.poll() is not None:break
  if any(l.split()[-1]==expected for l in Path('/proc',str(p.pid),'maps').read_text().splitlines()):return p,True
  time.sleep(.1)
 return p,False
save('stopping-verified-old-policy');stop(old['pid'],old['start_ticks']);save('starting-candidate-policy')
candidate_env=env.copy();candidate_env['SPA_PLUGIN_DIR']='/var/lib/samurai/k265-spa-fresh'
p,ready=start(candidate_env,'wireplumber',candidate);fallback=False
if not ready:
 if p.poll() is None:stop(p.pid,identity(p.pid))
 p,restored=start(env,'fallback-wireplumber','/usr/lib/spa-0.2/libcamera/libspa-libcamera.so');assert restored,'Inspect candidate state; normal fallback not ready'
 fallback=True
new=dict(name='wireplumber',pid=p.pid,start_ticks=identity(p.pid));assert identity(pw['pid'])==pw['start_ticks']
manifest=dict(stage=265,new_processes=[pw,new],spa_candidate_active=ready,spa_path=candidate if ready else '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so')
(root/'k265-services-current-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
report=dict(stage=265,candidate_ready=ready,normal_fallback_used=fallback,new_policy=new,pipewire_identity_unchanged=True,core_and_gstreamer_system_bytes_unchanged=True,system_packages_unchanged=True,no_forced_kill=True,spa_sha256=proof['spa_sha256'],taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');save('candidate-ready' if ready else 'normal-fallback-restored',True);print(json.dumps(report))
raise SystemExit(0 if ready else 1)
'''
q=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=45,check=False);(host.PRIVATE/'policy-candidate-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Read the one-shot transition state before continuing'
d=json.loads(q.stdout);(R/'policy-candidate-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))

