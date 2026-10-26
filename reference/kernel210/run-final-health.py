from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
p=host.ssh('python3 -',input=(here/'final-health.py').read_bytes(),timeout=90)
(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
