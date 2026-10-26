"""Install a reversible candidate before unload so automatic reload uses it."""
from pathlib import Path
import hashlib
import json
import os
import stat
import struct
import subprocess
import tempfile
import time

os.umask(0o077)
out = Path('/var/lib/samurai/k186-load-fastrpc-r2')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
target = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/misc/fastrpc.ko'
original = target.read_bytes()
assert original == Path('/var/lib/samurai/k186-load-fastrpc/fastrpc-original-private.ko').read_bytes()
candidate = Path('/var/lib/samurai/k186-tools/fastrpc-k186-private.ko').read_bytes()
build = json.loads(Path('/var/lib/samurai/k186-tools/fastrpc-module-build-validation.json').read_text())
tests = json.loads(Path('/var/lib/samurai/k186-tools/fastrpc-host-tests-validation.json').read_text())
assert tests['asan_ubsan_passed'] and tests['all_negative_controls_detected']
assert hashlib.sha256(candidate).hexdigest() == build['candidate_sha256']
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'fastrpc-original-private.ko').write_bytes(original)
def note(raw):
    off = struct.unpack_from('<Q', raw, 40)[0]
    size, count, idx = struct.unpack_from('<HHH', raw, 58)
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, off+i*size) for i in range(count)]
    strings = raw[rows[idx][4]:rows[idx][4]+rows[idx][5]]
    row = next(r for r in rows if strings[r[0]:].split(b'\0',1)[0] == b'.note.gnu.build-id')
    return raw[row[4]:row[4]+row[5]]
module = Path('/sys/module/fastrpc')
assert (module / 'notes/.note.gnu.build-id').read_bytes() == note(original)
assert (module / 'refcnt').read_text().strip() == '0'
old_dep = subprocess.check_output(['modinfo','-F','depends',str(target)],text=True).strip()
new_dep = subprocess.check_output(['modinfo','-F','depends','/var/lib/samurai/k186-tools/fastrpc-k186-private.ko'],text=True).strip()
assert set(old_dep.split(',')) == set(new_dep.split(','))

def replace(data):
    st = target.stat()
    fd, name = tempfile.mkstemp(prefix='.k186-', dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.chmod(name, st.st_mode & 0o777)
        os.chown(name, st.st_uid, st.st_gid)
        os.replace(name,target)
    finally:
        if os.path.exists(name): os.unlink(name)

def command(args,name):
    p = subprocess.run(args,capture_output=True,timeout=25)
    (out / name).write_bytes(p.stdout+p.stderr)
    assert p.returncode == 0, name

try:
    replace(candidate)
    command(['rmmod','fastrpc'],'old-unload-private.txt')
    # Either the observed automatic loader or this normal modprobe can load it.
    command(['modprobe','fastrpc'],'default-module-load-private.txt')
    deadline = time.monotonic()+5
    while time.monotonic()<deadline:
        if module.exists() and (module / 'notes/.note.gnu.build-id').read_bytes() == note(candidate): break
        time.sleep(.1)
    assert (module / 'notes/.note.gnu.build-id').read_bytes() == note(candidate)
    assert target.read_bytes() == candidate
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
    report = dict(stage=186,kernel_build=183,taint=0,default_module_candidate_under_test=True,
        loaded_build_id_matches=True,candidate_module_sha256=build['candidate_sha256'],
        original_module_sha256=hashlib.sha256(original).hexdigest(),dependencies_unchanged=True,
        original_backup_kept=True,runtime_sensor_cycles_verified=False,no_force_unload=True,
        before_first_slpi_start=True)
    (out / 'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
except BaseException:
    replace(original)
    (out / 'original-file-restored-after-failure.txt').write_text('yes\n')
    raise
