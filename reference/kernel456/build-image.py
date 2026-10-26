"""Request only Image in private456; real time, private O, bounded disk reserve."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('preflight456', HERE/'preflight.py')
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
SHARED = pre.storage.mount.mounted_build()
PRIVATE = pre.PRIVATE
DATA = json.loads((PRIVATE/'preflight-private.json').read_text())
STATE = json.loads((PRIVATE/'source-preparation-private.json').read_text())
SOURCE = Path(STATE['source'])
BUILD = Path(STATE['output'])
RELEASE = DATA['original']['release']
RESERVE = 2*1024**3


def main():
    assert STATE['passed'] and SOURCE.parent == BUILD.parent == SHARED.parent/'kernel456-core0064-private'
    assert pre.run(['git', '-C', SOURCE, 'rev-parse', 'HEAD']) == pre.COMMIT
    assert pre.run(['git', '-C', SOURCE, 'diff', '--name-only']) == 'drivers/media/v4l2-core/v4l2-device.c'
    assert pre.sha(SOURCE/'drivers/media/v4l2-core/v4l2-device.c') == STATE['actual_core_sha256']
    assert pre.sha(BUILD/'.config') == DATA['original']['artifacts']['.config']['sha256']
    assert {path: pre.sha(Path(path)) for path in DATA['shared_before']} == DATA['shared_before']
    assert (BUILD/'vmlinux.o').is_file() and not (BUILD/'vmlinux.o').is_symlink()
    assert (BUILD/'vmlinux.o').stat().st_ino != (SHARED/'vmlinux.o').stat().st_ino
    assert shutil.disk_usage(SHARED).free > 4*1024**3
    tmp = BUILD.parent/'tmp'; tmp.mkdir(exist_ok=True)
    env = dict(os.environ, PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],
               RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='456',
               KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai', TMPDIR=str(tmp))
    for key in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG', 'KBUILD_BUILD_TIMESTAMP',
                'SOURCE_DATE_EPOCH', 'KCFLAGS', 'KCPPFLAGS', 'KBUILD_EXTRA_SYMBOLS']:
        env.pop(key, None)
    command = ['make', '-C', str(SOURCE), 'O='+str(BUILD), 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
               'LOCALVERSION=+', 'KERNELRELEASE='+RELEASE, '-j4', 'W=1', 'Image']
    attempt = 1
    while (PRIVATE/f'image-build-r{attempt}-private.log').exists():
        attempt += 1
    logpath = PRIVATE/f'image-build-r{attempt}-private.log'
    marker = PRIVATE/'image-build-state-private.json'
    begun = time.monotonic()
    free_min = shutil.disk_usage(SHARED).free
    terminated_for_space = False
    with logpath.open('xb') as output:
        child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=output,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps(dict(stage=456, attempt=attempt, pid=child.pid, only_target='Image', started=True)), flush=True)
        while child.poll() is None:
            free = shutil.disk_usage(SHARED).free
            free_min = min(free_min, free)
            state = dict(stage=456, attempt=attempt, worker_pid=os.getpid(), make_pid=child.pid,
                         seconds=round(time.monotonic()-begun, 2), free_bytes=free,
                         min_free_bytes=free_min, terminal=False, requested_targets=['Image'])
            marker.write_text(json.dumps(state, indent=2)+'\n')
            if free < RESERVE + 256*1024**2:
                terminated_for_space = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
                break
            time.sleep(1)
        ret = child.wait()
    text = logpath.read_text(errors='replace')
    diagnostics = [line for line in text.splitlines() if re.search(r'warning:|error:', line, re.I)]
    compiled = re.findall(r'^\s+(?:CC|AS)\s+(?:\[M\]\s+)?([^\n]+)', text, re.M)
    shared_ok = {path: pre.sha(Path(path)) for path in DATA['shared_before']} == DATA['shared_before']
    initramfs_ok = pre.snapshot(Path(DATA['initramfs_source'])) == json.loads((PRIVATE/'initramfs-input-manifest-private.json').read_text())
    config_ok = pre.sha(BUILD/'.config') == DATA['original']['artifacts']['.config']['sha256']
    report = dict(stage=456, attempt=attempt, commit=pre.COMMIT, requested_targets=['Image'], exit=ret,
                  seconds=round(time.monotonic()-begun, 3), minimum_free_bytes=free_min,
                  stopped_for_space=terminated_for_space, reserve_bytes=RESERVE,
                  source_only_0064=True, core_source_sha256=STATE['actual_core_sha256'],
                  image363_config_exact=config_ok, shared_inputs_and_index_unchanged=shared_ok,
                  original_initramfs_unchanged=initramfs_ok, original_release_retained=True,
                  true_current_build_time=True, build_banner_version=456, object_timestamps_not_forged=True,
                  rebuilt_objects=len(compiled), compiled_module_objects=len(re.findall(r'^\s+CC\s+\[M\]', text, re.M)),
                  diagnostic_count=len(diagnostics),
                  changed_core_diagnostics=[line for line in diagnostics if 'v4l2-device.c' in line],
                  dtb_target_requested=False, all_modules_target_requested=False, boot_packaged=False,
                  sdk_or_phone_accessed=False, installed=False, passed=False)
    (PRIVATE/f'image-objects-r{attempt}-private.json').write_text(json.dumps(compiled, indent=2)+'\n')
    (PRIVATE/f'image-diagnostics-r{attempt}-private.json').write_text(json.dumps(diagnostics, indent=2)+'\n')
    if ret == 0:
        release = (BUILD/'include/config/kernel.release').read_text().strip()
        assert release == RELEASE
        report['release'] = release
        report['build_banner'] = (BUILD/'include/generated/utsversion.h').read_text().strip()
        assert '#456 ' in report['build_banner']
        artifacts = {}
        for relative, name in [('arch/arm64/boot/Image', 'Image-k456-core0064-private'),
                               ('vmlinux', 'vmlinux-k456-core0064-private'),
                               ('.config', 'config-k456-private')]:
            target = PRIVATE/name
            assert not target.exists(), 'Do not overwrite a finished Image result'
            shutil.copyfile(BUILD/relative, target)
            artifacts[relative] = dict(bytes=target.stat().st_size, sha256=pre.sha(target), private_path=str(target))
        assert artifacts['arch/arm64/boot/Image']['sha256'] != DATA['original']['artifacts']['arch/arm64/boot/Image']['sha256']
        embedded = subprocess.check_output([str(SOURCE/'scripts/extract-ikconfig'), str(PRIVATE/'Image-k456-core0064-private')])
        assert hashlib.sha256(embedded).hexdigest() == DATA['original']['artifacts']['.config']['sha256']
        notes = pre.run(['aarch64-linux-gnu-readelf', '-n', PRIVATE/'vmlinux-k456-core0064-private'])
        report.update(artifacts=artifacts, vmlinux_build_id=re.search(r'Build ID: ([0-9a-f]+)', notes)[1],
                      embedded_config_matches_original=True,
                      changed_core_object_rebuilt=any(item.strip() == 'drivers/media/v4l2-core/v4l2-device.o' for item in compiled))
        report['passed'] = bool(shared_ok and initramfs_ok and config_ok and free_min >= RESERVE
                                and not report['changed_core_diagnostics'] and report['changed_core_object_rebuilt']
                                and report['compiled_module_objects'] == 0)
    report['source_head_and_only_patch_preserved'] = (
        pre.run(['git', '-C', SOURCE, 'rev-parse', 'HEAD']) == pre.COMMIT and
        pre.run(['git', '-C', SOURCE, 'diff', '--name-only']) == 'drivers/media/v4l2-core/v4l2-device.c')
    assert report['source_head_and_only_patch_preserved']
    (HERE/f'build-r{attempt}-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (HERE/'build-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    marker.write_text(json.dumps(dict(report, terminal=True), indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
