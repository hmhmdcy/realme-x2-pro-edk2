from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
p=host.ssh('python3 -',input=(here/'prepare-build-sdk.py').read_bytes(),timeout=180);(host.PRIVATE/'prepare-sdk-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'sdk-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
