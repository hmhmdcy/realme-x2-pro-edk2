from pathlib import Path
import hashlib
import json
import host

ref = Path(__file__).resolve().parent
candidate = host.PRIVATE / 'hci_uart-k185-private.ko'
build = json.loads((ref / 'module-build-validation.json').read_text())
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == build['candidate_sha256']
for p in [candidate, ref / 'module-build-validation.json', ref / 'load-candidate.py']:
    host.upload(p, '/var/lib/samurai/k185-tools/' + p.name)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(p.read_bytes()).hexdigest() + '  /var/lib/samurai/k185-tools/' + p.name + '\n').encode())
result = host.ssh('python3 /var/lib/samurai/k185-tools/load-candidate.py', timeout=60)
(host.PRIVATE / 'candidate-load-host-private.log').write_bytes(result.stdout + result.stderr)
print(result.stdout.decode().strip())
