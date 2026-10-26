"""Read cached481 preparation only; never imports or executes target code."""
from pathlib import Path, PurePosixPath
import argparse
import ast
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def literal_assignment(text, name):
    matches = [node for node in ast.parse(text).body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    assert len(matches) == 1, name
    return ast.literal_eval(matches[0].value)


def inspect(work, require_current_sources=False):
    prepared = json.loads((work / 'preparation-private.json').read_bytes())
    plan = json.loads((work / 'plan-private.json').read_bytes())
    assert prepared['prepared'] and prepared['stage'] == plan['stage'] == 481
    assert plan['window_id'] == 'k481-package-adoption-r1'
    assert plan['target_root'] == '/var/lib/samurai/k481-package-adoption-r1'
    assert prepared['deployable'] == plan['deployable']
    assert sha(work / 'worker.py') == prepared['worker_sha256']
    assert sha(work / 'plan-private.json') == prepared['plan_sha256']
    ast.parse((work / 'worker.py').read_text())
    for action, digest in prepared['query_sha256'].items():
        assert sha(work / (action + '-query.py')) == digest
        ast.parse((work / (action + '-query.py')).read_text())
    stage = (work / 'stage-query.py').read_text()
    expected = literal_assignment(stage, 'expected')
    modes = literal_assignment(stage, 'modes')
    assert literal_assignment(stage, 'plan') == plan
    assert set(expected) == set(plan['payload_sha256']) | {'plan-private.json'}
    assert expected['plan-private.json'] == prepared['plan_sha256']
    assert all(expected[name] == digest for name, digest in plan['payload_sha256'].items())
    archive = work / 'payload-private.tar.gz'
    assert sha(archive) == prepared['archive_sha256'] and archive.stat().st_size == prepared['archive_bytes']
    file_count, directory_count = 0, 0
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        assert len({m.name for m in members}) == len(members)
        assert {m.name for m in members if m.isfile()} == set(expected)
        for member in members:
            name = PurePosixPath(member.name)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in member.name
            assert member.uid == member.gid == 0
            if member.isdir():
                assert member.mode == 0o700
                directory_count += 1
            else:
                assert member.isfile() and member.mode == modes[member.name]
                assert hashlib.sha256(stream.extractfile(member).read()).hexdigest() == expected[member.name]
                file_count += 1
    assert file_count == prepared['files']
    candidate_path = HERE.parent / 'kernel475/candidate-state.json'
    candidate = json.loads(candidate_path.read_bytes())
    assert sha(candidate_path) == plan['candidate_state_sha256'] == prepared['candidate_state_sha256']
    for path, digest in candidate['public_files_sha256'].items():
        assert sha(HERE.parent / 'kernel475' / path) == digest, path
    manifest_path = work.parent.parent / 'kernel475/cohort-r2-manifest-private.json'
    manifest = json.loads(manifest_path.read_bytes())
    assert sha(manifest_path) == plan['cohort_manifest_sha256']
    for key in ['release', 'modules', 'profiles', 'forward_packages', 'rollback_packages']:
        assert plan['cohort'][key] == manifest[key]
    for name, digest in manifest['files_sha256'].items():
        assert expected[name] == digest
    old = json.loads((HERE.parent / 'kernel440/current-state-validation.json').read_bytes())
    assert plan['cohort']['rollback_packages'] == old['packages']
    for row in plan['cohort']['modules']:
        if row['name'] == 's5k3m5':
            assert row['rollback_sha256'] == '966b29d8e05236ad3d123bdd60bf0202cc60886f60fc3186e06eda4df4059f29'
        else:
            assert row['rollback_sha256'] == old['modules'][row['name']]['sha256']
    for row in plan['cohort']['profiles']:
        assert row['rollback_sha256'] == old['private_profiles'][row['model']]
    source_drift = {name: dict(prepared=digest, current=sha(HERE.parent / name))
                    for name, digest in prepared['source_sha256'].items() if sha(HERE.parent / name) != digest}
    if plan['deployable'] or require_current_sources:
        assert not source_drift, ('Prepared sources are stale', source_drift)
    return dict(stage=483, scope='offline preparation material and syntax; no target execution',
                preparation_material_passed=True, prepared_deployable=plan['deployable'],
                files=file_count, directories=directory_count, archive_sha256=sha(archive),
                archive_bytes=archive.stat().st_size, worker_sha256=prepared['worker_sha256'],
                plan_sha256=prepared['plan_sha256'], query_sha256=prepared['query_sha256'],
                exact475_payload_and440_434_sensor_rollback=True, source_drift_since_preparation=source_drift,
                latest_sources_match=not source_drift,
                latest_source_gate_required=bool(plan['deployable'] or require_current_sources),
                native_apk_transaction_performed=False, phone_accessed=False, sdk_accessed=False,
                inspector_sha256=sha(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preparation', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-current-sources', action='store_true',
                        help='Required for a ready unbound template; always enforced for deployable preparations')
    args = parser.parse_args()
    result = inspect(args.preparation, args.require_current_sources)
    assert not args.output.exists(), 'Preserve prior reviews; select a new output'
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['preparation_material_passed', 'prepared_deployable', 'files', 'archive_sha256', 'source_drift_since_preparation']}))


if __name__ == '__main__':
    main()
