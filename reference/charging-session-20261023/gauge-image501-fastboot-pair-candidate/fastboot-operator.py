"""One-shot two-partition Image501 fastboot operator. Default is offline, read-only check-local."""
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
CARRIERS = HERE.parent / 'gauge-image501-carriers-candidate'
ACTIVATION = HERE.parent / 'gauge-image501-activation-candidate'
IMAGES = {
    'candidate': {
        'boot': (PRIVATE / 'gauge-image501-boot-private-01/boot-gauge501-private.img',
                 '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695', 100663296),
        'logdump': (PRIVATE / 'gauge-image501-logdump-private-01/logdump-gauge501-private.img',
                    '7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9', 67108864)},
    'original': {
        'boot': (PRIVATE / 'eud-boot-two-ffs-candidate-private-01/boot-two-ffs-private.img',
                 '4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf', 100663296),
        'logdump': (PRIVATE.parent / 'kernel365/logdump-k365-candidate-private.img',
                    'aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da', 67108864)}}
# Explicit two-file operation, no automatic reboot, recovery or second attempt.
PAIR_ACTIONS = {'flash-candidate': 'candidate', 'rollback-original': 'original'}
REBOOT_IMAGES = {'reboot-candidate': ('flash-candidate', 'candidate'),
                 'reboot-original': ('rollback-original', 'original')}
ACTIONS = ('inspect', *PAIR_ACTIONS, *REBOOT_IMAGES)


def pair_hashes(which):
    return {partition: row[1] for partition, row in IMAGES[which].items()}


