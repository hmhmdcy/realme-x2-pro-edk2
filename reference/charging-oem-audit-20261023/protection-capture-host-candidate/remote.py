"""Strict single-transaction transport wrapper, sent only by explicit host action.
No worker re-execution, stop, lease renewal, module or carrier operation here.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_json(path):
    try:
        return json.loads(path.read_bytes())
    except FileNotFoundError:
        return None


def observed_json(path):
    try:
        return read_json(path)
    except (OSError, ValueError) as error:
        return dict(read_error=type(error).__name__, errno=getattr(error, 'errno', None))


def process(receipt, expected_argv):
    if not receipt or type(receipt.get('pid')) is not int or receipt['pid'] <= 0:
        return dict(state='unknown', reason='no retained original child PID')
    pid = receipt['pid']
    try:
        directory = Path('/proc', str(pid))
        data = directory.joinpath('stat').read_text()
        fields = data[data.rindex(')') + 2:].split()
        ticks = int(fields[19])
        argv = [x.decode(errors='replace') for x in directory.joinpath('cmdline').read_bytes().split(b'\0') if x]
    except FileNotFoundError:
        return dict(state='absent', pid=pid)
    except (OSError, ValueError, IndexError):
        return dict(state='unknown', pid=pid)
    expected_ticks = receipt.get('start_ticks')
    if type(expected_ticks) is not int or expected_ticks <= 0:
        state = 'unknown'
    elif ticks != expected_ticks:
        state = 'pid_reused'
    elif fields[0] == 'Z':
        state = 'zombie'
    elif argv != expected_argv or receipt.get('argv') != expected_argv:
        state = 'unknown'
    else:
        state = 'alive'
    return dict(state=state, pid=pid, start_ticks=ticks, argv=argv)


def execute(data):
    os.umask(0o077)
    action = data['action']
    need(action in ('launch', 'status', 'fetch') and os.geteuid() == 0, 'explicit root action required')
    request_raw = base64.b64decode(data['request_base64'], validate=True)
    request = json.loads(request_raw)
    need(sha(request_raw) == data['request_sha256'] and request == data['request'], 'request bytes differ')
    tx = request['transaction_id']
    need(re.fullmatch(r'protection-capture-[a-z0-9-]{8,48}', tx), 'transaction name')
    need(request['schema'] == 'samurai-protection-capture-request-v1', 'request schema')
    root = Path('/root/charging-management-20261023') / tx
    worker = root / 'stage-worker.py'
    supervisor = root / 'stage-supervisor.py'
    out = root / 'device-stage'
    argv = ['python3', '-B', str(worker), '--execute-stage']
    supervisor_argv = ['python3', '-B', str(supervisor), '--execute-supervisor']
    guard = Path(request['adoption']['guard_path'])
    adoption_tx = request['adoption']['transaction_id']
    need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', adoption_tx), 'actual adoption transaction')
    need(str(guard) == '/var/lib/samurai/' + adoption_tx + '-adopted/boot-id-private.txt', 'adopted guard path')

    def observed_identity():
        try:
            actual_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        except (OSError, ValueError) as error:
            return dict(boot_id=None, source_boot_same=None, guard_matches=None, read_error=type(error).__name__)
        same = actual_boot == request['identity']['boot_id']
        result = dict(boot_id=actual_boot, source_boot_same=same, guard_matches=None)
        if same:
            try:
                result['guard_matches'] = (guard.read_text().strip() == actual_boot
                    and sha(guard.read_bytes()) == request['adoption']['guard_sha256'])
            except (OSError, ValueError) as error:
                result['guard_error'] = type(error).__name__
        return result

    identity_before = observed_identity()
    if action == 'launch':
        need(identity_before['source_boot_same'] is True and identity_before['guard_matches'] is True,
             'same original boot/guard required for launch')
        boot = identity_before['boot_id']
        need(data.get('window_confirmed') is True, 'current root exclusive window required')
        need(os.uname().version == request['identity']['version'], 'actual kernel version differs')
        need(not root.exists(), 'remote transaction already claimed; fetch only')
        raw = base64.b64decode(data['worker_base64'], validate=True)
        need(sha(raw) == request['worker_sha256'], 'worker source differs')
        supervisor_raw = base64.b64decode(data['supervisor_base64'], validate=True)
        need(sha(supervisor_raw) == data['supervisor_sha256'], 'supervisor source differs')
        root.mkdir(mode=0o700)
        with (root / 'request-private.json').open('xb') as stream:
            stream.write(request_raw); stream.flush(); os.fsync(stream.fileno())
        with worker.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        with supervisor.open('xb') as stream:
            stream.write(supervisor_raw); stream.flush(); os.fsync(stream.fileno())
        save(root / 'launch-claim-private.json', dict(transaction_id=tx, boot_id=boot,
             request_sha256=data['request_sha256'], request_count=1, argv=argv,
             supervisor_argv=supervisor_argv, supervisor_sha256=data['supervisor_sha256']))
        now = time.clock_gettime(time.CLOCK_BOOTTIME)
        lease = dict(transaction_id=tx, boot_id=boot, token=request['lease_token'], owner='charging',
                     exclusive=True, camera_released=True, bluetooth_released=True,
                     issued_boottime_s=now, expires_boottime_s=now + 120)
        save(Path('/run') / (tx + '-window-private.json'), lease)
        again = observed_identity()
        need(again['source_boot_same'] is True and again['guard_matches'] is True, 'launch identity changed')
        with (root / 'supervisor-private.log').open('xb') as log:
            child = subprocess.Popen(supervisor_argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, close_fds=True)
        try:
            data_stat = Path('/proc', str(child.pid), 'stat').read_text()
            ticks = int(data_stat[data_stat.rindex(')') + 2:].split()[19])
        except (OSError, ValueError, IndexError):
            ticks = None
        receipt = dict(transaction_id=tx, boot_id=boot, request_sha256=data['request_sha256'],
                       pid=child.pid, start_ticks=ticks, argv=supervisor_argv)
        save(root / 'launch-receipt-private.json', receipt)
        return dict(transaction_id=tx, request_sha256=data['request_sha256'], launched=True,
                    supervisor_receipt=receipt, supervisor_process=process(receipt, supervisor_argv),
                    process=dict(state='unknown', reason='worker Popen is owned by detached supervisor'),
                    terminal_not_assumed=True)

    retained = read_json(root / 'launch-claim-private.json')
    receipt_observation = observed_json(root / 'launch-receipt-private.json')
    receipt = receipt_observation
    if receipt is not None and 'read_error' in receipt:
        receipt = None  # Keep the observation/raw; do not attribute a PID.
    if retained is not None:
        need(retained['transaction_id'] == tx and retained['request_sha256'] == data['request_sha256']
             and retained['argv'] == argv and retained['supervisor_argv'] == supervisor_argv
             and retained['supervisor_sha256'] == data['supervisor_sha256'], 'original remote claim differs')
        need((root / 'request-private.json').read_bytes() == request_raw, 'original retained request differs')
        need(sha(worker.read_bytes()) == request['worker_sha256'], 'retained original worker differs')
        need(sha(supervisor.read_bytes()) == data['supervisor_sha256'], 'retained original supervisor differs')
    if receipt is not None:
        need(retained is not None and receipt['transaction_id'] == tx
             and receipt['request_sha256'] == data['request_sha256'] and receipt['argv'] == supervisor_argv,
             'original supervisor receipt differs')
        own = observed_json(root / 'supervisor-process-private.json')
        if receipt.get('start_ticks') is None and own is not None:
            if own.get('pid') == receipt['pid'] and own.get('argv') == supervisor_argv and type(own.get('start_ticks')) is int:
                receipt = dict(receipt, start_ticks=own['start_ticks'])
    child_receipt = observed_json(root / 'worker-launch-receipt-private.json')
    terminal = observed_json(root / 'worker-terminal-private.json')
    child_bound = bool(receipt and child_receipt and all(child_receipt.get(k) == v for k, v in
        dict(transaction_id=tx, boot_id=request['identity']['boot_id'], request_sha256=data['request_sha256'],
             supervisor_pid=receipt['pid'], argv=argv).items()) and type(child_receipt.get('pid')) is int)
    terminal_verified = bool(child_bound and terminal and terminal.get('terminal') is True
        and type(terminal.get('returncode')) is int and all(terminal.get(k) == child_receipt.get(k) for k in
            ('transaction_id', 'boot_id', 'request_sha256', 'supervisor_pid', 'pid', 'argv')))

    def source_process(original, expected):
        if identity_before['source_boot_same'] is False:
            return dict(state='source_boot_ended', source_boot_id=request['identity']['boot_id'],
                        current_boot_id=identity_before['boot_id'])
        if identity_before['source_boot_same'] is not True or identity_before['guard_matches'] is not True:
            return dict(state='unknown', reason='current source boot/guard unproved; no current PID attribution')
        return process(original, expected)

    response = dict(transaction_id=tx, request_sha256=data['request_sha256'],
                    supervisor_receipt=receipt, supervisor_process=source_process(receipt, supervisor_argv),
                    supervisor_receipt_observation=receipt_observation,
                    launch_receipt=child_receipt,
                    process=source_process(child_receipt if child_bound else None, argv),
                    worker_terminal=terminal, worker_terminal_verified=terminal_verified,
                    identity_observation=identity_before, worker_result=observed_json(out / 'result.json'),
                    runtime_validation_accepted=False)
    if action == 'fetch':
        files = {}
        paths = [(root / name, name) for name in ('worker-private.log', 'supervisor-private.log',
            'launch-receipt-private.json',
            'supervisor-process-private.json', 'supervisor-terminal-private.json',
            'worker-launch-receipt-private.json', 'worker-terminal-private.json')]
        if out.exists():
            need(out.is_dir() and not out.is_symlink(), 'indirect worker output')
            paths += [(p, p.name) for p in sorted(out.iterdir())]
        total = 0
        for path, name in paths:
            if not path.exists():
                continue
            need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'unsafe retained output name')
            details = path.lstat()
            need(stat.S_ISREG(details.st_mode) and not path.is_symlink() and details.st_size <= 8_000_000,
                 'nonregular or oversized retained output')
            raw = path.read_bytes()
            total += len(raw)
            need(total <= 16_000_000 and name not in files, 'retained output bound/collision')
            files[name] = dict(bytes=len(raw), sha256=sha(raw), base64=base64.b64encode(raw).decode())
        response['files'] = files
    response['identity_after'] = observed_identity()
    if response['identity_after'] != identity_before:
        response['identity_changed_during_observation'] = True
        state = 'source_boot_ended' if response['identity_after']['source_boot_same'] is False else 'unknown'
        response['process'] = dict(state=state, reason='boot/guard observation changed; no PID attribution')
        response['supervisor_process'] = dict(response['process'])
    return response


if __name__ == '__main__':
    print(json.dumps(execute(STAGE_TRANSPORT), indent=2), flush=True)
