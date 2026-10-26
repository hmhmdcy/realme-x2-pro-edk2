"""Quiesce the freshly captured boot and export evidence before any transition."""
from pathlib import Path
import hashlib
import json
import host

result = host.ssh('sh /var/lib/samurai/k184-tools/quiesce-current183.sh', timeout=110)
(host.PRIVATE / 'quiesce-host-private.log').write_bytes(result.stdout + result.stderr)
result = host.ssh('tar -C /var/lib/samurai -czf /tmp/k184-before-reboot-private.tar.gz k184-preflash k184-quiesce k184-baseline k184-baseline-r2 k184-sensor-light-v1 k184-sensor-light-v2 k184-libssc-r2 && sha256sum /tmp/k184-before-reboot-private.tar.gz', timeout=55)
expected = result.stdout.decode().split()[0]
dest = host.PRIVATE / 'k184-before-reboot-private.tar.gz'
host.download('/tmp/k184-before-reboot-private.tar.gz', dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == expected
result = host.ssh('cat /var/lib/samurai/k184-quiesce/quiesce-validation.json')
(host.PRIVATE / 'quiesce-validation-private.json').write_bytes(result.stdout)
proof = json.loads(result.stdout)
assert proof['current_kernel'] == 183 and proof['target_kernel'] == 183 and proof['quiesce_audit_pass']
(host.PRIVATE / 'pre-reboot-archive-validation.json').write_text(json.dumps({'archive_sha256': expected, 'verified': True}, indent=2) + '\n')
print(json.dumps({'quiesce_passed': True, 'evidence_archive_sha_verified': True,
                  'current_kernel': 183, 'flash_requested': False, 'transition_not_sent': True}))
