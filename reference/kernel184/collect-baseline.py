"""Save a current, private peripheral baseline; print only a sanitized summary."""
from pathlib import Path
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k184-baseline-r2')
out.mkdir(mode=0o700)
assert os.uname().version.startswith('#183 ')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
assert boot == Path('/var/lib/samurai/k183-runtime/boot-id-private.txt').read_bytes()


def capture(name, command):
    try:
        p = subprocess.run(command, capture_output=True, timeout=20)
    except OSError as error:
        (out / (name + '-private.txt')).write_text(str(error) + '\n')
        return 127, ''
    (out / (name + '-private.txt')).write_bytes(p.stdout + p.stderr)
    return p.returncode, p.stdout.decode(errors='replace')


_, log = capture('dmesg', ['dmesg'])
_, modem = capture('modem', ['mmcli', '-m', '0', '-J'])
capture('qrtr', ['qrtr-lookup'])
capture('services', ['rc-status', '--nocolor', 'default'])
capture('camera', ['media-ctl', '-p'])
capture('light-package', ['apk', 'info', '-a', 'libssc'])
capture('gps-package', ['apk', 'info', '-a', 'gpsd'])
capture('sensor-modules', ['sh', '-c', 'modinfo fastrpc; modinfo socinfo'])
capture('bluez', ['bluetoothctl', 'show'])
remote = {}
for p in Path('/sys/class/remoteproc').glob('remoteproc*'):
    remote[(p / 'name').read_text().strip()] = (p / 'state').read_text().strip()
errors = {name: log.count(pattern) for name, pattern in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'gpu': 'gpu fault:',
    'dpu_timeout': 'Frame done timeout', 'bluetooth_reassembly': 'Frame reassembly failed',
    'modem_crash': 'remoteproc 4080000.remoteproc: crash detected',
}.items()}
summary = {
    'kernel_build': 183, 'same_boot_as183_runtime': True,
    'taint': int(Path('/proc/sys/kernel/tainted').read_text()),
    'remoteproc': remote,
    'sensor_power': Path('/sys/devices/platform/sensor-power/state').read_text().strip(),
    'modem_state': json.loads(modem).get('modem', {}).get('generic', {}).get('state'),
    'modem_failure': json.loads(modem).get('modem', {}).get('generic', {}).get('state-failed-reason'),
    'video_nodes': len(list(Path('/dev').glob('video[0-9]*'))),
    'full_boot_fault_counts': errors,
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
