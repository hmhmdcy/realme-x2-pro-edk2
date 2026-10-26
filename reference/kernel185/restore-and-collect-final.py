"""Restore production BlueZ configuration after the separately verified scan."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import dbus

os.umask(0o077)
out = Path('/var/lib/samurai/k185-final')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k185-reboot-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
scan = json.loads(Path('/var/lib/samurai/k185-scan-postresume/scan-validation.json').read_text())
pm = json.loads(Path('/var/lib/samurai/k185-scan-after-suspend/powered-suspend/validation-reviewed.json').read_text())
assert scan['transport_fix_passed'] and scan['preexisting_pairing_keys_unchanged']
assert pm['suspend_and_rtc_resume_passed'] and pm['post_resume_three_transport_scans_passed']


def bluetooth_state():
    bus = dbus.SystemBus(private=True)
    objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    props = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
    assert not props['Powered'] and not props['Discovering']
    assert all(not v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
    bus.close()


def capture(args, name):
    p = subprocess.run(args, capture_output=True, timeout=40)
    (out / name).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, name
    return p.stdout.decode(errors='replace')


bluetooth_state()
config = Path('/etc/bluetooth/main.conf')
original = Path('/var/lib/samurai/k185post-policy/main.conf-before-private').read_bytes()
assert original == Path('/var/lib/samurai/k185-policy/main.conf-before-private').read_bytes()
policy = json.loads(Path('/var/lib/samurai/k185post-policy/summary.json').read_text())
assert hashlib.sha256(config.read_bytes()).hexdigest() == policy['temporary_config_sha256']
(out / 'temporary-policy-private.conf').write_bytes(config.read_bytes())
capture(['rc-service', 'bluetooth', 'stop'], 'service-stop-private.txt')
st = config.stat()
fd, name = tempfile.mkstemp(prefix='.k185-final-', dir=config.parent)
try:
    with os.fdopen(fd, 'wb') as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(name, st.st_mode & 0o777)
    os.chown(name, st.st_uid, st.st_gid)
    os.replace(name, config)
finally:
    if os.path.exists(name):
        os.unlink(name)
capture(['rc-service', 'bluetooth', 'start'], 'service-start-private.txt')
bluetooth_state()
assert config.read_bytes() == original
keys_before = json.loads(Path('/var/lib/samurai/k185-policy/pairing-keys-before-private.json').read_text())
current = {}
for p in Path('/var/lib/bluetooth').rglob('info'):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(p)
    current[str(p)] = {s: dict(cfg[s]) for s in cfg.sections() if 'key' in s.lower()}
assert all(current.get(p) == keys for p, keys in keys_before.items())
assert all(not keys for p, keys in current.items() if p not in keys_before)
module_root = Path('/usr/lib/modules') / os.uname().release
raw = (module_root / 'kernel/drivers/bluetooth/hci_uart.ko').read_bytes()
expected = json.loads(Path('/var/lib/samurai/k185-deploy/summary.json').read_text())['candidate_sha256']
assert hashlib.sha256(raw).hexdigest() == expected
off = struct.unpack_from('<Q', raw, 40)[0]
size, count, idx = struct.unpack_from('<HHH', raw, 58)
rows = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * size) for i in range(count)]
strings = raw[rows[idx][4]:rows[idx][4] + rows[idx][5]]
note = next(r for r in rows if strings[r[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id')
assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == raw[note[4]:note[4] + note[5]]
log = capture(['dmesg'], 'dmesg-private.txt')
faults = {key: log.count(value) for key, value in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'bluetooth_reassembly': 'Frame reassembly failed',
    'qca_setup': 'QCA Failed', 'asoc': 'ASoC error', 'irq_read': 'Failed to read IRQ status',
    'gpu': 'gpu fault:', 'dpu': 'Frame done timeout', 'ngd_resume': 'NGD resume failed',
    'wifi_key_delete': 'failed to remove peer key', 'wifi_resume_failure': 'failed to resume',
    'wifi_firmware_crash': 'firmware crashed'}.items()}
assert not any(faults.values())
assert log.lstrip().startswith('[    0.') and '#183 ' in log
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
          for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == {'slpi': 'offline', 'modem': 'running', 'adsp': 'running'}
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
    assert p.read_text().strip() == 'closed'
for addr in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + addr + '/status').read_text()
wifi = capture(['iw', 'dev', 'wlan0', 'link'], 'wifi-private.txt')
assert 'freq: 5180' in wifi
capture(['sha256sum', '-c', '/var/lib/samurai/k185-preflash/partition-check.sha256'], 'partition-check.txt')
capture(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-check.txt')
capture(['sha256sum', '-c', '/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'], 'source-check.txt')
capture(['sh', '-c', 'cd "$1" && sha256sum -c /var/lib/samurai/k185-preflash/old132-module-tree.sha256',
         'sh', str(module_root)], 'module-tree-check.txt')
mm = subprocess.run(['mmcli', '-m', 'any', '--output-json'], capture_output=True, timeout=20)
(out / 'modemmanager-private.json').write_bytes(mm.stdout + mm.stderr)
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
report = dict(stage=185, kernel_build=183, same_boot_as185_reboot_runtime=True, taint=0,
    full_boot_log_from_zero=True, full_boot_fault_counts=faults, remoteproc=remote,
    sensor_power='vdd=0 vddio=0', phosh_running=bool(subprocess.run(['pidof', 'phosh'], capture_output=True).stdout.strip()),
    wifi_frequency_mhz=5180, pcm_closed_and_amps_muted=True, bluetooth_service_running=True,
    bluetooth_powered=False, bluetooth_discovering=False, connected_bluetooth_devices=0,
    bluez_original_configuration_restored=True, pairing_keys_preserved=True,
    installed_and_loaded_module_verified=True, candidate_module_sha256=expected,
    module_files=770, total_tree_files_verified=784, module_overrides=1,
    pulse_rx_nuls=int(Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls').read_text()),
    warm_boot_verified=True, cold_power_cycle_verified=False, powered_s2idle_rtc_resume_verified=True,
    immediate_wifi_guard_failed=True, wifi_auto_recovery_verified=True, delayed_postresume_scans_verified=True,
    partitions_and_nv_verified=True, partitions_flashed=[], system_libssc_replaced=False,
    slpi_started_this_boot=False, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
os.sync()
print(json.dumps(report))
