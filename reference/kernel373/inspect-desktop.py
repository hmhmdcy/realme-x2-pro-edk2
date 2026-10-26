from pathlib import Path
import json,shlex
import host
code='''from pathlib import Path
import json,os
rows=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber','phosh','phoc']:
   rows.append(dict(pid=int(p.name),uid=p.stat().st_uid,name=name,state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]))
 except OSError:pass
logs={}
for directory in ['/run/user/10000','/home/user/.local/state','/var/log']:
 root=Path(directory)
 if root.exists():
  for p in root.glob('*'):
   if p.is_file() and any(n in p.name.lower() for n in ['pipewire','wireplumber','session']):
    try:logs[str(p)]=p.read_text(errors='replace')[-6000:]
    except OSError:pass
print(json.dumps(dict(uptime=Path('/proc/uptime').read_text().split()[0],processes=rows,logs=logs)))
'''
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
(host.PRIVATE/'desktop-inspection-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(uptime=d['uptime'],processes=d['processes'],log_paths=list(d['logs'])),indent=2))
