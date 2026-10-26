from pathlib import Path
import hashlib
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k184-reboot-runtime')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
old = Path('/var/lib/samurai/k184-preflash/boot-id-private.txt').read_bytes()
assert boot != old and os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)


def capture(args, name):
    p = subprocess.run(args, capture_output=True, timeout=25, check=True)
    (out / name).write_bytes(p.stdout)
    return p.stdout.decode(errors='replace')


log = capture(['dmesg'], 'dmesg-private.txt')
capture(['uname', '-a'], 'kernel.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k184-preflash/partition-check.sha256'], 'partition-check.txt')
capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
capture(['rc-status', '--nocolor', 'default'], 'services-private.txt')
capture(['cat', '/proc/asound/cards'], 'cards.txt')
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
          for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
faults = {name: log.count(value) for name, value in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'gpu': 'gpu fault:', 'dpu': 'Frame done timeout',
    'asoc': 'ASoC error', 'irq_read': 'Failed to read IRQ status',
    'bluetooth_reassembly': 'Frame reassembly failed', 'slpi_start_timeout': '2400000.remoteproc: start timed out',
}.items()}
for name in ['warning', 'oops', 'gpu', 'dpu', 'asoc', 'irq_read', 'slpi_start_timeout']:
    assert faults[name] == 0
assert remote == {'slpi': 'offline', 'modem': 'running', 'adsp': 'running'}
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
assert Path('/var/lib/samurai/k184-libssc-r2/build-validation.json').exists()
report = {'kernel_build': 183, 'new_boot_confirmed': True, 'taint': 0, 'remoteproc': remote,
          'boot_log_from_zero': log.lstrip().startswith('[    0.'), 'fault_counts': faults,
          'phosh_running': bool(subprocess.run(['pidof', 'phosh'], capture_output=True).stdout.strip()),
          'sound_card_present': 'samurai' in (out / 'cards.txt').read_text().lower(),
          'partitions_and_nv_verified': True, 'no_partitions_flashed': True,
          'uptime_seconds': float(Path('/proc/uptime').read_text().split()[0])}
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
