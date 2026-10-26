"""Read final-link closure; no compiler/linker/test invocation."""
from pathlib import Path
import fcntl
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
spec = importlib.util.spec_from_file_location('gauge_final_storage284', REF / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
lock_mode = 'original helper open-a'
try:
    build = storage.mounted_build()
except PermissionError:
    # Linux protected_regular rejects O_CREAT for root on an existing uid1000
    # file in sticky /run/lock. Use the SAME lock, without O_CREAT; never alter
    # ownership/permissions or skip its flock. Mount validation stays original.
    lock = Path('/run/lock/samurai-full282-mount.lock')
    info = lock.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid in (0, 1000)
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        build = storage._mounted_build_locked()
    finally:
        os.close(fd)
    lock_mode = 'same existing lock O_RDWR without O_CREAT + same flock/original mount validation'
source = build.parent / 'source354'


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


library = build / 'drivers/firmware/efi/libstub/lib.a'
members = subprocess.check_output(['aarch64-linux-gnu-ar', 't', str(library)], text=True).splitlines()
rows = {}
for name in members:
    p = Path(name)
    if not p.is_absolute():
        p = library.parent / p
    assert p.resolve().is_relative_to(build.resolve()), name
    rows[str(p.relative_to(build))] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
script = source / 'scripts/link-vmlinux.sh'
assert digest(script) == 'b363d8a74847ab4192ae5aa5fcb6b7c5a2e8c7706188e61a06da94a6b006b68b'
text = script.read_text()
selected = set()
lines = text.splitlines()
for i, line in enumerate(lines):
    if any(term in line for term in ['version-timestamp', 'VMLINUX_O', 'KBUILD_LDS',
                                    'vmlinux_link()', 'vmlinux_link ', 'scripts/Makefile']):
        selected.update(range(max(0, i - 3), min(len(lines), i + 11)))
extra = {}
for name in ['init/version-timestamp.o', 'init/.version-timestamp.o.cmd',
             'include/generated/utsversion.h', 'arch/arm64/tools/vmlinux.arch.o',
             '.vmlinux.export.o', '.vmlinux.export.c', '.vmlinux.export.o.cmd',
             '.vmlinux.export.c.cmd', 'scripts/mod/modpost']:
    p = build / name
    if p.is_file():
        row = {'bytes': p.stat().st_size, 'sha256': digest(p)}
        if p.suffix == '.cmd' or name.endswith('utsversion.h'):
            row['text'] = p.read_text()
        extra[name] = row
    else:
        extra[name] = {'missing': True}
result = {'same_lock_mode': lock_mode, 'libstub_members': rows,
          'libstub_members_count': len(rows), 'final_link_script_sha256': digest(script),
          'final_link_script_fragment': '\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)),
          'final_link_extra': extra, 'build_link_test_executed': False,
          'sdk_or_phone_accessed': False, 'shared_source_build_written': False}
(HERE / 'final-link-inputs.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
