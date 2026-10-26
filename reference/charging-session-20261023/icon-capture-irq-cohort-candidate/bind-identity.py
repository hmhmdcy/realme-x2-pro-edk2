"""Default source check; bind only a real completed IRQ adoption, without SSH."""
from pathlib import Path
import argparse, importlib.util, json, os, sys
if sys.flags.optimize: raise RuntimeError('optimized interpreter is unsupported')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('icon_irq_launcher', HERE / 'launcher.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def bind(context, camera, probe_directory, capture_directory, *, pins=None, migration=None):
    target = m.PINS if pins is None else Path(pins)
    checked = m.identity_review().review_adoption(context, camera, probe_directory, capture_directory)
    entries = {'schema': 'samurai-icon-irq-identity-v1', 'review_inputs': checked['review_inputs'],
               'reviewed': checked, 'transport_inputs': {'transport': {'path': str(HERE / 'transport.py'),
               'sha256': m.sha((HERE / 'transport.py').read_bytes())},
               'key_transport': checked['files']['key_transport']}}
    if target.exists(): raise ValueError('runtime pins already exist; do not overwrite or replay')
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = target.with_name('identity-pins-next-private.json')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(entries, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    m.adopt_local(pins=temporary, migration=m.MIGRATION if migration is None else migration)
    if target.exists(): raise ValueError('runtime pins appeared; preserve unpromoted next file')
    temporary.rename(target); sync_directory(target.parent)
    return {'bound_actual_identity': True, 'pins_sha256': m.sha(target.read_bytes()),
            'guard_path': checked['guard_path'], 'device_accessed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('context', 'camera', 'probe-directory', 'capture-directory'): parser.add_argument('--' + name)
    parser.add_argument('--execute-bind', action='store_true'); args = parser.parse_args()
    if args.execute_bind:
        print(json.dumps(bind(args.context, args.camera, args.probe_directory, args.capture_directory)))
    else:
        m.identity_review().adoption_module()
        print(json.dumps({'template_only': True, 'runtime_pins_created': False, 'device_accessed': False}))


if __name__ == '__main__': main()
