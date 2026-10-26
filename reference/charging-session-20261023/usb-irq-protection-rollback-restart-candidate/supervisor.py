"""One original quiesce child, joined independently of the SSH connection."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys

if sys.flags.optimize: raise RuntimeError('optimized interpreter is unsupported')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode()); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def identity(pid):
    path = Path('/proc', str(pid)); fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, startticks=int(fields[19]), argv=[s.decode() for s in (path / 'cmdline').read_bytes().split(b'\0') if s])


def supervise(root):
    os.umask(0o077)
    raw = (root / 'activation-request-private.json').read_bytes(); request = json.loads(raw)
    claim = json.loads((root / 'quiesce-intent-private.json').read_bytes())
    guard = root / 'guard-private.json'; worker = root / 'eud-quiesce.py'
    assert root.name == request['transaction_id'] == claim['transaction_id']
    assert sha(raw) == claim['request_sha256'] and sha(guard.read_bytes()) == request['guard_sha256']
    assert sha(worker.read_bytes()) == request['worker_hashes']['eud-quiesce.py']
    assert sha((root / 'activation-supervisor.py').read_bytes()) == request['supervisor_sha256']
    argv = ['python3', '-B', str(worker), '--guard', str(guard), '--commit-quiesce']
    own = dict(identity(os.getpid()), transaction_id=request['transaction_id'], token=request['token'],
               boot_id=request['expected_boot'], request_sha256=sha(raw))
    assert own['argv'] == ['python3', '-B', str(root / 'activation-supervisor.py'), '--supervise-quiesce']
    save(root / 'quiesce-supervisor-process-private.json', own)
    with (root / 'quiesce-private.log').open('xb') as log:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, close_fds=True)
        capture_error = None
        try:
            launch = dict(transaction_id=request['transaction_id'], token=request['token'], boot_id=request['expected_boot'],
                request_sha256=sha(raw), supervisor_pid=own['pid'], pid=child.pid, startticks=None, argv=argv)
            try:
                actual = identity(child.pid)
                assert actual['argv'] == argv
                launch['startticks'] = actual['startticks']
                save(root / 'quiesce-process-private.json', dict(actual, transaction_id=request['transaction_id'],
                    token=request['token'], boot_id=request['expected_boot'], request_sha256=sha(raw),
                    worker_sha256=request['worker_hashes']['eud-quiesce.py']))
            except Exception as error: capture_error = repr(error)
            save(root / 'quiesce-worker-launch-private.json', dict(launch, capture_error=capture_error))
        finally:
            rc = child.wait()  # The same handle even when metadata publication fails.
            log.flush(); os.fsync(log.fileno())
            save(root / 'quiesce-worker-terminal-private.json', dict(transaction_id=request['transaction_id'],
                token=request['token'], boot_id=request['expected_boot'], request_sha256=sha(raw),
                supervisor_pid=own['pid'], pid=child.pid, argv=argv, terminal=True, returncode=rc))
    save(root / 'quiesce-supervisor-terminal-private.json', dict(own, terminal=True, returncode=0,
                                                               worker_pid=child.pid, worker_returncode=rc))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--supervise-quiesce', action='store_true')
    args = parser.parse_args()
    if args.supervise_quiesce: supervise(Path(__file__).resolve().parent)
    else: print(json.dumps(dict(source_only=True, worker_started=False)))
