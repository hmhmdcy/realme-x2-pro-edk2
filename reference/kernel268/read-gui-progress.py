"""Observe the existing owned GUI test; never start another window."""
import json
import sys
import host

code=r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k268-snapshot-gui');result={}
for name in ['state-private.json','gui-control-summary-private.json']:
 if (p/name).exists() and (p/name).stat().st_size:
  d=json.loads((p/name).read_text())
  if name.startswith('gui-control'):
   for photo in d.get('new_jpegs',[]):photo.pop('path',None)
  result[name]=d
for name in ['gui-auto-private.log','failure-private.txt']:
 if (p/name).exists():result[name]=(p/name).read_text()[-2400:]
tree=p/'accessible-tree-private.json'
if tree.exists() and tree.stat().st_size:
 result['observed_control_labels']=[dict(name=e.get('name'),description=e.get('description'),actions=[a[0] for a in e.get('actions',[])]) for e in json.loads(tree.read_text()) if e.get('actions')]
result['camera_power']={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','9-0010']}
print(json.dumps(result))
'''
if sys.argv[1:]:
 assert len(sys.argv)==2 and sys.argv[1] in ['r2','r3','r4','r5'];code=code.replace('k268-snapshot-gui','k268-snapshot-gui-'+sys.argv[1])
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'gui-progress-private.json').write_bytes(q.stdout);print(q.stdout.decode())
