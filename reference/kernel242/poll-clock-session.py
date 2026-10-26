from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k242-clock-session');state=json.loads((p/'state-private.json').read_text())
r=dict(state=state)
if (p/'summary.json').exists():r['summary']=json.loads((p/'summary.json').read_text())
if (p/'failure-private.txt').exists():r['failure']=(p/'failure-private.txt').read_text()
print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'clock-poll-private.json').write_bytes(p.stdout)
v=json.loads(p.stdout);print(json.dumps(v))
if v['state']['terminal'] and 'summary' in v:
 (R/'clock-session-validation.json').write_text(json.dumps(v['summary'],indent=2)+'\n')
