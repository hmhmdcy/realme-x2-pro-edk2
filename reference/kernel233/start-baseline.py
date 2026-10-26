from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
r=host.ssh('python3 -',input=(R/'collect-baseline.py').read_bytes(),timeout=120)
(host.PRIVATE/'baseline-host-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);(R/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
