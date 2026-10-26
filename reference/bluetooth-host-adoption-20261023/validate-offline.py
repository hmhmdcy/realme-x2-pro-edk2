"""Narrow real APK3 add/failure/del fixture using copied real115 metadata.

Only the supplied fresh private Linux root is written. The real115 source is
read-only; no dependency records/APKs are invented and no dependency payload,
trigger, service or device is exercised. This does not enable live apply.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tarfile
import uuid

HERE = Path(__file__).resolve().parent
API = runpy.run_path(str(HERE / 'preflight.py'))
require, sha, NAME, FILES, ORDER = (API[name] for name in ['require', 'sha', 'NAME', 'FILES', 'ORDER'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source-rootfs', 'build-root', 'candidate', 'artifact-manifest', 'module-archive', 'apk', 'verification-keys', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use a private Linux fixture')
    require(args.build_root.is_absolute() and not args.build_root.exists() and not str(args.build_root).startswith('/mnt/'), 'Fresh Linux filesystem fixture root required')
    require(args.output.is_absolute() and not args.output.exists(), 'New result path required')
    source_db = (args.source_rootfs / 'lib/apk/db/installed').read_bytes()
    source_world = (args.source_rootfs / 'etc/apk/world').read_bytes()
    require(len(source_db) > 1000000 and b'P:bluez\nV:5.87-r0\n' in source_db, 'Expected the actual full115 installed metadata')
    archive_raw = args.module_archive.read_bytes()
    require(sha(archive_raw) == 'fca01dab22b0a3917f9ce5600059d00b29aa9685381c2cd2f2e4867b9fb8f73b', 'Wrong original363 module archive')
    with tarfile.open(args.module_archive) as archive:
        modules_order = archive.extractfile(ORDER).read()
    # modules_install rewrites build .o names to kernel/... .ko paths. This
    # installed file is distinct from build/modules.order in the363 report.
    require(len(modules_order) == 32289 and sha(modules_order) == '81507a3119cebd985936e87d10b1ccbc28677d0fca370a979521449e1dc8e81f', 'Wrong installed original363 modules.order')
    args.build_root.mkdir(parents=True, mode=0o700)
    root = args.build_root / 'success-root'
    root.mkdir()
    (root / 'usr/lib/apk/db').mkdir(parents=True)
    (root / 'lib').symlink_to('usr/lib')
    (root / 'usr/lib/apk/db/installed').write_bytes(source_db)
    (root / 'etc/apk').mkdir(parents=True)
    (root / 'etc/apk/world').write_bytes(source_world)
    for relative, raw in {
        ORDER: modules_order,
        'proc/sys/kernel/random/boot_id': (str(uuid.uuid4()) + '\n').encode(),
        'proc/sys/kernel/osrelease': (API['RELEASE'] + '\n').encode(),
        'sys/firmware/devicetree/base/compatible': b'realme,samurai\0qcom,sm8150\0',
        API['MANIFEST']: b'{"offline_fixture":true}\n',
        '.host-adoption-fixture.json': b'{"kind":"offline-real-apk-fixture","bluetoothd_query_rc":1}\n',
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (root / 'sys/module').mkdir()
    guard = '/var/lib/samurai/k449-adopted/boot-id-private.txt'
    (root / guard.lstrip('/')).parent.mkdir(parents=True)
    (root / guard.lstrip('/')).write_bytes((root / 'proc/sys/kernel/random/boot_id').read_bytes())
    before_records, _ = API['database'](source_db, API['ReadRoot'](root))
    require(NAME not in before_records and all(name in before_records for name in ['bluez', 'kmod', 'openrc']), 'Real dependency metadata missing or candidate already present')
    handoff = dict(kind='current-host-module-adoption-handoff', original_guard_path=guard,
        charging_manifest_sha256=sha((root / API['MANIFEST']).read_bytes()), release=API['RELEASE'],
        modules_order=dict(sha256=sha(modules_order), owner=None),
        dependencies={name: before_records[name]['V'] for name in ['bluez', 'kmod', 'openrc']},
        state_is_offline_fixture=True)
    handoff_path = args.build_root / 'fixture-handoff.json'
    handoff_path.write_text(json.dumps(handoff, indent=2) + '\n')
    failed_root = args.build_root / 'failure-root'
    shutil.copytree(root, failed_root, symlinks=True)
    invocations, preflight_results = [], []

    def preflight(target, action='adopt', extra=(), success=True, label='preflight'):
        command = [sys.executable, str(HERE / 'preflight.py'), '--root', str(target), '--fixture',
            '--baseline-lock', str(handoff_path), '--guard-file', guard,
            '--charging-manifest-sha256', handoff['charging_manifest_sha256'],
            '--candidate', str(args.candidate), '--artifact-manifest', str(args.artifact_manifest),
            '--apk', str(args.apk), '--verification-keys', str(args.verification_keys), '--action', action, *extra]
        before = snapshot(target)
        result = subprocess.run(command, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        report = json.loads(result.stdout)
        require((result.returncode == 0) == success and snapshot(target) == before, 'Read-only preflight changed state or returned wrong status')
        require(report['apk_mutations'] == 0, 'Preflight invoked a mutating APK operation')
        preflight_results.append(dict(label=label, accepted=report['preflight_passed'], no_state_change=True,
                                      apk_mutations=0, refusal=report.get('refusal')))

    def snapshot(target):
        current = {str(path): sha(path.read_bytes()) for path in [target / 'lib/apk/db/installed', target / 'etc/apk/world', target / ORDER] if path.is_file()}
        for relative in FILES:
            path = target / relative
            current[relative] = sha(path.read_bytes()) if path.is_file() else None
        return current

    def apk(target, verb, label, success=True):
        argument = args.candidate if verb == 'add' else NAME
        result = subprocess.run([str(args.apk), '--root', str(target), '--arch', 'aarch64',
            '--keys-dir', str(args.verification_keys), '--no-network', '--no-scripts', '--no-commit-hooks', verb, str(argument)], capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        invocations.append(dict(label=label, operation=verb, exit=result.returncode))
        require((result.returncode == 0) == success, 'Unexpected native APK result: ' + label)
        return result.returncode

    def records(target):
        return API['database']((target / 'lib/apk/db/installed').read_bytes(), API['ReadRoot'](target))[0]

    def restored(target):
        after = records(target)
        require(after == before_records, 'Rollback changed a preexisting package identity/version/failure state')
        require(set((target / 'etc/apk/world').read_text().splitlines()) == set(source_world.decode().splitlines()), 'Rollback world differs')
        require((target / ORDER).read_bytes() == modules_order and all(not (target / relative).exists() for relative in FILES), 'Rollback did not restore three absent payloads/modules.order')

    preflight(root, label='adopt-ready')
    preflight(root, extra=['--apply'], success=False, label='apply-refused')
    saved_order = (root / ORDER).read_bytes()
    (root / ORDER).unlink()
    preflight(root, success=False, label='missing-order-refused')
    (root / ORDER).write_bytes(saved_order)
    apk(root, 'add', 'install-success')
    preflight(root, 'rollback', label='rollback-ready')
    apk(root, 'del', 'rollback-success')
    restored(root)
    # Simulate another actor changing an ancestor after successful preflight.
    # The original signed APK is unchanged. Real APK then produces a partial
    # committed package and a nonzero status; the injector owns only this file.
    preflight(failed_root, label='before-concurrent-drift')
    blocker = failed_root / 'usr/lib/modules-load.d'
    blocker.write_bytes(b'private-fixture-concurrent-ancestor-drift\n')
    apk(failed_root, 'add', 'real-partial-failure', success=False)
    failed_record = records(failed_root).get(NAME)
    require(failed_record is not None and 'f' in failed_record.get('f', ''), 'Expected real committed broken-file state was not observed')
    failed_payload = snapshot(failed_root)
    preflight(failed_root, 'rollback', success=False, label='unknown-ancestor-refused')
    require(blocker.read_bytes() == b'private-fixture-concurrent-ancestor-drift\n', 'Fixture injector lost ownership of blocker')
    blocker.unlink()  # Undo only the known injector-owned drift, not a package file.
    preflight(failed_root, 'rollback', label='partial-rollback-ready')
    apk(failed_root, 'del', 'partial-rollback')
    restored(failed_root)
    require((args.source_rootfs / 'lib/apk/db/installed').read_bytes() == source_db and
            (args.source_rootfs / 'etc/apk/world').read_bytes() == source_world, 'Shared source metadata changed')
    require(sha(args.candidate.read_bytes()) == API['APK_SHA'], 'Frozen APK changed')
    report = dict(schema=1, passed=True, preflight_source_sha256=sha((HERE / 'preflight.py').read_bytes()),
        validation_source_sha256=sha(Path(__file__).read_bytes()), package_sha256=API['APK_SHA'],
        copied_real115_installed_database_sha256=sha(source_db), copied_real115_installed_database_bytes=len(source_db),
        copied_real115_package_records=len(before_records), real_dependency_versions=handoff['dependencies'],
        fabricated_dependency_records_or_apks_used=False, real_dependency_payloads_copied_or_tested=False,
        isolated_identity_and_process_state_are_explicit_fixtures=True,
        native_apk_successful_install_and_rollback_passed=True,
        native_apk_nonzero_partial_commit_observed=True, partial_install_failure_flags=failed_record.get('f', ''),
        partial_committed_payload_count=sum(failed_payload[relative] is not None for relative in FILES),
        unknown_concurrent_ancestor_refused_before_rollback=True,
        injector_undid_only_its_own_known_ancestor_drift=True,
        native_apk_partial_failure_rollback_passed=True,
        prior_package_names_versions_flags_world_and_modules_order_restored=True,
        scripts_commit_hooks_dependency_triggers_disabled=True, native_kmod_index_regeneration_not_tested=True,
        live_apply_supported=False, live_or_original_rootfs_install_performed=False,
        original_rootfs_metadata_and_frozen_candidate_unchanged=True,
        device_ssh_service_module_sdk_or_reboot_actions=False,
        preflight_results=preflight_results, native_apk_invocations=invocations,
        pan_hog_and_hardware_rollback_acceptance_pending=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ['passed', 'native_apk_successful_install_and_rollback_passed',
        'native_apk_nonzero_partial_commit_observed', 'partial_install_failure_flags', 'native_apk_partial_failure_rollback_passed', 'live_apply_supported']}))


if __name__ == '__main__':
    main()
