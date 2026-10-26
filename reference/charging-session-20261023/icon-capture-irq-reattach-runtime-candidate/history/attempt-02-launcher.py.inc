"""Thin same-boot charger-update profile for the unchanged finite icon collector."""
from pathlib import Path
import argparse, ast, hashlib, importlib.util, json, sys
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-session-20261023/icon-capture-irq-reattach-runtime')
PINS = PRIVATE / 'identity-pins-private.json'
MIGRATION = HERE / 'template-test-result.json'
MANIFEST = '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
REMOTE_BASE = '/root/charging-session-20261023/icon-capture-irq-reattach-runtime'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def identity_review():
    return load(HERE / 'update-review.py', 'icon_same_boot_update_review')


def identity(pins=PINS, *, retained=False):
    module = identity_review(); bound = json.loads(Path(pins).read_bytes())
    module.need(bound.get('schema') == 'samurai-icon-irq-runtime-update-v1', 'actual same-boot update pins required')
    if retained:
        # Status/fetch retain the originally bound completion evidence. No
        # postboot/adoption recomputation is included in measured SSH time.
        module.check_sources(); actual = bound['reviewed']
        module.need(actual['manifest_sha256'] == MANIFEST and actual['base_adoption_manifest_sha256'] == module.OLD and
                    actual['runtime_expected']['notes']['samurai_mp2650'] == module.NEW_NOTE and
                    actual['pointer']['charging_manifest_sha256'] == module.OLD and
                    bound['review_inputs'] == actual['review_inputs'], 'retained runtime overlay profile differs')
        for name, entry in actual['files'].items():
            module.need(sha(module.local(entry['path']).read_bytes()) == entry['sha256'], 'retained evidence changed: ' + name)
    else:
        inputs = bound['review_inputs']
        base = module.base_module().review_adoption(**inputs['base_adoption'])
        actual = module.review_update(inputs['update_directory'], base)
        module.need(bound['reviewed'] == actual, 'completed update/adoption originals changed')
    entries = bound['transport_inputs']
    module.need(set(entries) == {'transport', 'key_transport'} and
                module.local(entries['transport']['path']) == (HERE / 'transport.py').resolve(), 'runtime profile transport differs')
    for name, entry in entries.items():
        module.need(sha(module.local(entry['path']).read_bytes()) == entry['sha256'], 'transport source changed: ' + name)
    module.need(entries['key_transport'] == actual['files']['key_transport'], 'original strict key differs')
    return actual, entries


def reviewed_identity(pins=PINS):
    actual, entries = identity(pins)
    return actual['boot_id'], actual['guard_path'], entries


def runtime_expected(pins=PINS):
    reviewed_identity(pins)
    return json.loads(Path(pins).read_bytes())['reviewed']['runtime_expected']


def adopt_local(bundle=HERE, pins=PINS, migration=MIGRATION):
    module = collector()
    files = {name: (Path(bundle) / name).read_bytes() for name in module.FROZEN}
    if any(sha(files[name]) != digest for name, digest in module.FROZEN.items()):
        raise ValueError('frozen worker/audit/entry/historical receipt changed')
    tested = json.loads(files['baseline-test-result.json'])
    if not (tested.get('passed') is True and tested.get('tests_run') == 32 and all(
            tested['sha256'][name] == module.FROZEN[name] for name in ('worker.py', 'audit.py'))):
        raise ValueError('original generic collector receipt differs')
    checked = json.loads(Path(migration).read_bytes())
    if not (checked.get('schema') == 'charging-icon-irq-runtime-update-template-tests-v1' and checked.get('passed') is True
            and checked.get('runtime_identity_unbound') is True and checked.get('manifest_sha256') == MANIFEST
            and checked.get('sha256') == module.FROZEN):
        raise ValueError('affected profile receipt differs')
    for name, digest in checked['files'].items():
        if sha((Path(bundle) / name).read_bytes()) != digest: raise ValueError('tested source changed: ' + name)
    boot, guard, _ = reviewed_identity(pins)
    return files, boot, guard


def collector():
    """Original run/ready/fetch/cleanup bodies; only profile globals are supplied."""
    review = identity_review(); pins, values = review.check_sources()
    module = load(review.local(pins['base_launcher']['path']), 'icon_original_finite_collector')
    module.HERE = HERE; module.PRIVATE = PRIVATE; module.PINS = PINS; module.MIGRATION = MIGRATION
    module.MANIFEST = MANIFEST; module.REMOTE_BASE = REMOTE_BASE
    original = '/root/charging-session-20261023/icon-capture-irq-cohort'
    review.need(module.REMOTE.count(original) == 1, 'original remote profile changed')
    module.REMOTE = module.REMOTE.replace(original, REMOTE_BASE)
    module.reviewed_identity = reviewed_identity; module.runtime_expected = runtime_expected
    module.adopt_local = adopt_local
    return module


def run(action, transaction, confirmed=False, *, ssh=None, private=PRIVATE, bundle=HERE,
        pins=PINS, migration=MIGRATION, max_seconds=300):
    module = collector()
    if action in ('status', 'fetch'):
        def saved_identity(selected=PINS):
            actual, entries = identity(selected, retained=True)
            return actual['boot_id'], actual['guard_path'], entries
        def saved_expected(selected=PINS):
            actual, _ = identity(selected, retained=True)
            return actual['runtime_expected']
        module.reviewed_identity = saved_identity; module.runtime_expected = saved_expected
    if ssh is None:
        actual, entries = identity(pins, retained=action in ('status', 'fetch'))
        transport = load(HERE / 'transport.py', 'icon_prevalidated_runtime_transport')
        ssh = transport.prevalidated(actual['endpoint'], entries)
    return module.run(action, transaction, confirmed, ssh=ssh, private=Path(private), bundle=Path(bundle),
                      pins=Path(pins), migration=Path(migration), max_seconds=max_seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='check-local', choices=('check-local', 'launch', 'status', 'fetch'))
    parser.add_argument('--transaction'); parser.add_argument('--window-confirmed', action='store_true')
    parser.add_argument('--max-seconds', type=int, default=300); args = parser.parse_args(argv)
    if args.action == 'check-local':
        review = identity_review(); review.check_sources(); module = collector()
        for name, digest in module.FROZEN.items():
            if sha((HERE / name).read_bytes()) != digest: raise ValueError('frozen generic file changed: ' + name)
        for name in ('launcher.py', 'update-review.py', 'transport.py', 'bind-identity.py'):
            ast.parse((HERE / name).read_text())
        tested = json.loads(MIGRATION.read_bytes())
        if tested.get('passed') is not True: raise ValueError('affected profile tests absent/failed')
        for name, digest in tested['files'].items():
            if sha((HERE / name).read_bytes()) != digest: raise ValueError('tested profile changed: ' + name)
        # Source-only default intentionally does not read a runtime pointer or pins.
        print(json.dumps({'local_sources_verified': True, 'device_accessed': False,
                          'runtime_identity_bound': False, 'deadline_seconds': 300})); return
    if not args.transaction: raise ValueError('fresh capture transaction required')
    print(json.dumps(run(args.action, args.transaction, args.window_confirmed, max_seconds=args.max_seconds), indent=2))


if __name__ == '__main__': main()
