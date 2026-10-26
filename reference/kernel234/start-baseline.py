from pathlib import Path
import json
import host

R = Path(__file__).resolve().parent
r = host.ssh('python3 -', input=(R / 'collect-baseline.py').read_bytes(), timeout=65)
(host.PRIVATE / 'baseline-host-private.log').write_bytes(r.stdout + r.stderr)
report = json.loads(r.stdout)
(R / 'baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
for name in ['samurai-bluetooth-private', 'main.conf-private', 'geni-events-private.json']:
    host.download('/var/lib/samurai/k234-baseline-r2/' + name, host.PRIVATE / name)
print(json.dumps(report))
