"""One real r32 -> r33 -> r32 transaction in a private SDK overlay, without devices."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import traceback
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
volume = storage.mount.mounted_build().parent
work = storage.workspace() / 'apk-root-r1'
parser = argparse.ArgumentParser()
parser.add_argument('--resume-after-pretransaction-cache-key-failure', action='store_true')
parser.add_argument('--resume-after-pretransaction-rootfs-key-path-correction', action='store_true')
parser.add_argument('--new-corresponding-rootfs-r2', action='store_true')
args = parser.parse_args()
rootfs_r2 = args.new_corresponding_rootfs_r2
if rootfs_r2:
    prior = json.loads((HERE / 'apk-root-validation.json').read_bytes())
    assert not prior['passed'] and prior['overlay_unmounted'] and prior['lower_sdk_database_and_world_unchanged']
    assert [item['label'] for item in prior['commands']] == ['mount', 'cache-index']
    retained = HERE / 'apk-root-r1-local-cache-signers-failure-validation.json'
    assert not retained.exists()
    shutil.copyfile(HERE / 'apk-root-validation.json', retained)
    work = storage.workspace() / 'apk-root-r2'
corrected_key_path_resume = args.resume_after_pretransaction_rootfs_key_path_correction
args.resume_after_pretransaction_cache_key_failure |= corrected_key_path_resume
if args.resume_after_pretransaction_cache_key_failure:
    prior = json.loads((HERE / 'apk-root-validation.json').read_bytes())
    assert not prior['passed'] and prior['overlay_unmounted'] and prior['lower_sdk_database_and_world_unchanged']
    assert [item['label'] for item in prior['commands']] == ['mount', 'cache-index'] and prior['commands'][-1]['exit_code'] == 99
    retained = HERE / ('apk-root-r1-rootfs-etc-key-path-failure-validation.json' if corrected_key_path_resume else 'apk-root-r1-pretransaction-failure-validation.json')
    assert not retained.exists()
    shutil.copyfile(HERE / 'apk-root-validation.json', retained)
else:
    assert not work.exists() and (not (HERE / 'apk-root-validation.json').exists() or rootfs_r2)
assert subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
assert not subprocess.check_output(['findmnt', '-rn', '-R', str(storage.SDK)], text=True).strip() if subprocess.run(['findmnt', '-rn', '-R', str(storage.SDK)], capture_output=True).returncode == 0 else True
assert shutil.disk_usage(volume).free > 2 * 1024 ** 3 + 1024 ** 3
package_proof = json.loads((HERE / 'package-r1-validation.json').read_bytes())
payload_proof = json.loads((HERE / 'private-payload-validation.json').read_bytes())
assert package_proof['passed'] and payload_proof['passed']
manifest = json.loads((PRIVATE / 'cohort-r1/manifest-private.json').read_bytes())
state = json.loads((PRIVATE / 'package-state-r1-private.json').read_bytes())
apk = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
signing = Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
keys = PRIVATE / 'isolated-union-public-keys'
root = work / 'root'
upper = work / 'upper'
overlay_work = work / 'work'
for path in [root, upper, overlay_work]:
    path.mkdir(parents=True, exist_ok=args.resume_after_pretransaction_cache_key_failure)
report = dict(stage=475, passed=False, phone_accessed=False, modules_loaded=False, sdk_bind_used=False,
              sdk_overlay_used=True, dependency_scripts_and_commit_hooks_executed=False,
              current_phone_apk_version_requeried=False, target_current_binary_compatibility_proven=False,
              default640_or_raw_capture_executed=False, device_transition_validated=False)
report['resume_from_pretransaction_cache_index_only'] = args.resume_after_pretransaction_cache_key_failure
report['sdk_overlay_used'] = not rootfs_r2
report['corresponding_cached_rootfs_overlay_used'] = rootfs_r2


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(arguments, label, timeout=90):
    started = time.monotonic()
    result = subprocess.run(arguments, capture_output=True, timeout=timeout)
    (PRIVATE / f'apk-root-{label}-private.log').write_bytes(result.stdout + result.stderr)
    report.setdefault('commands', []).append(dict(label=label, exit_code=result.returncode, seconds=round(time.monotonic() - started, 3)))
    print(json.dumps(dict(stage=475, isolated_root_command=label, exit_code=result.returncode)), flush=True)
    assert result.returncode == 0, f'{label}: exit {result.returncode}; see retained private log'
    return result


def target_path(absolute):
    relative = absolute.lstrip('/')
    assert '..' not in Path(relative).parts
    path = root / relative
    assert path.resolve(strict=False).is_relative_to(root)
    return path


def packages(kind):
    selected = manifest[kind + '_packages']
    return ['chroot', str(root), '/sbin/apk', '--no-network', '--repositories-file', '/etc/apk/camera475.list',
            'add', '--scripts=no', '--commit-hooks=no', *[name + '=' + version for name, version in sorted(selected.items())]]


def set_repositories(kind):
    path = root / 'etc/apk/camera475.list'
    path.write_text('ndx file:///var/lib/camera475/' + kind + '/packages.adb\nndx file:///var/lib/camera475/cache/packages.adb\n')


def versions():
    values = {}
    for block in (root / 'lib/apk/db/installed').read_text().split('\n\n'):
        row = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
        if row.get('P') in manifest['rollback_packages']:
            values[row['P']] = row['V']
    return values


def package_files(kind):
    for item in state['inventories']:
        expected = item['after_files' if kind == 'forward' else 'before_files']
        for relative, row in expected.items():
            path = target_path('/' + relative)
            if 'symlink' in row:
                assert path.is_symlink() and os.readlink(path) == row['symlink'], relative
            else:
                assert path.is_file() and not path.is_symlink() and sha(path) == row['sha256'], relative


def private_files(kind):
    for family, key in [('modules', 'name'), ('profiles', 'model')]:
        for row in manifest[family]:
            path = target_path(row['resolved_path'])
            source = PRIVATE / 'cohort-r1' / kind / family / (row[key] + ('.ko' if family == 'modules' else '.yaml'))
            assert sha(source) == row[kind + '_sha256']
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.camera475-tmp')
            assert not temporary.exists()
            shutil.copyfile(source, temporary)
            temporary.chmod(0o644)
            os.replace(temporary, path)
            assert sha(path) == row[kind + '_sha256']


version_evidence = PRIVATE.parent / 'charging-management-20261023/apk-version-after474-1792758202248797751'
version_receipt = json.loads((version_evidence / 'result-private.json').read_bytes())
assert version_receipt['command'] == 'apk --version' and version_receipt['exit_code'] == 0 and version_receipt['read_only']
target_version = (version_evidence / 'stdout-private.txt').read_text().strip()
assert target_version == 'apk-tools 3.0.8-r0, compiled for aarch64.'
report.update(cached_target_apk_version=target_version, target_version_observed_by_charging_owner=True,
              target_version_stdout_sha256=sha(version_evidence / 'stdout-private.txt'),
              target_version_receipt_sha256=sha(version_evidence / 'result-private.json'),
              target_on_device_package_install_or_loader_tested=False)
lower_before = {name: sha(storage.SDK / name) for name in ['lib/apk/db/installed', 'etc/apk/world']}
lower_root = Path('/home/cy122/pmos-samurai-rootfs01/work/chroot_rootfs_postmarketos-trailblazer') if rootfs_r2 else storage.SDK
selected_lower_before = {name: sha(lower_root / name) for name in ['lib/apk/db/installed', 'etc/apk/world']}
key_sources = [storage.SDK / 'etc/apk/keys', Path('/home/cy122/pmos-samurai-rootfs01/work/chroot_rootfs_postmarketos-trailblazer/usr/share/apk/keys')]
assert not keys.exists() or corrected_key_path_resume or rootfs_r2
keys.mkdir(exist_ok=corrected_key_path_resume or rootfs_r2)
key_rows = []
for source_directory in key_sources:
    for source in sorted(source_directory.iterdir()):
        if not source.is_file():
            continue
        assert source.name.endswith('.pub'), 'Only retained public keys may enter this isolated trust set'
        destination = keys / source.name
        if destination.exists():
            assert sha(destination) == sha(source)
        else:
            shutil.copyfile(source, destination)
        key_rows.append(dict(source=str(source), sha256=sha(source), filename=source.name))
report['isolated_trust_set_public_key_sources'] = key_rows
report['allow_untrusted_used'] = False
mounted = False
try:
    run(['mount', '-t', 'overlay', 'overlay', '-o', f'lowerdir={lower_root},upperdir={upper},workdir={overlay_work}', str(root)], 'mount')
    mounted = True
    assert subprocess.run(['mountpoint', '-q', str(root / 'sys')], capture_output=True).returncode != 0
    assert subprocess.run(['mountpoint', '-q', str(root / 'dev')], capture_output=True).returncode != 0
    cache = root / 'var/lib/camera475/cache'
    cache.mkdir(parents=True, exist_ok=args.resume_after_pretransaction_cache_key_failure)
    for source in keys.iterdir():
        destination = root / 'etc/apk/keys' / source.name
        if destination.exists():
            assert sha(destination) == sha(source)
        else:
            shutil.copyfile(source, destination)
    cache_source = Path('/home/cy122/pmos-samurai-rootfs01/work/cache_apk_aarch64')
    excluded = set(re.findall(r'/([^/\s]+\.apk): UNTRUSTED signature', (PRIVATE / 'apk-root-cache-index-private.log').read_text())) if rootfs_r2 else set()
    report['untrusted_cache_packages_excluded_from_dependency_repository'] = len(excluded)
    cache_bytes = sum(path.stat().st_size for path in cache_source.glob('*.apk'))
    assert shutil.disk_usage(volume).free > cache_bytes + 2 * 1024 ** 3 + 256 * 1024 ** 2
    for source in sorted(cache_source.glob('*.apk')):
        with tarfile.open(source, 'r:gz', ignore_zeros=True) as archive:
            fields = dict(line.split(' = ', 1) for line in archive.extractfile('.PKGINFO').read().decode().splitlines() if ' = ' in line)
        destination = cache / (fields['pkgname'] + '-' + fields['pkgver'] + '.apk')
        if destination.name in excluded:
            continue
        if destination.exists():
            assert sha(destination) == sha(source)
        else:
            shutil.copyfile(source, destination)
    run([str(apk), '--keys-dir', str(keys), 'mkndx', '--sign-key', str(signing), '--pkgname-spec', '${name}-${version}.apk',
         '--output', str(cache / 'packages.adb'), *[str(path) for path in sorted(cache.glob('*.apk'))]], 'cache-index')
    for kind in ['forward', 'rollback']:
        shutil.copytree(PRIVATE / 'cohort-r1' / kind / 'repository', root / 'var/lib/camera475' / kind)
    version_output = run(['chroot', str(root), '/sbin/apk', '--version'], 'apk-version').stdout.decode().strip()
    assert version_output == target_version
    cached_rootfs_apk = Path('/home/cy122/pmos-samurai-rootfs01/work/chroot_rootfs_postmarketos-trailblazer/sbin/apk')
    report.update(isolated_apk_version=version_output, isolated_apk_sha256=sha(root / 'sbin/apk'),
                  cached_rootfs_apk_sha256=sha(cached_rootfs_apk),
                  target_apk3_format_version_matches_isolated_tool=True,
                  isolated_apk_equals_cached_rootfs_binary=sha(root / 'sbin/apk') == sha(cached_rootfs_apk))
    set_repositories('rollback')
    run(packages('rollback'), 'baseline-r32')
    assert versions() == manifest['rollback_packages']
    package_files('rollback')
    private_files('rollback')
    world_before_upgrade = (root / 'etc/apk/world').read_bytes()
    set_repositories('forward')
    run(packages('forward'), 'upgrade-r33')
    assert versions() == manifest['forward_packages']
    package_files('forward')
    private_files('forward')
    report['actual_baseline_install_and_upgrade_payload_hashes_verified'] = True
    run(['chroot', str(root), '/usr/bin/cam', '--help'], 'cam-default-loader', timeout=30)
    run(['chroot', str(root), '/lib/ld-musl-aarch64.so.1', '--list', '/usr/bin/cam'], 'cam-loader-list', timeout=30)
    run(['chroot', str(root), '/usr/bin/lc-compliance', '--help'], 'lc-compliance-default-loader', timeout=30)
    libraries = ['/usr/lib/libcamera-base.so.0.7.2', '/usr/lib/libcamera.so.0.7.2',
                 '/usr/lib/gstreamer-1.0/libgstlibcamera.so', '/usr/libexec/libcamera/v4l2-compat.so',
                 '/usr/lib/libcamera/ipa/ipa_camss_vfe.so']
    code = 'import ctypes,os,json; paths=' + repr(libraries) + '; loaded=[ctypes.CDLL(p,mode=os.RTLD_NOW|os.RTLD_LOCAL) for p in paths]; print(json.dumps(dict(rtld_now_loaded=paths)))'
    run(['chroot', str(root), '/usr/bin/python3', '-B', '-c', code], 'rtld-now-five-dsos', timeout=30)
    verify_source = volume / 'libcamera473-processed-manager-capacity/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify'
    shutil.copyfile(verify_source, root / 'tmp/ipa-verify475')
    (root / 'tmp/ipa-verify475').chmod(0o755)
    signatures = []
    for path in sorted((root / 'usr/lib/libcamera/ipa').glob('*.so')):
        result = run(['chroot', str(root), '/tmp/ipa-verify475', '/usr/lib/libcamera/ipa/' + path.name], 'ipa-signature-' + path.name, timeout=30)
        assert b'IPA module signature is valid' in result.stdout
        signatures.append(path.name)
    assert len(signatures) == 6
    report.update(default_loader_cam_and_tools_verified=True, gstreamer_v4l2_and_ipa_rtld_now_verified=True,
                  six_ipa_signatures_verified_against_packaged_core=signatures)
    set_repositories('rollback')
    run(packages('rollback'), 'rollback-r32')
    assert versions() == manifest['rollback_packages']
    package_files('rollback')
    private_files('rollback')
    assert (root / 'etc/apk/world').read_bytes() == world_before_upgrade
    report.update(actual_upgrade_and_downgrade=True, exact440_package_payload_and_world_restored=True,
                  four_module_and_four_profile_files_replaced_and_restored=True,
                  scripts_hooks_services_and_module_loading_not_tested=True, passed=True)
except BaseException:
    (PRIVATE / 'apk-root-failure-private.txt').write_text(traceback.format_exc())
    report['failure'] = traceback.format_exc().splitlines()[-1]
finally:
    if mounted:
        result = subprocess.run(['umount', str(root)], capture_output=True)
        (PRIVATE / 'apk-root-unmount-private.log').write_bytes(result.stdout + result.stderr)
        report['overlay_unmounted'] = result.returncode == 0
    else:
        report['overlay_unmounted'] = True
    report['lower_sdk_database_and_world_unchanged'] = all(sha(storage.SDK / name) == digest for name, digest in lower_before.items())
    report['selected_lower_database_and_world_unchanged'] = all(sha(lower_root / name) == digest for name, digest in selected_lower_before.items())
    report['sdk_work_slot_unbound'] = subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
    report['passed'] = bool(report['passed'] and report['overlay_unmounted'] and report['lower_sdk_database_and_world_unchanged'] and report['sdk_work_slot_unbound'])
    report['free_after_bytes'] = shutil.disk_usage(volume).free
    (HERE / 'apk-root-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
assert report['passed'], 'See retained isolated-root failure; do not replay this root blindly'
