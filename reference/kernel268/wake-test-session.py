"""Wake the existing test session through its normal ScreenSaver service."""
import host,json
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
assert b'--unlocked' in (p/'cmdline').read_bytes()
raw={k.decode():v.decode() for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
result={}
for method,args in [('GetActive',[]),('SetActive',['false']),('SimulateUserActivity',[]),('GetActive',[])]:
 q=subprocess.run(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.'+method,*args],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
 result[method+'-'+str(len(result))]=dict(exit=q.returncode,result=q.stdout,error=q.stderr)
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30);print(q.stdout.decode())
