from pathlib import Path
import json
import host
code="""
from pathlib import Path
import json
r=Path('/var/lib/samurai/k274-focus-position-r1')
print(json.dumps(dict(state=json.loads((r/'state-private.json').read_text()),failure=(r/'failure-private.txt').read_text(),stderr_tail=(r/'capture-stderr-private.log').read_text()[-4000:])))
"""
q=host.ssh('python3 -',input=code.encode(),timeout=15);d=json.loads(q.stdout)
(host.PRIVATE/'focus-r1-failure-inspection-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(state=d['state']['state'],terminal=d['state']['terminal'],failure=d['failure'],stderr_tail=d['stderr_tail']),indent=2))
