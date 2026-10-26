"""Restart one idle desktop with SensorProxy ready; restore temporary login files."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import gi,hashlib,json,os,pwd,shutil,subprocess,time,traceback
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
os.umask(0o077);root=Path('/var/lib/samurai/k269-ready-sensor-session-r1');root.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False);saved=[]
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def processes():
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:result.append((p,(p/'comm').read_text().strip()))
  except OSError:pass
 return result
save()
try:
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['7-0010','9-0010'])
 assert not any(n in ['snapshot','megapixels'] for p,n in processes())
 system=Gio.bus_get_sync(Gio.BusType.SYSTEM,None)
 props=system.call_sync('net.hadess.SensorProxy','/net/hadess/SensorProxy','org.freedesktop.DBus.Properties','GetAll',GLib.Variant('(s)',('net.hadess.SensorProxy',)),None,Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
 assert props['HasAccelerometer']
 old=next(int(p.name) for p,n in processes() if n=='phosh');state['old_phosh_pid']=old
 u=pwd.getpwuid(10000);home=Path(u.pw_dir)
 base=Path('/usr/share/applications/mobi.phosh.Shell.desktop').read_bytes();assert base.count(b'Exec=/usr/libexec/phosh\n')==1
 replacement=base.replace(b'Exec=/usr/libexec/phosh\n',b'Exec=/usr/libexec/phosh --unlocked\n')
 for i,relative in enumerate(['.local/share/applications/mobi.phosh.Shell.desktop','.config/autostart/mobi.phosh.Shell.desktop']):
  p=home/relative;row=dict(path=str(p),existed=p.exists())
  if p.exists():
   assert p.is_file() and not p.is_symlink();st=p.stat();row.update(uid=st.st_uid,gid=st.st_gid,mode=st.st_mode&0o777)
   backup=root/('override-'+str(i)+'.before');shutil.copy2(p,backup);row['backup']=str(backup)
  saved.append(row);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(replacement);p.chmod(0o644);os.chown(p,u.pw_uid,u.pw_gid)
 (root/'overrides-before-private.json').write_text(json.dumps(saved,indent=2))
 marker=Path('/run/greetd.run');assert marker.is_file() and not marker.is_symlink() and marker.stat().st_size==0
 state['state']='stopping-known-idle-desktop';save()
 q=subprocess.run(['rc-service','greetd','stop'],capture_output=True,timeout=35);(root/'stop-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 assert marker.is_file() and marker.stat().st_size==0;shutil.copy2(marker,root/'initial-login-marker.before');marker.unlink()
 state['state']='starting-with-sensor-proxy-ready';save()
 q=subprocess.run(['rc-service','greetd','start'],capture_output=True,timeout=35);(root/'start-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
 deadline=time.monotonic()+35;new=None
 while time.monotonic()<deadline:
  new=next((p for p,n in processes() if n=='phosh' and int(p.name)!=old),None)
  if new:break
  time.sleep(.3)
 assert new,'Inspect the saved transition; do not repeat the restart blindly'
 assert b'--unlocked' in (new/'cmdline').read_bytes();time.sleep(3)
 current=[]
 for p,n in processes():
  if n in ['pipewire','wireplumber','phosh','phoc','iio-sensor-prox']:
   current.append(dict(pid=int(p.name),comm=n,start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
 (Path('/var/lib/samurai')/'k269-services-current-private.json').write_text(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),processes=current),indent=2))
 state.update(state='terminal',terminal=True,exit_code=0,phosh_pid=int(new.name),current_processes=current);save()
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
finally:
 for row in saved:
  p=Path(row['path'])
  if row['existed']:
   shutil.copy2(row['backup'],p);os.chown(p,row['uid'],row['gid']);p.chmod(row['mode'])
  elif p.exists():p.unlink()
 (root/'temporary-overrides-restored').write_text('Original startup desktop files restored; no lock/idle setting changed.\n')
print(json.dumps(dict(stage=269,**state,temporary_startup_files_restored=True,lock_and_idle_preferences_unchanged=True,phone_kernel_not_restarted=True)))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=115);(P/'ready-sensor-session-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'ready-sensor-session-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
