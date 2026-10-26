"""Read the existing software TX journal; do not emit a console test line."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

out = Path('/var/lib/samurai/k142-eud-journal')
boot = Path('/var/lib/samurai/k142-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
assert os.uname().version.startswith('#140 ') and not out.exists()
paths = [p.joinpath('tx_journal') for p in Path('/sys/bus/platform/drivers/qcom_eud_com').iterdir()
    if p.name not in ['module'] and p.joinpath('tx_journal').is_file()]
assert len(paths) == 1
out.mkdir(mode=0o700)
out.joinpath('boot-id-private.txt').write_bytes(boot)
out.joinpath('tx-journal-private.bin').write_bytes(paths[0].read_bytes())
out.joinpath('printk-private.txt').write_text(Path('/proc/sys/kernel/printk').read_text())
out.joinpath('console-active-private.txt').write_text(Path('/sys/class/tty/console/active').read_text())
out.joinpath('manifest.json').write_text(json.dumps(dict(stage=142, kernel_build=140,
    same_boot=True, read_only=True, no_console_test_message=True, no_host_ack_claim=True,
    goal_complete=False), indent=2)+'\n')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k142-eud-journal-private.tar.gz', '.'], check=True, timeout=20)
print('K142_EXISTING_EUD_SOFTWARE_JOURNAL_READ_ONLY_CAPTURED')
