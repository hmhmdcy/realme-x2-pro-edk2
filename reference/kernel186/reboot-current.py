"""Single audited bootloader round-trip; never flash a partition."""
from pathlib import Path
import json
import subprocess
import host

marker = host.PRIVATE / 'reboot-request-private.json'
assert not marker.exists(), 'Inspect an existing request instead of repeating it'
proof = json.loads((host.PRIVATE / 'quiesce-validation-private.json').read_text())
assert proof['current_kernel'] == 183 and proof['quiesce_audit_pass'] and proof['taint'] == 0
boot = proof['boot_id']
assert len(boot) == 36 and all(c in '0123456789abcdef-' for c in boot)
result = host.ssh('sh /tmp/k186-freeze-for-bootloader.sh ' + boot, timeout=40)
(host.PRIVATE / 'freeze-current-private.log').write_bytes(result.stdout + result.stderr)
assert b'F2FS_FROZEN_FOR_BOOTLOADER' in result.stdout
result = host.ssh('python3 /var/lib/samurai/k186-reboot-tools/linux-restart2-bootloader.py --inspect')
(host.PRIVATE / 'restart-inspection-private.json').write_bytes(result.stdout)
assert json.loads(result.stdout)['inspect_only']
marker.write_text(json.dumps({'source_boot_id': boot, 'request_count': 1,
                             'command': 'bootloader', 'flash_requested': False}, indent=2) + '\n')
try:
    p = host.ssh('python3 /var/lib/samurai/k186-reboot-tools/linux-restart2-bootloader.py', timeout=20)
    (host.PRIVATE / 'restart-submit-private.log').write_bytes(p.stdout + p.stderr)
except subprocess.CalledProcessError as error:
    (host.PRIVATE / 'restart-submit-private.log').write_bytes(error.stdout + error.stderr)
except subprocess.TimeoutExpired as error:
    (host.PRIVATE / 'restart-submit-private.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
print(json.dumps({'single_restart2_submitted': True, 'fresh_fastboot_verification_required': True,
                  'partitions_flashed': []}))
