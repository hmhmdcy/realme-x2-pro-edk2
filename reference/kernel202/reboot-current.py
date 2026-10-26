"""One ordinary bootloader round trip; no partition flash."""
from pathlib import Path
import json, subprocess
import host

marker = host.PRIVATE/'reboot-request-private.json'
assert not marker.exists(), 'Inspect existing transition instead of repeating'
proof = json.loads((host.PRIVATE/'quiesce-validation-private.json').read_text())
assert proof['stage'] == 202 and proof['current_kernel'] == 183 and proof['quiesce_audit_pass'] and proof['taint'] == 0
boot = proof['boot_id']
assert len(boot) == 36 and all(c in '0123456789abcdef-' for c in boot)
marker.write_text(json.dumps(dict(source_boot_id=boot, request_count=1, command='bootloader', flash_requested=False), indent=2)+'\n')
command = 'PYTHONDONTWRITEBYTECODE=1 sh /tmp/k202-freeze-for-bootloader.sh '+boot+' && PYTHONDONTWRITEBYTECODE=1 python3 /var/lib/samurai/k202-reboot-tools/linux-restart2-bootloader.py --inspect && PYTHONDONTWRITEBYTECODE=1 python3 /var/lib/samurai/k202-reboot-tools/linux-restart2-bootloader.py'
try:
    result = host.ssh(command, timeout=50)
    output = result.stdout+result.stderr
except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
    output = (error.stdout or b'')+(error.stderr or b'')
(host.PRIVATE/'restart-submit-private.log').write_bytes(output)
assert b'F2FS_FROZEN_FOR_BOOTLOADER' in output and b'validated-current-linux' in output, 'Inspect same operation; do not repeat'
print(json.dumps(dict(single_restart2_path_entered=True, final_console_receipt_observed=b'before-single-restart2' in output, fresh_fastboot_verification_required=True, partitions_flashed=[])))
