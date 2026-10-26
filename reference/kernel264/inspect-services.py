from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,re,subprocess
root=Path('/var/lib/samurai');user=pwd.getpwuid(10000)
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber','pipewire-pulse','phosh']:
   parent=int(re.search(r'^PPid:\s*(\d+)',(p/'status').read_text(),re.M)[1])
   processes.append(dict(name=name,pid=int(p.name),parent=parent,parent_comm=Path('/proc',str(parent),'comm').read_text().strip(),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19],cgroup=(p/'cgroup').read_text(),cmdline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()))
 except FileNotFoundError:pass
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
inherited={k.decode():v.decode() for x in (desktop/'environ').read_bytes().split(b'\0') if b'=' in x for k,v in [x.split(b'=',1)]}
env={k:v for k,v in inherited.items() if k in ['PATH','HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','DISPLAY']};env['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
commands={}
for name,args in [('help',['rc-service','--help']),('status',['rc-status','--user','-a']),('pipewire',['rc-service','--user','pipewire','status']),('wireplumber',['rc-service','--user','wireplumber','status'])]:
 p=subprocess.run(args,env=env,preexec_fn=demote,capture_output=True,text=True,timeout=8);commands[name]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
paths=['/etc/user/init.d/pipewire','/etc/user/init.d/wireplumber','/usr/bin/pipewire-launcher','/usr/libexec/pipewire-launcher']
files={p:Path(p).read_text() for p in paths if Path(p).is_file()}
print(json.dumps(dict(processes=processes,commands=commands,files=files)))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=45);(host.PRIVATE/'services-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);print(json.dumps(dict(processes=[{k:v for k,v in p.items() if k not in ['cmdline','cgroup']} for p in d['processes']],commands=d['commands'],files=list(d['files'])),indent=2))
