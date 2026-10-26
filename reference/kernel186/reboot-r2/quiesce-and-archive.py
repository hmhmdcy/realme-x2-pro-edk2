from pathlib import Path
import hashlib
import json
import host

p = host.ssh('sh /var/lib/samurai/k186r2-reboot-tools/quiesce-current183.sh', timeout=110)
(host.PRIVATE / 'r2-quiesce-host-private.log').write_bytes(p.stdout + p.stderr)
names = ['k186-baseline', 'k186-slpi-lifecycle', 'k186r2-preflash', 'k186r2-quiesce', 'k186-tools','k186-load-fastrpc-r2','k186-original-cycle1','k186-candidate-failure','k186-candidate-kmsg']
p = host.ssh('tar -C /var/lib/samurai -czf /tmp/k186r2-before-reboot-private.tar.gz ' +
    ' '.join(names) + ' && sha256sum /tmp/k186r2-before-reboot-private.tar.gz', timeout=55)
digest = p.stdout.decode().split()[0]
path = host.PRIVATE / 'r2-k186-before-reboot-private.tar.gz'
host.download('/tmp/k186r2-before-reboot-private.tar.gz', path)
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
p = host.ssh('cat /var/lib/samurai/k186r2-quiesce/quiesce-validation.json')
proof = json.loads(p.stdout)
assert proof['current_kernel'] == 183 and proof['quiesce_audit_pass'] and proof['taint'] == 0
(host.PRIVATE / 'r2-quiesce-validation-private.json').write_bytes(p.stdout)
(Path(__file__).resolve().parent / 'pre-reboot-archive-validation.json').write_text(json.dumps(
    dict(archive_sha256=digest, archive_sha_verified=True, all_dsp_and_display_quiesced=True,
         current_kernel=183, partitions_flashed=[]), indent=2) + '\n')
print(json.dumps({'quiesce_passed': True, 'archive_sha_verified': True, 'transition_not_yet_sent': True}))
