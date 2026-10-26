"""One detached owner for one rollback worker Popen. Default does not execute."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys

sha = lambda data: hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def ticks(pid):
    data = Path('/proc', str(pid), 'stat').read_text()
    return int(data[data.rindex(')') + 2:].split()[19])


def supervise(root):
    os.umask(0o077)
    request_path = root / 'request-private.json'
    request_raw = request_path.read_bytes()
    request = json.loads(request_raw)
    claim = json.loads((root / 'launch-claim-private.json').read_bytes())
    worker = root / 'restore-worker.py'
    argv = ['python3', '-B', str(worker), '--execute-rollback']
    assert request['schema']=='samurai-irq-native-usb-pm-cold-rollback-request-v1'
    assert root.name == request['transaction_id'] == claim['transaction_id']
    assert sha(request_raw) == claim['request_sha256']
    assert sha(worker.read_bytes()) == request['worker_sha256']
    assert sha((root / 'rollback-supervisor.py').read_bytes()) == claim['supervisor_sha256']
    pid = os.getpid()
    own = dict(transaction_id=request['transaction_id'], boot_id=request['identity']['boot_id'],
               request_sha256=sha(request_raw), pid=pid, start_ticks=ticks(pid),
               argv=['python3', '-B', str(root / 'rollback-supervisor.py'), '--execute-supervisor'])
    save(root / 'supervisor-process-private.json', own)
    # A regular fsynced request survives the SSH transport. No stdin pipe is
    # needed by this supervisor or the rollback worker.
    with request_path.open('rb') as request_stream, (root / 'worker-private.log').open('xb') as log:
        child = subprocess.Popen(argv, stdin=request_stream, stdout=log, stderr=subprocess.STDOUT, close_fds=True)
        try:
            try:
                start = ticks(child.pid)
            except (OSError, ValueError, IndexError):
                start = None
            receipt = dict(transaction_id=request['transaction_id'], boot_id=request['identity']['boot_id'],
                           request_sha256=sha(request_raw), supervisor_pid=pid,
                           pid=child.pid, start_ticks=start, argv=argv)
            save(root / 'worker-launch-receipt-private.json', receipt)
        finally:
            # This exact Popen is retained through the actual terminal, even
            # if receipt publication fails. No timeout, kill or second launch.
            rc = child.wait()
            log.flush(); os.fsync(log.fileno())
            save(root / 'worker-terminal-private.json', dict(transaction_id=request['transaction_id'],
                 boot_id=request['identity']['boot_id'], request_sha256=sha(request_raw),
                 supervisor_pid=pid, pid=child.pid, argv=argv, terminal=True, returncode=rc))
    save(root / 'supervisor-terminal-private.json', dict(own, terminal=True, worker_pid=child.pid,
                                                       worker_returncode=rc, returncode=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-supervisor', action='store_true')
    arguments = parser.parse_args()
    if arguments.execute_supervisor:
        if sys.flags.optimize:
            raise RuntimeError('optimized Python disables supervisor checks')
        supervise(Path(__file__).resolve().parent)
    else:
        print(json.dumps(dict(source_only=True, worker_started=False)))
