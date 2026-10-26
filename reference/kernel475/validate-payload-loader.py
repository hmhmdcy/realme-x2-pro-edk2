"""Extract signed payloads and test their loader in SDK; this is not APK installation."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import traceback
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
volume = storage.mount.mounted_build().parent
parser = argparse.ArgumentParser()
parser.add_argument('--after-extract-collision-r2', action='store_true')
args = parser.parse_args()
if args.after_extract_collision_r2:
    previous = json.loads((HERE / 'payload-loader-validation.json').read_bytes())
    assert not previous['passed'] and previous['overlay_unmounted'] and previous['lower_sdk_database_and_world_unchanged']
    assert previous['commands'][-1] == dict(label='extract-r33', exit_code=99)
    retained = HERE / 'payload-loader-r1-collision-validation.json'
    assert not retained.exists()
    shutil.copyfile(HERE / 'payload-loader-validation.json', retained)
work = storage.workspace() / ('payload-loader-r2' if args.after_extract_collision_r2 else 'payload-loader-r1')
assert not work.exists() and (not (HERE / 'payload-loader-validation.json').exists() or args.after_extract_collision_r2)
assert subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
assert shutil.disk_usage(volume).free > 2 * 1024 ** 3 + 256 * 1024 ** 2
root, upper, overlay_work = [work / name for name in ['root', 'upper', 'work']]
for path in [root, upper, overlay_work]:
    path.mkdir(parents=True)
apk = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
keys = PRIVATE / 'isolated-union-public-keys'
manifest = json.loads((PRIVATE / 'cohort-r2-manifest-private.json').read_bytes())
state = json.loads((PRIVATE / 'package-state-r1-private.json').read_bytes())
report = dict(stage=475, passed=False, actual_signed_apk_payloads_used=True, sdk_dependencies_used=True,
              apk_database_install_upgrade_or_downgrade_performed=False, dependency_solver_bypassed_for_install=False,
              payload_extraction_has_no_dependency_or_database_semantics=True,
              phone_accessed=False, modules_loaded=False, sdk_bind_used=False, sdk_overlay_used=True,
              on_device_default_path_capture_tested=False)
report['fresh_extract_prefixes_then_verified_file_copy'] = args.after_extract_collision_r2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(arguments, label):
    result = subprocess.run(arguments, capture_output=True, timeout=45)
    (PRIVATE / f'payload-loader-{label}-private.log').write_bytes(result.stdout + result.stderr)
    report.setdefault('commands', []).append(dict(label=label, exit_code=result.returncode))
    print(json.dumps(dict(stage=475, payload_loader_command=label, exit_code=result.returncode)), flush=True)
    assert result.returncode == 0, label + ': see retained private log'
    return result


def checked_path(relative):
    path = root / relative.lstrip('/')
    assert path.resolve(strict=False).is_relative_to(root)
    return path


def verify_package_bytes(kind):
    for item in state['inventories']:
        for relative, row in item['after_files' if kind == 'forward' else 'before_files'].items():
            path = checked_path(relative)
            if 'symlink' in row:
                assert path.is_symlink() and os.readlink(path) == row['symlink'], relative
            else:
                assert sha(path) == row['sha256'] and (path.stat().st_mode & 0o7777) == row['mode'], relative


def swap_private_files(kind):
    for family, name_key, suffix in [('modules', 'name', '.ko'), ('profiles', 'model', '.yaml')]:
        for row in manifest[family]:
            source = PRIVATE / 'cohort-r1' / kind / family / (row[name_key] + suffix)
            assert sha(source) == row[kind + '_sha256']
            destination = checked_path(row['resolved_path'])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.parent.chmod(0o755)
            shutil.copyfile(source, destination)
            destination.chmod(0o644)
            os.chown(destination, 0, 0)
            assert sha(destination) == row[kind + '_sha256']
            assert destination.stat().st_uid == destination.stat().st_gid == 0


def extract_and_copy(kind, label):
    inputs = sorted((PRIVATE / 'repository-r1' / kind).glob('*.apk'))
    if not args.after_extract_collision_r2:
        run([str(apk), '--keys-dir', str(keys), 'extract', '--destination', str(root), *[str(path) for path in inputs]], 'extract-' + label)
        return
    prefix = work / ('extracted-' + label)
    prefix.mkdir()
    run([str(apk), '--keys-dir', str(keys), 'extract', '--destination', str(prefix), *[str(path) for path in inputs]], 'extract-' + label)
    for directory in sorted(path for path in prefix.rglob('*') if path.is_dir() and not path.is_symlink()):
        destination = checked_path(directory.relative_to(prefix).as_posix())
        destination.mkdir(parents=True, exist_ok=True)
        destination.chmod(directory.stat().st_mode & 0o7777)
    for item in state['inventories']:
        for relative, row in item['after_files' if kind == 'forward' else 'before_files'].items():
            source = prefix / relative
            destination = checked_path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if 'symlink' in row:
                assert source.is_symlink() and os.readlink(source) == row['symlink']
                if destination.is_symlink():
                    destination.unlink()
                else:
                    assert not destination.exists()
                destination.symlink_to(row['symlink'])
            else:
                assert sha(source) == row['sha256'] and not destination.is_symlink()
                shutil.copyfile(source, destination)
                destination.chmod(row['mode'])
                os.chown(destination, 0, 0)


before = {relative: sha(storage.SDK / relative) for relative in ['lib/apk/db/installed', 'etc/apk/world']}
mounted = False
try:
    run(['mount', '-t', 'overlay', 'overlay', '-o', f'lowerdir={storage.SDK},upperdir={upper},workdir={overlay_work}', str(root)], 'mount')
    mounted = True
    assert subprocess.run(['mountpoint', '-q', str(root / 'dev')], capture_output=True).returncode != 0
    assert subprocess.run(['mountpoint', '-q', str(root / 'sys')], capture_output=True).returncode != 0
    for kind, label in [('rollback', 'r32-initial'), ('forward', 'r33')]:
        extract_and_copy(kind, label)
        verify_package_bytes(kind)
        swap_private_files(kind)
    run(['chroot', str(root), '/usr/bin/cam', '--help'], 'cam')
    run(['chroot', str(root), '/usr/bin/lc-compliance', '--help'], 'lc-compliance')
    run(['chroot', str(root), '/lib/ld-musl-aarch64.so.1', '--list', '/usr/bin/cam'], 'loader-list-cam')
    libraries = ['/usr/lib/libcamera-base.so.0.7.2', '/usr/lib/libcamera.so.0.7.2',
                 '/usr/lib/gstreamer-1.0/libgstlibcamera.so', '/usr/libexec/libcamera/v4l2-compat.so',
                 '/usr/lib/libcamera/ipa/ipa_camss_vfe.so']
    code = 'import ctypes,os,json; paths=' + repr(libraries) + '; loaded=[ctypes.CDLL(p,mode=os.RTLD_NOW|os.RTLD_LOCAL) for p in paths]; print(json.dumps(dict(rtld_now_loaded=paths)))'
    run(['chroot', str(root), '/usr/bin/python3', '-B', '-c', code], 'rtld-now')
    verify = volume / 'libcamera473-processed-manager-capacity/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify'
    shutil.copyfile(verify, root / 'tmp/ipa-verify475')
    (root / 'tmp/ipa-verify475').chmod(0o755)
    signatures = []
    for path in sorted((root / 'usr/lib/libcamera/ipa').glob('*.so')):
        result = run(['chroot', str(root), '/tmp/ipa-verify475', '/usr/lib/libcamera/ipa/' + path.name], 'ipa-' + path.name)
        assert b'IPA module signature is valid' in result.stdout
        signatures.append(path.name)
    assert len(signatures) == 6
    report.update(default_loader_cam_and_tools_verified=True,
                  packaged_core_base_gstreamer_v4l2_ipa_rtld_now_verified=True,
                  ipa_signatures_verified_against_actual_packaged_core=signatures)
    extract_and_copy('rollback', 'r32-restored')
    verify_package_bytes('rollback')
    swap_private_files('rollback')
    report.update(signed_payload_file_transition_r32_r33_r32_verified=True,
                  four_module_four_profile_file_content_and_install_attributes_restored=True, passed=True)
except BaseException:
    (PRIVATE / 'payload-loader-failure-private.txt').write_text(traceback.format_exc())
    report['failure'] = traceback.format_exc().splitlines()[-1]
finally:
    if mounted:
        result = subprocess.run(['umount', str(root)], capture_output=True)
        (PRIVATE / 'payload-loader-unmount-private.log').write_bytes(result.stdout + result.stderr)
        report['overlay_unmounted'] = result.returncode == 0
    else:
        report['overlay_unmounted'] = True
    report['lower_sdk_database_and_world_unchanged'] = all(sha(storage.SDK / name) == value for name, value in before.items())
    report['sdk_work_slot_unbound'] = subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
    report['passed'] = bool(report['passed'] and report['overlay_unmounted'] and report['lower_sdk_database_and_world_unchanged'] and report['sdk_work_slot_unbound'])
    report['free_after_bytes'] = shutil.disk_usage(volume).free
    (HERE / 'payload-loader-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
assert report['passed'], 'Keep this terminal loader test and inspect its failure'
