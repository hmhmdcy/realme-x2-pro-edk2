from pathlib import Path
import json
import os
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k184-final')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == Path('/var/lib/samurai/k184-reboot-runtime-r2/boot-id-private.txt').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
trial = Path('/var/lib/samurai/k184-sensor-light-v4')
assert (trial / 'trial-exit.txt').read_text().strip() == '0'
userspace = json.loads((trial / 'userspace/summary.json').read_text())
assert userspace['light_claim_succeeded'] and userspace['proxy_exit'] == 0
assert userspace['vendor_type']['measurements'] > 0 and userspace['vendor_type']['exit_code'] == 0
assert userspace['default_type']['exit_code'] == 254
assert userspace['system_library_unchanged'] and userspace['package_database_unchanged']
assert (trial / 'nv-before.txt').read_bytes() == (trial / 'nv-after.txt').read_bytes()
assert (trial / 'source-before.txt').read_bytes() == (trial / 'source-after.txt').read_bytes()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not subprocess.run(['pidof', 'hexagonrpcd'], capture_output=True).stdout.strip()
assert not subprocess.run(['pidof', 'iio-sensor-proxy'], capture_output=True).stdout.strip()
log = subprocess.check_output(['dmesg'], text=True)
(out / 'dmesg-private.txt').write_text(log)
faults = {n: log.count(p) for n, p in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'gpu': 'gpu fault:', 'dpu': 'Frame done timeout',
    'asoc': 'ASoC error', 'irq_read': 'Failed to read IRQ status',
    'slpi_start_timeout': '2400000.remoteproc: start timed out', 'bluetooth_reassembly': 'Frame reassembly failed',
}.items()}
assert all(v == 0 for k, v in faults.items() if k != 'bluetooth_reassembly')
bluetooth = [line for line in log.splitlines() if 'Frame reassembly failed' in line]
(out / 'bluetooth-startup-private.txt').write_text('\n'.join(bluetooth) + '\n')
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
          for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == {'slpi': 'offline', 'modem': 'running', 'adsp': 'running'}
pcm = {str(p.relative_to('/proc/asound')): p.read_text().strip()
       for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')}
assert pcm and all(s == 'closed' for s in pcm.values())
amps = [Path('/sys/bus/i2c/devices/' + n + '/status').read_text() for n in ['1-0039', '1-003a']]
assert all('powered=0 muted=1' in text for text in amps)
for args, name in [
    (['sha256sum', '-c', '/var/lib/samurai/k184r2-preflash/partition-check.sha256'], 'partition-check.txt'),
    (['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt'),
    (['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')]:
    (out / name).write_bytes(subprocess.check_output(args))
report = {'kernel_build': 183, 'same_boot_as_reboot_runtime_r2': True, 'taint': 0,
          'remoteproc': remote, 'sensor_power': 'vdd=0 vddio=0', 'temporary_processes_stopped': True,
          'phosh_running': bool(subprocess.run(['pidof', 'phosh'], capture_output=True).stdout.strip()),
          'pcm_closed_and_amps_muted': True, 'full_boot_fault_counts': faults,
          'original_sources_nv_and_partitions_verified': True, 'partitions_flashed': [],
          'system_library_replaced': False, 'default_services_enabled_by_this_stage': [],
          'userspace_alias_fix_verified': True, 'physical_lux_accuracy_verified': False,
          'uptime_seconds': float(Path('/proc/uptime').read_text().split()[0])}
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
