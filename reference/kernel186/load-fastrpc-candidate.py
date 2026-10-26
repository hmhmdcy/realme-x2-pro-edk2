"""Temporarily load the candidate only before the new boot's first SLPI start."""
from pathlib import Path
import hashlib
import json
import os
import stat
import struct
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k186-load-fastrpc')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
log = subprocess.check_output(['dmesg'], text=True)
assert '2400000.remoteproc: remote processor slpi is now up' not in log
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'dmesg-before-private.txt').write_text(log)
module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/misc/fastrpc.ko'
original = module.read_bytes()
(out / 'fastrpc-original-private.ko').write_bytes(original)
candidate = Path('/var/lib/samurai/k186-tools/fastrpc-k186-private.ko')
build = json.loads(Path('/var/lib/samurai/k186-tools/fastrpc-module-build-validation.json').read_text())
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == build['candidate_sha256']


def note(raw):
    off = struct.unpack_from('<Q', raw, 40)[0]
    size, count, idx = struct.unpack_from('<HHH', raw, 58)
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * size) for i in range(count)]
    strings = raw[rows[idx][4]:rows[idx][4] + rows[idx][5]]
    row = next(r for r in rows if strings[r[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id')
    return raw[row[4]:row[4] + row[5]]


had_original_loaded = Path('/sys/module/fastrpc').exists()
if had_original_loaded:
    assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes() == note(original)
devices = {p.stat().st_rdev for p in Path('/dev').glob('fastrpc-*') if stat.S_ISCHR(p.stat().st_mode)}
users = []
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        for fd in (process / 'fd').iterdir():
            try:
                value = fd.stat()
                if stat.S_ISCHR(value.st_mode) and value.st_rdev in devices:
                    users.append({'pid': process.name, 'fd': fd.name})
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
(out / 'existing-fastrpc-fds-private.json').write_text(json.dumps(users, indent=2) + '\n')
assert not users
if had_original_loaded:
    assert Path('/sys/module/fastrpc/refcnt').read_text().strip() == '0'


def command(args, name):
    p = subprocess.run(args, capture_output=True, timeout=30)
    (out / name).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, name


try:
    if had_original_loaded:
        command(['rmmod', 'fastrpc'], 'old-module-unload-private.txt')
    assert not Path('/sys/module/fastrpc').exists()
    command(['insmod', str(candidate)], 'candidate-insmod-private.txt')
    assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes() == note(candidate.read_bytes())
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert module.read_bytes() == original
    remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
              for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
    assert remote == {'slpi': 'offline', 'modem': 'running', 'adsp': 'running'}
    report = dict(stage=186, kernel_build=183, taint=0, loaded_build_id_matches=True,
        candidate_module_sha256=build['candidate_sha256'], original_module_sha256=hashlib.sha256(original).hexdigest(),
        no_existing_fastrpc_fds=True, default_module_file_unchanged=True,
        before_first_slpi_start=True, remoteproc=remote, no_force_unload=True)
    report['original_module_was_loaded'] = had_original_loaded
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
except BaseException:
    if not Path('/sys/module/fastrpc').exists():
        p = subprocess.run(['modprobe', 'fastrpc'], capture_output=True, timeout=30)
        (out / 'rollback-private.txt').write_bytes(p.stdout + p.stderr)
    raise
