"""Validate a PM candidate against a copied, previously validated r0 fixture."""
from pathlib import Path
import argparse
import json
import os
import runpy
import shutil
import subprocess
from hardening import HERE, load_lock, require, sha, validate_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['first', 'second', 'baseline-fixture', 'candidate-lock', 'apk', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(os.geteuid() == 0 and args.build_root.is_absolute() and not args.build_root.exists(), 'Use a new isolated Linux directory')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem')
    args.build_root.mkdir(parents=True, mode=0o700)
    root = args.build_root / 'root'
    shutil.copytree(args.baseline_fixture, root)
    lock = load_lock()
    candidate = json.loads(args.candidate_lock.read_text())
    manifest = json.loads((args.first.parent / 'package-manifest.json').read_text())
    require(args.first.read_bytes() == args.second.read_bytes(), 'PM candidate builds differ')
    require(sha(args.first.read_bytes()) == manifest['package_sha256'], 'Candidate manifest mismatch')
    baseline = {r['name']: sha((root / r['target']).read_bytes()) for r in lock['modules']}
    require(all(baseline[r['name']] == r['sha256'] for r in lock['modules']), 'Not a current r0 fixture')

    def run(command, label, success=True):
        result = subprocess.run([str(x) for x in command], capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require((result.returncode == 0) == success, label + ' unexpected status')

    run([args.apk, '--keys-dir', args.verification_keys, 'verify', args.first], 'verify')
    hook = runpy.run_path(str(HERE / 'build-apk.py'))['adoption_hook'](lock, True)
    require(sha(hook) == manifest['adoption_hook_sha256'], 'Test hook differs from candidate package')
    (root / 'guard').write_bytes(hook)
    pgrep = root / 'bin/pgrep'

    def process_state(status):
        pgrep.write_text('#!/bin/sh\nexit ' + str(status) + '\n')
        pgrep.chmod(0o755)

    process_state(1)  # Explicit no-process result; 0 and tool errors must fail.
    run(['chroot', root, '/bin/sh', '/guard'], 'stopped-current-baseline')
    module_state = root / 'sys/module/hci_uart'
    module_state.mkdir(parents=True)
    run(['chroot', root, '/bin/sh', '/guard'], 'loaded-module-rejected', False)
    module_state.rmdir()
    process_state(0)
    run(['chroot', root, '/bin/sh', '/guard'], 'running-daemon-rejected', False)
    process_state(2)
    run(['chroot', root, '/bin/sh', '/guard'], 'process-query-error-rejected', False)
    process_state(1)
    run([args.apk, '--root', root, '--keys-dir', args.verification_keys, '--arch', 'aarch64',
         '--no-scripts', '--no-network', 'add', args.first], 'offline-upgrade')
    changed = [r['name'] for r in lock['modules'] if sha((root / r['target']).read_bytes()) != baseline[r['name']]]
    require(changed == ['hci_uart'], 'Unexpected module change set')
    record = dict(next(r for r in lock['modules'] if r['name'] == 'hci_uart'), sha256=candidate['module_sha256'], bytes=candidate['module_bytes'])
    module = validate_module((root / record['target']).read_bytes(), record, lock)
    for name, entry in manifest['files'].items():
        path = root / name
        require(sha(path.read_bytes()) == entry['sha256'] and path.stat().st_mode & 0o777 == entry['mode'], 'Installed candidate differs')
    run(['chroot', root, '/bin/sh', '/guard'], 'repeat-transition-rejected', False)
    report = dict(schema=1, package=manifest['package'], package_sha256=manifest['package_sha256'],
                  independent_signed_builds_byte_identical=True, trusted_signature_verified=True,
                  stopped_r0_baseline_guard_passed=True, loaded_hci_uart_rejected=True,
                  running_bluetoothd_rejected=True, pgrep_error_rejected=True,
                  only_hci_uart_module_changed=True, module=module,
                  offline_r0_to_candidate_upgrade_passed=True, all_candidate_files_modes_verified=True,
                  repeat_transition_after_candidate_rejected=True, current_owner_requires_device_window=True,
                  process_and_module_state_are_model_fixtures=True, offline_installation_scripts_disabled=True,
                  device_install_performed=False, real_pm_or_bluetooth_acceptance=False)
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
