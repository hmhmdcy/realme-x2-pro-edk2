"""Stateful integration: real signed APKs, advisory-hook failure and recovery.

No device access. APK/DB/filesystem changes are limited to fresh isolated roots.
"""
from pathlib import Path
import argparse
import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
from hardening import HERE, load_lock, require, sha
import staged_apk_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline-fixture', 'r0-apk', 'r2-apk', 'module-archive', 'legacy-module', 'apk', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(os.geteuid() == 0 and args.build_root.is_absolute() and not args.build_root.exists(), 'New isolated Linux directory required')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem')
    args.build_root.mkdir(parents=True, mode=0o700)
    root = args.build_root / 'guarded-root'
    shutil.copytree(args.baseline_fixture, root)
    lock = load_lock()
    module_record = next(r for r in lock['modules'] if r['name'] == 'hci_uart')
    module_path = module_record['target']
    package_hashes = {str(p): sha(p.read_bytes()) for p in [args.r0_apk, args.r2_apk]}
    transaction = HERE / 'staged-bluetooth-transaction.py'
    txn = runpy.run_path(str(transaction))

    def register(target):
        staged_apk_fixture.prepare(target, lock['release'])
        info = target.stat()
        data = dict(kind='isolated-apk-fixture', root_dev=info.st_dev, root_ino=info.st_ino,
                    release=lock['release'], compatible='realme,samurai', bluetoothd_query_status=1, hci_uart_loaded=False)
        (target / txn['MARKER']).write_text(json.dumps(data))
        (target / txn['MARKER']).chmod(0o600)

    register(root)
    count = args.build_root / 'apk-invocations.txt'
    tracer = args.build_root / 'apk-traced'
    tracer.write_text('#!/bin/sh\nprintf "invoked\\n" >> ' + shlex.quote(str(count)) + '\nexec ' + shlex.quote(str(args.apk)) + ' "$@"\n')
    tracer.chmod(0o755)

    def calls():
        return len(count.read_text().splitlines()) if count.exists() else 0

    def snapshot(target):
        names = [r['target'] for r in lock['modules']] + ['lib/apk/db/installed', 'lib/apk/db/scripts.tar', 'etc/apk/world']
        return {name: sha((target / name).read_bytes()) for name in names if (target / name).exists()}

    def state(target):
        record, owners = txn['database']((target / 'lib/apk/db/installed').read_bytes())
        return dict(version=record['V'], flags=record.get('f', ''), script_failed='s' in record.get('f', ''),
                    hci_uart_sha256=sha((target / module_path).read_bytes()), owner=owners[module_path])

    def command(target, action, label, apply=True, success=True):
        values = dict(root=target, r0_apk=args.r0_apk, r2_apk=args.r2_apk, module_archive=args.module_archive,
                      apk=tracer, verification_keys=args.verification_keys)
        cmd = [sys.executable, str(transaction), '--action', action]
        for key, value in values.items():
            cmd += ['--' + key.replace('_', '-'), str(value)]
        if apply:
            cmd += ['--apply']
        result = subprocess.run(cmd, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require((result.returncode == 0) == success, label + ' unexpected status: ' + result.stdout.decode())
        return json.loads(result.stdout)

    refused = []

    def reject(label):
        before, invocations = snapshot(root), calls()
        result = command(root, 'upgrade', label, success=False)
        require(snapshot(root) == before and calls() == invocations, 'Rejected request invoked APK or changed DB/payload')
        refused.append(dict(case=label, apk_not_invoked=True, db_and_payload_unchanged=True, error=result['error']))

    marker = root / txn['MARKER']
    original_marker = marker.read_bytes()
    data = json.loads(original_marker)
    data['bluetoothd_query_status'] = 0
    marker.write_text(json.dumps(data))
    reject('running-daemon')
    marker.write_bytes(original_marker)
    data['bluetoothd_query_status'] = 1
    data['hci_uart_loaded'] = True
    marker.write_text(json.dumps(data))
    reject('loaded-module')
    marker.write_bytes(original_marker)
    original_module = (root / module_path).read_bytes()
    (root / module_path).write_bytes(args.legacy_module.read_bytes())
    reject('legacy-k132-module')
    (root / module_path).write_bytes(original_module)
    parent = (root / module_path).parent
    saved = parent.with_name('bluetooth.saved')
    parent.rename(saved)
    outside = args.build_root / 'outside-target'
    shutil.copytree(saved, outside)
    parent.symlink_to(outside, target_is_directory=True)
    outside_before = {p.name: sha(p.read_bytes()) for p in outside.iterdir() if p.is_file()}
    reject('ancestor-symlink-escape')
    require(outside_before == {p.name: sha(p.read_bytes()) for p in outside.iterdir() if p.is_file()}, 'Escape target changed')
    parent.unlink()
    saved.rename(parent)
    before, invocations = snapshot(root), calls()
    dry = command(root, 'upgrade', 'dry-run', apply=False)
    require(dry['pure_dry_run'] and snapshot(root) == before and calls() == invocations, 'Dry run mutated state or invoked APK')
    forward = command(root, 'upgrade', 'guarded-upgrade')
    require(state(root)['version'] == '0.1.0-r2' and state(root)['flags'] == 'S', 'Forward state is not clean r2')
    restored = command(root, 'restore-bytes', 'restore-r0-bytes')
    require(restored['package_downgrade_pending'] and state(root)['version'] == '0.1.0-r2' and state(root)['hci_uart_sha256'] == module_record['sha256'], 'Restore order not demonstrated')
    rollback = command(root, 'rollback', 'guarded-downgrade')
    clean = state(root)
    require(clean['version'] == '0.1.0-r0' and clean['flags'] == 'S' and clean['hci_uart_sha256'] == module_record['sha256'], 'Rollback state not clean')
    # A separate real DB demonstrates the unsafe native invocation and repair.
    unsafe = args.build_root / 'advisory-hook-root'
    shutil.copytree(root, unsafe)
    register(unsafe)
    command(unsafe, 'upgrade', 'unsafe-root-prepare')
    native = subprocess.run([str(tracer), '--root', str(unsafe), '--arch', 'aarch64', '--no-network',
                             '--keys-dir', str(args.verification_keys), 'add', str(args.r0_apk)], capture_output=True)
    (args.build_root / 'native-hook-failed-but-committed.log').write_bytes(native.stdout + native.stderr)
    unsafe_state = state(unsafe)
    require(native.returncode != 0 and unsafe_state['version'] == '0.1.0-r0' and unsafe_state['flags'] == 'sS'
            and unsafe_state['hci_uart_sha256'] == module_record['sha256'], 'Expected advisory-hook failure/commit not reproduced')
    repair = command(unsafe, 'repair-r0', 'repair-native-broken-r0')
    require(state(unsafe) == clean and not repair['after_script_failed'], 'Native failure flags were not repaired')
    expected_hooks = {sha(runpy.run_path(str(HERE / 'build-apk.py'))['adoption_hook'](lock, candidate)) for candidate in [False, True]}
    observed_hooks = [sha(p.read_bytes()) for target in [root, unsafe] for p in (target / 'samurai-fixture').glob('*.original')]
    require(observed_hooks and set(observed_hooks) <= expected_hooks, 'Executed hook differs from original signed guard')
    require(package_hashes == {str(p): sha(p.read_bytes()) for p in [args.r0_apk, args.r2_apk]}, 'Frozen signed APK changed')
    report = dict(schema=1, passed=True, rejected_before_any_apk_invocation=refused,
                  dry_run_invoked_no_apk_and_changed_no_payload_or_db=True,
                  original_signed_hooks_executed_with_only_device_tree_read_adapter=True,
                  guarded_upgrade=forward, controlled_r0_restore=restored, guarded_downgrade=rollback,
                  final_clean_state=clean, native_advisory_failure=dict(exit=native.returncode, state=unsafe_state,
                    pre_upgrade_failed_but_payload_and_database_committed=True),
                  native_broken_script_state_repair=repair, native_failure_fixture_final_state=state(unsafe),
                  signed_packages_unchanged=True, service_and_module_state_are_fixtures=True,
                  device_actions_performed=False, live_deployment_or_pm_not_verified=True,
                  apk_failure_flag_s_is_error_and_S_is_format=True,
                  primary_source='reference/bluetooth-20261023/apk-hook-semantics.json')
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(passed=True, rejected_states=len(refused), forward_rollback_clean=True,
                         native_hook_failure_committed=True, native_failure_repaired_clean=True,
                         signed_packages_unchanged=True, device_actions_performed=False)))


if __name__ == '__main__':
    main()
