from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
user=pwd.getpwuid(10000);desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
raw={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in raw.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY']};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
commands={}
for name,args in [('toolkit',['gsettings','get','org.gnome.desktop.interface','toolkit-accessibility']),('lock',['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive']),('a11y',['gdbus','call','--session','--dest','org.a11y.Bus','--object-path','/org/a11y/bus','--method','org.a11y.Bus.GetAddress'])]:
 p=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5);commands[name]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
print(json.dumps(commands))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'accessibility-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);print(json.dumps(dict(toolkit=d['toolkit'],lock=d['lock'],a11y_address_available=d['a11y']['returncode']==0),indent=2))
