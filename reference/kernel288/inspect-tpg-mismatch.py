"""Cross-check the active media links against the observed TPG/IPP format mismatch."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,re
graph=Path('/var/lib/samurai/k288-tpg-r2/graph-before-private.txt').read_text()
section=next(s for s in re.split(r'(?m)^- entity ',graph) if re.match(r'\d+: msm_csid0 ',s))
print(json.dumps(dict(csid0_graph=section)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15)
data=json.loads(q.stdout)
(ROOT/'tpg-topology-validation.json').write_text(json.dumps(dict(stage=288,**data),indent=2)+'\n')
print(json.dumps(data,indent=2))
