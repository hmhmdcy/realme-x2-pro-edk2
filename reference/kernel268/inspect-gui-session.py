"""Read the current screen state and available Snapshot resource metadata."""
from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import json,os,pwd,subprocess,shutil
u=pwd.getpwuid(10000);p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for item in (p/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY']}
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
out={}
for label,args in [('screensaver',['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive']),
 ('resources',['gresource','list','/usr/bin/snapshot'])]:
 if not shutil.which(args[0]):out[label]=dict(exit=None,stdout='',stderr='optional tool unavailable');continue
 q=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=10);out[label]=dict(exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
print(json.dumps(out))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'gui-session-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(json.dumps(d['screensaver']));print(json.dumps(dict(resource_exit=d['resources']['exit'],resource_lines=d['resources']['stdout'].splitlines()[:12])))
