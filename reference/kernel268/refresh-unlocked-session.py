"""One recorded normal session restart, with temporary automatic lock inhibition."""
from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import json,os,pwd,subprocess,time,traceback,shutil
os.umask(0o077);r=Path('/var/lib/samurai');out=r/'k268-unlocked-session-r2';out.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False)
def save(): (out/'state-private.json').write_text(json.dumps(state)+'\n')
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for n in ['7-0010','9-0010']:assert Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended'
 p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
 assert b'--unlocked' in (p/'cmdline').read_bytes();old=int(p.name)
 assert not any((p/'comm').exists() and (p/'comm').read_text().strip()=='snapshot' for p in Path('/proc').glob('[0-9]*'))
 raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
 env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
 u=pwd.getpwuid(10000)
 def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
 settings=[('org.gnome.desktop.screensaver','lock-enabled','false'),('org.gnome.desktop.session','idle-delay','uint32 0')]
 saved=[]
 for schema,key,new in settings:
  value=subprocess.check_output(['gsettings','get',schema,key],env=env,preexec_fn=demote,timeout=5).decode().strip()
  saved.append(dict(schema=schema,key=key,before=value,test_value=new))
 (out/'settings-before-private.json').write_text(json.dumps(saved)+'\n')
 for s in saved:subprocess.run(['gsettings','set',s['schema'],s['key'],s['test_value']],env=env,preexec_fn=demote,check=True,timeout=5)
 marker=Path('/run/greetd.run');assert marker.is_file() and not marker.is_symlink() and marker.stat().st_size==0
 for n in ['.local/share/applications/mobi.phosh.Shell.desktop','.config/autostart/mobi.phosh.Shell.desktop']:
  assert 'Exec=/usr/libexec/phosh --unlocked\n' in Path(u.pw_dir,n).read_text()
 state.update(state='stopping_known_session',old_phosh_pid=old);save()
 q=subprocess.run(['rc-service','greetd','stop'],capture_output=True,timeout=35)
 (out/'stop-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 assert marker.is_file() and marker.stat().st_size==0;shutil.copy2(marker,out/'initial-login-marker-private.before');marker.unlink()
 state['state']='starting_configured_initial_session';save()
 q=subprocess.run(['rc-service','greetd','start'],capture_output=True,timeout=35)
 (out/'start-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 deadline=time.monotonic()+35;newproc=None
 while time.monotonic()<deadline:
  for p in Path('/proc').glob('[0-9]*'):
   try:
    if int(p.name)!=old and (p/'comm').read_text().strip()=='phosh' and b'--unlocked' in (p/'cmdline').read_bytes():newproc=p;break
   except OSError:pass
  if newproc:break
  time.sleep(.3)
 assert newproc,'Inspect recorded transition before any repeat'
 state.update(state='terminal',terminal=True,exit_code=0,phosh_pid=int(newproc.name));save()
 print(json.dumps(state))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=code.encode(),timeout=100,check=False)
(host.PRIVATE/'refresh-unlocked-session-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Read the recorded session state before further action'
print(q.stdout.decode())
