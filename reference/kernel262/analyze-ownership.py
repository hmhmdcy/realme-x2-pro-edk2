from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import collections,json,re
p=Path('/var/lib/samurai/k262-pipewire-6000000-r2');assert json.loads((p/'state-private.json').read_text())['state']=='terminal'
s=(p/'stderr-private.txt').read_text(errors='replace')
samples=[tuple(map(int,m)) for m in re.findall(r'ownership-trace busy=(-?\d+) refs=(\d+) metas=(\d+) fd=(-?\d+)',s)]
print(json.dumps(dict(stage=262,not_recycled_errors=s.count('was not recycled'),ownership_samples=len(samples),busy_values=dict(collections.Counter(x[0] for x in samples)),reference_counts=dict(collections.Counter(x[1] for x in samples)),spa_meta_counts=dict(collections.Counter(x[2] for x in samples)),summary=json.loads((p/'summary.json').read_text()),kernel_fault_not_established=True,diagnostic_plugin_not_installed=True)))
'''
r=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'ownership-analysis-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout);(Path(__file__).parent/'ownership-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k!='summary'},indent=2))
