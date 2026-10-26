"""Validate a concrete offline491 payload and retained local evidence; no transport."""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, io, json, subprocess, sys, tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel491')
digest = lambda data: hashlib.sha256(data).hexdigest()
sha = lambda path: digest(Path(path).read_bytes())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def validate(work):
    prepared = json.loads((work/'preparation-private.json').read_bytes())
    plan_data = (work/'plan-private.json').read_bytes(); plan = json.loads(plan_data)
    assert prepared['prepared'] and prepared['stage'] == plan['stage'] == 491
    assert not prepared['deployable'] and not plan['deployable'], 'This check covers an unbound offline template'
    assert prepared['no_ssh'] and prepared['no_sdk'] and prepared['no_target_execution']
    assert sha(work/'plan-private.json') == prepared['plan_sha256']
    assert plan['window_id'] == 'k491-package-only-r1'
    assert plan['target_root'] == '/var/lib/samurai/' + plan['window_id']
    assert plan['source_sha256'] == prepared['source_sha256']
    for name, expected in plan['source_sha256'].items():
        assert sha(HERE/name) == expected, ('Source drift', name)
    assert sha(HERE.parent/'kernel490/candidate-state.json') == plan['candidate_state_sha256'] == prepared['candidate_state_sha256']
    assert not any(plan[key] for key in ['modules_or_private_profiles_replaced', 'persistent_repository_created', 'candidate_retained'])
    assert plan['preserve_repository_directories'] == ['/var/lib/samurai/camera-r33-r28-k481-r1']
    assert plan['promotion_deadline_seconds'] == 300 and plan['diagnostic_budget_seconds'] == 480
    package_files = plan['package_files']
    assert len(package_files['forward']) == len(package_files['rollback']) == 57
    assert package_files['forward'].keys() == package_files['rollback'].keys()
    changed = [name for name in package_files['forward'] if package_files['forward'][name] != package_files['rollback'][name]]
    assert changed == ['/usr/lib/libcamera.so.0.7.2']
    for family in ['modules', 'profiles']:
        assert len(plan['cohort'][family]) == 4
        for row in plan['cohort'][family]:
            assert row['forward_sha256'] == row['rollback_sha256']
            if family == 'modules':
                assert row['forward_note_sha256'] == row['rollback_note_sha256']
    builder = load(HERE/'prepare-runtime.py', 'prepare491_local_validation')
    assert plan['expected_forward']['cases'] == builder.cases()
    expected_worker, gate_source, charging = builder.compose_worker(plan['window_id'])
    worker = (work/'worker.py').read_bytes()
    assert worker == expected_worker.encode() and digest(worker) == prepared['worker_sha256']
    functions = {node.name for node in ast.parse(worker).body if isinstance(node, ast.FunctionDef)}
    assert not functions.intersection({'switch_modules', 'keep_forward', 'install_profile'})
    payload = (work/'payload-private.tar.gz').read_bytes()
    assert len(payload) == prepared['archive_bytes'] < 64*1024**2
    assert digest(payload) == prepared['archive_sha256']
    mapping = dict(plan['payload_sha256'], **{'plan-private.json': digest(plan_data)})
    assert len(mapping) == prepared['files'] == 23
    tools = set(plan['expected_forward']['probe_tools'])
    directories = {parent.as_posix() for name in mapping for parent in Path(name).parents if str(parent) != '.'}
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(mapping)+len(directories)
        assert {item.name for item in members} == set(mapping)|directories
        for item in members:
            assert not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
            assert item.uid == item.gid == 0
            if item.isdir():
                assert item.name in directories and item.mode == 0o700
            else:
                assert item.isfile() and item.mode == (0o755 if item.name in tools else 0o600)
                assert digest(archive.extractfile(item).read()) == mapping[item.name]
    unbound = []
    query_bytes = {}
    for action, expected in prepared['query_sha256'].items():
        path = work/(action+'-query.py'); source = path.read_bytes()
        assert digest(source) == expected; ast.parse(source); query_bytes[action] = len(source)
        if action in ['stage', 'launch']:
            # authorization() rejects deployable=false before boot, sysfs,
            # APK, target namespace or child-process access in either query.
            checked = subprocess.run([sys.executable, '-B', str(path)], stdin=subprocess.DEVNULL, capture_output=True)
            assert checked.returncode != 0 and not checked.stdout
            error = checked.stderr.decode()
            assert 'AssertionError' in error and 'authorization' in error and 'deployable' in error
            unbound.append(action)
    local_path = HERE/'local-validation.json'; local = json.loads(local_path.read_bytes())
    probe_path = PRIVATE/'probe-local-006.json'; probe = json.loads(probe_path.read_bytes())
    for receipt in [local, probe]:
        assert receipt['passed'] and receipt['stage'] == 491
        for name, expected in receipt['source_sha256'].items():
            assert sha(HERE/name) == expected, ('Local evidence source drift', name)
    assert not local['device_or_sdk_accessed'] and not local['actual_apk_or_services_executed']
    assert not probe['target_callback_executed'] and not probe['target_or_sdk_access']
    return dict(stage=491, passed=True, scope='concrete unbound archive and local preparation; no target execution',
        deployable=False, device_or_sdk_accessed=False, target_callback_executed=False,
        archive_bytes=len(payload), archive_sha256=digest(payload), files=len(mapping),
        worker_sha256=digest(worker), plan_sha256=digest(plan_data), source_sha256=plan['source_sha256'],
        prepared_archive_members_modes_hashes=True, worker_reconstructed_exactly=True,
        package_file_count=57, changed_package_files=changed, protected_modules_profiles_unchanged=True,
        cases=plan['expected_forward']['cases'], unbound_queries_rejected_before_target_io=unbound,
        query_source_bytes=query_bytes, original_repository_preserved=True, candidate_retained=False,
        local_transaction_evidence=dict(file=local_path.name, sha256=sha(local_path), scope=local['scope']),
        cached_probe_evidence=dict(file=probe_path.name, sha256=sha(probe_path), full_audits=len(probe['full_audits']),
            partial_protocol_audits=len(probe['protocol_only']), limitations=probe['limitations']),
        limitations=['No phone installation, rollback, service restart, live callback or image-quality proof',
            'New fresh owner/preflight and transport binding required before any device action'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    load(HERE.parent/'kernel461/storage.py', 'original491_validation_guard').mount.mounted_build()
    assert args.work.is_absolute() and args.work.parent == PRIVATE and args.work.is_dir()
    assert not args.output.exists(), 'Preserve prior validation outputs'
    report = validate(args.work)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps(dict(passed=True, receipt=str(args.output), sha256=sha(args.output))))


if __name__ == '__main__':
    main()