def pinned_tools():
    pins = read_json(HERE / 'activation-pins.json')
    for name, digest in pins.items():
        require(name in ('prepare-contract.json', 'eud-restart.py'), 'unexpected activation pin')
        require(sha(ACTIVATION / name) == digest, 'activation source changed: ' + name)
    require(set(pins) == {'prepare-contract.json', 'eud-restart.py'}, 'activation pin set')
    return pins


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
    """Local files only; checks all four payloads before any USB command."""
    require(sys.platform == 'linux', 'run inside the existing WSL environment')
    pins = pinned_tools()
    for name, which, key, size_key in (
        ('boot-result.json', 'candidate', 'boot_sha256', 'boot_bytes'),
        ('logdump-result.json', 'candidate', 'logdump_sha256', 'logdump_bytes')):
        receipt = read_json(CARRIERS / name)
        part = 'boot' if name.startswith('boot') else 'logdump'
        require(receipt['passed'] is True and receipt['no_deployment_or_device_access' if part == 'boot'
                    else 'no_device_or_deployment'] is True, 'packaging receipt not passed')
        require(receipt[key] == IMAGES[which][part][1] and
                receipt[size_key] == IMAGES[which][part][2], 'carrier receipt identity mismatch')
    for which in IMAGES:
        for part, (path, digest, size) in IMAGES[which].items():
            require(path.stat().st_size == size and sha(path) == digest, which + ' ' + part + ' changed')
    identity = read_json(IDENTITY)
    require(isinstance(identity['serial'], str) and
            re.fullmatch(r'[A-Za-z0-9._:-]+', identity['serial']), 'invalid private serial')
    require(identity.get('product') == 'msmnile', 'private product is not msmnile')
    require(Path(FASTBOOT).is_file(), 'fixed Windows fastboot executable missing')
    return {'pairs': {k: pair_hashes(k) for k in IMAGES}, 'sizes': {'boot': 100663296, 'logdump': 67108864},
            'private_identity_sha256': sha(IDENTITY), 'fastboot_executable_sha256': sha(FASTBOOT),
            'carrier_receipts': {n: sha(CARRIERS / n) for n in ('boot-result.json', 'logdump-result.json')},
            'activation_pins': pins}


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
    require(context['schema'] == 'samurai-image501-fastboot-context-v1', 'context schema')
    txn, token, boot = (context[k] for k in ('transaction_id', 'token', 'old_boot_id'))
    require(re.fullmatch(r'image501-[a-z0-9-]{8,64}', txn) and
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
    require(guard['schema'] == 'samurai-image501-activation-v1', 'old activation schema')
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
                item['worker_sha256'] == pinned_tools()['eud-restart.py'] and item['argv'] == rargv,
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
    # Both partition geometries must pass before the first write.
    for part in ('boot', 'logdump'):
        out, err = call(part + '-size', [FASTBOOT, '-s', serial, 'getvar', 'partition-size:' + part])
        sizes = re.findall(r'(?m)^(?:\(bootloader\)\s*)?partition-size:' + part +
                           r':\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$', out + '\n' + err)
        require(len(sizes) == 1 and int(sizes[0], 16 if sizes[0].startswith('0x') else 10)
                == IMAGES['candidate'][part][2], 'fresh partition size mismatch: ' + part)
    result = {'fresh_exact_bootloader_identity': True, 'partitions_written': [],
              'runtime_readback_pending': action != 'inspect'}
    if action in PAIR_ACTIONS:
        which = PAIR_ACTIONS[action]
        pair = IMAGES[which]
        # Revalidate all members before the first write. Never reboot a mixed pair.
        for part, (image, digest, size) in pair.items():
            require(image.stat().st_size == size and sha(image) == digest,
                    'image changed before pair dispatch: ' + part)
        # The new kernel is staged first; boot follows. Reboot is a separate action.
        for part in ('logdump', 'boot'):
            image, digest, size = pair[part]
            require(image.stat().st_size == size and sha(image) == digest,
                    'image changed before dispatch: ' + part)
            out, err = call('flash-' + part, [FASTBOOT, '-s', serial, 'flash', part, windows_path(image)])
            text = out + '\n' + err
            require(re.search(r"Writing '" + part + r"'\s+OKAY", text) and 'FAILED' not in text,
                    'flash return/output did not establish successful write: ' + part)
            result['partitions_written'].append(part)
        result['flashed_pair_sha256'] = pair_hashes(which)
        result['pair_complete'] = True
    elif action in REBOOT_IMAGES:
        out, err = call('reboot', [FASTBOOT, '-s', serial, 'reboot'])
        require('FAILED' not in out + err, 'reboot command failed')
        result['reboot_command_returned_zero'] = True
        result['boot_success_proven'] = False
    return result


def reboot_binding(directory, action):
    image_action, which = REBOOT_IMAGES[action]
    image_results = [p for p in directory.glob('*/result-private.json') if p.parent.name in PAIR_ACTIONS]
    require(image_results, 'reboot requires a successful corresponding pair action')
    latest = max(image_results, key=lambda p: read_json(p)['claimed_ns'])
    result = read_json(latest)
    require(latest.parent.name == image_action and result['action'] == image_action and
            result['passed'] is True and result['terminal'] is True and result['commands_terminal'] is True and
            result['partitions_written'] == ['logdump', 'boot'] and result['pair_complete'] is True and
            result['flashed_pair_sha256'] == pair_hashes(which),
            'reboot requires the last pair action, both exact members successful')
    return {'image_action': image_action, 'pair_sha256': pair_hashes(which),
            'image_claim_sha256': sha(latest.parent / 'request-private.json'),
            'image_result_sha256': sha(latest), 'image_claimed_ns': result['claimed_ns']}


def prior_terminal(directory, action):
    """A lost owner / absent child without wait receipt is UNKNOWN, never success."""
    require(not (directory / 'reboot').exists(),
            'legacy reboot claim present; no R2 phase bypass of original evidence')
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
    if action in REBOOT_IMAGES:
        return reboot_binding(directory, action)


def claim_action(directory, action, request):
    require(action in ACTIONS, 'unsupported claim action')
    binding = prior_terminal(directory, action)
    request = dict(request)
    if binding is not None:
        request['image_binding'] = binding
    dest = directory / action
    dest.mkdir(mode=0o700)  # Existing, even partial, means this action is consumed.
    fsync_dir(directory)
    once(dest / 'request-private.json', request)
    return dest


def worker(request_path):
    request_path = Path(request_path).resolve()
    directory = request_path.parent
    request = read_json(request_path)
    require(request['schema'] == 'samurai-image501-fastboot-action-v1' and
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
            if request['action'] in REBOOT_IMAGES:
                require(request['image_binding'] == reboot_binding(directory.parent, request['action']),
                        'corresponding image evidence changed after reboot claim')
            serial = read_json(IDENTITY)['serial']
            report = run_action(request['action'], serial,
                                lambda label, argv: command(directory, label, argv))
            if request['action'] in REBOOT_IMAGES:
                report['image_binding'] = request['image_binding']
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
        request = {'schema': 'samurai-image501-fastboot-action-v1', 'execute_authorized': True,
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
