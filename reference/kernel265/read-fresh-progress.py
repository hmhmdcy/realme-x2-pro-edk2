from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');p=r/'k265-camera-11';state=json.loads((p/'state-private.json').read_text());s=r/'k265-policy-candidate/wireplumber-private.log'
with s.open('rb') as f:f.seek(max(0,s.stat().st_size-8000));tail=f.read().decode(errors='replace')
print(json.dumps(dict(state=state,policy_tail=tail.splitlines()[-20:]),indent=2))
'''
try:
 q=host.ssh('python3 -',input=code.encode(),timeout=15);print(q.stdout.decode())
except Exception as e:print(type(e).__name__)

