"""One-shot boot-only fastboot operator. Default is offline, read-only check-local."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
FASTBOOT = '/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
IDENTITY = PRIVATE.parent / 'kernel109/fastboot-identity.json'
CANDIDATE = PRIVATE / 'eud-boot-two-ffs-candidate-private-01/boot-two-ffs-private.img'
ROLLBACK = PRIVATE / 'usb-boot/boot-charging-usb-dt.img'
BYTES = 100663296
CANDIDATE_SHA = '4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
ROLLBACK_SHA = 'a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
RESULT_SHA = '6dafe9e10877973d62b4348fdded0236ef47944e121d10ae2da96a9e84787b44'
PACKER_SHA = 'f8e9a8aeb7b92c87be4cf66f8a99d950b6247146cf913b5971734bf496d141bf'
INSPECTION_SHA = '2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
CONTRACT_SHA = 'f12d65b62f8787732795f45d15edf0560672f3782bc16aed915c42dbd6f92dec'
RESTART_SHA = '0fb0948b49f7b15ca04015991d771056f1f5357539d7e9a834d4536928956ddf'
ACTIVATION = HERE.parent / 'eud-boot-activation-candidate'
ACTIONS = ('inspect', 'flash-candidate', 'rollback-original', 'reboot')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink(), 'regular non-symlink file required')
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def once(path, value):
    """A failed/partial durable claim remains present and is never reused."""
    raw = (json.dumps(value, indent=2) + '\n').encode()
    with Path(path).open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    fsync_dir(Path(path).parent)


def publish_result(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.incomplete')
    once(temporary, value)
    require(not path.exists(), 'terminal result already exists')
    os.rename(temporary, path)
    fsync_dir(path.parent)


@contextlib.contextmanager
def locked(directory):
    import fcntl
    with (Path(directory) / 'operator.lock').open('ab') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def local_inputs():
    """Local bytes only. No subprocess, transport import, USB or directory creation."""
    require(sys.platform == 'linux', 'run inside the existing WSL environment')
    contract_path = ACTIVATION / 'prepare-contract.json'
    require(sha(contract_path) == CONTRACT_SHA, 'activation contract changed')
    require(sha(ACTIVATION / 'eud-restart.py') == RESTART_SHA, 'restart worker changed')
    result_path = CANDIDATE.parent / 'result.json'
    require(sha(result_path) == RESULT_SHA, 'actual packaging result changed')
    result = read_json(result_path)
    require(result['passed'] is True and result['boot_sha256'] == CANDIDATE_SHA,
            'candidate packaging did not pass')
    require(result['boot_bytes'] == BYTES and result['rollback_a30_sha256'] == ROLLBACK_SHA,
            'packaging image identity mismatch')
    require(len(result['commands']) == 12 and
            all(c['returncode'] == 0 for c in result['commands']), 'packaging command failed')
    require(result['inputs_before'] == result['inputs_after'], 'packaging parent inputs changed')
    packer = HERE.parent / 'eud-boot-two-ffs-candidate/package.py'
    require(sha(packer) == PACKER_SHA and result['inputs_before'][str(packer)] == PACKER_SHA,
            'actual packaging source mismatch')
    inspection = REF / 'charging-session-20261023/eud-boot-packaging-review/inspection.json'
    require(sha(inspection) == INSPECTION_SHA, 'rollback inspection changed')
    old = read_json(inspection)['rollback']
    require(old['sha256'] == ROLLBACK_SHA and old['bytes'] == BYTES, 'rollback receipt mismatch')
    for p, digest in ((CANDIDATE, CANDIDATE_SHA), (ROLLBACK, ROLLBACK_SHA)):
        require(p.stat().st_size == BYTES and sha(p) == digest, 'full image hash/size mismatch')
    identity = read_json(IDENTITY)
    require(isinstance(identity['serial'], str) and
            re.fullmatch(r'[A-Za-z0-9._:-]+', identity['serial']), 'invalid private serial')
    require(identity.get('product') == 'msmnile', 'private product is not msmnile')
    require(Path(FASTBOOT).is_file(), 'fixed Windows fastboot executable missing')
    return {'candidate_sha256': CANDIDATE_SHA, 'rollback_sha256': ROLLBACK_SHA,
            'bytes': BYTES, 'packaging_result_sha256': RESULT_SHA,
            'private_identity_sha256': sha(IDENTITY), 'fastboot_executable_sha256': sha(FASTBOOT),
            'activation_contract_sha256': CONTRACT_SHA}


def reference_file(base, item):
    name = item['path']
    require(isinstance(name, str) and name == Path(name).name and name not in ('.', '..'),
            'evidence must be one same-directory filename')
    p = base / name
    require(re.fullmatch(r'[0-9a-f]{64}', item['sha256']) and sha(p) == item['sha256'],
            'evidence hash mismatch')
    return p


def validate_context(path, contract=None):
    path = Path(path)
    require(path.name == 'host-context-private.json' and path.is_file() and not path.is_symlink(),
            'regular context filename')
    path = path.resolve()
    context = read_json(path)
    require(context['schema'] == 'samurai-eud-fastboot-context-v1', 'context schema')
    txn, token, boot = (context[k] for k in ('transaction_id', 'token', 'old_boot_id'))
    require(re.fullmatch(r'eud-boot-[a-z0-9-]{8,64}', txn) and
            re.fullmatch(r'[0-9a-f]{32,64}', token) and
            re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', boot),
            'fresh transaction/token/boot shape')
    require(path.parent.name == txn, 'new transaction directory mismatch')
    keys = {'guard', 'quiesce_state', 'quiesce_summary', 'quiesce_boot_id',
            'quiesce_process', 'restart_dispatch', 'restart_claim'}
    require(set(context['files']) == keys, 'context evidence set')
    paths = {k: reference_file(path.parent, v) for k, v in context['files'].items()}
    require(len(set(paths.values())) == len(keys), 'distinct evidence files required')
    guard = read_json(paths['guard'])
    require(context['guard_sha256'] == context['files']['guard']['sha256'], 'guard digest mismatch')
    require(guard['schema'] == 'samurai-eud-boot-activation-v1', 'old activation schema')
    require((guard['transaction_id'], guard['token'], guard['boot_id']) == (txn, token, boot),
            'guard transaction mismatch')
    contract = contract or read_json(ACTIVATION / 'prepare-contract.json')
    for key, expected in contract['fixed_guard_fields'].items():
        require(guard[key] == expected, 'guard fixed identity mismatch: ' + key)
    require(guard['kernel_version'].startswith('#363 '), 'kernel version')
    for key in ('rootfs_release_sha256', 'soc_serial_sha256', 'compatible_sha256'):
        require(re.fullmatch(r'[0-9a-f]{64}', guard[key]), 'fresh board identity missing')
    for name in ('quiesce_state', 'quiesce_summary', 'quiesce_process', 'restart_claim', 'restart_dispatch'):
        item = read_json(paths[name])
        require((item['transaction_id'], item['token'], item['boot_id']) == (txn, token, boot),
                name + ' transaction mismatch')
    state, summary, process = (read_json(paths[k]) for k in
                                ('quiesce_state', 'quiesce_summary', 'quiesce_process'))
    require(state['terminal'] is True and state['exit_code'] == 0 and summary['taint'] == 0,
            'quiesce not successful terminal')
    require(paths['quiesce_boot_id'].read_text().strip() == boot, 'saved old boot mismatch')
    remote = '/root/charging-management-20261023/' + txn
    qargv = ['python3', '-B', remote + '/eud-quiesce.py', '--guard',
             remote + '/guard-private.json', '--commit-quiesce']
    require(process['pid'] == state['pid'] and process['pid'] > 0 and process['startticks'] > 0 and
            process['argv'] == qargv and process['status'] in ('absent', 'zombie'),
            'original quiesce process not proven ended')
    rargv = ['python3', '-B', remote + '/eud-restart.py', '--guard',
             remote + '/guard-private.json', '--commit-restart2-bootloader']
    claim, dispatch = (read_json(paths[k]) for k in ('restart_claim', 'restart_dispatch'))
    require(claim['schema'] == 'samurai-eud-restart-host-claim-v1' and
            dispatch['schema'] == 'samurai-eud-restart-dispatch-v1', 'restart receipt schema')
    for item in (claim, dispatch):
        require(item['guard_sha256'] == context['guard_sha256'] and item['request_count'] == 1 and
                item['worker_sha256'] == RESTART_SHA and item['argv'] == rargv,
                'restart claim/worker/argv mismatch')
    hp = dispatch['host_process']
    require(dispatch['host_claim_sha256'] == context['files']['restart_claim']['sha256'] and
            dispatch['state'] == 'dispatched_once' and
            dispatch['restart_claim_intent'] == 'claimed_by_pinned_worker' and
            hp['pid'] > 0 and hp['startticks'] > 0 and hp['argv'] and
            hp['terminal'] is True and type(hp['returncode']) is int,
            'original restart dispatch is not terminal/bound')
    # A terminal SSH status (including 255), or captured armed phase, is NOT a
    # RESTART2 success. Fresh exact fastboot identity is still required below.
    return context


def process_info(pid):
    try:
        raw = Path('/proc', str(pid), 'stat').read_text()
        fields = raw[raw.rindex(')') + 2:].split()
        return {'pid': pid, 'startticks': int(fields[19]), 'state': fields[0],
                'argv': [s.decode(errors='replace') for s in
                         Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0') if s]}
    except FileNotFoundError:
        return {'pid': pid, 'absent': True}


def command(directory, label, argv):
    """No timeout/kill/retry. The detached owner persists the real wait result."""
    out, err = directory / (label + '-stdout-private.bin'), directory / (label + '-stderr-private.bin')
    once(directory / (label + '-command-private.json'), {'requested_argv': argv, 'request_count': 1})
    with out.open('xb') as stdout, err.open('xb') as stderr:
        try:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     close_fds=True)
        except OSError:
            once(directory / (label + '-terminal-private.json'),
                 {'spawn_failed': True, 'terminal': True, 'requested_argv': argv})
            raise
        receipt_error = None
        try:
            identity = process_info(child.pid)
            require(identity.get('startticks', 0) > 0 and identity.get('argv'),
                    'child exited before its exact /proc identity could be captured')
            once(directory / (label + '-process-private.json'),
                 {'pid': child.pid, 'requested_argv': argv, 'observed': identity})
        except Exception as exc:
            receipt_error = str(exc)
        # Even a receipt failure after Popen must join the same real child.
        rc = child.wait()
        stdout.flush(); stderr.flush()
        os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
    once(directory / (label + '-terminal-private.json'),
         {'pid': child.pid, 'returncode': rc, 'terminal': True, 'requested_argv': argv,
          'stdout_sha256': sha(out), 'stderr_sha256': sha(err)})
    require(receipt_error is None, 'child identity receipt failed: ' + str(receipt_error))
    require(rc == 0, label + ' failed; raw output retained')
    return out.read_bytes().decode(errors='replace'), err.read_bytes().decode(errors='replace')


def windows_path(path):
    name = str(path)
    require(name.startswith('/mnt/e/'), 'image must remain on fixed E drive')
    return 'E:/' + name[len('/mnt/e/'):]


def run_action(action, serial, call):
    require(action in ACTIONS, 'unsupported action')
    stdout, _ = call('devices', [FASTBOOT, 'devices'])
    found = re.findall(r'(?m)^(\S+)\s+fastboot\s*$', stdout)
    require(found == [serial] and len(stdout.split()) == 2,
            'fresh devices must be sole exact private serial')
    out, err = call('product', [FASTBOOT, '-s', serial, 'getvar', 'product'])
    values = re.findall(r'(?m)^(?:\(bootloader\)\s*)?product:\s*(\S+)\s*$', out + '\n' + err)
    require(values == ['msmnile'], 'fresh product must be exactly msmnile')
    out, err = call('boot-size', [FASTBOOT, '-s', serial, 'getvar', 'partition-size:boot'])
    sizes = re.findall(r'(?m)^(?:\(bootloader\)\s*)?partition-size:boot:\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$', out + '\n' + err)
    require(len(sizes) == 1 and int(sizes[0], 16 if sizes[0].startswith('0x') else 10) == BYTES,
            'fresh boot partition must be exactly 96MiB')
    result = {'fresh_exact_bootloader_identity': True, 'partitions_written': [],
              'runtime_readback_pending': action != 'inspect'}
    if action in ('flash-candidate', 'rollback-original'):
        image, digest = (CANDIDATE, CANDIDATE_SHA) if action == 'flash-candidate' else (ROLLBACK, ROLLBACK_SHA)
        # Repeat immediately before dispatch; the earlier check binds both files.
        require(image.stat().st_size == BYTES and sha(image) == digest, 'image changed before dispatch')
        out, err = call('flash', [FASTBOOT, '-s', serial, 'flash', 'boot', windows_path(image)])
        text = out + '\n' + err
        require(re.search(r"Writing 'boot'\s+OKAY", text) and 'FAILED' not in text,
                'flash return/output did not establish successful boot write')
        result.update(partitions_written=['boot'], flashed_sha256=digest)
    elif action == 'reboot':
        out, err = call('reboot', [FASTBOOT, '-s', serial, 'reboot'])
        require('FAILED' not in out + err, 'reboot command failed')
        result['reboot_command_returned_zero'] = True
        result['boot_success_proven'] = False
    return result


def prior_terminal(directory, action):
    """A lost owner / absent child without wait receipt is UNKNOWN, never success."""
    for previous in directory.iterdir():
        if previous.name not in ACTIONS:
            continue
        require(previous.is_dir() and not previous.is_symlink() and
                (previous / 'request-private.json').is_file(), 'partial prior action; fetch only')
        terminal = previous / 'result-private.json'
        require(terminal.is_file(), 'prior action still running or outcome unknown; fetch only')
        result = read_json(terminal)
        request = read_json(previous / 'request-private.json')
        require(result.get('terminal') is True and result.get('commands_terminal') is True,
                'prior command outcome unknown; fetch only')
        require(result['action'] == previous.name and all(result[k] == request[k] for k in
                ('transaction_id', 'token', 'old_boot_id', 'context_sha256', 'claimed_ns')),
                'prior terminal receipt not bound to original action')
    if action == 'reboot':
        flashes = [read_json(p) for p in directory.glob('*/result-private.json')
                   if p.parent.name in ('flash-candidate', 'rollback-original')]
        require(flashes and max(flashes, key=lambda r: r['claimed_ns'])['passed'] is True,
                'reboot requires last explicit image action to have succeeded')


def claim_action(directory, action, request):
    require(action in ACTIONS, 'unsupported claim action')
    prior_terminal(directory, action)
    dest = directory / action
    dest.mkdir(mode=0o700)  # Existing, even partial, means this action is consumed.
    fsync_dir(directory)
    once(dest / 'request-private.json', request)
    return dest


def worker(request_path):
    request_path = Path(request_path).resolve()
    directory = request_path.parent
    request = read_json(request_path)
    require(request['schema'] == 'samurai-eud-fastboot-action-v1' and
            request['execute_authorized'] is True and request['window_confirmed'] is True,
            'worker requires the original explicit execute/window claim')
    require(directory.name == request['action'] and directory.parent.name == 'fastboot-operator',
            'worker request path')
    require(sha(__file__) == request['operator_sha256'], 'operator changed after claim')
    with locked(directory.parent):
        once(directory / 'worker-process-private.json',
             {'pid': os.getpid(), 'observed': process_info(os.getpid()), 'argv': sys.argv})
        passed = False
        report = {}
        try:
            context_path = Path(request['context_path'])
            require(sha(context_path) == request['context_sha256'], 'context changed after claim')
            context = validate_context(context_path)
            require(context['transaction_id'] == directory.parent.parent.name, 'worker transaction path')
            require((context['transaction_id'], context['token'], context['old_boot_id']) ==
                    (request['transaction_id'], request['token'], request['old_boot_id']),
                    'worker claim transaction mismatch')
            require(local_inputs() == request['inputs'], 'local inputs changed after claim')
            serial = read_json(IDENTITY)['serial']
            report = run_action(request['action'], serial,
                                lambda label, argv: command(directory, label, argv))
            passed = True
        except Exception as exc:
            report = {'error': str(exc), 'runtime_readback_pending': True}
        # If a command was started but its durable terminal receipt was lost,
        # even an exception above must not unblock a subsequent write.
        commands_terminal = all((directory / (p.name.removesuffix('-command-private.json') +
                                              '-terminal-private.json')).is_file()
                                for p in directory.glob('*-command-private.json'))
        publish_result(directory / 'result-private.json',
             dict(report, action=request['action'], terminal=True, commands_terminal=commands_terminal,
                  passed=passed and commands_terminal, claimed_ns=request['claimed_ns'],
                  transaction_id=request['transaction_id'], token=request['token'],
                  old_boot_id=request['old_boot_id'], context_sha256=request['context_sha256']))


def fetch(context_path):
    context = validate_context(context_path)
    directory = Path(context_path).resolve().parent / 'fastboot-operator'
    result = {'transaction_id': context['transaction_id'], 'this_fetch_usb_accessed': False, 'actions': {}}
    if directory.exists():
        for p in sorted(directory.glob('*/request-private.json')):
            action = {'claim_present': True}
            terminal = p.parent / 'result-private.json'
            if terminal.exists():
                report = read_json(terminal)
                action.update(terminal=report['terminal'], passed=report['passed'],
                              commands_terminal=report['commands_terminal'])
            else:
                action.update(terminal=False, status='running_or_unknown_no_replay')
            for record in p.parent.glob('*-process-private.json'):
                child = read_json(record)
                current = process_info(child['pid'])
                observed = child['observed']
                # Reading same PID is diagnostic only. Absence/PID reuse never
                # manufactures a lost exit code or grants another write.
                action[record.stem] = {'current': {k: v for k, v in current.items() if k != 'argv'},
                    'same_observed_argv': current.get('argv') == observed.get('argv'),
                    'same_startticks': not current.get('absent') and
                    current.get('startticks') == observed.get('startticks')}
            result['actions'][p.parent.name] = action
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='check-local', choices=('check-local', 'fetch') + ACTIONS)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--window-confirmed', action='store_true')
    parser.add_argument('--wait-seconds', type=int, default=20)
    args = parser.parse_args(argv)
    require(0 <= args.wait_seconds <= 60, 'bounded client wait 0..60 seconds')
    if args.action == 'check-local':
        inputs = local_inputs()
        if args.context:
            validate_context(args.context)
        print(json.dumps({'passed': True, 'usb_accessed': False, 'files_created': False, 'inputs': inputs}))
        return 0
    require(args.context is not None, 'explicit new transaction context required')
    if args.action == 'fetch':
        print(json.dumps(fetch(args.context)))
        return 0
    require(args.execute and args.window_confirmed, 'USB action requires --execute --window-confirmed')
    inputs = local_inputs()
    context = validate_context(args.context)
    base = args.context.resolve().parent / 'fastboot-operator'
    base.mkdir(mode=0o700, exist_ok=True)
    require(not base.is_symlink(), 'operator directory must not be a symlink')
    with locked(base):
        request = {'schema': 'samurai-eud-fastboot-action-v1', 'execute_authorized': True,
                   'window_confirmed': True, 'action': args.action, 'transaction_id': context['transaction_id'],
                   'token': context['token'], 'old_boot_id': context['old_boot_id'],
                   'context_path': str(args.context.resolve()), 'context_sha256': sha(args.context),
                   'operator_sha256': sha(__file__), 'inputs': inputs, 'claimed_ns': time.time_ns()}
        directory = claim_action(base, args.action, request)
    # A failure after durable claim never removes it. The action is not replayed.
    with (directory / 'worker-stdout-private.bin').open('xb') as out, \
         (directory / 'worker-stderr-private.bin').open('xb') as err:
        argv = [sys.executable, '-B', str(Path(__file__).resolve()), '--_worker',
                str(directory / 'request-private.json')]
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 close_fds=True, start_new_session=True)
        once(directory / 'launcher-process-private.json',
             {'pid': child.pid, 'requested_argv': argv, 'observed': process_info(child.pid)})
    end = time.monotonic() + args.wait_seconds
    while time.monotonic() < end and not (directory / 'result-private.json').exists():
        time.sleep(0.1)
    print(json.dumps(fetch(args.context)))
    if not (directory / 'result-private.json').exists():
        return 2  # pending/unknown, never kill or replay
    return 0 if read_json(directory / 'result-private.json')['passed'] else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--_worker':
        worker(sys.argv[2])
    else:
        try:
            raise SystemExit(main())
        except Exception as exc:
            print(json.dumps({'passed': False, 'error': str(exc), 'no_retry': True}))
            raise SystemExit(1)
