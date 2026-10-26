"""Continue the recorded operation only after proving restart2 never ran."""
from pathlib import Path
import json
import host

log = (host.PRIVATE / 'restart-submit-private.log').read_bytes()
assert b'F2FS_FROZEN_FOR_BOOTLOADER' in log
assert b"can't open file '/var/lib/samurai/k228-reboot-tools/linux-restart2-bootloader.py'" in log
assert b'validated-current-linux' not in log and b'before-single-restart2' not in log
marker = host.PRIVATE / 'restart-continuation-private.json'
assert not marker.exists(), 'Inspect this same continuation rather than replaying'
code = b"from pathlib import Path; import json; assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k228-baseline/boot-id-private.txt').read_bytes(); assert Path('/run/k228-bootloader-state').read_text().strip()=='FROZEN'; assert not Path('/run/k228-linux-restart2-phase-private.json').exists(); assert Path('/sys/bus/platform/devices/88e0000.serial/driver').exists(); print(json.dumps({'same_boot':True,'frozen_marker':True,'restart_phase_absent':True,'eud_still_bound':True}))"
result = host.ssh('PYTHONDONTWRITEBYTECODE=1 python3 -', input=code, timeout=15)
(host.PRIVATE / 'restart-path-recovery-preflight-private.log').write_bytes(result.stdout + result.stderr)
proof = json.loads(result.stdout)
assert all(proof.values())
result = host.ssh('PYTHONDONTWRITEBYTECODE=1 python3 /var/lib/samurai/k228-tools/linux-restart2-bootloader.py --inspect', timeout=15)
(host.PRIVATE / 'restart-path-recovery-inspect-private.log').write_bytes(result.stdout + result.stderr)
assert json.loads(result.stdout)['inspect_only']
marker.write_text(json.dumps(dict(same_original_operation=True, previous_failure_before_restart_syscall=True,
                                  root_already_frozen=True, corrected_existing_script_path=True,
                                  kernel_restart_syscall_request_count=1), indent=2) + '\n')
try:
    result = host.ssh('PYTHONDONTWRITEBYTECODE=1 python3 /var/lib/samurai/k228-tools/linux-restart2-bootloader.py', timeout=50)
    output = result.stdout + result.stderr
except RuntimeError:
    output = (host.PRIVATE / 'transport-last-failure-private.log').read_bytes()
(host.PRIVATE / 'restart-continuation-submit-private.log').write_bytes(output)
assert b'validated-current-linux' in output and b'before-single-restart2' in output, 'Observe current operation; never repeat'
print(json.dumps(dict(stage=228, path_failure_recovered=True, same_operation_continued=True,
                      single_restart2_entry_observed=True, fresh_fastboot_identity_required=True,
                      partitions_flashed=[])))
