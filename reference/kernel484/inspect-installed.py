"""Audit cached481 installation originals; no phone, SDK or target-code execution."""
from pathlib import Path, PurePosixPath
import argparse
import ast
import hashlib
import importlib.util
import json
import re
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
read = lambda path: json.loads(Path(path).read_bytes())
PHASES = [('forward-first', 'forward'), ('rollback-exact', 'rollback'), ('forward-final', 'forward')]
CASES = {'s5kgw1-gst', 'imx319-gst', 's5k3m5-gst', 'imx471-gst',
         's5kgw1-raw', 's5k3m5-raw', 's5kgw1-dual'}
CORE = '/usr/lib/libcamera.so.0.7.2'
BASE = '/usr/lib/libcamera-base.so.0.7.2'
IPA = '/usr/lib/libcamera/ipa/ipa_camss_vfe.so'
PLUGIN = '/usr/lib/gstreamer-1.0/libgstlibcamera.so'


def database(path):
    result = {}
    for block in Path(path).read_bytes().split(b'\n\n'):
        if not block.strip():
            continue
        lines = block.splitlines()
        names = [line[2:].decode() for line in lines if line.startswith(b'P:')]
        assert len(names) == 1 and names[0] not in result
        result[names[0]] = lines
    return result


def versions(entries, names):
    return {name: next(line[2:].decode() for line in entries[name] if line.startswith(b'V:')) for name in names}


def idle(value, expected_refs=0):
    assert not any(value['status'][key] for key in ['users', 'running', 'fatal', 'pinned', 'orphans', 'first_error'])
    assert value['status']['owner_refs'] == expected_refs
    assert not any(value['core'][key] for key in ['backing_owned', 'cpu_enabled', 'irq_enabled', 'power_held',
        'remaining_groups', 'remaining_domains', 'mapped_bytes', 'ipe_dma_pending', 'request_fw_mapped', 'imported_buffers', 'imported_bytes'])
    assert set(value['pm'].values()) == {'suspended'}


def installed(value, expected):
    assert value['packages'] == expected['packages']
    assert set(value['runtime']) == set(expected['runtime_files'])
    for path, digest in expected['runtime_files'].items():
        assert value['runtime'][path] == dict(sha256=digest, resolved=path)
    assert value['modules'] == expected['modules'] and value['profiles'] == expected['profiles']


def world_parts(data, names):
    found, other = {}, []
    for line in data.splitlines(keepends=True):
        stripped = line.rstrip(b'\r\n')
        match = re.fullmatch(rb'([A-Za-z0-9_.+-]+)(?:@[^<>=~\s]+)?(?:[<>=~].*)?', stripped)
        name = match[1].decode() if match else None
        if name in names:
            assert name not in found
            found[name] = stripped.decode()
        else:
            other.append(line)
    return found, other


def mapped_process(identity, expected, program=None):
    assert all(int(n) == 10000 for n in identity['uid'].split()) and int(identity['capeff'], 16) == 0
    assert '(deleted)' not in identity['maps']
    mapped = sorted({line.split(None, 5)[5] for line in identity['maps'].splitlines()
                     if len(line.split(None, 5)) == 6 and line.split(None, 5)[5].startswith('/')})
    assert mapped == identity['mapped']
    assert all(path in mapped for path in [CORE, BASE, IPA])
    for path in mapped:
        if any(token in path for token in ['libcamera', 'ipa_camss', 'camss_ipa_proxy']):
            assert path in expected['runtime_files']
    if program:
        assert Path(identity['exe']).name == program
        assert identity['exe_sha256'] == expected['probe_tools'][program]['sha256']
    if program == 'gst-sustained':
        assert PLUGIN in mapped
    assert not any(key.startswith('LIBCAMERA_') and key != 'LIBCAMERA_LOG_LEVELS'
                   for key in identity['camera_environment'])


