"""Validate this fresh140 shutdown; retain an exact known warning, never a broad allowlist."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

base = Path('/var/lib/samurai/k145-quiesce')
assert os.uname().version.startswith('#140 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (base / 'boot-id-private.txt').read_bytes()
assert (base / 'boot-id-private.txt').read_bytes() == Path('/var/lib/samurai/k145-preflash/boot-id-private.txt').read_bytes()
taint = int(Path('/proc/sys/kernel/tainted').read_text())
before = (base / 'dmesg-before.txt').read_text()
after = subprocess.check_output(['dmesg'], text=True)
assert after.startswith(before) and before.count('WARNING:') == 0
delta = after[len(before):]
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|frame done timeout|dsi_err_worker|Unable to allocate TID|TX queue full|BAM.*allocation failed', delta)
failed = [line for line in delta.splitlines() if 'unable to prepare channel' in line]
sealed_shutdown = False
if failed:
    expected = json.loads((base / 'observed-shutdown-expected-private.json').read_text())
    assert expected['transition_only'] and expected['current_kernel'] == 140 and expected['target_kernel'] == 145
    assert expected['boot_id'] == (base / 'boot-id-private.txt').read_text().strip()
    assert hashlib.sha256(before.encode()).hexdigest() == expected['before_sha256']
    prefix = after.encode()[:expected['sealed_after_bytes']]
    assert hashlib.sha256(prefix).hexdigest() == expected['sealed_after_sha256']
    assert len(failed) == expected['shutdown_tx_prepare_failures'] == 70 and taint == 0
    assert all(re.fullmatch(r'\[\s*\d+\.\d+\] qcom,slim-ngd-ctrl 171c0000.slim-ngd: unable to prepare channel', line) for line in failed)
    sealed_shutdown = True
warning_count = after.count('WARNING:')
if warning_count == 0:
    assert taint == 0
else:
    assert warning_count == 1 and taint == 512
    assert delta.count('ida_free called for id=1 which is not allocated.') == 1
    assert re.search(r'WARNING: lib/idr.c:594 at ida_free\+', delta)
    assert all(name + '+' in delta for name in ['ida_free', 'slim_unregister_controller', 'slim_pd_status', 'pdr_notifier_work'])
assert all(Path('/sys/class/remoteproc/remoteproc' + str(i) + '/state').read_text().strip() == 'offline' for i in range(3))
report = dict(stage=145, current_kernel=140, target_kernel=145, taint=taint,
              shutdown_state_validated=True, warning_count=warning_count,
              known_warning_transition_only=warning_count == 1,
              known_warning='SLIMbus controller ID freed again during PDR shutdown' if warning_count else None,
              old_log_prefix_preserved=True, no_new_gpu_display_dma_faults=True,
              no_new_bug_oops_panic=True, all_remoteprocs_offline=True,
              old_warning_not_fixed=True, clean_runtime_accepted=False, goal_complete=False)
report['no_new_gpu_display_dma_faults'] = not failed
report.update(sealed_shutdown_faults_transition_only=sealed_shutdown,
              shutdown_tx_prepare_failures=len(failed), old_shutdown_fault_not_fixed=bool(failed),
              each_shutdown_failure_channel_state_not_recorded=bool(failed))
receipt = base / 'shutdown-state-validation.json'
if '--record' in sys.argv:
    assert not receipt.exists()
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    (base / 'dmesg-after.txt').write_text(after)
else:
    assert json.loads(receipt.read_text()) == report
print('K145_FRESH140_SHUTDOWN_STATE_GUARDED_TAINT_' + str(taint))
