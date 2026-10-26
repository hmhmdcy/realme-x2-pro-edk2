"""Bind only a completed same-boot update; default checks source without identity."""
from pathlib import Path
import argparse, importlib.util, json, os, sys
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('icon_runtime_profile', HERE / 'launcher.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def bind(context, camera, probe_directory, capture_directory, update_directory, *, pins=None, migration=None):
    review = m.identity_review()
    base = review.base_module().review_adoption(context, camera, probe_directory, capture_directory)
    checked = review.review_update(update_directory, base)
    target = m.PINS if pins is None else Path(pins)
    values = {'schema': 'samurai-icon-irq-runtime-update-v1', 'review_inputs': checked['review_inputs'],
              'reviewed': checked, 'transport_inputs': {
                  'transport': {'path': str(HERE / 'transport.py'), 'sha256': m.sha((HERE / 'transport.py').read_bytes())},
                  'key_transport': checked['files']['key_transport']}}
    if target.exists(): raise ValueError('runtime pins already exist; do not overwrite')
    # Every real adoption/update/terminal/tuple gate precedes any mkdir or write.
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = target.with_name('identity-pins-next-private.json')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(values, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    m.adopt_local(pins=temporary, migration=m.MIGRATION if migration is None else migration)
    if target.exists(): raise ValueError('runtime pins appeared; retain unpromoted next file')
    temporary.rename(target)
    if os.name != 'nt':
        fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return {'bound_actual_runtime_update': True, 'pins_sha256': m.sha(target.read_bytes()),
            'guard_path': checked['guard_path'], 'device_accessed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('context', 'camera', 'probe-directory', 'capture-directory', 'update-directory'):
        parser.add_argument('--' + name)
    parser.add_argument('--execute-bind', action='store_true'); args = parser.parse_args()
    if args.execute_bind:
        print(json.dumps(bind(args.context, args.camera, args.probe_directory, args.capture_directory, args.update_directory)))
    else:
        m.identity_review().check_sources()
        print(json.dumps({'template_only': True, 'runtime_pins_created': False, 'device_accessed': False}))


if __name__ == '__main__': main()
