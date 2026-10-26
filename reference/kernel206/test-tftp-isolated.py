"""Native candidate validation on QRTR instance206; original service stays live."""
from pathlib import Path
import dbus, hashlib, json, os, signal, subprocess, time, traceback
os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k206-tftp-isolated'
assert (out / 'artifacts-private.json').is_file()
assert not (out / 'started-private.json').exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k205r2-runtime/boot-id-private.txt').read_bytes()
artifacts = json.loads((out / 'artifacts-private.json').read_text())
for name, digest in artifacts.items():
    assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
original_pid = int(Path('/run/samurai-wifi/tftp.pid').read_text())
original_stat = Path('/proc/%d/stat' % original_pid).read_text().split(') ', 1)[1].split()[19]
original_hash = hashlib.sha256(Path('/usr/sbin/samurai-tqftpserv').read_bytes()).hexdigest()
(out / 'started-private.json').write_text(json.dumps(dict(original_pid=original_pid, original_start=original_stat, original_hash=original_hash)) + '\n')
(out / 'boot-id-private.txt').write_bytes(boot)
before = subprocess.check_output(['dmesg'])
(out / 'dmesg-before-private.txt').write_bytes(before)
def command(args, label, timeout=35):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, label
    return p
server = None
mounted = False
cache = out / 'ram'
log = None
try:
    command([str(out / 'test-tftp-ram-arm64'), str(out)], 'arm64-file-fixture')
    baseline = json.loads(command([str(out / 'test-tftp-qrtr-arm64'), '0', 'deny'], 'baseline-qrtr-denial').stdout)
    cache.mkdir(mode=0o700)
    command(['mount', '-t', 'tmpfs', '-o', 'size=32m,mode=0700,nosuid,nodev,noexec', 'tmpfs', str(cache)], 'mount-test-cache')
    mounted = True
    firmware = out / 'firmware'
    firmware.mkdir(mode=0o700)
    (firmware / 'fixture').write_bytes(b'unchanged-firmware-fixture')
    log = (out / 'isolated-server-private.log').open('wb')
    env = dict(os.environ, SAMURAI_TFTP_RW_ROOT=str(cache), SAMURAI_TFTP_FIRMWARE_ROOT=str(firmware))
    server = subprocess.Popen([str(out / 'samurai-tqftpserv-isolated'), '-d'], stdout=log, stderr=subprocess.STDOUT, env=env)
    (out / 'test-server-pid-private.txt').write_text(str(server.pid) + '\n')
    time.sleep(0.4)
    assert server.poll() is None
    candidate = json.loads(command([str(out / 'test-tftp-qrtr-arm64'), '206', 'pass'], 'candidate-qrtr', timeout=40).stdout)
    assert server.poll() is None
    assert (firmware / 'fixture').read_bytes() == b'unchanged-firmware-fixture'
    assert candidate['qrtr_transactions'] == 13 and candidate['readback_bytes_compared'] == 20435
    assert baseline['qrtr_transactions'] == 1 and baseline['readback_bytes_compared'] == 0
    assert Path('/proc/%d/stat' % original_pid).read_text().split(') ', 1)[1].split()[19] == original_stat
    assert hashlib.sha256(Path('/usr/sbin/samurai-tqftpserv').read_bytes()).hexdigest() == original_hash
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    after = subprocess.check_output(['dmesg'])
    (out / 'dmesg-after-private.txt').write_bytes(after)
    faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert all(value == 0 for value in faults.values())
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    result = dict(stage=206, arm64_file_fixture_passed=True, actual_qrtr_packets=True, baseline_denial=baseline, isolated_candidate=candidate, firmware_fixture_preserved=True, production_service_pid_and_binary_unchanged=True, gps_started=False, modem_owner_unchanged=True, modem_restarted=False, fault_delta=faults, taint=int(Path('/proc/sys/kernel/tainted').read_text()))
except Exception:
    (out / 'failure-private.txt').write_text(traceback.format_exc())
    raise
finally:
    bus.close()
    if server is not None:
        server.terminate()
        server.wait(timeout=8)
    if log is not None:
        log.close()
    if mounted:
        command(['umount', str(cache)], 'unmount-test-cache')
    (out / 'cleanup-private.json').write_text(json.dumps(dict(server_terminated=server is None or server.poll() is not None, cache_unmounted=not mounted or not os.path.ismount(cache))) + '\n')
result['isolated_server_terminated'] = True
result['test_cache_unmounted'] = True
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
