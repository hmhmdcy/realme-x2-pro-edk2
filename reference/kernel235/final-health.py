"""Read-only current-boot health after disk staging, without loading candidates."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import dbus

os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k233-runtime/boot-id-private.txt').read_bytes() == (root / 'k235-baseline/boot-id-private.txt').read_bytes()
out = root / 'k235-final-health'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
stage = root / 'k235-module-stage'
assert json.loads((stage / 'transaction-state-private.json').read_text())['state'] == 'verified'
tree = Path('/usr/lib/modules') / os.uname().release
sha = lambda data: hashlib.sha256(data).hexdigest()
actual = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
assert actual == json.loads((stage / 'module-inventory-after-private.json').read_text())
assert len(actual) == 789 and sum(name.endswith('.ko') for name in actual) == 775
assert Path('/etc/modprobe.d/samurai-pmic-bringup.conf').read_bytes() == b'options qcom_pm8008 experimental_p_imx319_power=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + n * size) for n in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    result = [data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(result) == 1
    return result[0]
assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes() == note((stage / 'before/kernel/drivers/mfd/qcom-pm8008.ko').read_bytes())
assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip() == 'Y'
assert not Path('/sys/module/imx319').exists() and not Path('/sys/module/qcom_pm8008_imx319_lab').exists()
for name, relative in [('fastrpc', 'kernel/drivers/misc/fastrpc.ko'),
                       ('imx471', 'kernel/drivers/media/i2c/imx471.ko'),
                       ('qcom_camss', 'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'),
                       ('hci_uart', 'kernel/drivers/bluetooth/hci_uart.ko'),
                       ('reset_realme_rmx1931_pm8008', 'kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko')]:
    assert Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes() == note((tree / relative).read_bytes())
for name in ['1-0004', '1-0008']:
    assert Path('/sys/bus/i2c/devices', name, 'driver').resolve().name == 'pm8008'
assert Path('/sys/bus/platform/devices/camera-pmic-resets/driver').resolve().name == 'rmx1931-pm8008-resets'
assert not Path('/sys/bus/i2c/devices/1-0009').exists()
for path in ['/sys/bus/i2c/devices/7-0010', '/sys/bus/platform/devices/acb3000.camss', '/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(path, 'power/runtime_status').read_text().strip() == 'suspended'
hashes = json.loads((root / 'k235-baseline/userspace-hashes-private.json').read_text())
for name, digest in hashes.items():
    if name != '/etc/modprobe.d/samurai-pmic-bringup.conf':
        assert sha(Path(name).read_bytes()) == digest
remote = {(path / 'name').read_text().strip(): (path / 'state').read_text().strip() for path in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == dict(adsp='running', slpi='running', modem='running')
bus = dbus.SystemBus(private=True)
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
sensor = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
assert all(sensor.Get('net.hadess.SensorProxy', name) for name in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity'])
bus.close()
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
faults = {name: log.count(needle) for name, needle in dict(warning=b'WARNING:', oops=b'Oops:',
    gpu=b'gpu fault:', dsp_fatal=b'fatal error received', bt_reassembly=b'Frame reassembly failed').items()}
assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not any(path.read_text().strip() for path in Path('/sys/module').glob('*/taint'))
check = subprocess.run(['sha256sum', '-c', str(root / 'k233-tools/partition-after.sha256')], capture_output=True, timeout=40)
(out / 'partition-readback-private.log').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=235, current233_identity_verified=True, staged_module_files=789, staged_ko=775,
              live232_mfd_verified_separately_from_staged235=True, lab_and_imx319_not_loaded=True,
              p_identity_only_no_secondary=True, front_and_camss_suspended=True,
              unchanged_fastrpc_camera_bluetooth_provider_loaded_notes_match=True,
              bluetooth_off_no_connections=True, sensorproxy_three_has_true=True,
              remoteprocs=remote, partition_readback_unchanged=True, fault_counts=faults,
              taint=0, no_hardware_candidate_acceptance_claimed=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
