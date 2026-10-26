"""Allow only this recorded old-kernel warning for one boot transition."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

base = Path('/var/lib/samurai/k143-quiesce')
assert os.uname().version.startswith('#140 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == base.joinpath('boot-id-private.txt').read_bytes()
assert base.joinpath('boot-id-private.txt').read_bytes() == Path('/var/lib/samurai/k143-preflash/boot-id-private.txt').read_bytes()
assert int(Path('/proc/sys/kernel/tainted').read_text()) == 512
before = base.joinpath('dmesg-before.txt').read_text()
after = subprocess.check_output(['dmesg'], text=True)
assert after.startswith(before), 'Old log prefix must remain available'
delta = after[len(before):]
assert before.count('WARNING:') == 0 and after.count('WARNING:') == 1
assert delta.count('ida_free called for id=1 which is not allocated.') == 1
assert re.search(r'WARNING: lib/idr.c:594 at ida_free\+', delta)
assert all(name + '+' in delta for name in ['ida_free', 'slim_unregister_controller', 'slim_pd_status', 'pdr_notifier_work'])
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|frame done timeout|dsi_err_worker|unable to prepare channel', delta)
patterns = ['gpu fault:', 'frame done timeout', 'dsi_err_worker', 'unable to prepare channel']
assert all(after.count(pattern) == before.count(pattern) for pattern in patterns)
assert all(Path('/sys/class/remoteproc/remoteproc' + str(i) + '/state').read_text().strip() == 'offline' for i in range(3))
report = dict(stage=143, current_kernel=140, target_kernel=143, taint=512,
              known_warning_transition_only=True, warning_count=1,
              known_warning='SLIMbus controller ID freed again during PDR shutdown',
              old_log_prefix_preserved=True, no_new_gpu_display_dma_faults=True,
              no_new_bug_oops_panic=True, all_remoteprocs_offline=True,
              old_warning_not_fixed=True, clean_runtime_accepted=False, goal_complete=False)
if '--record' in sys.argv:
    assert not base.joinpath('known-warning-transition.json').exists()
    base.joinpath('known-warning-transition.json').write_text(json.dumps(report, indent=2) + '\n')
    base.joinpath('dmesg-after.txt').write_text(after)
else:
    assert json.loads(base.joinpath('known-warning-transition.json').read_text()) == report
print('K143_EXACT_OLD_SLIM_WARNING_RETAINED_TRANSITION_ONLY')
