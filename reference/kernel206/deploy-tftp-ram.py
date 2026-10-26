"""Replace only TFTP, preserving live modem/RMTFS state and original files."""
from pathlib import Path
import dbus, hashlib, json, os, shutil, signal, subprocess, time, traceback
os.umask(0o077)
root = Path('/var/lib/samurai')
stage = root / 'k206-tftp-stage'
out = root / 'k206-tftp-deploy'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k205r2-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root / 'k206-tftp-isolated/summary.json').read_text())['isolated_server_terminated']
for name, digest in json.loads((stage / 'artifacts-private.json').read_text()).items():
    assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest
binary = Path('/usr/sbin/samurai-tqftpserv')
helper = Path('/usr/sbin/samurai-wifi')
pid_path = Path('/run/samurai-wifi/tftp.pid')
old_pid = int(pid_path.read_text())
args = [a.decode() for a in Path('/proc/%d/cmdline' % old_pid).read_bytes().split(b'\0') if a]
assert args == [str(binary), '-d']
old_start = Path('/proc/%d/stat' % old_pid).read_text().split(') ', 1)[1].split()[19]
environment = dict(entry.decode().split('=', 1) for entry in Path('/proc/%d/environ' % old_pid).read_bytes().split(b'\0') if entry)
assert environment['SAMURAI_TFTP_FIRMWARE_ROOT'] == '/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai'
rmtfs_pid = int(Path('/run/samurai-wifi/rmtfs.pid').read_text())
rmtfs_start = Path('/proc/%d/stat' % rmtfs_pid).read_text().split(') ', 1)[1].split()[19]
cache = Path('/run/samurai-wifi/tftp-rw')
assert not cache.exists()
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
for p, name in [(binary, 'samurai-tqftpserv-original'), (helper, 'samurai-wifi-original.sh'), (Path('/run/samurai-wifi/tftp.log'), 'tftp-before-private.log')]:
    shutil.copyfile(p, out / name)
(out / 'original-environment-private.json').write_text(json.dumps(environment, indent=2) + '\n')
before = subprocess.check_output(['dmesg'])
(out / 'dmesg-before-private.txt').write_bytes(before)
def command(args, label, timeout=40):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, label
    return p
def replace(source, target):
    temp = target.with_name(target.name + '.k206-new')
    temp.write_bytes(source.read_bytes()); temp.chmod(0o755); os.replace(temp, target)
def alive(pid, started):
    p = Path('/proc/%d/stat' % pid)
    if not p.exists(): return False
    fields = p.read_text().split(') ', 1)[1].split()
    return fields[19] == started and fields[0] != 'Z'
def start_service(env, name):
    stream = Path('/run/samurai-wifi/tftp.log').open('wb')
    proc = subprocess.Popen([str(binary), '-d'], stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    stream.close(); pid_path.write_text(str(proc.pid) + '\n')
    (out / (name + '-pid-private.txt')).write_text(str(proc.pid) + '\n')
    time.sleep(0.5); assert proc.poll() is None
    return proc
candidate = None
stopped = False
try:
    cache.mkdir(mode=0o700)
    command(['mount', '-t', 'tmpfs', '-o', 'size=32m,mode=0700,nosuid,nodev,noexec', 'tmpfs', str(cache)], 'mount-cache')
    assert alive(old_pid, old_start)
    os.kill(old_pid, signal.SIGTERM)
    limit = time.monotonic() + 8
    while alive(old_pid, old_start) and time.monotonic() < limit: time.sleep(0.05)
    assert not alive(old_pid, old_start)
    stopped = True
    replace(stage / 'samurai-tqftpserv-new', binary)
    replace(stage / 'samurai-wifi-new.sh', helper)
    env = dict(environment, SAMURAI_TFTP_RW_ROOT=str(cache))
    candidate = start_service(env, 'candidate')
    protocol = json.loads(command([str(root / 'k206-tftp-isolated/test-tftp-qrtr-arm64'), '0', 'pass'], 'production-qrtr', timeout=40).stdout)
    assert protocol['qrtr_transactions'] == 13 and protocol['readback_bytes_compared'] == 20435
    test_dir = cache / 'samurai-validation206'
    assert test_dir.resolve().parent == cache.resolve()
    (test_dir / 'work.tmp').unlink(); test_dir.rmdir()
    assert alive(rmtfs_pid, rmtfs_start)
    assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
    assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
    command(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-sources-after')
    after = subprocess.check_output(['dmesg'])
    (out / 'dmesg-after-private.txt').write_bytes(after)
    faults = {k: after.count(v) - before.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert all(v == 0 for v in faults.values())
    assert candidate.poll() is None and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    result = dict(stage=206, new_tftp_server_installed_and_running=True, helper_prepares_32m_private_tmpfs_on_boot=True, actual_production_qrtr=protocol, protocol_test_files_removed=True, nv_sources_unchanged=True, rmtfs_same_process=True, modem_owner_unchanged=True, modem_restarted=False, gps_started=False, fault_delta=faults, taint=int(Path('/proc/sys/kernel/tainted').read_text()), rebooted=False, partitions_flashed=[], binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
except Exception:
    (out / 'failure-private.txt').write_text(traceback.format_exc())
    if candidate is not None and candidate.poll() is None:
        candidate.terminate(); candidate.wait(timeout=8)
    if stopped:
        replace(out / 'samurai-tqftpserv-original', binary)
        replace(out / 'samurai-wifi-original.sh', helper)
        start_service(environment, 'rollback')
    raise
finally:
    bus.close()
