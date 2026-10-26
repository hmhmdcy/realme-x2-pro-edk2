"""Remove the completed 205 diagnostic deployment using preserved original bytes."""
from pathlib import Path
import configparser, dbus, hashlib, json, os, shutil, struct, subprocess, traceback

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k206-bt-restore'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k205r2-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko'
helper = Path('/usr/sbin/samurai-bluetooth')
config = Path('/etc/bluetooth/main.conf')
original = root / 'k205-bootdiag-deploy/hci_uart185-original.ko'
original_helper = root / 'k205-bootdiag-deploy/samurai-bluetooth-original.sh'
original_config = root / 'k205-bt-policy/main.conf-before-private'
assert sha(module) == 'ee14310674722fda61529a113cc8e90ae3c247e5c36a5a2c95544aed7741b480'
assert sha(helper) == 'ae46b800ed036f0527c6a0434c7da03c8a722abf74a34b420cbe44e1913ef762'
assert sha(original) == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
assert b'samurai_rx_diag' not in original_helper.read_bytes()
cfg = configparser.ConfigParser(interpolation=None)
cfg.read(original_config)
assert cfg.getboolean('Policy', 'AutoEnable') is False

def keys():
    result = {}
    for p in Path('/var/lib/bluetooth').rglob('info'):
        c = configparser.ConfigParser(interpolation=None)
        c.read(p)
        result[str(p)] = {s: dict(c[s]) for s in c.sections() if 'key' in s.lower()}
    return result

def idle():
    bus = dbus.SystemBus(private=True)
    obj = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    adapters = [v['org.bluez.Adapter1'] for v in obj.values() if 'org.bluez.Adapter1' in v]
    assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
    assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in obj.values())
    mm = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
    assert int(mm.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    bus.close()

idle()
assert keys() == json.loads((root / 'k205-bt-policy/pairing-keys-before-private.json').read_text())
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
for p, name in [(module, 'diagnostic-module-private.ko'), (helper, 'diagnostic-helper-private.sh'), (config, 'temporary-main-conf-private')]:
    shutil.copyfile(p, out / name)
before = subprocess.check_output(['dmesg'])
(out / 'dmesg-before-private.txt').write_bytes(before)
def command(args, label, timeout=40, cwd=None):
    p = subprocess.run(args, capture_output=True, timeout=timeout, cwd=cwd)
    (out / (label + '-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, label
def replace(source, target, mode):
    temp = target.with_name(target.name + '.k206-restore')
    temp.write_bytes(source.read_bytes())
    temp.chmod(mode)
    os.replace(temp, target)

try:
    command(['rc-service', 'bluetooth', 'stop'], 'bluez-stop')
    command([str(helper), 'stop'], 'diagnostic-unload')
    assert not Path('/sys/module/hci_uart').exists()
    replace(original, module, 0o644)
    replace(original_helper, helper, 0o755)
    replace(original_config, config, config.stat().st_mode & 0o777)
    command([str(helper), 'start'], 'original-start')
    command(['rc-service', 'bluetooth', 'start'], 'bluez-start')
    idle()
    assert keys() == json.loads((root / 'k205-bt-policy/pairing-keys-before-private.json').read_text())
    assert sha(module) == sha(original) and helper.read_bytes() == original_helper.read_bytes() and config.read_bytes() == original_config.read_bytes()
    data = module.read_bytes()
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[headers[index][4]:headers[index][4] + headers[index][5]]
    notes = [r for r in headers if strings[r[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(notes) == 1
    note = notes[0]
    assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == data[note[4]:note[4] + note[5]]
    assert not Path('/sys/module/hci_uart/parameters/samurai_rx_diag').exists()
    command(['sha256sum', '-c', str(root / 'k200-deploy/paired-module-tree.sha256')], 'full-original-module-tree', cwd=Path('/usr/lib/modules') / os.uname().release)
    after = subprocess.check_output(['dmesg'])
    (out / 'dmesg-after-private.txt').write_bytes(after)
    faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert all(value == 0 for value in faults.values())
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    result = dict(stage=206, current_r2_boot_verified=True, restored185_module_and_loaded_build_id=True, restored_original_helper=True, restored_original_bluez_config=True, original_autoenable_false=True, pairing_keys_unchanged=True, full_784_module_tree_original_manifest_passed=True, bt_powered=False, bt_discovering=False, bt_connections=0, gps_enabled=0, fault_delta=faults, taint=0, rebooted=False, partitions_flashed=[], uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
except Exception:
    (out / 'failure-private.txt').write_text(traceback.format_exc())
    raise
