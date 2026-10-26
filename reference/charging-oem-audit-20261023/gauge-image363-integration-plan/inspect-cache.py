"""Read existing cache/receipts only, apart from authorized old-volume remount."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
VOLUME = Path('/mnt/samurai-full282')
OLD = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
spec = importlib.util.spec_from_file_location('gauge_plan_mount284', REF / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
before = [r for r in Path('/proc/self/mountinfo').read_text().splitlines() if r.split()[4] == str(VOLUME)]
build = storage.mounted_build()
after = [r for r in Path('/proc/self/mountinfo').read_text().splitlines() if r.split()[4] == str(VOLUME)]
source = VOLUME / 'source354'
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], env=env)


def config(raw):
    return {line.split('=', 1)[0]: line.split('=', 1)[1] for line in raw.decode().splitlines()
            if line.startswith('CONFIG_')}


head = git('rev-parse', 'HEAD').decode().strip()
image = Path('/mnt/e/edk2-samurai-out/kernel363/Image-k363-private')
raw = image.read_bytes()
assert digest(image) == '15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
start = raw.index(b'IKCFG_ST') + 8
original_config = gzip.decompress(raw[start:raw.index(b'IKCFG_ED', start)])
assert hashlib.sha256(original_config).hexdigest() == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
a, b = config(original_config), config((build / '.config').read_bytes())
config_delta = {k: {'Image363': a.get(k, 'n'), 'current': b.get(k, 'n')}
                for k in a.keys() | b.keys() if a.get(k, 'n') != b.get(k, 'n')}
paths = ['.config', 'Module.symvers', 'vmlinux', 'vmlinux.o', 'vmlinux.a',
         'arch/arm64/boot/Image', 'drivers/power/supply/bq27xxx_battery.o',
         'drivers/power/supply/.bq27xxx_battery.o.cmd', 'drivers/power/supply/built-in.a',
         'drivers/built-in.a', 'built-in.a', 'include/generated/compile.h',
         'include/generated/autoconf.h', 'include/generated/utsrelease.h',
         'include/config/auto.conf', 'include/config/kernel.release', '.version',
         '.vmlinux.cmd', '.vmlinux.o.cmd', '.vmlinux.a.cmd',
         'arch/arm64/boot/.Image.cmd', 'usr/initramfs_data.cpio', 'usr/initramfs_inc_data',
         'usr/built-in.a', 'usr/initramfs_data.o', 'usr/.initramfs_data.o.cmd',
         'usr/.initramfs_inc_data.cmd', 'vmlinux.symvers', '.tmp_vmlinux1', '.tmp_vmlinux2',
         '.tmp_vmlinux.kallsyms1', '.tmp_vmlinux.kallsyms2', 'System.map']
files, commands = {}, {}
for relative in paths:
    p = build / relative
    if p.is_file():
        files[relative] = {'bytes': p.stat().st_size, 'sha256': digest(p), 'symlink': p.is_symlink()}
        if p.suffix == '.cmd' or relative.endswith('compile.h') or relative.endswith('kernel.release'):
            commands[relative] = p.read_text()
    else:
        files[relative] = {'missing': True}
result = {'mount_before': before, 'mount_after': after,
          'head': head, 'image363_commit': OLD,
          'source_delta': git('diff-tree', '--no-commit-id', '--name-status', '-r', OLD, head).decode().splitlines(),
          'worktree_tracked_delta': git('diff', '--no-ext-diff', '--no-textconv', '--name-status', 'HEAD').decode().splitlines(),
          'image363_config_sha256': hashlib.sha256(original_config).hexdigest(),
          'current_config_assignments_delta': config_delta,
          'build_files': files, 'command_cache': commands,
          'volume_entries': sorted(p.name for p in VOLUME.iterdir()),
          'free_bytes_volume': os.statvfs(VOLUME).f_bavail * os.statvfs(VOLUME).f_frsize,
          'free_bytes_home': os.statvfs('/home/cy122').f_bavail * os.statvfs('/home/cy122').f_frsize,
          'original_epoch': int(git('show', '-s', '--format=%ct', OLD)),
          'build_or_object_test_executed': False, 'sdk_or_device_accessed': False,
          'shared_source_build_written': False}
(HERE / 'cache-inventory.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'head': head, 'source_delta': result['source_delta'], 'config_delta': config_delta,
                  'files': files, 'entries': result['volume_entries']}), flush=True)
