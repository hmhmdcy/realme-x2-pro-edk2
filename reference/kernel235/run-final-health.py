from pathlib import Path
import json
import host

R = Path(__file__).resolve().parent
result = host.ssh('python3 -', input=(R / 'final-health.py').read_bytes(), timeout=100)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
