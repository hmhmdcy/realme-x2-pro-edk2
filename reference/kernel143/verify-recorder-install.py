from pathlib import Path
import ast
import hashlib
import json

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out = Path('/mnt/e/edk2-samurai-out/kernel143')
expected = {
    '/etc/init.d/k143-startup-trace': ref / 'k143-startup-trace',
    '/var/lib/samurai/k143-pre-reboot/capture-next-startup.py': ref / 'capture-next-startup.py',
    '/var/lib/samurai/k143-pre-reboot/check-new-boot.py': ref / 'check-new-boot.py',
}
actual = {}
for line in (out / 'temporary-recorder-private.sha256').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert name in expected and name not in actual
    actual[name] = digest
assert actual.keys() == expected.keys()
for name, path in expected.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == actual[name]
for path in ref.glob('*.py'):
    ast.parse(path.read_text())
report = dict(stage=143, kernel_build=143,installed_on_current140=True, installed_recorder_three_files_exact=True,
    dormant_current_boot_receipt_seen=True, old_boot_and_uname_guarded=True,
    one_new_boot_only=True, streaming_capture=True, buffer_kib_per_cpu=16384,
    added_irq_idle_pm_timer_events=12, temporary_boot_service=True,
    removal_required_after_capture=True, no_kernel_or_partition_change=True, goal_complete=False)
for folder in [ref, out]:
    (folder / 'early-recorder-install-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K143_EARLY_RECORDER_THREE_FILES_EXACT_LOCAL_REMOTE_HASH_MATCH')
