"""Allow only this recorded old-kernel warning for one boot transition."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

base = Path('/var/lib/samurai/k143-rollback-quiesce')
assert os.uname().version.startswith('#143 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == base.joinpath('boot-id-private.txt').read_bytes()
assert base.joinpath('boot-id-private.txt').read_bytes() == Path('/var/lib/samurai/k143-first-runtime/boot-id-private.txt').read_bytes()
taint=int(Path('/proc/sys/kernel/tainted').read_text())
assert taint == 0
before = base.joinpath('dmesg-before.txt').read_text()
after = subprocess.check_output(['dmesg'], text=True)
assert after.startswith(before), 'Old log prefix must remain available'
delta = after[len(before):]
assert before.count('WARNING:') == 0
assert after.count('WARNING:') == (1 if taint == 512 else 0)
if taint == 512:
    assert delta.count('ida_free called for id=1 which is not allocated.') == 1
    assert re.search(r'WARNING: lib/idr.c:594 at ida_free\+', delta)
    assert all(name + '+' in delta for name in ['ida_free','slim_unregister_controller','slim_pd_status','pdr_notifier_work'])
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:', delta)
dma=[line for line in delta.splitlines() if 'unable to prepare channel' in line]
assert len(dma)==70
assert all(re.fullmatch(r'\[\s*\d+\.\d+\] qcom,slim-ngd-ctrl 171c0000.slim-ngd: unable to prepare channel',line) for line in dma)
times=[float(re.search(r'\[\s*(\d+\.\d+)\]',line)[1]) for line in dma]
assert times[-1]-times[0]<0.2
assert delta.count('TX DMA diagnostic: state=3 qmi=1 channel=0 device=0 sg=0 config_sg=0 len=8')==1
assert not re.search(r'Unable to allocate TID|TX queue full|BAM.*allocation failed',delta)
blank=base.joinpath('dmesg-at-blank.txt').read_text()
assert after.startswith(blank)
assert not re.search(r'frame done timeout|dsi_err_worker',after[len(blank):])
patterns = ['gpu fault:']
assert all(after.count(pattern) == before.count(pattern) for pattern in patterns)
assert all(Path('/sys/class/remoteproc/remoteproc' + str(i) + '/state').read_text().strip() == 'offline' for i in range(3))
report = dict(stage=143, current_kernel=143, target_kernel=140, taint=taint,
              known_shutdown_faults_transition_only=True, warning_count=after.count('WARNING:'),
              shutdown_tx_dma_failures=70, dma_null_channel_state_down_verified=True,
              known_warning='SLIMbus controller ID freed again during PDR shutdown',
              old_log_prefix_preserved=True, no_new_gpu_faults=True,
              no_display_errors_after_blank=True,
              no_new_bug_oops_panic=True, all_remoteprocs_offline=True,
              old_warning_not_fixed=True, clean_runtime_accepted=False, goal_complete=False)
if '--record' in sys.argv:
    assert not base.joinpath('known-warning-transition.json').exists()
    base.joinpath('known-warning-transition.json').write_text(json.dumps(report, indent=2) + '\n')
    base.joinpath('dmesg-after.txt').write_text(after)
else:
    assert json.loads(base.joinpath('known-warning-transition.json').read_text()) == report
print('K143_ROLLBACK_QUIESCED_FAULT_SCOPE_CHECKED')
