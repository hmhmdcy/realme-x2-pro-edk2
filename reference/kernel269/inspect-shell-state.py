"""Read desktop accessibility state using the current boot, without clicking."""
from pathlib import Path
import ast,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
tree=ast.parse((R.parent/'kernel268/inspect-shell-camera.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=ast.literal_eval(node.value)
q=h.ssh('python3 -',input=code.encode(),timeout=35);(P/'shell-state-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
showing=lambda e:e.get('states') and bool(e['states'][0]&(1<<25))
print(json.dumps(dict(phosh_pid=d['owner_pid'],entries=len(d['entries']),
 showing=[dict(name=e['name'],actions=e['actions'],path=e['path']) for e in d['entries'] if showing(e) and e.get('name')],
 orientation_actions=[e for e in d['entries'] if any(n in str(e.get('name','')).lower() for n in ['rotation','portrait','landscape','旋转','横屏','竖屏','unlock','解锁'])]),indent=2))
