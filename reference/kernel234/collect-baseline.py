"""Read-only native baseline before a temporary HCI diagnostic load."""
from pathlib import Path
import configparser
import dbus
import hashlib
import json
import os
import struct
import subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root / 'k233-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert os.uname().version.startswith('#183 ')
out = root / 'k234-baseline-r2'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
sha = lambda data: hashlib.sha256(data).hexdigest()
module_root = Path('/usr/lib/modules') / os.uname().release
module = module_root / 'kernel/drivers/bluetooth/hci_uart.ko'
assert sha(module.read_bytes()) == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'


def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + n * size) for n in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    notes = [data[s[4]:s[4] + s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(notes) == 1
    return notes[0]


assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == note(module.read_bytes())
assert not Path('/sys/module/hci_uart/parameters/samurai_rx_diag').exists()
modules = {str(p.relative_to(module_root)): sha(p.read_bytes()) for p in module_root.rglob('*') if p.is_file()}
assert len(modules) == 787 and sum(n.endswith('.ko') for n in modules) == 773
(out / 'module-tree-private.json').write_text(json.dumps(modules, indent=2) + '\n')
hashes = {}
for name in ['/usr/sbin/samurai-bluetooth', '/etc/init.d/bluetooth', '/etc/bluetooth/main.conf',
             '/etc/modprobe.d/samurai-pmic-bringup.conf', '/usr/sbin/samurai-ssc', '/usr/bin/ModemManager']:
    data = Path(name).read_bytes()
    hashes[name] = sha(data)
    (out / (Path(name).name + '-private')).write_bytes(data)
(out / 'userspace-hashes-private.json').write_text(json.dumps(hashes, indent=2) + '\n')
keys = {}
for p in Path('/var/lib/bluetooth').rglob('info'):
    config = configparser.ConfigParser(interpolation=None)
    config.read(p)
    keys[str(p)] = {s: dict(config[s]) for s in config.sections() if 'key' in s.lower()}
(out / 'pairing-keys-private.json').write_text(json.dumps(keys, indent=2) + '\n')
bus = dbus.SystemBus(private=True)
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
sensor = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
assert all(sensor.Get('net.hadess.SensorProxy', n) for n in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity'])
bus.close()
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == dict(adsp='running', slpi='running', modem='running')
assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip() == 'Y'
for p in ['/sys/bus/i2c/devices/7-0010', '/sys/bus/platform/devices/acb3000.camss', '/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(p, 'power/runtime_status').read_text().strip() == 'suspended'
assert all((Path(p) / 'driver').is_symlink() for p in ['/sys/bus/i2c/devices/1-0008', '/sys/bus/i2c/devices/1-0004', '/sys/bus/platform/devices/camera-pmic-resets'])
events = Path('/sys/kernel/tracing/events/qcom_geni_serial')
available = sorted(p.name for p in events.iterdir() if p.is_dir())
(out / 'geni-events-private.json').write_text(json.dumps(available, indent=2) + '\n')
for p in events.iterdir():
    if p.is_dir():
        (out / (p.name + '-format-private.txt')).write_bytes((p / 'format').read_bytes())
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', dsp_fatal=b'fatal error received', reassembly=b'Frame reassembly failed').items()}
assert not any(faults.values())
report = dict(stage=234, current233_identity_verified=True, loaded_and_default185_module_match=True,
              module_files=len(modules), module_ko_count=773, bt_off_no_connections=True,
              remoteprocs=remote, front_suspended=True, pmic_p_q_provider_bound=True,
              faults=faults, taint=0, available_geni_events=available,
              no_service_module_power_or_partition_change=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
