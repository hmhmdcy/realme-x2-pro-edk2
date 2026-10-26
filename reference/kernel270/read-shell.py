"""Read actual desktop accessibility before selecting any camera UI action."""
from pathlib import Path
import ast,json
import host
tree=ast.parse((Path(__file__).parents[1]/'kernel268/inspect-shell-camera.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
q=host.ssh('python3 -',input=ast.literal_eval(node.value).encode(),timeout=35)
(host.PRIVATE/'shell-accessible-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps(dict(phosh_pid=d['owner_pid'],entries=len(d['entries']),state_names=d['state_names'],
 visible_actions=[dict(name=e.get('name'),actions=e['actions'],bus=e['bus'],path=e['path']) for e in d['entries'] if e['actions'] and e.get('states') and e['states'][0]&(1<<25) and any(s in str(e.get('name','')).lower() for s in ['camera','snapshot','unlock','password','pin','解锁','密码','相机'])]),indent=2))
