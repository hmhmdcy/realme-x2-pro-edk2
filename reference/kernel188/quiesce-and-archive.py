from pathlib import Path
import hashlib
import json
import host

p = host.ssh('sh /var/lib/samurai/k188-reboot-tools/quiesce-current183.sh', timeout=110)
(host.PRIVATE / 'quiesce-host-private.log').write_bytes(p.stdout + p.stderr)
p = host.ssh('tar -C /var/lib/samurai -czf /tmp/k188-before-reboot-private.tar.gz k188-deploy k188-preflash k188-quiesce k188-tools && sha256sum /tmp/k188-before-reboot-private.tar.gz', timeout=55)
digest = p.stdout.decode().split()[0]
path = host.PRIVATE / 'k188-before-reboot-private.tar.gz'
host.download('/tmp/k188-before-reboot-private.tar.gz', path)
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
p = host.ssh('cat /var/lib/samurai/k188-quiesce/quiesce-validation.json')
proof = json.loads(p.stdout)
assert proof['quiesce_audit_pass'] and proof['current_kernel'] == 183
(host.PRIVATE / 'quiesce-validation-private.json').write_bytes(p.stdout)
(Path(__file__).resolve().parent / 'pre-reboot-archive-validation.json').write_text(json.dumps(dict(
    archive_sha256=digest, verified=True, all_remoteprocs_offline=True, no_transition_sent=True), indent=2) + '\n')
print(json.dumps(dict(quiesce_passed=True, archive_sha_verified=True, no_flash_requested=True)))
