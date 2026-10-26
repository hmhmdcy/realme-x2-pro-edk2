"""Reload the idle camera provider once to use the newly installed common library."""
from pathlib import Path
import json
import host

R=Path(__file__).resolve().parent
assert json.loads((R/'native-install-validation.json').read_text())['native_signed_apk_transaction_completed']
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,select,signal,subprocess,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
old=json.loads((r/'k267-services-current-private.json').read_text());previous=next(x for x in old['new_processes'] if x['name']=='wireplumber');pw=next(x for x in old['new_processes'] if x['name']=='pipewire')
def proc(item):
 p=Path('/proc',str(item['pid']));assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks'];return p
p=proc(previous);proc(pw)
assert (p/'comm').read_text().strip()=='wireplumber' and os.readlink(p/'exe')=='/usr/bin/wireplumber'
assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['7-0010','9-0010'])
user=pwd.getpwuid(10000);assert int((p/'status').read_text().split('Uid:',1)[1].split()[0])==user.pw_uid
env={k.decode():v.decode() for item in (p/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
assert not any(k in env for k in ['LD_LIBRARY_PATH','SPA_PLUGIN_DIR','PIPEWIRE_MODULE_DIR'])
argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x];assert argv==['/usr/bin/wireplumber'] or argv==['wireplumber']
cwd=os.readlink(p/'cwd');o=r/'k268-services';o.mkdir(mode=0o700)
(o/'original-environment-private.json').write_text(json.dumps(env,indent=2)+'\n')
fd=os.pidfd_open(previous['pid'],0)
try:
 signal.pidfd_send_signal(fd,signal.SIGTERM);poll=select.poll();poll.register(fd,select.POLLIN);assert poll.poll(8000)
finally:os.close(fd)
time.sleep(.5)
def wps():
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()=='wireplumber' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)
  except OSError:pass
 return result
found=wps();assert len(found)<=1
manual=not found
if manual:
 def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
 with (o/'wireplumber-private.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/wireplumber'],env=env,cwd=cwd,preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
deadline=time.monotonic()+12
while time.monotonic()<deadline:
 found=wps()
 if len(found)==1:
  maps=(found[0]/'maps').read_text()
  if '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in maps and '/usr/lib/libcamera.so.0.7.2' in maps:break
 time.sleep(.2)
assert len(found)==1
p=found[0];maps=(p/'maps').read_text()
assert '/usr/lib/libcamera.so.0.7.2' in maps and '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in maps
assert not any('(deleted)' in line and 'libcamera' in line for line in maps.splitlines())
proc(pw)
manifest=json.loads((r/'k268-r19-package-candidates/forward-manifest.json').read_text())
files={n:item for x in manifest['packages'] for n,item in x['files'].items()}
for name in ['usr/lib/libcamera.so.0.7.2','usr/lib/libcamera-base.so.0.7.2']:
 assert hashlib.sha256((Path('/')/name).read_bytes()).hexdigest()==files[name]['sha256']
new=dict(name='wireplumber',pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19])
report=dict(stage=268,new_processes=[pw,new],spa_path=old['spa_path'],spa_candidate_active=False,
 pipewire_process_preserved=True,wireplumber_reloaded_once_for_library_update=True,
 original_environment_and_standard_binary=True,new_libcamera_default_mapped=True,
 manual_spawn_needed=manual)
(r/'k268-services-current-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'services-current-private.json').write_bytes(q.stdout)
(R/'service-reload-validation.json').write_text(json.dumps(json.loads(q.stdout),indent=2)+'\n');print(q.stdout.decode())
