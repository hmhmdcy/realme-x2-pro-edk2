import json
import host
code=r'''
from pathlib import Path
import json,subprocess
p=Path('/var/lib/samurai/k276-quiesce')
print(json.dumps(dict(worker_context_exists=p.exists(),state=json.loads((p/'state-private.json').read_text()) if (p/'state-private.json').exists() else None,greetd_status=subprocess.run(['rc-service','greetd','status'],capture_output=True,text=True).returncode)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'quiesce-submission-inspection-private.json').write_bytes(q.stdout);print(q.stdout.decode())
