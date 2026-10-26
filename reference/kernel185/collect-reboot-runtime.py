"""Fresh boot, default module, full log and original data validation."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import struct
import subprocess
import time
import dbus

os.umask(0o077)
out = Path('/var/lib/samurai/k185-reboot-runtime')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot != Path('/var/lib/samurai/k185-preflash/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
if out.exists():
    assert (out / 'boot-id-private.txt').read_bytes() == boot
else:
    out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
# The controller setup precedes bluetoothd during the normal OpenRC startup.
# Observe the real service owner; do not trigger D-Bus activation while it starts.
ready_bus = dbus.SystemBus(private=True)
deadline = time.monotonic() + 90
while not ready_bus.name_has_owner('org.bluez') and time.monotonic() < deadline:
    time.sleep(0.5)
assert ready_bus.name_has_owner('org.bluez')
ready_bus.close()


def capture(args, name):
    p = subprocess.run(args, capture_output=True, timeout=25, check=True)
    (out / name).write_bytes(p.stdout)
    return p.stdout.decode(errors='replace')


log = capture(['dmesg'], 'dmesg-private.txt')
assert log.lstrip().startswith('[    0.') and '#183 ' in log
capture(['uname', '-a'], 'kernel.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k185-preflash/partition-check.sha256'], 'partition-check.txt')
capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
module_root = Path('/usr/lib/modules') / os.uname().release
capture(['sh', '-c', 'cd "$1" && sha256sum -c /var/lib/samurai/k185-preflash/old132-module-tree.sha256',
         'sh', str(module_root)], 'module-tree-check.txt')
capture(['rc-status', '--nocolor', 'default'], 'services-private.txt')
capture(['cat', '/proc/asound/cards'], 'cards.txt')
capture(['iw', 'dev', 'wlan0', 'link'], 'wifi-private.txt')
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
          for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == {'slpi': 'offline', 'modem': 'running', 'adsp': 'running'}
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
faults = {name: log.count(value) for name, value in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'gpu': 'gpu fault:', 'dpu': 'Frame done timeout',
    'asoc': 'ASoC error', 'irq_read': 'Failed to read IRQ status', 'qca_setup': 'QCA Failed',
    'bluetooth_reassembly': 'Frame reassembly failed', 'slpi_start_timeout': '2400000.remoteproc: start timed out',
}.items()}
assert not any(faults.values())
raw = (module_root / 'kernel/drivers/bluetooth/hci_uart.ko').read_bytes()
expected = json.loads(Path('/var/lib/samurai/k185-deploy/summary.json').read_text())['candidate_sha256']
assert hashlib.sha256(raw).hexdigest() == expected
off = struct.unpack_from('<Q', raw, 40)[0]
size, count, idx = struct.unpack_from('<HHH', raw, 58)
rows = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * size) for i in range(count)]
strings = raw[rows[idx][4]:rows[idx][4] + rows[idx][5]]
note = next(r for r in rows if strings[r[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id')
assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == raw[note[4]:note[4] + note[5]]
counter = int(Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls').read_text())
assert counter >= 2
assert Path('/etc/bluetooth/main.conf').read_bytes() == Path('/var/lib/samurai/k185-policy/main.conf-before-private').read_bytes()
keys_before = json.loads(Path('/var/lib/samurai/k185-policy/pairing-keys-before-private.json').read_text())
current = {}
for p in Path('/var/lib/bluetooth').rglob('info'):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(p)
    current[str(p)] = {s: dict(cfg[s]) for s in cfg.sections() if 'key' in s.lower()}
assert all(current.get(p) == keys for p, keys in keys_before.items())
assert all(not keys for p, keys in current.items() if p not in keys_before)
bus = dbus.SystemBus(private=True)
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
props = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
assert not props['Powered'] and not props['Discovering']
assert all(not v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
(out / 'objects-private.json').write_text(json.dumps(objects, indent=2, default=str) + '\n')
bus.close()
assert 'freq: 5180' in (out / 'wifi-private.txt').read_text()
assert subprocess.run(['rc-service', 'bluetooth', 'status'], capture_output=True).returncode == 0
report = {'stage': 185, 'kernel_build': 183, 'new_boot_confirmed': True,
    'warm_reboot_verified': True, 'cold_power_cycle_verified': False, 'taint': 0, 'remoteproc': remote,
    'boot_log_from_zero': True, 'fault_counts': faults, 'default_module_sha256': expected,
    'loaded_module_build_id_matches': True, 'pulse_rx_nuls': counter, 'module_tree_files_verified': 784,
    'module_files': 770, 'module_overrides': 1, 'bluez_original_configuration_restored': True,
    'pairing_keys_preserved': True, 'no_connected_devices': True, 'bluetooth_powered': False,
    'bluetooth_discovering': False, 'phosh_running': bool(subprocess.run(['pidof', 'phosh'], capture_output=True).stdout.strip()),
    'sound_card_present': 'samurai' in (out / 'cards.txt').read_text().lower(), 'wifi_frequency_mhz': 5180,
    'partitions_and_nv_verified': True, 'no_partitions_flashed': True,
    'uptime_seconds': float(Path('/proc/uptime').read_text().split()[0])}
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
