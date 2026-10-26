from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
q=host.ssh('python3 -',input=(HERE/'native-inspect-services.py').read_bytes(),timeout=20)
report=json.loads(q.stdout)
(HERE/'services-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
