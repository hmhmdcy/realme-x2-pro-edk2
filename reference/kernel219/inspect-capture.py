from pathlib import Path
import host,json,re,sys

assert len(sys.argv)==2 and re.fullmatch('[A-Za-z0-9-]+',sys.argv[1])
tag=sys.argv[1]
code="from pathlib import Path;import json;p=Path('/var/lib/samurai/k219-capture-"+tag+"');print(json.dumps(dict(stderr=(p/'stderr-private.txt').read_text(),report=json.loads((p/'summary.json').read_text()))))"
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/(tag+'-diagnostics-private.json')).write_bytes(p.stdout)
data=json.loads(p.stdout)
print('\n'.join(l for l in data['stderr'].splitlines() if any(t in l.lower() for t in ['error','failed','warning','cannot','no memory','allocat'])))
print(json.dumps(dict(frames=[{k:f[k] for k in ['byte_min','byte_max','mean','stddev','occupied_bins','changed_fraction']} for f in data['report']['frames']])))
