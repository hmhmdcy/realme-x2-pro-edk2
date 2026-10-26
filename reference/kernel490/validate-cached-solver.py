"""One host-only r33-cache -> r34 dependency simulation; never install packages."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import traceback
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel490')
SOURCE = PRIVATE.parent / 'kernel481/runtime-collected-r1'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def entries(data):
    result = {}
    for block in data.decode().strip().split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
        name = fields['P']
        assert name not in result
        result[name] = dict(version=fields['V'], entry_sha256=hashlib.sha256(block.encode()).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, choices=['r2'])
    args = parser.parse_args()
    workspace = storage.workspace()  # 461 mounted_build guard before all WSL/ext4 access.
    attempt = 'cached-solver-' + args.attempt
    work = workspace / attempt
    evidence = PRIVATE / attempt
    report_path = HERE / (attempt + '-validation.json')
    assert not work.exists() and not evidence.exists() and not report_path.exists(), 'Preserve this single attempt'
    assert shutil.disk_usage(workspace.parent).free > 2 * 1024**3 + 32 * 1024**2
    evidence.mkdir(mode=0o700)
    work.mkdir(mode=0o700)
    root = work / 'root'
    root.mkdir(mode=0o700)
    apk = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
    keys = PRIVATE.parent / 'kernel475/isolated-union-public-keys'
    repo = PRIVATE / 'repository-r1/forward'
    cache = work / 'cache'
    cache.mkdir(mode=0o700)
    report = dict(stage=490, attempt=attempt, passed=False,
                  scope='host APK simulation against a copy of cached real481 forward-final r33/r28 DB/world',
                  package_transaction_performed=False, current_phone_state_proven=False,
                  install_or_rollback_tested=False, sdk_accessed=False, device_accessed=False,
                  dependency_or_signature_bypass_used=False, fake_providers_used=False,
                  scripts_or_hooks_disabled_by_flags=False, commands=[])
    source_paths = {
        'lib/apk/db/installed': SOURCE / 'forward-final-installed-db-forensic.txt',
        'etc/apk/world': SOURCE / 'forward-final-world-forensic.txt',
    }
    source_before = {name: sha(path) for name, path in source_paths.items()}
    original_candidate = HERE / 'candidate-state.json'
    report['candidate_at_repack_sha256'] = sha(original_candidate)
    report['source_cached_files'] = {name: dict(path=str(path), bytes=path.stat().st_size, sha256=source_before[name])
                                     for name, path in source_paths.items()}
    public_report = json.loads((HERE / 'package-r1-validation.json').read_text())
    initial = json.loads(original_candidate.read_text())
    assert public_report['passed'] and sha(HERE / 'package-r1-validation.json') == initial['public_files_sha256']['package-r1-validation.json']
    expected_repo = {row['file']: row['sha256'] for row in public_report['packages']}
    expected_repo['packages.adb'] = public_report['index_sha256']['forward']
    identity = json.loads((PRIVATE / 'tool-identity-private.json').read_text())
    assert sha(apk) == identity['host_apk_sha256']
    key_before = {path.name: sha(path) for path in sorted(keys.iterdir())}
    assert key_before == identity['public_keys_sha256']
    repo_before = {path.name: sha(path) for path in sorted(repo.iterdir())}
    assert repo_before == expected_repo
    report.update(host_apk_sha256=sha(apk), public_key_set_sha256=key_before,
                  repository_files_sha256=repo_before,
                  actual481_audit_sha256=sha(HERE.parent / 'kernel484/hardware-validation.json'))
    audit = json.loads((HERE.parent / 'kernel484/hardware-validation.json').read_text())
    assert audit['passed'] and audit['collected_files'] == 234
    report.update(source_collected_archive_sha256=audit['collected_archive_sha256'],
                  source_actual_worker_state_sha256=audit['state_sha256'])
    for name, path in source_paths.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o600)
        assert sha(target) == source_before[name]
    baseline = entries((root / 'lib/apk/db/installed').read_bytes())
    versions = {row['name']: row['version'] for row in public_report['packages']}
    rollback = public_report['rollback_versions']
    assert len(baseline) == 961 and all(baseline[name]['version'] == version for name, version in rollback.items())
    pins = [name + '=' + version for name, version in sorted(versions.items())]
    report.update(cached_installed_entries=961, cached_noncohort_entries=954,
                  baseline_cohort=rollback, requested_pins=pins,
                  baseline_world_sha256=source_before['etc/apk/world'])
    (evidence / 'inputs-private.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(arguments, label, timeout=60):
        started = time.monotonic()
        result = subprocess.run(arguments, capture_output=True, timeout=timeout,
                                env={**os.environ, 'LC_ALL': 'C'})
        stdout = evidence / (label + '-stdout-private.txt')
        stderr = evidence / (label + '-stderr-private.txt')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        report['commands'].append(dict(label=label, argv=arguments, exit_code=result.returncode,
                                       elapsed_seconds=round(time.monotonic() - started, 3),
                                       stdout_sha256=sha(stdout), stderr_sha256=sha(stderr)))
        assert result.returncode == 0, label + ': nonzero exit; preserve original failure'
        return result

    try:
        version = run([str(apk), '--version'], 'version')
        assert version.stdout.decode().strip() == identity['version']
        # Reuse the actual481/480 repositories-file contract. --repository does not accept the ndx directive.
        repos = work / 'repositories-private.list'
        repos.write_text('ndx file://' + str(repo / 'packages.adb') + '\n')
        repos.chmod(0o600)
        report['repositories_file_sha256'] = sha(repos)
        report['prior_cli_failure_report_sha256'] = sha(HERE / 'cached-solver-r1-validation.json')
        command = [str(apk), '--root', str(root), '--arch', 'aarch64', '--keys-dir', str(keys),
                   '--repositories-file', str(repos),
                   '--cache-dir', str(cache), '--logfile=no', '--no-network', '--simulate', 'add', *pins]
        result = run(command, 'simulate', timeout=90)
        lines = result.stdout.decode().splitlines()
        changes = []
        for line in lines:
            match = re.fullmatch(r'\((\d+)/(\d+)\) Upgrading ([^ ]+) \(([^ ]+) -> ([^)]+)\)', line)
            if match:
                ordinal, total, name, old, new = match.groups()
                changes.append(dict(number=int(ordinal), total=int(total), name=name, old=old, new=new))
        assert len(changes) == 7, 'Expected exactly seven native upgrade plan rows'
        assert [row['number'] for row in changes] == list(range(1, 8)) and all(row['total'] == 7 for row in changes)
        assert {row['name']: row['old'] for row in changes} == rollback
        assert {row['name']: row['new'] for row in changes} == versions
        assert len(lines) == 8 and re.fullmatch(r'OK: .+ in 961 packages', lines[-1]), 'Unexpected additional plan output'
        report.update(native_upgrade_plan=changes, planned_updates=7, planned_new_installs=0,
                      planned_removals=0, planned_noncohort_changes=0, simulation_exit_code=0)
        report['passed'] = True
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        report['source_cached_files_unchanged'] = source_before == {name: sha(path) for name, path in source_paths.items()}
        report['isolated_db_world_unchanged'] = source_before == {name: sha(root / name) for name in source_paths}
        after = entries((root / 'lib/apk/db/installed').read_bytes())
        report['isolated_all_961_entries_unchanged'] = after == baseline
        report['isolated_noncohort_entries_unchanged'] = len([name for name in baseline if name not in versions and baseline[name] == after.get(name)])
        report['public_keys_unchanged'] = key_before == {path.name: sha(path) for path in sorted(keys.iterdir())}
        report['repository_unchanged'] = repo_before == {path.name: sha(path) for path in sorted(repo.iterdir())}
        report['free_bytes_after'] = shutil.disk_usage(workspace.parent).free
        report['passed'] &= all(report[key] for key in ['source_cached_files_unchanged', 'isolated_db_world_unchanged',
                                                       'isolated_all_961_entries_unchanged', 'public_keys_unchanged', 'repository_unchanged'])
        report['passed'] &= report['isolated_noncohort_entries_unchanged'] == 954 and report['free_bytes_after'] > 2 * 1024**3
        report['tool_sha256'] = sha(__file__)
        (evidence / 'result-private.json').write_text(json.dumps(report, indent=2) + '\n')
        report['private_result_sha256'] = sha(evidence / 'result-private.json')
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(stage=490, cached_solver=report['passed'], commands=[(row['label'], row['exit_code']) for row in report['commands']],
                          report_sha256=sha(report_path))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
