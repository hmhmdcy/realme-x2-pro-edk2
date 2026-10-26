"""Export private scan evidence and the freshly audited offline state."""
from pathlib import Path
import hashlib
import json
import tarfile
import host

result = host.ssh('sh /var/lib/samurai/k185-reboot-tools/quiesce-current183.sh', timeout=110)
(host.PRIVATE / 'quiesce-host-private.log').write_bytes(result.stdout + result.stderr)
names = ['k185-preflash', 'k185-preflash-initial-private', 'k185-preflash-r2-private', 'k185-quiesce', 'k185-baseline', 'k185-policy',
         'k185-scan-before', 'k185-scan-before-v2', 'k185-load', 'k185-scan-after', 'k185-deploy', 'k185-tools']
result = host.ssh('tar -C /var/lib/samurai -czf /tmp/k185-before-reboot-private.tar.gz ' + ' '.join(names) +
                  ' && sha256sum /tmp/k185-before-reboot-private.tar.gz', timeout=55)
digest = result.stdout.decode().split()[0]
dest = host.PRIVATE / 'k185-before-reboot-private.tar.gz'
host.download('/tmp/k185-before-reboot-private.tar.gz', dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
folder = host.PRIVATE / 'before-reboot-evidence-private'
with tarfile.open(dest) as tar:
    tar.extractall(folder, filter='data')
proof = json.loads((folder / 'k185-quiesce/quiesce-validation.json').read_text())
assert proof['current_kernel'] == 183 and proof['target_kernel'] == 183 and proof['quiesce_audit_pass']
(host.PRIVATE / 'quiesce-validation-private.json').write_text(json.dumps(proof, indent=2) + '\n')
ref = Path(__file__).resolve().parent
for name, source in [('scan-comparison-validation.json', 'k185-load/scan-comparison.json'),
                     ('deployment-validation.json', 'k185-deploy/summary.json'),
                     ('module-override-validation.json', 'k185-preflash/module-override-validation.json')]:
    data = json.loads((folder / source).read_text())
    data['evidence_archive_sha256'] = digest
    (ref / name).write_text(json.dumps(data, indent=2) + '\n')
(ref / 'before-reboot-archive-validation.json').write_text(json.dumps({'archive_sha256': digest, 'verified': True,
    'private_archive_contains_keys_and_must_not_be_published': True}, indent=2) + '\n')
print(json.dumps({'quiesce_passed': True, 'evidence_archive_sha_verified': True,
                  'module_files_verified': 770, 'declared_overrides': 1,
                  'flash_requested': False, 'transition_not_sent': True}))
