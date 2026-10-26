from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');states=[]
for p in sorted(r.glob('k264-*/state-private.json')):
 d=json.loads(p.read_text());states.append(dict(directory=p.parent.name,state=d.get('state'),phase=d.get('phase'),terminal=d.get('terminal'),exit_code=d.get('exit_code')))
print(json.dumps(dict(states=states,contexts=[p.name for p in sorted(r.glob('k264-*')) if p.is_dir()],current_services=json.loads((r/'k264-services-current-private.json').read_text())),indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'state-inventory-private.json').write_bytes(q.stdout);print(q.stdout.decode())
