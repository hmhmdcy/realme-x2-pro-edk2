from pathlib import Path
import configparser
import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile

os.umask(0o077)
out = Path('/var/lib/samurai/k185-deploy')
out.mkdir(mode=0o700)
assert os.uname().version.startswith('#183 ')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k185-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
comparison = json.loads(Path('/var/lib/samurai/k185-load/scan-comparison.json').read_text())
assert comparison['transport_fix_passed'] and comparison['preexisting_pairing_keys_unchanged']
baseline = json.loads(Path('/var/lib/samurai/k185-baseline/summary.json').read_text())
build = json.loads(Path('/var/lib/samurai/k185-tools/module-build-validation.json').read_text())
directory = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth'
target = directory / 'hci_uart.ko'
candidate = Path('/var/lib/samurai/k185-tools/hci_uart-k185-private.ko')
before = target.read_bytes()
assert hashlib.sha256(before).hexdigest() == baseline['original_hci_uart_sha256']
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == build['candidate_sha256']
old_dep = set(subprocess.check_output(['modinfo', '-F', 'depends', str(target)], text=True).strip().split(','))
new_dep = set(subprocess.check_output(['modinfo', '-F', 'depends', str(candidate)], text=True).strip().split(','))
assert new_dep == old_dep
for name, digest in baseline['sibling_modules_sha256'].items():
    assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
(out / 'hci_uart-original-private.ko').write_bytes(before)
(out / 'boot-id-private.txt').write_bytes(boot)
config = Path('/etc/bluetooth/main.conf')
config_current = config.read_bytes()
original_config = Path('/var/lib/samurai/k185-policy/main.conf-before-private').read_bytes()
(out / 'temporary-policy-private.conf').write_bytes(config_current)


def command(args, name, timeout=30):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (name + '-private.log')).write_bytes(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError(name + ' failed')


def replace(path, data):
    original = path.stat()
    fd, name = tempfile.mkstemp(prefix='.k185-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, original.st_mode & 0o777)
        os.chown(name, original.st_uid, original.st_gid)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


try:
    command(['rc-service', 'bluetooth', 'stop'], 'service-stop')
    command(['/usr/sbin/samurai-bluetooth', 'stop'], 'module-stop')
    assert not Path('/sys/module/hci_uart').exists()
    replace(target, candidate.read_bytes())
    replace(config, original_config)
    command(['rc-service', 'bluetooth', 'start'], 'default-service-start', timeout=35)
    counter = Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls')
    assert counter.is_file() and int(counter.read_text()) >= 2
    raw = candidate.read_bytes()
    off = struct.unpack_from('<Q', raw, 40)[0]
    size, count, idx = struct.unpack_from('<HHH', raw, 58)
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * size) for i in range(count)]
    strings = raw[rows[idx][4]:rows[idx][4] + rows[idx][5]]
    note = next(r for r in rows if strings[r[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id')
    assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == raw[note[4]:note[4] + note[5]]
    assert target.read_bytes() == candidate.read_bytes()
    assert config.read_bytes() == original_config
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    report = {'stage': 185, 'kernel_build': 183, 'runtime_generation': 132,
              'candidate_sha256': build['candidate_sha256'],
              'original_module_sha256': baseline['original_hci_uart_sha256'],
              'default_module_path_updated': True, 'default_service_reload_used_installed_candidate': True,
              'loaded_build_id_matches': True, 'dependencies_unchanged': True,
              'sibling_modules_unchanged': True, 'original_bluez_config_restored': True,
              'pulse_rx_nuls_after_reload': int(counter.read_text()),
              'cold_boot_or_suspend_verified': False, 'taint': 0}
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
except BaseException:
    subprocess.run(['rc-service', 'bluetooth', 'stop'], capture_output=True, timeout=25)
    subprocess.run(['/usr/sbin/samurai-bluetooth', 'stop'], capture_output=True, timeout=25)
    replace(target, before)
    replace(config, original_config)
    p = subprocess.run(['rc-service', 'bluetooth', 'start'], capture_output=True, timeout=35)
    (out / 'rollback-private.log').write_bytes(p.stdout + p.stderr)
    (out / 'rollback-exit.txt').write_text(str(p.returncode) + '\n')
    raise
