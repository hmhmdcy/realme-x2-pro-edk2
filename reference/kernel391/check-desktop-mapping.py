import json,shlex
import host
code=r'''from pathlib import Path
import json
result={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:
   result[name]=dict(pid=int(p.name),maps=[line.split()[-1] for line in (p/'maps').read_text().splitlines() if 'libcamera' in line])
 except OSError:pass
print(json.dumps(result))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20)
host.PRIVATE.joinpath('desktop-mapping-diagnosis-private.json').write_bytes(q.stdout)
print(q.stdout.decode())
