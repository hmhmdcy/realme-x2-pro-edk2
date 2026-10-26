"""Local-only480 adapter of pinned477 preparation. No transport or SDK access."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'kernel477'
SOURCE_SHA256 = '897d8edaef0cc3ddd27fcd3416f1c1ba75a6e8ea3813c2c077a77ce90cac7a70'
WORKER_SHA256 = '5d2f51e3a2712ed7496147c937c4ffb1070b2943e13515d1eec70985ab0cf638'


def main():
    source = (BASE/'prepare-runtime.py').read_bytes()
    worker = (BASE/'target-worker.py').read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    assert hashlib.sha256(worker).hexdigest() == WORKER_SHA256
    expected_worker = worker.replace(b'k477-target-deps-r1', b'k480-target-deps-r1').replace(
        b'k476-control-delay-r1', b'k476-control-delay-r2').replace(b'stage=477', b'stage=480')
    assert (HERE/'target-worker.py').read_bytes() == expected_worker
    adapted = source.decode().replace('Local-only477', 'Local-only480').replace(
        'guard477', 'guard480').replace('kernel477', 'kernel480').replace(
        'k477-target-deps-r1', 'k480-target-deps-r1').replace('stage=477', 'stage=480')
    namespace = {'__file__':str(HERE/'prepare-runtime.py'), '__name__':'kernel480_preparation'}
    exec(compile(adapted, str(HERE/'prepare-runtime.py')+'[pinned477]', 'exec'), namespace)
    namespace['main']()


if __name__ == '__main__': main()
