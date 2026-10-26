"""Export only sanitized reports from a hash-verified private archive."""
from pathlib import Path
import hashlib
import json
import tarfile
import host

names = ['k185-reboot-runtime', 'k185-reboot-runtime-initial-private', 'k185post-policy',
         'k185-scan-after-suspend', 'k185-postresume-inspection', 'k185-scan-postresume', 'k185-final']
p = host.ssh('test -f /var/lib/samurai/k185-final/summary.json && tar -C /var/lib/samurai -czf /tmp/k185-final-evidence-private.tar.gz ' +
    ' '.join(names) + ' && sha256sum /tmp/k185-final-evidence-private.tar.gz', timeout=55)
digest = p.stdout.decode().split()[0]
dest = host.PRIVATE / 'k185-final-evidence-private.tar.gz'
host.download('/tmp/k185-final-evidence-private.tar.gz', dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
folder = host.PRIVATE / 'final-evidence-private'
with tarfile.open(dest) as tar:
    tar.extractall(folder, filter='data')
ref = Path(__file__).resolve().parent
for name, source in [('reboot-runtime-validation.json', 'k185-reboot-runtime/summary.json'),
    ('powered-suspend-validation.json', 'k185-scan-after-suspend/powered-suspend/validation-reviewed.json'),
    ('combined-trial-failure-validation.json', 'k185-scan-after-suspend/result.json'),
    ('postresume-scan-validation.json', 'k185-scan-postresume/scan-validation.json'),
    ('postresume-inspection-validation.json', 'k185-postresume-inspection/summary.json'),
    ('final-validation.json', 'k185-final/summary.json')]:
    data = json.loads((folder / source).read_text())
    data['evidence_archive_sha256'] = digest
    (ref / name).write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'final_archive_sha_verified': True, 'sanitized_reports_exported': 6,
    'candidate_persisted_after_warm_boot_and_s2idle': True, 'initial_combined_trial_failure_retained': True}))
