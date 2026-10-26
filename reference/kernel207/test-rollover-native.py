from pathlib import Path
import dbus, hashlib, json, os, re, resource, subprocess, time, traceback
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.umask(0o077)
root = Path('/var/lib/samurai'); out = root / 'k207-tftp-isolated'
assert not (out / 'started-private.json').exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207-baseline/boot-id-private.txt').read_bytes()
for name, digest in json.loads((out / 'artifacts-private.json').read_text()).items():
    assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
production_pid = int(Path('/run/samurai-wifi/tftp.pid').read_text())
production_start = Path('/proc/%d/stat' % production_pid).read_text().split(') ', 1)[1].split()[19]
production_sha = hashlib.sha256(Path('/usr/sbin/samurai-tqftpserv').read_bytes()).hexdigest()
(out / 'started-private.json').write_text(json.dumps(dict(production_pid=production_pid, production_start=production_start)))
(out / 'boot-id-private.txt').write_bytes(boot)
cache = out / 'ram'; cache.mkdir(mode=0o700)
mount = subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=32m,mode=0700,nosuid,nodev,noexec', 'tmpfs', str(cache)], capture_output=True)
(out / 'mount-private.log').write_bytes(mount.stdout + mount.stderr); assert mount.returncode == 0
firmware = out / 'firmware'; firmware.mkdir(mode=0o700)
(firmware / 'fixture').write_bytes(b'unchanged-firmware-fixture')
before = subprocess.check_output(['dmesg']); (out / 'dmesg-before-private.txt').write_bytes(before)
results = {}
server = None
try:
    for label, binary, mode, marker in [('old-write', 'old-isolated', 'rollover-write', 'WRQ_ACK_MISMATCH'), ('old-read', 'old-isolated', 'rollover-read', 'RRQ_DATA_MISMATCH'), ('new-rollover', 'new-isolated', 'rollover', None), ('new-regression', 'new-isolated', 'pass', None)]:
        env = dict(os.environ, SAMURAI_TFTP_RW_ROOT=str(cache), SAMURAI_TFTP_FIRMWARE_ROOT=str(firmware))
        with (out / (label + '-server-private.log')).open('wb') as log:
            server = subprocess.Popen([str(out / binary)], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env)
            (out / 'active-test-server-pid-private.txt').write_text(str(server.pid) + '\n')
            try:
                time.sleep(0.3); assert server.poll() is None
                started = time.monotonic()
                p = subprocess.run([str(out / 'native-client'), '207', mode], capture_output=True, timeout=70)
                (out / (label + '-client-private.log')).write_bytes(p.stdout + p.stderr)
                if marker:
                    assert p.returncode == -6 and marker.encode() in p.stderr, label
                    absolute = int(re.search(rb'absolute=(\d+)', p.stderr)[1])
                    results[label] = dict(expected_failure_reproduced=True, failure_marker=marker, absolute_block=absolute, client_exit=p.returncode)
                else:
                    assert p.returncode == 0, label
                    results[label] = json.loads(p.stdout)
                results[label]['elapsed_seconds'] = time.monotonic() - started
                (out / 'progress.json').write_text(json.dumps(results, indent=2) + '\n')
            finally:
                if server.poll() is None: server.terminate()
                server.wait(timeout=8)
                server = None
    assert results['old-write']['absolute_block'] > 65535 and results['old-read']['absolute_block'] > 65535
    assert results['new-rollover']['readback_bytes_compared'] == 1048603 and results['new-rollover']['wire_block_zero_events'] == 4
    assert results['new-regression']['readback_bytes_compared'] == 26580 and results['new-regression']['qrtr_transactions'] == 14
    assert (firmware / 'fixture').read_bytes() == b'unchanged-firmware-fixture'
    assert Path('/proc/%d/stat' % production_pid).read_text().split(') ', 1)[1].split()[19] == production_start
    assert hashlib.sha256(Path('/usr/sbin/samurai-tqftpserv').read_bytes()).hexdigest() == production_sha
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    after = subprocess.check_output(['dmesg']); (out / 'dmesg-after-private.txt').write_bytes(after)
    faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert not any(faults.values()) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    result = dict(stage=207, actual_native_qrtr=True, cases=results, firmware_fixture_unchanged=True, production_pid_and_binary_unchanged=True, modem_owner_unchanged=True, modem_restarted=False, gps_started=False, fault_delta=faults, taint=int(Path('/proc/sys/kernel/tainted').read_text()))
except Exception:
    (out / 'failure-private.txt').write_text(traceback.format_exc()); raise
finally:
    if server is not None and server.poll() is None:
        server.terminate(); server.wait(timeout=8)
    unmount = subprocess.run(['umount', str(cache)], capture_output=True)
    (out / 'unmount-private.log').write_bytes(unmount.stdout + unmount.stderr)
    assert unmount.returncode == 0
    bus.close()
    (out / 'cleanup-private.json').write_text(json.dumps(dict(test_servers_terminal=True, cache_unmounted=not os.path.ismount(cache))) + '\n')
result.update(test_servers_terminal=True, cache_unmounted=True)
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
