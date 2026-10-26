"""Read a finite test's status and diagnostics, without retrieving scene files."""
import json
import sys
import host

name=sys.argv[1];assert name in ['camera-16','camera-17','camera-18','snapshot-gui']
code=r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k267-NAME');result={}
for name in ['state-private.json','failure-private.txt','stderr-private.txt','stdout-private.json','gui-auto-private.log']:
 if (p/name).exists():result[name]=(p/name).read_text()[-6000:]
print(json.dumps(result))
'''.replace('NAME',name)
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/(name+'-context-private.json')).write_bytes(q.stdout)
for name,text in json.loads(q.stdout).items():print(name+':\n'+text)
