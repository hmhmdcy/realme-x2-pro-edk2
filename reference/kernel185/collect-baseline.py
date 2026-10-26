from pathlib import Path
import hashlib
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k185-baseline')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k184-final/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko'
assert module.is_file()
(out / 'hci_uart-original-private.ko').write_bytes(module.read_bytes())
log = subprocess.check_output(['dmesg'], text=True)
(out / 'dmesg-private.txt').write_text(log)
assert not any(value in log for value in ['WARNING:', 'Oops:', 'gpu fault:', 'Frame done timeout', 'ASoC error'])
counts = {'bluetooth_reassembly': log.count('Frame reassembly failed')}
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
assert subprocess.run(['rc-service', 'bluetooth', 'status'], capture_output=True).returncode == 0
elf = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth'
report = {'kernel_build': 183, 'same_boot_as184_final': True, 'taint': 0,
          'original_hci_uart_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
          'bluetooth_baseline_faults': counts,
          'sibling_modules_sha256': {name: hashlib.sha256((elf / name).read_bytes()).hexdigest()
                                    for name in ['bluetooth.ko'] if (elf / name).is_file()},
          'uptime_seconds': float(Path('/proc/uptime').read_text().split()[0])}
for p in ['btqca.ko', 'btbcm.ko']:
    report['sibling_modules_sha256'][p] = hashlib.sha256((elf / p).read_bytes()).hexdigest()
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
