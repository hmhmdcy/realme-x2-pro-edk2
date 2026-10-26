"""Three source-only defaults, each with its original owned child wait."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix='icon-runtime-source-only-') as tmp:
        for name in ('update-review.py', 'bind-identity.py', 'launcher.py'):
            argv = [sys.executable, '-B', str(HERE / name)]
            stdout_path, stderr_path = Path(tmp) / (name + '.stdout'), Path(tmp) / (name + '.stderr')
            with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
                child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                rc = child.wait(); out.flush(); err.flush()
            stdout, stderr = stdout_path.read_bytes(), stderr_path.read_bytes()
            data = json.loads(stdout)
            if rc != 0 or data.get('device_accessed') is not False: raise RuntimeError('source-only default failed: ' + name)
            results.append({'source': name, 'pid': child.pid, 'argv': argv, 'terminal': True, 'returncode': rc,
                            'stdout': data, 'stderr_bytes': len(stderr), 'stderr_sha256': hashlib.sha256(stderr).hexdigest()})
    receipt = {'passed': True, 'device_accessed': False, 'actual_runtime_pins_created': False, 'defaults': results,
               'files': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in
                         ('update-review.py', 'bind-identity.py', 'launcher.py', 'transport.py', 'source-pins.json', 'template-test-result.json')}}
    with (HERE / 'local-check-result.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'passed': True, 'source_only_defaults': len(results), 'device_accessed': False}))


if __name__ == '__main__': main()
