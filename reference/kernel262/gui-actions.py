"""Read the actual application's exported actions while the GUI probe runs."""
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,subprocess
user=pwd.getpwuid(10000)
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
env={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
result={}
for path in ['/org/gnome/Snapshot','/org/gnome/Snapshot/window/1']:
 p=subprocess.run(['gdbus','call','--session','--dest','org.gnome.Snapshot','--object-path',path,'--method','org.gtk.Actions.DescribeAll'],env=env,preexec_fn=demote,capture_output=True,text=True,timeout=5)
 result[path]=dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=18)
(host.PRIVATE/'gui-actions-private.json').write_bytes(r.stdout)
print(r.stdout.decode())
