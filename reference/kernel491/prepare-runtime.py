"""Prepare a new491 package-only transaction locally; never opens transport/SDK."""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, io, json, shutil, sys, tarfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel491')
HELPERS = ['sha', 'metadata', 'atomic', 'database', 'versions', 'unchanged_other_packages',
           'trust_inventory', 'idle', 'camera_fds', 'quiesce', 'faults']
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def function(text, name):
    return next(ast.get_source_segment(text, node) for node in ast.parse(text).body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def compose_worker(window):
    parent = HERE.parent / 'kernel481/worker-body.py'
    assert sha(parent) == 'ee8f17a36e7e69534d872dd44f6ed43edc46e82e65547621783157dc2cce1a83'
    original = parent.read_text()
    fragments = []
    for name in HELPERS:
        source = function(original, name)
        if name == 'atomic':
            source = source.replace('.k481-tmp', '.k491-tmp')
        if name == 'quiesce':
            source = source.replace('before any module operation', 'before any package operation')
        fragments.append(source)
    charging_path = HERE.parent / 'kernel451/capture-body-comparison.py'
    assert sha(charging_path) == 'a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff'
    charging = function(charging_path.read_text(), 'charging')
    authorization_source = (HERE / 'owner-gate.py').read_text()
    source = ('WINDOW=' + repr(window) + '\n' + authorization_source + '\n' +
              (HERE / 'runtime-common.py').read_text() + '\n' + '\n\n'.join(fragments) +
              '\n' + charging + '\n' + (HERE / 'worker-body.py').read_text())
    ast.parse(source)
    return source, authorization_source, charging


def cases():
    result = []
    for model in ['s5kgw1', 'imx319', 's5k3m5', 'imx471']:
        result.append(dict(name=model + '-640x480-native', model=model, width=640, height=480, frames=12, isolated=False))
    for width, height in [(1280, 720), (1920, 1080)]:
        for isolated in [False, True]:
            result.append(dict(name='s5kgw1-' + str(width) + 'x' + str(height) + ('-isolated' if isolated else '-native'),
                               model='s5kgw1', width=width, height=height, frames=12, isolated=isolated))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, choices=['r1', 'r2', 'r3'])
    parser.add_argument('--template-revision', type=int, choices=range(1, 10), default=1)
    parser.add_argument('--preflight-window-id', default='k476-control-delay-r4')
    for name in ['handoff', 'owner-return', 'scoped-owner-return']:
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    assert all([args.handoff, args.owner_return, args.scoped_owner_return]) or not any([args.handoff, args.owner_return, args.scoped_owner_return])
    guard = load(HERE.parent / 'kernel461/storage.py', 'guard491')
    guard.mount.mounted_build()
    candidate_path = HERE.parent / 'kernel490/candidate-state.json'
    candidate = json.loads(candidate_path.read_bytes())
    assert candidate['revision'] == 2 and candidate['candidate_prepared'] and candidate['dependency_solver_performed']
    for name, digest in candidate['public_files_sha256'].items():
        assert sha(HERE.parent / 'kernel490' / name) == digest
    old = PRIVATE.parent / 'kernel490'
    package_state_path = old / 'package-state-r1-private.json'
    assert sha(package_state_path) == candidate['private_package_state_sha256']
    packaged = json.loads(package_state_path.read_bytes())
    window = 'k491-package-only-' + args.attempt
    suffix = '-bound' if args.handoff else '-offline-template-r' + str(args.template_revision)
    work = PRIVATE / (window + suffix)
    assert not work.exists(), 'Keep a terminal/partial preparation; use a fresh template revision'
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    work.mkdir(mode=0o700)
    files = {}
    for kind in ['forward', 'rollback']:
        repository = old / 'repository-r1' / kind
        expected_index = candidate['index_sha256'][kind]
        assert sha(repository / 'packages.adb') == expected_index
        assert len(list(repository.glob('*.apk'))) == 7
        for path in repository.iterdir():
            assert path.is_file() and not path.is_symlink()
            files[kind + '/repository/' + path.name] = path
    package_files = {}
    for kind, key in [('rollback', 'before_files'), ('forward', 'after_files')]:
        combined = {}
        for item in packaged['inventories']:
            for relative, row in item[key].items():
                path = '/' + relative
                assert path not in combined
                combined[path] = row
        package_files[kind] = combined
    assert set(package_files['forward']) == set(package_files['rollback'])
    assert [path for path in package_files['forward'] if package_files['forward'][path] != package_files['rollback'][path]] == ['/usr/lib/libcamera.so.0.7.2']
    old_manifest = json.loads((PRIVATE.parent / 'kernel475/cohort-r2-manifest-private.json').read_bytes())
    modules, profiles = [], []
    for family, result in [('modules', modules), ('profiles', profiles)]:
        for old_row in old_manifest[family]:
            row = {key: value for key, value in old_row.items() if key not in ['rollback_sha256', 'rollback_note_sha256']}
            row['rollback_sha256'] = row['forward_sha256']
            if family == 'modules':
                row['rollback_note_sha256'] = row['forward_note_sha256']
            result.append(row)
    forward_packages = {row['name']: row['version'] for row in candidate_packages(candidate)}
    rollback_packages = {name: '0.1.0-r28' if name.startswith('samurai-camera-') else '99990.7.2-r33' for name in forward_packages}
    cohort = dict(release=old_manifest['release'], modules=modules, profiles=profiles,
                  forward_packages=forward_packages, rollback_packages=rollback_packages)
    worker, gate_source, charging = compose_worker(window)
    (work / 'worker.py').write_text(worker); files['worker.py'] = work / 'worker.py'
    for name in ['default-probe.py', 'probe-log-audit.py']:
        path = HERE / name
        ast.parse(path.read_text()); files[name] = path
    tools = {
        'pipeline-fixture': (PRIVATE.parent / 'kernel449/pipeline-fixture-long', 'bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43'),
        'gst-sustained': (PRIVATE.parent / 'kernel449/gst-sustained', '7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a'),
        'user-launcher.py': (HERE.parent / 'kernel486/user-launcher.py', '6c28bc2a9193c4adec64a9c0bde40d44589b360b83640ebe3f8dc1a4297b6446'),
    }
    probe_tools = {}
    for name, (path, digest) in tools.items():
        assert sha(path) == digest
        files[name] = path; probe_tools[name] = dict(path=name, sha256=digest)
    expected = dict(window_id=window, packages=forward_packages,
                    runtime_files={path: row['sha256'] for path, row in package_files['forward'].items() if 'sha256' in row},
                    modules=[dict(name=row['name'], path=row['path'], sha256=row['rollback_sha256'], note_sha256=row['rollback_note_sha256']) for row in modules],
                    profiles=[dict(model=row['model'], path=row['path'], sha256=row['rollback_sha256']) for row in profiles],
                    probe_tools=probe_tools, cases=cases())
    plan = dict(stage=491, window_id=window, target_root='/var/lib/samurai/' + window,
                preflight_window_id=args.preflight_window_id, deployable=bool(args.handoff),
                cohort=cohort, package_files=package_files, expected_forward=expected,
                payload_sha256={name: sha(path) for name, path in files.items()},
                minimum_target_free_bytes=512 * 1024**2, promotion_deadline_seconds=300, diagnostic_budget_seconds=480,
                preserve_repository_directories=['/var/lib/samurai/camera-r33-r28-k481-r1'],
                candidate_state_sha256=sha(candidate_path), package_inventory_source_sha256=sha(package_state_path),
                modules_or_private_profiles_replaced=False, persistent_repository_created=False,
                candidate_retained=False, source_sha256={name: sha(HERE / name) for name in
                    ['prepare-runtime.py', 'worker-body.py', 'runtime-common.py', 'owner-gate.py', 'render-queries.py', 'default-probe.py', 'probe-log-audit.py']})
    if args.handoff:
        plan.update(handoff=json.loads(args.handoff.read_bytes()), owner=json.loads(args.owner_return.read_bytes()),
                    scoped_owner=json.loads(args.scoped_owner_return.read_bytes()))
        baseline = args.handoff.parent / 'baseline-private.json'
        assert sha(baseline) == plan['handoff']['formal_baseline_sha256']
        files['baseline-private.json'] = baseline; plan['payload_sha256']['baseline-private.json'] = sha(baseline)
        for key in ['charging_manifest_private', 'provenance_private']:
            assert sha(plan['owner'][key]) == plan['owner'][key.replace('_private', '_sha256')]
        context = {'WINDOW': window}
        exec(gate_source, context)
        context['authorization'](plan, context['datetime'].now(context['timezone'].utc))
        plan['authorization_files_sha256'] = {str(path): sha(path) for path in [args.handoff, args.owner_return, args.scoped_owner_return]}
    (work / 'plan-private.json').write_text(json.dumps(plan, indent=2) + '\n'); files['plan-private.json'] = work / 'plan-private.json'
    modes = {name: (0o755 if name in tools else 0o600) for name in files}
    directories = sorted({parent.as_posix() for name in files for parent in Path(name).parents if str(parent) != '.'}, key=lambda value: (value.count('/'), value))
    archive = work / 'payload-private.tar.gz'
    with tarfile.open(archive, 'w:gz', format=tarfile.PAX_FORMAT) as tar:
        for name in directories:
            item = tarfile.TarInfo(name); item.type = tarfile.DIRTYPE; item.mode = 0o700; item.uid = item.gid = 0; tar.addfile(item)
        for name, path in sorted(files.items()):
            data = path.read_bytes(); item = tarfile.TarInfo(name); item.mode = modes[name]; item.uid = item.gid = 0; item.size = len(data); tar.addfile(item, io.BytesIO(data))
    assert archive.stat().st_size < 64 * 1024**2
    mapping = {name: sha(path) for name, path in files.items()}
    renderer = load(HERE / 'render-queries.py', 'renderer491')
    renderer.render(work, plan, mapping, modes, directories, sha(archive), gate_source, charging)
    report = dict(stage=491, prepared=True, deployable=plan['deployable'], no_ssh=True, no_sdk=True, no_target_execution=True,
                  files=len(files), archive_bytes=archive.stat().st_size, archive_sha256=sha(archive),
                  worker_sha256=sha(work / 'worker.py'), plan_sha256=sha(work / 'plan-private.json'),
                  candidate_state_sha256=sha(candidate_path), source_sha256=plan['source_sha256'],
                  query_sha256={name: sha(work / (name + '-query.py')) for name in ['stage', 'launch', 'observe', 'collect']})
    (work / 'preparation-private.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(work=str(work), **report)))


def candidate_packages(candidate):
    report = json.loads((HERE.parent / 'kernel490/package-r1-validation.json').read_bytes())
    assert report['passed'] and report['core_sha256'] == candidate['core_sha256']
    return report['packages']


if __name__ == '__main__':
    main()
