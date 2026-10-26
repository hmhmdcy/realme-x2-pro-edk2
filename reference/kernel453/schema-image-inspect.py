"""Read-only audit of the pinned k363 Image source and present build cache."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_image_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
build = storage.mount.mounted_build()
source = build.parent / 'source354'
private = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
record = json.loads((HERE.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
base = record['commit']
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], env=env)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

head = git('rev-parse', 'HEAD').decode().strip()
status = git('status', '--porcelain').decode()
git('cat-file', '-e', base + '^{commit}')
changes = git('diff', '--name-status', base, head).decode().splitlines()
core = 'drivers/media/v4l2-core/v4l2-device.c'
baseline_core = git('show', base + ':' + core)
current_core = (source / core).read_bytes()
cache = {}
for relative in ['.config', 'Module.symvers', 'modules.order', 'arch/arm64/boot/Image', 'vmlinux',
                 'vmlinux.o', '.vmlinux.cmd', '.vmlinux.o.cmd', 'vmlinux.a', '.vmlinux.a.cmd',
                 'drivers/media/v4l2-core/v4l2-device.o', 'drivers/media/v4l2-core/.v4l2-device.o.cmd',
                 'drivers/media/v4l2-core/built-in.a', 'drivers/media/built-in.a',
                 'include/config/kernel.release', 'include/config/auto.conf',
                 'include/generated/autoconf.h', 'include/generated/utsrelease.h',
                 'usr/initramfs_data.cpio', 'usr/initramfs_data.cpio.gz',
                 'source', 'Makefile']:
    p = build / relative
    row = dict(exists=p.exists(), symlink=p.is_symlink())
    if p.exists():
        row.update(bytes=p.stat().st_size, resolved=str(p.resolve()))
        if p.is_file() and (relative in record['artifacts'] or p.stat().st_size < 2_000_000):
            row['sha256'] = sha(p.read_bytes())
        if relative in record['artifacts']:
            row['matches_k363_receipt'] = row.get('sha256') == record['artifacts'][relative]['sha256']
        if relative.endswith('.cmd') or relative in ['include/config/kernel.release', 'Makefile']:
            (private / ('image-cache-' + relative.replace('/', '_') + '-private.txt')).write_bytes(p.read_bytes())
    cache[relative] = row

config = (build / '.config').read_text()
selected_config = [line for line in config.splitlines() if line.startswith((
    'CONFIG_LOCALVERSION', 'CONFIG_INITRAMFS_SOURCE', 'CONFIG_MEDIA_SUPPORT=',
    'CONFIG_VIDEO_DEV=', 'CONFIG_VIDEO_V4L2=', 'CONFIG_IKCONFIG=', 'CONFIG_CC_VERSION_TEXT=',
    'CONFIG_MODULE_REL_CRCS=', 'CONFIG_MODVERSIONS=', 'CONFIG_LTO', 'CONFIG_RANDSTRUCT',
    'CONFIG_DEBUG_INFO_BTF=', 'CONFIG_KALLSYMS=', 'CONFIG_BUILD_SALT='))]
initramfs = next(line.split('=', 1)[1].strip('"') for line in config.splitlines() if line.startswith('CONFIG_INITRAMFS_SOURCE='))
payload = Path(initramfs)
report = dict(stage=453, scope='read-only feasibility audit; no make, checkout, SDK or phone action',
    k363_commit=base, current_source_head=head, current_source_clean=not status,
    pinned_commit_locally_available=True, changed_paths_since_k363=changes,
    core_path=core, k363_core_sha256=sha(baseline_core), current_core_sha256=sha(current_core),
    core_unchanged_since_k363=baseline_core == current_core, cache=cache,
    selected_config=selected_config, initramfs_source_exists=payload.exists(),
    initramfs_source_is_directory=payload.is_dir(),
    current_453_source_view_is_not_pinned_k363=True,
    safe_incremental_image_needs_new_pinned_private_source_and_writable_cache_copy=True,
    complete_cached_object_set_not_attested_as_k363=True,
    absolute_source_and_output_paths_in_cached_commands=True,
    safe_image_target_may_rebuild_broader_dependencies=True,
    only_single_object_rebuild_guaranteed=False, actual_image_build_performed=False,
    shared_source_or_build_modified=False, sdk_or_phone_accessed=False)
(HERE / 'schema-image-inspection.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['cache']}, indent=2))
print(json.dumps({'cache': cache}, indent=2))
