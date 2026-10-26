"""One temporary module lifecycle and one finite scan; always restore baseline."""
from pathlib import Path
import configparser
import dbus
import hashlib
import json
import os
import re
import struct
import subprocess
import time
import traceback

os.umask(0o077)
root = Path('/var/lib/samurai')
baseline = root / 'k234-baseline-r2'
tools = root / 'k234-tools'
out = root / 'k234-diagnostic'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root / 'k233-runtime/boot-id-private.txt').read_bytes() == (baseline / 'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
out.mkdir(mode=0o700)
module_root = Path('/usr/lib/modules') / os.uname().release
original = module_root / 'kernel/drivers/bluetooth/hci_uart.ko'
candidate = tools / 'hci_uart.ko'
build = json.loads((tools / 'diagnostic-build-validation.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(candidate.read_bytes()) == build['candidate_sha256']
assert sha(original.read_bytes()) == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
original_config = Path('/etc/bluetooth/main.conf').read_bytes()
assert original_config == (baseline / 'main.conf-private').read_bytes()
before = subprocess.check_output(['dmesg'])
(out / 'dmesg-before-private.txt').write_bytes(before)
instance = Path('/sys/kernel/tracing/instances/k234-bt')
assert not instance.exists()
events = json.loads((baseline / 'geni-events-private.json').read_text())
report = dict(stage=234, state='starting', no_reboot_or_partition_flash=True,
              no_pair_connect_or_haptic_commands=True, diagnostic_is_not_functional_fix=True)
failure = None
cleanup_errors = []
services_touched = False
trace_created = False
candidate_loaded = False


def command(argv, label, timeout=40):
    result = subprocess.run(argv, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, label
    return result


def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + n * size) for n in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    notes = [data[s[4]:s[4] + s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(notes) == 1
    return notes[0]


def state():
    bus = dbus.SystemBus(private=True)
    try:
        objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
        adapters = [(p, v['org.bluez.Adapter1']) for p, v in objects.items() if 'org.bluez.Adapter1' in v]
        assert len(adapters) == 1
        assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
        return dict(powered=bool(adapters[0][1]['Powered']), discovering=bool(adapters[0][1]['Discovering']))
    finally:
        bus.close()


def write_config(data, label):
    target = Path('/etc/bluetooth/main.conf')
    temporary = target.with_name('main.conf.k234-' + label)
    with temporary.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(target.stat().st_mode & 0o777)
    os.replace(temporary, target)


def attempt(function, label):
    try:
        function()
    except Exception:
        cleanup_errors.append(label)
        (out / (label + '-failure-private.txt')).write_text(traceback.format_exc())


try:
    assert state() == dict(powered=False, discovering=False)
    for name, digest in json.loads((baseline / 'userspace-hashes-private.json').read_text()).items():
        assert sha(Path(name).read_bytes()) == digest
    # Disable reconnection before restarting BlueZ; preserve exact original bytes.
    text = original_config.decode()
    match = re.search(r'(?ms)^\[Policy\]\s*\n(.*?)(?=^\[|\Z)', text)
    assert match
    policy = match[1]
    for key, value in [('AutoEnable', 'false'), ('ReconnectAttempts', '0'), ('ReconnectUUIDs', '')]:
        pattern = r'(?m)^' + key + r'\s*=.*$'
        if re.search(pattern, policy):
            policy = re.sub(pattern, key + '=' + value, policy)
        else:
            policy += '\n' + key + '=' + value + '\n'
    temporary_config = (text[:match.start(1)] + policy + text[match.end(1):]).encode()
    services_touched = True
    command(['rc-service', 'bluetooth', 'stop'], 'bluez-stop')
    write_config(temporary_config, 'temporary')
    command(['/usr/sbin/samurai-bluetooth', 'stop'], 'original-modules-stop')
    assert not Path('/sys/class/bluetooth/hci0').exists()
    instance.mkdir()
    trace_created = True
    (instance / 'buffer_size_kb').write_text('1024')
    (instance / 'trace_clock').write_text('mono')
    for name in events:
        event = instance / 'events/qcom_geni_serial' / name
        (event / 'filter').write_text('name == "c8c000.serial"')
        (event / 'enable').write_text('1')
    (instance / 'tracing_on').write_text('1')
    for name in ['btbcm', 'btqca']:
        command(['insmod', str(original.parent / (name + '.ko'))], name + '-load')
    command(['insmod', str(candidate), 'samurai_rx_diag=1'], 'candidate-load')
    candidate_loaded = True
    assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == note(candidate.read_bytes())
    assert Path('/sys/module/hci_uart/parameters/samurai_rx_diag').read_text().strip() == 'Y'
    command(['/usr/sbin/samurai-bluetooth', 'start'], 'normal-address-provision-and-start', timeout=50)
    command(['rc-service', 'bluetooth', 'start'], 'bluez-start')
    assert state() == dict(powered=False, discovering=False)
    report.update(state='candidate_loaded', temporary_candidate_note_verified=True)
    (out / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')
    bus = dbus.SystemBus(private=True)
    try:
        obj = bus.get_object('org.bluez', '/org/bluez/hci0')
        props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
        adapter = dbus.Interface(obj, 'org.bluez.Adapter1')
        for name in ['Pairable', 'Connectable', 'Discoverable']:
            props.Set('org.bluez.Adapter1', name, dbus.Boolean(False), timeout=10)
        props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True), timeout=25)
        assert state()['powered']
        for name in ['Pairable', 'Connectable', 'Discoverable']:
            props.Set('org.bluez.Adapter1', name, dbus.Boolean(False), timeout=10)
        adapter.SetDiscoveryFilter(dbus.Dictionary({'Transport': dbus.String('auto'), 'Discoverable': dbus.Boolean(False), 'AutoConnect': dbus.Boolean(False)}, signature='sv'), timeout=10)
        adapter.StartDiscovery(timeout=15)
        time.sleep(4)
        adapter.StopDiscovery(timeout=10)
        props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(False), timeout=20)
        assert state() == dict(powered=False, discovering=False)
        report['one_power_on_and_four_second_scan_completed'] = True
    finally:
        # Runs also on an interrupted/failed scan; make no connection calls.
        try:
            current = props.GetAll('org.bluez.Adapter1')
            if current['Discovering']:
                adapter.StopDiscovery(timeout=10)
            if current['Powered']:
                props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(False), timeout=20)
        finally:
            bus.close()
except Exception:
    failure = traceback.format_exc()
    (out / 'failure-private.txt').write_text(failure)
finally:
    # Stop capture before restoring original modules to separate candidate evidence.
    if trace_created:
        attempt(lambda: (instance / 'tracing_on').write_text('0'), 'trace-stop')
        attempt(lambda: (out / 'uart-trace-private.txt').write_text((instance / 'trace').read_text()), 'trace-save')
        attempt(lambda: (out / 'trace-stats-private.json').write_text(json.dumps({p.parent.name: p.read_text() for p in (instance / 'per_cpu').glob('cpu*/stats')}, indent=2) + '\n'), 'trace-stats')
        for name in events:
            attempt(lambda n=name: (instance / 'events/qcom_geni_serial' / n / 'enable').write_text('0'), 'trace-disable-' + name)
        attempt(instance.rmdir, 'trace-instance-remove')
    attempt(lambda: (out / 'dmesg-candidate-private.txt').write_bytes(subprocess.check_output(['dmesg'])), 'candidate-log')
    if services_touched:
        attempt(lambda: command(['rc-service', 'bluetooth', 'stop'], 'restore-bluez-stop'), 'restore-bluez-stop')
        attempt(lambda: command(['/usr/sbin/samurai-bluetooth', 'stop'], 'restore-modules-stop'), 'restore-modules-stop')
        # Restore modules before starting the original AutoEnable=false daemon.
        attempt(lambda: write_config(original_config, 'restore'), 'restore-config')
        attempt(lambda: command(['/usr/sbin/samurai-bluetooth', 'start'], 'restore-original-start', timeout=50), 'restore-original-start')
        attempt(lambda: command(['rc-service', 'bluetooth', 'start'], 'restore-bluez-start'), 'restore-bluez-start')
    report.update(failed=failure is not None, cleanup_errors=cleanup_errors, candidate_was_loaded=candidate_loaded,
                  trace_instance_removed=not instance.exists())
    (out / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')

assert not cleanup_errors, 'Cleanup failed; inspect native state, do not repeat lifecycle blindly'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (baseline / 'boot-id-private.txt').read_bytes()
assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == note(original.read_bytes())
assert not Path('/sys/module/hci_uart/parameters/samurai_rx_diag').exists()
assert state() == dict(powered=False, discovering=False)
assert Path('/etc/bluetooth/main.conf').read_bytes() == original_config
after_modules = {str(p.relative_to(module_root)): sha(p.read_bytes()) for p in module_root.rglob('*') if p.is_file()}
assert after_modules == json.loads((baseline / 'module-tree-private.json').read_text())
for name, digest in json.loads((baseline / 'userspace-hashes-private.json').read_text()).items():
    assert sha(Path(name).read_bytes()) == digest
keys = {}
for p in Path('/var/lib/bluetooth').rglob('info'):
    c = configparser.ConfigParser(interpolation=None)
    c.read(p)
    keys[str(p)] = {s: dict(c[s]) for s in c.sections() if 'key' in s.lower()}
assert keys == json.loads((baseline / 'pairing-keys-private.json').read_text())
after = subprocess.check_output(['dmesg'])
(out / 'dmesg-after-private.txt').write_bytes(after)
faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', dsp_fatal=b'fatal error received', reassembly=b'Frame reassembly failed', qca_setup=b'QCA Failed').items()}
candidate_log = (out / 'dmesg-candidate-private.txt').read_bytes()
delta = candidate_log[len(before):] if candidate_log.startswith(before) else candidate_log
records = [l for l in delta.splitlines() if b'RXDIAG234 ' in l and b' ns=' in l]
assert len(records) <= 16
report.update(state='restored', original_loaded_note_restored=True,
              installed_module_tree787_unchanged=True, original_userspace_and_config_restored=True,
              pairing_keys_unchanged=True, bt_restored_off=True,
              phase5_state_records=len(records), taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              fault_delta=faults, diagnostic_changes_timing=True,
              not_proof_of_phase5_fix=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
assert failure is None and not any(faults.values()) and report['taint'] == 0
