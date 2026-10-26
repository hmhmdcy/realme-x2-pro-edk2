"""Create only private456 source and writable O; preserve all shared inputs."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('preflight456', HERE/'preflight.py')
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
SHARED = pre.storage.mount.mounted_build()
PRIVATE = pre.PRIVATE
DATA = json.loads((PRIVATE/'preflight-private.json').read_text())
ISOLATED = SHARED.parent/'kernel456-core0064-private'
SOURCE = ISOLATED/'source'
BUILD = ISOLATED/'O'
COMMIT = pre.COMMIT


def main():
    assert not ISOLATED.exists(), 'Inspect existing private preparation; never reset it blindly'
    assert {path: pre.sha(Path(path)) for path in DATA['shared_before']} == DATA['shared_before']
    assert shutil.disk_usage(SHARED).free > DATA['required_bytes_including_2gib_reserve']
    ISOLATED.mkdir(mode=0o700)
    logfile = PRIVATE/'prepare-source-r1-private.log'
    with logfile.open('xb') as log:
        def command(args, cwd=None):
            result = subprocess.run(list(map(str, args)), cwd=cwd, env=pre.ENV, stdout=log, stderr=subprocess.STDOUT)
            assert result.returncode == 0, args
        command(['git', 'clone', '--shared', '--no-checkout', '--no-hardlinks', DATA['source'], SOURCE])
        command(['git', '-C', SOURCE, 'checkout', '--detach', COMMIT])
        git = lambda *args: pre.run(['git', '-C', SOURCE, *args])
        assert git('rev-parse', 'HEAD') == COMMIT and not git('status', '--porcelain')
        core = SOURCE/'drivers/media/v4l2-core/v4l2-device.c'
        original = core.read_bytes()
        assert pre.sha(core) == '3cb62dc7339cdf3d8140e30b9b1dddcbab102c85dec2d11dac979fe9ff3875e7'
        patch = HERE.parent/'kernel453/0064-media-v4l2-core-clear-devnode-before-subdev-release.patch'
        command(['patch', '--dry-run', '--batch', '--forward', '--fuzz=0', '-p1', '-i', patch], SOURCE)
        command(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', patch], SOURCE)
        old = b'\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);\n\tsd->devnode = NULL;'
        new = b'\tsd->devnode = NULL;\n\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);'
        assert original.count(old) == 1 and core.read_bytes() == original.replace(old, new)
        assert git('diff', '--name-only') == 'drivers/media/v4l2-core/v4l2-device.c'
        command(['git', '-C', SOURCE, 'diff', '--check'])
        assert shutil.disk_usage(SHARED).free > DATA['sizes']['build'] + 4*1024**3
        print(json.dumps(dict(stage=456, source_pinned=True, patch_only_core=True, copying_writable_O=True)), flush=True)
        command(['cp', '-a', '--reflink=auto', SHARED, BUILD])
    log = logfile.read_text(errors='replace')
    assert 'with fuzz' not in log.lower() and '(offset' not in log.lower()
    removed = []
    # Cached output links must not write into any shared source/O.
    for path in list(BUILD.rglob('*')):
        if path.is_symlink():
            removed.append(dict(path=str(path.relative_to(BUILD)), target=os.readlink(path)))
            path.unlink()
    for relative in ['Makefile', '.config.old', 'include/config/auto.conf', 'include/config/auto.conf.cmd',
                     'include/generated/autoconf.h', 'include/generated/rustc_cfg',
                     'include/config/kernel.release', 'include/generated/utsrelease.h']:
        path = BUILD/relative
        if path.exists():
            assert path.is_file() and path.resolve().is_relative_to(BUILD.resolve())
            path.unlink()
    (BUILD/'.config').write_bytes((PRIVATE/'config363-from-image-private').read_bytes())
    assert pre.sha(BUILD/'.config') == DATA['original']['artifacts']['.config']['sha256']
    assert (BUILD/'vmlinux.o').is_file() and not (BUILD/'vmlinux.o').is_symlink()
    assert (BUILD/'vmlinux.o').stat().st_ino != (SHARED/'vmlinux.o').stat().st_ino
    assert {path: pre.sha(Path(path)) for path in DATA['shared_before']} == DATA['shared_before']
    assert pre.run(['git', '-C', DATA['source'], 'rev-parse', 'HEAD']) == DATA['source_head_before']
    assert shutil.disk_usage(SHARED).free > 4*1024**3
    report = dict(stage=456, commit=COMMIT, source=str(SOURCE), output=str(BUILD),
                  actual_core_sha256=pre.sha(core), patch_sha256=pre.sha(patch),
                  changed_source_paths=['drivers/media/v4l2-core/v4l2-device.c'],
                  exact_0064_zero_fuzz_offset=True, other39_head_changes_excluded=True,
                  original_config_restored_exactly=True, independent_private_git_index=True,
                  full_writable_O_copy=True, no_shared_vmlinux_object_link=True,
                  removed_cached_symlinks=removed, shared_source_index_and_build_unchanged=True,
                  free_bytes_after_preparation=shutil.disk_usage(SHARED).free,
                  sdk_or_phone_accessed=False, image_not_built_yet=True, passed=True)
    (PRIVATE/'source-preparation-private.json').write_text(json.dumps(report, indent=2)+'\n')
    (HERE/'source-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
