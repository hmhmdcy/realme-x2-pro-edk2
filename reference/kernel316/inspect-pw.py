import json,shlex
import host
code='''
from pathlib import Path
import json,os,pwd,subprocess
p=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='pipewire')
env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\\0') if x)
user=pwd.getpwuid(p.stat().st_uid)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
q=subprocess.run(['pw-dump'],env=env,preexec_fn=demote,capture_output=True,timeout=15)
if q.returncode:raise RuntimeError('pw-dump failed')
nodes=[]
for item in json.loads(q.stdout):
 props=item.get('info',{}).get('props',{})
 if props.get('media.class')=='Video/Source':
  nodes.append({'id':item['id'],'properties':{k:v for k,v in props.items() if k in ['node.name','node.description','object.serial','api.libcamera.path','device.api','device.id']}})
print(json.dumps(nodes))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'pw-context.json').write_bytes(q.stdout);print(q.stdout.decode())
