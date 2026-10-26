"""Read actual boot270 health; do not change services, capture, or write phone files."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
t=ast.parse((R.parent/'kernel270/final-health.py').read_text())
n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
code=ast.literal_eval(n.value)
code=code[:code.index('manifest=')]+code[code.index('report=dict'):]
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'current-idle-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);d.pop('dmesg');d.pop('package_database_sha256');d['stage']=272
d['passed']=d['taint']==0 and not any(d['faults'].values()) and not d['camera_clients'] and all(v=='suspended' for v in d['runtime'].values()) and len(d['rails'])==6 and all(v['state']=='disabled' and v['num_users']=='0' for v in d['rails'].values()) and not any(d['mclk_enable_counts'].values())
d['read_only']=True;d['gw1_not_installed']=True
(R/'current-idle-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
