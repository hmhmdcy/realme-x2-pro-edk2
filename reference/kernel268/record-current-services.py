"""Observe actual services after the normal display-session restart."""
from pathlib import Path
import ast
import json
import host

R=Path(__file__).resolve().parent
tree=ast.parse((R.parent/'kernel267/record-services.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=ast.literal_eval(node.value).replace('stage=267','stage=268').replace('k267-services-current-private','k268-services-current-private')
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'services-after-session-private.json').write_bytes(q.stdout)
(R/'services-current-validation.json').write_text(json.dumps(json.loads(q.stdout),indent=2)+'\n');print(q.stdout.decode())
