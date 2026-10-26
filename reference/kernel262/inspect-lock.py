"""Inspect the live desktop's idle/lock policy and supported session API."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
desktops=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip()=='phosh':desktops.append(p)
 except OSError:pass
assert len(desktops)==1
env={k.decode():v.decode() for x in (desktops[0]/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
def run(args):
 q=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=8)
 return dict(exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
result={s:run(['gsettings','list-recursively',s]) for s in ['org.gnome.desktop.screensaver','org.gnome.desktop.session','sm.puri.phosh']}
result['screensaver_interface']=run(['gdbus','introspect','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver'])
result['lock']=run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'])
result['session']=run(['loginctl','show-session',env.get('XDG_SESSION_ID',''),'--property=Active','--property=State','--property=LockedHint','--property=Type'])
print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=45)
(host.PRIVATE/'lock-inspection-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout)
print(json.dumps(d,indent=2))
