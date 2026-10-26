from pathlib import Path
import hashlib
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k186-baseline')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k185-final/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
assert not subprocess.run(['pidof', 'hexagonrpcd'], capture_output=True).stdout.strip()
log = subprocess.check_output(['dmesg'], text=True)
assert 'remote processor 2400000.remoteproc is now up' not in log
assert '2400000.remoteproc: remote processor' not in log or '2400000.remoteproc: remote processor slpi is now up' not in log
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'dmesg-private.txt').write_text(log)
(out / 'interrupts-private.txt').write_text(Path('/proc/interrupts').read_text())
firmware = Path('/sys/class/remoteproc/remoteproc0/firmware').read_text().strip()
assert firmware == 'qcom/sm8150/realme/samurai/slpi.mdt'
module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest() == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
report = {'stage': 186, 'kernel_build': 183, 'same_boot_as185_final': True,
    'taint': 0, 'slpi_offline_and_sensor_supplies_off': True, 'no_existing_rpc_daemon': True,
    'original_slpi_firmware_selected': True, 'hci_uart185_module_preserved': True,
    'uptime_seconds': float(Path('/proc/uptime').read_text().split()[0])}
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
