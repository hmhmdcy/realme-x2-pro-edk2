"""Atomically stage the verified module for the next boot; keep the old driver live."""
from pathlib import Path
import hashlib
import json
import os
import stat
import struct
import subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
before = root / 'k228-baseline'
out = root / 'k228-module-install'
assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (before / 'boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
build = json.loads((root / 'k228-tools/fastrpc-build-validation.json').read_text())
proof = build['results']['candidate']
candidate = (root / 'k228-tools/fastrpc-candidate-private.ko').read_bytes()
digest = lambda b: hashlib.sha256(b).hexdigest()
assert digest(candidate) == proof['module_sha256'] == '7ca5d442fb8351f841dcae3d16e4f981d9b08e7326b42c674f7ceaf4f08bdc0a'
assert len(candidate) == 50216
tree = Path('/usr/lib/modules') / os.uname().release
relative = 'kernel/drivers/misc/fastrpc.ko'
module = tree / relative
old = module.read_bytes()
assert old == (before / 'fastrpc-original-private.ko').read_bytes()
old_meta = module.stat()
loaded = Path('/sys/module/fastrpc/notes/.note.gnu.build-id')
assert loaded.read_bytes() == (before / 'fastrpc-loaded-note-private.bin').read_bytes()
old_vm = subprocess.check_output(['modinfo', '-F', 'vermagic', str(module)], text=True).strip()
new_vm = subprocess.check_output(['modinfo', '-F', 'vermagic', str(root / 'k228-tools/fastrpc-candidate-private.ko')], text=True).strip()
assert old_vm == new_vm == proof['vermagic']
assert subprocess.check_output(['modinfo', '-F', 'depends', str(module)]) == subprocess.check_output(['modinfo', '-F', 'depends', str(root / 'k228-tools/fastrpc-candidate-private.ko')])
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes((before / 'boot-id-private.txt').read_bytes())
(out / 'fastrpc-original-private.ko').write_bytes(old)
state_path = out / 'transaction-state-private.json'


def state(phase):
    state_path.write_text(json.dumps(dict(stage=228, state=phase, runtime_reloaded=False, transition_sent=False)) + '\n')


state('prepared')
temp = module.with_name('.fastrpc.ko.k228-new')
fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IMODE(old_meta.st_mode))
try:
    with os.fdopen(fd, 'wb', closefd=False) as output:
        output.write(candidate)
        output.flush()
    os.fchown(fd, old_meta.st_uid, old_meta.st_gid)
    os.fchmod(fd, stat.S_IMODE(old_meta.st_mode))
    os.fsync(fd)
finally:
    os.close(fd)
assert temp.read_bytes() == candidate
os.replace(temp, module)
parent = os.open(module.parent, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(parent)
finally:
    os.close(parent)
state('file_replaced')
inventory = json.loads((before / 'module-inventory-private.json').read_text())
expected = dict(inventory)
expected[relative] = digest(candidate)
actual = {str(p.relative_to(tree)): digest(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
assert actual == expected and len(actual) == 786
(out / 'module-inventory-after-private.json').write_text(json.dumps(actual, indent=2) + '\n')
(out / 'module-tree-after.sha256').write_text(''.join(v + '  ' + n + '\n' for n, v in sorted(actual.items())))
assert loaded.read_bytes() == (before / 'fastrpc-loaded-note-private.bin').read_bytes()
assert Path('/lib/apk/db/installed').read_bytes() == (before / 'installed-before-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
state('verified')
report = dict(stage=228, candidate_installed_for_next_boot=True, running_driver_remains_original=True,
              candidate_sha256=digest(candidate), candidate_bytes=len(candidate), unrelated785_module_files_unchanged=True,
              module_tree_count=786, vermagic_matches=True, dependency_names_unchanged=True,
              original_backed_up_twice=True, package_database_unchanged=True, no_unload_or_reload=True,
              taint=0, transition_sent=False)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