def inspect(private):
    original = private / 'runtime-collected-r1'
    bound = private / 'k481-package-adoption-r1-bound'
    prepared, plan, state = [read(path) for path in [bound / 'preparation-private.json', original / 'plan-private.json', original / 'state-private.json']]
    assert sha(original / 'plan-private.json') == sha(bound / 'plan-private.json') == prepared['plan_sha256']
    assert prepared['prepared'] and prepared['deployable'] and plan['deployable']
    assert sha(bound / 'worker.py') == prepared['worker_sha256']
    candidate_path = HERE.parent / 'kernel475/candidate-state.json'
    candidate = read(candidate_path)
    assert sha(candidate_path) == plan['candidate_state_sha256']
    for name, digest in candidate['public_files_sha256'].items():
        assert sha(candidate_path.parent / name) == digest
    manifest_path = private.parent / 'kernel475/cohort-r2-manifest-private.json'
    manifest = read(manifest_path)
    assert sha(manifest_path) == plan['cohort_manifest_sha256']
    for key in ['release', 'modules', 'profiles', 'forward_packages', 'rollback_packages']:
        assert plan['cohort'][key] == manifest[key]
    for name, digest in prepared['source_sha256'].items():
        assert sha(HERE.parent / name) == digest
    assert state['terminal'] and state['passed'] and state['installed'] and state['phase'] == 'complete'
    assert state['active_child'] is None and not state['unknown_state'] and not state['manual_inspection_required']
    assert state['failure'] is None and not state.get('cleanup_failure') and not state['new_faults'] and state['taint_after'] == 0
    assert state['final_baseline'] == 'r33-r28-candidate' and state['exact_rollback_verified'] and state['rollback_database_semantics_verified']
    assert [(row['phase'], row['kind']) for row in state['phases']] == PHASES
    assert all(row['verified'] for row in state['phases']) and len(state['quiescence']) == 3
    assert all(row['no_live_camera_fds'] and row['ownership_zero_or_module_absent'] and row['idle_verified'] for row in state['quiescence'])

    archives = list(private.glob('collect-stdout-*-private.tar.gz'))
    assert len(archives) == 1
    with tarfile.open(archives[0]) as stream:
        members = stream.getmembers()
        names = [member.name for member in members]
        assert len(names) == len(set(names))
        assert set(names) == {path.relative_to(original).as_posix() for path in original.rglob('*') if path.is_file()}
        for member in members:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts and '\\' not in member.name
            assert hashlib.sha256(stream.extractfile(member).read()).hexdigest() == sha(original / member.name)
    backup = original / 'backup'
    attributes = read(backup / 'original-attributes-private.json')
    for path, row in attributes.items():
        if row['type'] == 'file':
            assert sha(backup / path.lstrip('/')) == row['sha256']
    cohort = plan['cohort']
    old_db = database(backup / 'forensic-apk-db/installed')
    names = set(cohort['forward_packages'])
    old_other = {k: v for k, v in old_db.items() if k not in names}
    transactions = []
    result_files = list(original.glob('*-result-private.json'))
    for file in result_files:
        result = read(file)
        label = file.name.removesuffix('-result-private.json')
        assert result['exit_code'] == 0 and not result['finished_after_deadline']
        for channel in ['stdout', 'stderr']:
            assert sha(original / (label + '-' + channel + '-private.txt')) == result[channel + '_sha256']
    for label, kind in PHASES:
        result = read(original / (label + '-packages-result-private.json'))
        argv = result['argv']
        assert argv[0] == '/sbin/apk' and argv.count('add') == 1 and '--no-network' in argv
        assert not any(flag in argv for flag in ['--simulate', '--allow-untrusted', '--no-scripts', '--no-commit-hooks'])
        pins = cohort[kind + '_packages']
        assert argv[argv.index('add') + 1:] == [name + '=' + version for name, version in sorted(pins.items())]
        current = database(original / (label + '-installed-db-forensic.txt'))
        assert versions(current, names) == pins
        assert {k: v for k, v in current.items() if k not in names} == old_other
        if kind == 'rollback':
            assert current == old_db
            assert (original / (label + '-world-forensic.txt')).read_bytes() == (backup / 'etc/apk/world').read_bytes()
        proof = read(original / (label + '-proof-private.json'))
        assert proof['kind'] == kind and proof['packages'] == pins and proof['noncohort_database_entries_unchanged']
        assert proof['installed_database_sha256'] == sha(original / (label + '-installed-db-forensic.txt'))
        assert proof['world_sha256'] == sha(original / (label + '-world-forensic.txt'))
        assert proof['package_files_checked'] == len(plan['package_files'][kind])
        for row in cohort['modules']:
            actual = proof['modules'][row['name']]
            assert actual['file']['sha256'] == row[kind + '_sha256'] and actual['note_sha256'] == row[kind + '_note_sha256']
            assert actual['file']['uid'] == actual['file']['gid'] == 0 and actual['file']['mode'] == 0o644
        for row in cohort['profiles']:
            actual = proof['profiles'][row['model']]
            assert actual['sha256'] == row[kind + '_sha256'] and actual['uid'] == actual['gid'] == 0 and actual['mode'] == 0o644
        for action, order in [('unload', ['qcom_camss', 'camss_icp_a5_m2m', 'qcom_camss_icp_a5_core', 's5k3m5']),
                              ('load', ['s5k3m5', 'qcom_camss_icp_a5_core', 'camss_icp_a5_m2m', 'qcom_camss'])]:
            for name in order:
                command = read(original / (label + '-' + action + '-' + name + '-result-private.json'))['argv']
                assert command[0] == ('rmmod' if action == 'unload' else 'insmod')
        transactions.append(dict(phase=label, kind=kind, native_apk_exit_code=0, packages=pins,
            noncohort_entries_unchanged=len(old_other), exact_original_database_entries=(kind == 'rollback')))

    audit_path = HERE.parent / 'kernel482/probe-log-audit.py'
    assert sha(audit_path) == '357e57fc91ec61a69b3acc66aa2dfd4c0ef1046c2363f49a208ddf5a7b4cd94e'
    spec = importlib.util.spec_from_file_location('cached_log484', audit_path)
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)
    cases, all_warnings, fallback_messages = [], [], 0
    expected = plan['expected_forward']
    for phase in ['forward-first', 'forward-final']:
        directory = original / ('default-probe-' + phase)
        report = read(directory / 'probe-report-private.json')
        assert report == state['default_probes'][phase] and report['passed']
        assert not report['force_isolation_overridden'] and not report['private_library_or_profile_override']
        assert set(report['cases']) == CASES and report['installed_before'] == report['installed_after']
        installed(report['installed_before'], expected)
        idle(report['idle_before']); idle(report['idle_after'])
        for name, recorded in report['cases'].items():
            log = directory / name / 'client.log'
            witness_path = directory / name / 'live-witness-private.json'
            assert sha(log) == recorded['log_sha256'] and sha(witness_path) == recorded['witness_sha256']
            assert recorded['exit_code'] == 0 and recorded['user_directory_removed']
            idle(recorded['idle_before']); idle(recorded['idle_after'])
            text = log.read_text()
            fallback_messages += text.count("libcamera is not installed. Adding '//src/ipa' to the IPA search path")
            checked = auditor.audit(text, model=recorded['model'], kind=recorded['kind'],
                before=recorded['idle_before']['status'], after=recorded['idle_after']['status'])
            assert all(checked[key] == recorded[key] for key in checked)
            witness = read(witness_path)
            assert witness['passed'] and witness['branch'] == 'native-valid-signature'
            assert witness['application_pid'] == witness['ipa_pid'] and not witness['configuration_forced']
            assert set(witness['signature_results']) == {'valid'} and len(witness['processes']) == 1
            program = 'gst-sustained' if recorded['kind'] == 'gst' else 'pipeline-smoke'
            mapped_process(witness['processes'][0], expected, program)
            lease = witness['manager_lease']
            stop = checked['capacity_stop'][0]
            if checked['capacity_start']:
                assert lease['active'] and lease['status'] == 0 and lease['users'] == 1
                assert lease['live_affinity'] == list(map(int, lease['selected'].split(',')))
                assert lease['thread_start_ticks'] > 0
                start = checked['capacity_start'][0]
                assert int(start['tid']) == lease['tid'] and start['selected'] == lease['selected']
                assert stop['reason'] == 'restored' and stop['original'] == lease['original']
            else:
                assert recorded['kind'] == 'raw' and lease is None and stop['reason'] == 'inactive'
            all_warnings.extend(checked['warnings_and_errors'])
            cases.append(dict(phase=phase, name=name, **{key: checked[key] for key in [
                'model', 'kind', 'frames', 'delivered_sofs', 'ipe_delta', 'history', 'queues', 'successful_receipts', 'stop_classes',
                'bootstrap', 'numerical_prepares', 'numerical_commits', 'numerical_stop_aborted_tokens', 'extra_successful_processed_sofs']},
                log_sha256=sha(log), witness_sha256=sha(witness_path), native_signed_default_paths=True,
                manager_live_mask=lease['selected'] if lease else None, manager_stop_reason=stop['reason'],
                warnings_and_errors=len(checked['warnings_and_errors'])))

    health_path = private / 'final-health-r2-private.json'
    health = read(health_path)
    assert health['passed'] and health['candidate_installed'] and not health['original_recovered']
    assert health['state_sha256'] == sha(original / 'state-private.json') and health['worker_absent_or_zombie']
    assert not health['new_faults'] and health['packages'] == cohort['forward_packages'] == state['packages']
    installed(health['files'], expected)
    baseline_refs = read(original / 'baseline-private.json')['status']['owner_refs']
    idle(health['camera_before'], baseline_refs); idle(health['camera_after'], baseline_refs)
    assert health['camera_before'] == health['camera_after']
    policy = health['apk_policy']
    old_world = (backup / 'etc/apk/world').read_bytes()
    final_world = policy['world_text'].encode()
    assert hashlib.sha256(final_world).hexdigest() == policy['world']['sha256']
    found, others = world_parts(final_world, names)
    assert found == {name: name + '=' + value for name, value in cohort['forward_packages'].items()}
    assert others == world_parts(old_world, names)[1]
    for key in ['uid', 'gid', 'mode', 'type']:
        assert policy['world'][key] == attributes['/etc/apk/world'][key]
    assert policy['repositories'] == attributes['/etc/apk/repositories']
    original_repos = {path: row for path, row in attributes.items() if path.startswith('/etc/apk/repositories.d/')}
    new_repo = plan['persistent_repository_file']
    assert set(policy['repository_entries']) == set(original_repos) | {new_repo}
    assert all(policy['repository_entries'][path] == row for path, row in original_repos.items())
    new_repo_bytes = ('ndx file://' + plan['persistent_repository_dir'] + '/packages.adb\n').encode()
    assert policy['repository_entries'][new_repo] == dict(type='file', uid=0, gid=0, mode=0o644,
        sha256=hashlib.sha256(new_repo_bytes).hexdigest(), bytes=len(new_repo_bytes))
    repo_files = {name.rsplit('/', 1)[1]: digest for name, digest in plan['payload_sha256'].items() if name.startswith('forward/repository/')}
    assert set(policy['persistent_repository_files']) == set(repo_files) and len(repo_files) == 8
    for name, digest in repo_files.items():
        row = policy['persistent_repository_files'][name]
        assert row['sha256'] == digest and row['uid'] == row['gid'] == 0 and row['mode'] == 0o644 and row['type'] == 'file'
    assert policy['installed_database']['sha256'] == sha(original / 'forward-final-installed-db-forensic.txt')
    assert policy['installed_database']['uid'] == policy['installed_database']['gid'] == 0
    solver = read(original / 'final-default-repositories-solver-result-private.json')
    assert '--simulate' in solver['argv'] and '--repositories-file' not in solver['argv']

    deleted = []
    for name, identity in health['services'].items():
        assert identity['pid'] == state['final_services'][name]['pid']
        assert identity['start_ticks'] == int(state['final_services'][name]['start_ticks'])
        assert all(int(value) == 10000 for value in identity['uid'].split()) and int(identity['capeff'], 16) == 0
        for line in identity['maps'].splitlines():
            if '(deleted)' in line:
                fields = line.split(None, 5)
                assert len(fields) == 6 and fields[5].startswith('/memfd:pipewire-memfd:') and 'x' not in fields[1]
                deleted.append(dict(service=name, permissions=fields[1]))
        assert not identity['camera_environment']
    assert all(path in health['services']['wireplumber']['mapped'] for path in [CORE, BASE])
    prior_deleted = [line for line in (original / 'final-wireplumber-maps-private.txt').read_text().splitlines() if '(deleted)' in line]
    assert len(prior_deleted) == 8 and all(line.split(None, 5)[5].startswith('/memfd:pipewire-memfd:') and 'x' not in line.split()[1] for line in prior_deleted)
    assert (private / 'final-health-r1-private.json').read_bytes() == b''
    assert 'in process\nAssertionError' in (private / 'final-health-r1-stderr-private.txt').read_text()
    summary = health['health_audit']
    assert summary['passed'] and summary['sample_count'] == 2 and summary['same_boot'] and summary['taint'] == 0
    assert not any(summary['fault_delta'].values()) and summary['limits_unchanged'] and summary['camera_and_four_services_unchanged']
    assert health['charging'] == plan['handoff']['charging']
    assert not health['long_endurance_or_optics_validated']
    health_query = private / 'final-health-r2-query-private.py'
    ast.parse(health_query.read_bytes())
    warning_patterns = dict(configuration_lookup='Failed to open configuration file',
        missing_static_properties='No static properties available', properties_database_advice='Please consider updating the camera sensor properties database',
        missing_rotation_control='Rotation control not available', unsupported_bus_format='Unsupported media bus format 0x2027',
        unknown_subdev_format='Unknown subdev format 0x2027')
    warning_counts = {name: sum(token in line for line in all_warnings) for name, token in warning_patterns.items()}
    assert sum(warning_counts.values()) == len(all_warnings)
    return dict(stage=484, passed=True, scope='independent cached-original audit of actual481 transactions and482 installed default probes',
        collected_archive_sha256=sha(archives[0]), collected_archive_bytes=archives[0].stat().st_size, collected_files=len(members),
        bound_worker_sha256=prepared['worker_sha256'], bound_plan_sha256=prepared['plan_sha256'], state_sha256=sha(original / 'state-private.json'),
        transactions=transactions, successful_command_receipts=len(result_files), exact_rollback_database_entries=True,
        noncohort_database_entries=len(old_other), backup_file_hashes_verified=sum(row['type'] == 'file' for row in attributes.values()),
        private_original_symlink_metadata_retained=sum(row['type'] == 'symlink' for row in attributes.values()),
        final_world_only_seven_pins_changed=True, original_repositories_and_attributes_preserved=True,
        persistent_signed_repository_files=8, native_default_repository_solver_passed=True, cases=cases,
        gst_delivered_frames=sum(row['frames'] for row in cases if row['kind'] == 'gst'),
        raw_only_frames=sum(row['frames'] for row in cases if row['kind'] == 'raw'),
        dual_frame_pairs=sum(row['frames'] for row in cases if row['kind'] == 'dual'),
        ipe_completed=sum(row['ipe_delta']['completed'] for row in cases),
        general_negative_receipts=sum(row['stop_classes']['queued_failed_receipts'] + row['stop_classes']['unqueued_failed_receipts'] for row in cases),
        warnings_and_errors_retained=len(all_warnings), warning_classes=warning_counts,
        build_tree_ipa_fallback_info_messages=fallback_messages,
        external_health_r1_failed_at_overbroad_deleted_map_assertion=True,
        external_health_r2_sha256=sha(health_path), external_health_r2_passed=True,
        external_health_r2_query_sha256=sha(health_query), external_health_r2_host_sha256=sha(private / 'final-health-r2-host-private.py'),
        permitted_nonexec_pipewire_memfd_deleted_maps=deleted, health_samples=summary['sample_count'], health_seconds=summary['duration_seconds'],
        final_running_services_owner_refs=baseline_refs, probe_cleanup_and_pre_unload_owner_refs_zero=True,
        faults=0, taint=0, default_native_signed_usr_paths_verified=True, phone_accessed_by_inspector=False, sdk_accessed_by_inspector=False,
        limits=['finite two-phase default640 and necessary RAW probes; no new720p/1080p or isolation matrix',
                'no reboot persistence, endurance, optics or image-quality proof',
                'UID10000 probe inherited HOME=/root; normal user HOME personal configuration override not validated',
                'build-tree //src/ipa search fallback INFO retained; actual IPA and libraries were signed /usr paths',
                'native scripts/hooks enabled, cohort scripts absent; exercise not claimed',
                'module order established by frozen sequential worker plus successful receipts, not independent timestamp trace'],
        inspector_sha256=sha(__file__), cached_log_auditor_sha256=sha(audit_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve earlier receipts'
    result = inspect(args.private_root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['stage', 'passed', 'collected_files', 'gst_delivered_frames', 'raw_only_frames', 'dual_frame_pairs', 'ipe_completed', 'general_negative_receipts']}))


if __name__ == '__main__':
    main()
