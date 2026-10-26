from pathlib import Path
import dbus, hashlib, json, os, shutil, signal, subprocess, time, traceback
os.umask(0o077)
root = Path('/var/lib/samurai'); stage = root / 'k207-tftp-stage'; out = root / 'k207-tftp-deploy'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root / 'k207-tftp-isolated/summary.json').read_text())['cases']['new-rollover']['wire_block_zero_events'] == 4
proof = json.loads((stage / 'build-validation.json').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(stage / 'samurai-tqftpserv-new') == proof['candidate_sha256'] and proof['compiler_warnings'] == 0
binary = Path('/usr/sbin/samurai-tqftpserv')
assert sha(binary) == 'd0906a5abb939fa5d1e906692b0ac769f0760857d4a9780a07ad5b59d1c4ca4e'
assert sha('/usr/sbin/samurai-wifi') == 'ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd'
pid_path = Path('/run/samurai-wifi/tftp.pid'); pid = int(pid_path.read_text())
assert Path('/proc/%d/exe' % pid).resolve() == binary.resolve()
assert sha('/proc/%d/exe' % pid) == sha(binary)
started = Path('/proc/%d/stat' % pid).read_text().split(') ', 1)[1].split()[19]
environment = dict(entry.decode().split('=', 1) for entry in Path('/proc/%d/environ' % pid).read_bytes().split(b'\0') if entry)
assert environment['SAMURAI_TFTP_RW_ROOT'] == '/run/samurai-wifi/tftp-rw'
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
out.mkdir(mode=0o700); (out / 'boot-id-private.txt').write_bytes(boot)
shutil.copyfile(binary, out / 'samurai-tqftpserv206-original')
shutil.copyfile('/run/samurai-wifi/tftp.log', out / 'tftp-before-private.log')
(out / 'original-environment-private.json').write_text(json.dumps(environment, indent=2) + '\n')
before = subprocess.check_output(['dmesg']); (out / 'dmesg-before-private.txt').write_bytes(before)
def replace(source):
    temp = binary.with_name(binary.name + '.k207-new'); temp.write_bytes(source.read_bytes()); temp.chmod(0o755); os.replace(temp, binary)
def alive():
    path = Path('/proc/%d/stat' % pid)
    if not path.exists(): return False
    fields = path.read_text().split(') ', 1)[1].split()
    return fields[19] == started and fields[0] != 'Z'
def launch(label):
    log = Path('/run/samurai-wifi/tftp.log').open('wb')
    p = subprocess.Popen([str(binary), '-d'], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
    log.close(); pid_path.write_text(str(p.pid) + '\n')
    (out / (label + '-pid-private.txt')).write_text(str(p.pid) + '\n')
    time.sleep(0.4); assert p.poll() is None
    return p
child = None; stopped = False
try:
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 8
    while alive() and time.monotonic() < deadline: time.sleep(0.05)
    assert not alive(); stopped = True
    replace(stage / 'samurai-tqftpserv-new'); child = launch('candidate')
    test = subprocess.run([str(root / 'k207-tftp-isolated/native-client'), '0', 'pass'], capture_output=True, timeout=75)
    (out / 'production-regression-private.log').write_bytes(test.stdout + test.stderr)
    assert test.returncode == 0
    result_test = json.loads(test.stdout)
    assert result_test['qrtr_transactions'] == 14 and result_test['readback_bytes_compared'] == 26580
    fixture = Path('/run/samurai-wifi/tftp-rw/samurai-validation207')
    assert fixture.resolve().parent == Path('/run/samurai-wifi/tftp-rw')
    (fixture / 'work.tmp').unlink(); fixture.rmdir()
    check = subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], capture_output=True)
    (out / 'nv-source-check-private.log').write_bytes(check.stdout + check.stderr); assert check.returncode == 0
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    assert child.poll() is None and sha('/proc/%d/exe' % child.pid) == proof['candidate_sha256']
    after = subprocess.check_output(['dmesg']); (out / 'dmesg-after-private.txt').write_bytes(after)
    faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert not any(faults.values()) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    report = dict(stage=207, block_fix_installed_and_loaded=True, runtime_sha256=sha(binary), production_regression=result_test, protocol_test_files_removed=True, wifi_startup_helper_unchanged=True, nv_sources_unchanged=True, modem_owner_unchanged=True, modem_restarted=False, rebooted=False, partitions_flashed=[], fault_delta=faults, taint=int(Path('/proc/sys/kernel/tainted').read_text()))
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report))
except Exception:
    (out / 'failure-private.txt').write_text(traceback.format_exc())
    if child is not None and child.poll() is None: child.terminate(); child.wait(timeout=8)
    if stopped: replace(out / 'samurai-tqftpserv206-original'); launch('rollback')
    raise
finally:
    bus.close()
