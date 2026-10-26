"""Read/hash existing thin-archive inputs; no link, compile or object test."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
spec = importlib.util.spec_from_file_location('gauge_plan_link_storage284', REF / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mounted_build()
source = build.parent / 'source354'
previous = json.loads((HERE / 'cache-inventory.json').read_bytes())
changed = [line.split('\t')[-1] for line in previous['source_delta']]
config_changed = list(previous['current_config_assignments_delta'])
environment = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def digest(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def command(argv):
    return subprocess.check_output(argv, text=True, env=environment)


members = command(['aarch64-linux-gnu-ar', 't', str(build / 'vmlinux.a')]).splitlines()
inventory, missing, source_intersections, config_intersections = {}, [], [], []
total = 0
for name in members:
    member = build / name
    assert member.resolve().is_relative_to(build.resolve()), name
    relative = str(member.relative_to(build))
    if not member.is_file():
        missing.append(relative)
        continue
    total += member.stat().st_size
    cmd = member.parent / ('.' + member.name + '.cmd')
    row = {'bytes': member.stat().st_size, 'sha256': digest(member),
           'command_sha256': digest(cmd) if cmd.is_file() else None}
    if cmd.is_file():
        text = cmd.read_text()
        hit = [path for path in changed if str(source / path) in text]
        if hit:
            source_intersections.append({'object': relative, 'changed_source_dependencies': hit})
        hit = [key for key in config_changed if 'include/config/' + key.removeprefix('CONFIG_') in text]
        if hit:
            config_intersections.append({'object': relative, 'changed_config_dependencies': hit})
    inventory[relative] = row
extra = {}
for p in sorted(build.iterdir()):
    if 'vmlinux' in p.name or p.name in ['built-in-fixup.a', '.built-in-fixup.a.cmd',
                                         '.built-in.a.cmd', 'vmlinux.lds']:
        if p.is_file():
            row = {'bytes': p.stat().st_size, 'sha256': digest(p)}
            if p.suffix == '.cmd':
                row['text'] = p.read_text()
            extra[p.name] = row
for rel in ['arch/arm64/kernel/vmlinux.lds', 'include/generated/utsversion.h',
            'include/generated/uapi/linux/version.h', 'scripts/link-vmlinux.sh',
            'scripts/kallsyms', 'scripts/sorttable', 'tools/bpf/resolve_btfids/resolve_btfids',
            'drivers/firmware/efi/libstub/lib.a']:
    p = build / rel
    if p.is_file():
        extra[rel] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
versions = {}
for binary in ['aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ld', 'aarch64-linux-gnu-objcopy',
               'aarch64-linux-gnu-ar', 'pahole']:
    p = shutil.which(binary)
    versions[binary] = {'path': p, 'sha256': digest(Path(p).resolve()) if p else None,
                        'version': command([p, '--version']).splitlines()[0] if p else None}
rust = []
for p in sorted(Path('/home/cy122/.rustup/toolchains').glob('*/bin/rustc')):
    rust.append({'path': str(p), 'version': command([str(p), '-Vv']), 'sha256': digest(p)})
scripts = {}
for rel in ['scripts/Makefile.vmlinux_a', 'scripts/Makefile.vmlinux_o', 'scripts/Makefile.vmlinux',
            'scripts/link-vmlinux.sh', 'Makefile', 'arch/arm64/Makefile', 'arch/arm64/boot/Makefile']:
    p = source / rel
    raw = p.read_bytes()
    original = subprocess.check_output(['git', '-C', str(source), 'show', previous['image363_commit'] + ':' + rel],
                                        env=environment)
    assert raw == original, rel
    scripts[rel] = {'sha256': hashlib.sha256(raw).hexdigest(), 'equal_ba61': True}
    if rel in ['scripts/Makefile.vmlinux_a', 'scripts/Makefile.vmlinux_o', 'scripts/Makefile.vmlinux']:
        scripts[rel]['text'] = raw.decode()
result = {'member_count': len(members), 'unique_member_count': len(inventory), 'members': inventory,
          'member_total_bytes': total, 'missing_members': missing,
          'changed_source_dependencies': source_intersections,
          'changed_rust_config_dependencies': config_intersections, 'link_cache': extra,
          'toolchains': versions, 'rust_toolchains': rust, 'build_scripts': scripts,
          'bq_member_count': sum(name.endswith('/bq27xxx_battery.o') for name in inventory),
          'build_link_or_object_test_executed': False, 'sdk_or_device_accessed': False,
          'shared_source_build_written': False}
(HERE / 'link-inputs.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['member_count', 'unique_member_count', 'member_total_bytes',
    'missing_members', 'changed_source_dependencies', 'changed_rust_config_dependencies', 'bq_member_count',
    'toolchains', 'rust_toolchains']}), flush=True)
