"""Read standard session display/idle interfaces before exercising the camera window."""
import json
import host

code=r'''
from pathlib import Path
import json,os,pwd,subprocess
u=pwd.getpwuid(10000);p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for item in (p/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
result={}
for name,path in [('org.gnome.Mutter.DisplayConfig','/org/gnome/Mutter/DisplayConfig'),('org.gnome.SessionManager','/org/gnome/SessionManager'),('org.gnome.ScreenSaver','/org/gnome/ScreenSaver'),('org.gnome.Shell','/org/gnome/Shell'),('sm.puri.Phosh','/sm/puri/Phosh')]:
 q=subprocess.run(['gdbus','introspect','--session','--dest',name,'--object-path',path],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
 result[name]=dict(exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
q=subprocess.run(['gsettings','get','org.gnome.desktop.session','idle-delay'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5);result['idle-delay']=q.stdout
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'display-interfaces-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
for name,item in d.items():
 if isinstance(item,dict):
  print(name+': '+str(item['exit']))
  lines=item['stdout'].splitlines()
  for i,line in enumerate(lines):
   if any(s in line for s in ['PowerSaveMode','Inhibit(','Uninhibit(','SetActive(','GetActive(','SimulateUserActivity','InhibitedActions','OverviewActive','FocusApp','ShowApplications','Version','ShellState']):print('\n'.join(lines[max(0,i-1):i+5]))
 else:print(name+': '+item)
