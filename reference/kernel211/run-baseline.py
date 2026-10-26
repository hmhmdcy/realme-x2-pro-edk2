from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
p=host.ssh('python3 -',input=(here/'baseline.py').read_bytes(),timeout=90)
(host.PRIVATE/'baseline-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
host.download('/var/lib/samurai/k211-baseline/loader-and-rules-private.json',host.PRIVATE/'loader-and-rules-private.json')
print(json.dumps(report))
