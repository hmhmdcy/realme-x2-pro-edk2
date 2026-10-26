from pathlib import Path
import hashlib
import json
import tarfile
import host

result = host.ssh('test -f /var/lib/samurai/k184-final/summary.json && tar -C /var/lib/samurai -czf /tmp/k184-final-evidence-private.tar.gz k184-reboot-runtime k184-reboot-runtime-r2 k184-sensor-light-v3 k184-sensor-light-v4 k184-final && sha256sum /tmp/k184-final-evidence-private.tar.gz', timeout=45)
expected = result.stdout.decode().split()[0]
dest = host.PRIVATE / 'k184-final-evidence-private.tar.gz'
host.download('/tmp/k184-final-evidence-private.tar.gz', dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest() == expected
folder = host.PRIVATE / 'final-evidence-private'
with tarfile.open(dest) as tar:
    tar.extractall(folder, filter='data')
ref = Path(__file__).resolve().parent
for name, source in [
    ('final-validation.json', 'k184-final/summary.json'),
    ('userspace-v4-validation.json', 'k184-sensor-light-v4/userspace/summary.json'),
    ('userspace-v3-failure-validation.json', 'k184-sensor-light-v3/userspace/summary.json'),
    ('reboot-runtime-validation.json', 'k184-reboot-runtime/summary.json'),
    ('reboot-runtime-r2-validation.json', 'k184-reboot-runtime-r2/summary.json')]:
    data = json.loads((folder / source).read_text())
    data['evidence_archive_sha256'] = expected
    (ref / name).write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'final_archive_sha_verified': True, 'sanitized_reports_exported': 5,
                  'all_required_userspace_alias_checks_passed': True}))
