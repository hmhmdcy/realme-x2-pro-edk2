from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'runtime-validation.json').read_text())['sensor_titan_top_domain_attached']
p=host.ssh('python3 -',input=(here/'test-independent-sensor-pm.py').read_bytes(),timeout=90);(host.PRIVATE/'independent-pm-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'independent-sensor-pm-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
