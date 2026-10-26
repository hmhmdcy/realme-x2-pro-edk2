"""Fresh current identity and manifests for the staged235 boot transition."""
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
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
out = root / 'k236-baseline'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'start-uptime-private.txt').write_bytes(Path('/proc/uptime').read_bytes())
sha = lambda data: hashlib.sha256(data).hexdigest()
tree = Path('/usr/lib/modules') / os.uname().release
actual = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
assert actual == json.loads((root / 'k235-module-stage/module-inventory-after-private.json').read_text())
assert len(actual) == 789 and sum(name.endswith('.ko') for name in actual) == 775
assert json.loads((root / 'k235-module-stage/transaction-state-private.json').read_text())['state'] == 'verified'
(out / 'module-inventory-private.json').write_text(json.dumps(actual, indent=2) + '\n')
def checked(args, label):
    result = subprocess.run(args, capture_output=True, timeout=45)
    (out / (label + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, label
# These files supply expected content, never the current boot identity.
parts = (root / 'k233-tools/partition-after.sha256').read_bytes()
assert len(parts.decode().splitlines()) == 3
lock = json.loads((root / 'k235-tools/deployment-lock-private.json').read_text())
assert any(line == lock['files']['boot232_rollback']['sha256'] + '  /dev/sde11' for line in parts.decode().splitlines())
(out / 'partition-check.sha256').write_bytes(parts)
checked(['sha256sum', '-c', str(out / 'partition-check.sha256')], 'partitions')
userspace = (root / 'k233-baseline/userspace-check.sha256').read_bytes()
(out / 'userspace-check.sha256').write_bytes(userspace)
checked(['sha256sum', '-c', str(out / 'userspace-check.sha256')], 'userspace')
installed = Path('/lib/apk/db/installed').read_bytes()
assert installed == (root / 'k233-baseline/installed-before-private.txt').read_bytes()
(out / 'installed-before-private.txt').write_bytes(installed)
config = Path('/etc/modprobe.d/samurai-pmic-bringup.conf').read_bytes()
assert config == b'options qcom_pm8008 experimental_p_imx319_power=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
(out / 'pmic-loader-staged-private.conf').write_bytes(config)
def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    found = [data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(found) == 1
    return found[0]
old_mfd = (root / 'k235-module-stage/before/kernel/drivers/mfd/qcom-pm8008.ko').read_bytes()
assert sha(old_mfd) == 'f633467fa1edcc27eabbb76f8caee00f7d60d3e2440ebca7bc68138c051ae01a'
running = Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()
assert running == note(old_mfd)
(out / 'mfd-loaded-note-private.bin').write_bytes(running)
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
(out / 'pmic-q-before-private.json').write_text(json.dumps(dict(device='1-0004')) + '\n')
for path in ['/sys/bus/i2c/devices/7-0010', '/sys/bus/platform/devices/acb3000.camss', '/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(path, 'power/runtime_status').read_text().strip() == 'suspended'
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
assert all(props.Get('net.hadess.SensorProxy', name) for name in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity'])
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [value['org.bluez.Adapter1'] for value in objects.values() if 'org.bluez.Adapter1' in value]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(value.get('org.bluez.Device1', {}).get('Connected', False) for value in objects.values())
bus.close()
remote = {(path / 'name').read_text().strip(): (path / 'state').read_text().strip() for path in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == dict(adsp='running', slpi='running', modem='running')
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
faults = {name: log.count(needle) for name, needle in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:',
    dsp_fatal=b'fatal error received', bt_reassembly=b'Frame reassembly failed').items()}
assert not any(faults.values())
assert not any(path.read_text().strip() for path in Path('/sys/module').glob('*/taint'))
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=236, current233_identity_verified=True, default_intree2abde_note_saved=True,
              staged775_ko789_files_verified=True, live232_mfd_note_verified=True, p_q_provider_retained=True,
              full_transition_baseline_saved=True, original_userspace_packages_and_partitions_exact=True,
              front_suspended=True, remoteprocs=remote, bluetooth_off_no_connections=True,
              sensorproxy_three_has_true=True, faults=faults, taint=0, transition_not_started=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
