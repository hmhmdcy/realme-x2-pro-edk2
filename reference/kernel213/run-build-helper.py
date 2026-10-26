from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
p=host.ssh('python3 -',input=(here/'build-helper-candidate.py').read_bytes(),timeout=1400);(host.PRIVATE/'build-helper-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'helper-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
