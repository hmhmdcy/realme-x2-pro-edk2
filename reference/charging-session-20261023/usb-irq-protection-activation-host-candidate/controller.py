"""Stage-authenticated IRQ activation. Default source-check; never dispatch by default."""
from pathlib import Path, PurePosixPath
import argparse, ast, base64, hashlib, importlib.util, json, os, re, secrets, subprocess, sys, time

if sys.flags.optimize: raise RuntimeError('optimized interpreter is unsupported')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
WORKERS = REF / 'charging-session-20261023/usb-irq-protection-restart-candidate'
STAGE = REF / 'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
MUTATING = {'prepare', 'quiesce', 'restart'}
WORKER_HASHES = {'eud-quiesce.py': '43c5bd1952949504e918c660b208ca6bb45cfa103be9c9be575268b64ef9036e',
                 'eud-restart.py': '56a58c08bd3f79813d95955279f3ad07f7338d522239d32a7cfec4ea8d3b05be'}
TX_PATTERN = r'usb-irq-protection-activate-[a-z0-9-]{8,48}'


def need(condition, message):
    if not condition: raise ValueError(message)


def local(value):
    text = str(value).replace('\\', '/')
    return Path('/mnt/e/' + text[3:] if os.name != 'nt' and text.startswith('E:/') else text)


PRIVATE = local('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-activation')


def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)


def save(path, value): create(path, (json.dumps(value, indent=2) + '\n').encode())
def load_json(path): return json.loads(Path(path).read_bytes())
def fact(path): return dict(path=Path(path).name, sha256=sha(Path(path).read_bytes()))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source_check():
    pins = load_json(HERE / 'source-pins.json')
    required = {'device_delivery', 'device_contract', 'device_common', 'quiesce', 'restart',
                'stage_proof', 'stage_proof_frozen', 'postboot_host_delivery', 'operator_delivery',
                'camera_wrapper', 'key_transport', 'baseline_controller', 'baseline_remote', 'baseline_supervisor'}
    need(set(pins) == required, 'exact source pin set')
    for name, item in pins.items():
        need(sha(local(item['path']).read_bytes()) == item['sha256'], 'frozen source changed: ' + name)
    for name in ('device_delivery', 'postboot_host_delivery', 'operator_delivery'):
        path = local(pins[name]['path']); delivery = load_json(path)
        need(delivery['passed'] is True and delivery['frozen'] is True, 'unfrozen input: ' + name)
        for relative, row in delivery['files'].items():
            need(sha((path.parent / relative).read_bytes()) == (row['sha256'] if isinstance(row, dict) else row),
                 'delivery member changed: ' + relative)
    need(pins['device_delivery']['sha256'] == '6187ea66cedfb7eaf747f0894ec17d54da2cd278e3ef0460cf002ee7a3579ad2', 'device delivery')
    need(pins['device_contract']['sha256'] == '13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914', 'fixed contract')
    need(pins['stage_proof']['sha256'] == '85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093', 'stage proof')
    need(pins['operator_delivery']['sha256'] == 'ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41', 'boot-only operator')
    need(pins['postboot_host_delivery']['sha256'] == '8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a', 'postboot host R2')
    for name, digest in WORKER_HASHES.items(): need(sha((WORKERS / name).read_bytes()) == digest, name)
    for name in ('controller.py', 'remote.py', 'supervisor.py'): ast.parse((HERE / name).read_bytes())
    return pins


def reviewed(stage_directory, stage_fetch_directory):
    source_check()
    proof = load(STAGE / 'stage-proof.py', 'activation_actual_stage_proof')
    result = proof.review_stage(local(stage_directory), local(stage_fetch_directory))
    return result, proof.guard_stage_fields(result)


def make_guard(tx, token, review, projection):
    need(re.fullmatch(TX_PATTERN, tx) and re.fullmatch('[0-9a-f]{48}', token), 'new activation identity')
    fixed = load_json(WORKERS / 'prepare-contract.json')['fixed_guard_fields']
    identity = review['identity']
    need(review['source_stage_authenticated'] is True and review['source_version'] == fixed['kernel_version'] == identity['version'], 'real complete adopted Image502 stage required')
    need(review['source_boot_id'] == identity['boot_id'], 'stage identity mismatch')
    adoption = dict(review['adoption'])
    adoption['fresh_validation_sha256'] = adoption.pop('actual_fresh_validation_sha256')
    return dict(fixed, transaction_id=tx, token=token, boot_id=identity['boot_id'],
        soc_serial_sha256=identity['serial_sha256'], compatible_sha256=identity['compatible_sha256'],
        rootfs_release_sha256=identity['rootfs_sha256'], adoption=adoption, stage=projection)


def endpoint_from_stage(stage_directory, review):
    path = local(stage_directory) / 'binding-private.json'; raw = path.read_bytes(); binding = json.loads(raw)
    need(sha(raw) == review['host_binding_sha256'], 'authenticated original stage binding')
    endpoint = binding['endpoint']
    need(endpoint == dict(kind='usb-ipv6', peer='fe80::62:bcff:fe28:a101%29', interface_index=29,
        host_key_alias='169.254.42.1', original_key_verified=True, observed_new_boot=review['source_boot_id'],
        guard_path=review['adoption']['guard_path'], postboot_Image502_passed=True), 'actual adopted endpoint')
    return endpoint


def bind(tx, stage_directory, stage_fetch_directory, *, private=PRIVATE):
    # All original material must authenticate BEFORE any mkdir or owner/guard.
    pins = source_check(); review, projection = reviewed(stage_directory, stage_fetch_directory)
    endpoint = endpoint_from_stage(stage_directory, review)
    token = secrets.token_hex(24); guard = make_guard(tx, token, review, projection)
    root = Path(private); out = root / tx
    need(not out.exists() and not (root / 'active-owner-private.json').exists(), 'new independent activation directory/owner required')
    files = {name: (WORKERS / name).read_bytes() for name in WORKER_HASHES}
    files['camera481-expected-private.json'] = local(pins['camera_wrapper']['path']).read_bytes()
    files['common.py'] = (WORKERS / 'common.py').read_bytes()
    files['activation-supervisor.py'] = (HERE / 'supervisor.py').read_bytes()
    guard_raw = (json.dumps(guard, indent=2) + '\n').encode()
    request = dict(schema='samurai-usb-irq-protection-host-request-v1', transaction_id=tx, token=token,
        expected_boot=guard['boot_id'], guard_sha256=sha(guard_raw),
        files={name: dict(sha256=sha(raw), base64=base64.b64encode(raw).decode()) for name, raw in files.items()},
        guard_base64=base64.b64encode(guard_raw).decode(), worker_hashes=WORKER_HASHES,
        common_sha256=sha(files['common.py']), supervisor_sha256=sha(files['activation-supervisor.py']))
    binding = dict(schema='samurai-usb-irq-protection-host-binding-v1', transaction_id=tx,
        stage_directory=str(local(stage_directory).resolve()), stage_fetch_directory=str(local(stage_fetch_directory).resolve()),
        stage_review=review, stage_projection=projection, endpoint=endpoint,
        source_pins_sha256=sha((HERE / 'source-pins.json').read_bytes()), guard_sha256=sha(guard_raw),
        device_accessed=False, generated_from_actual_Image502=True)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    save(root / 'active-owner-private.json', dict(transaction_id=tx, token=token, boot_id=guard['boot_id']))
    out.mkdir(mode=0o700)
    create(out / 'guard-private.json', guard_raw); save(out / 'request-private.json', request)
    binding['request_sha256'] = sha((out / 'request-private.json').read_bytes())
    save(out / 'binding-private.json', binding)
    return dict(bound=True, directory=str(out), device_accessed=False, transaction_id=tx)


def bound(tx, *, private=PRIVATE, revalidate=False):
    need(re.fullmatch(TX_PATTERN, tx), 'activation transaction name')
    pins = source_check(); directory = Path(private) / tx
    binding = load_json(directory / 'binding-private.json'); request_raw = (directory / 'request-private.json').read_bytes()
    request = json.loads(request_raw); guard_raw = (directory / 'guard-private.json').read_bytes()
    need(binding['transaction_id'] == request['transaction_id'] == tx and
        binding['source_pins_sha256'] == sha((HERE / 'source-pins.json').read_bytes()) and
        binding['request_sha256'] == sha(request_raw) and
        binding['guard_sha256'] == request['guard_sha256'] == sha(guard_raw) and
        base64.b64decode(request['guard_base64'], validate=True) == guard_raw, 'immutable bound inputs')
    owner = load_json(Path(private) / 'active-owner-private.json')
    need(owner == dict(transaction_id=tx, token=request['token'], boot_id=request['expected_boot']), 'exact existing activation owner')
    if revalidate:
        review, projection = reviewed(binding['stage_directory'], binding['stage_fetch_directory'])
        need(review == binding['stage_review'] and projection == binding['stage_projection'], 'original source stage changed')
        need(make_guard(tx, request['token'], review, projection) == json.loads(guard_raw), 'actual guard changed')
        need(endpoint_from_stage(binding['stage_directory'], review) == binding['endpoint'], 'endpoint original changed')
    return directory, request, binding, pins


def ssh_argv(pins, endpoint):
    key = load(local(pins['key_transport']['path']), 'activation_original_key')
    need(endpoint['kind'] == 'usb-ipv6' and endpoint['original_key_verified'] is True and
         endpoint['peer'] == 'fe80::62:bcff:fe28:a101%29' and endpoint['host_key_alias'] == '169.254.42.1', 'exact original-key endpoint')
    return [key.SSH, '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias=169.254.42.1', 'root@' + endpoint['peer'], 'python3 -']


def process_identity(pid):
    p = Path('/proc', str(pid)); fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, startticks=int(fields[19]), argv=[x.decode() for x in (p / 'cmdline').read_bytes().split(bytes([0])) if x])


def process_status(receipt):
    try:
        now = process_identity(receipt['pid'])
        if now['startticks'] != receipt['startticks']: return 'pid_reused'
        fields = Path('/proc', str(receipt['pid']), 'stat').read_text().rsplit(')', 1)[1].split()
        return 'zombie' if fields[0] == 'Z' else 'alive' if now['argv'] == receipt['argv'] else 'unknown'
    except FileNotFoundError: return 'absent'
    except (OSError, KeyError, ValueError, IndexError): return 'unknown'


def ssh_worker(job_path):
    job_path = Path(job_path); j = load_json(job_path); directory = job_path.parent
    need(directory.is_relative_to(PRIVATE) and j['controller_sha256'] == sha(Path(__file__).read_bytes()), 'original host worker')
    program = Path(j['program']).read_bytes(); need(sha(program) == j['program_sha256'], 'original exact stdin')
    out = err = None
    identity = None; receipt_error = None; io_error = None; cleanup_errors = {}; waited = False
    try:
        out = (directory / 'stdout-private.bin').open('xb'); err = (directory / 'stderr-private.bin').open('xb')
        child = subprocess.Popen(j['ssh_argv'], stdin=subprocess.PIPE, stdout=out, stderr=err, close_fds=True)
        try:
            try:
                identity = process_identity(child.pid)
                save(directory / 'ssh-process-private.json', dict(identity, requested_argv=j['ssh_argv'], stdin_sha256=sha(program)))
            except Exception as error: receipt_error = repr(error)
            try: child.communicate(input=program)
            except Exception as error: io_error = repr(error)
        finally:
            # A partial communicate may leave the remote python waiting for
            # EOF. Close only this Popen's still-open pipe BEFORE waiting.
            try:
                if child.stdin is not None and not child.stdin.closed: child.stdin.close()
            except Exception as error: cleanup_errors['stdin_close'] = repr(error)
            try: child.wait(); waited = True  # Same handle; no timeout, kill or retry.
            except Exception as error: cleanup_errors['wait'] = repr(error)
            for name, stream in (('stdout', out), ('stderr', err)):
                try: stream.flush(); os.fsync(stream.fileno())
                except Exception as error: cleanup_errors[name + '_flush'] = repr(error)
    finally:
        for name, stream in (('stdout', out), ('stderr', err)):
            if stream is not None:
                try: stream.close()
                except Exception as error: cleanup_errors[name + '_close'] = repr(error)
    hashes = {}
    for name in ('stdout', 'stderr'):
        try: hashes[name + '_sha256'] = sha((directory / (name + '-private.bin')).read_bytes())
        except Exception as error: hashes[name + '_sha256'] = None; cleanup_errors[name + '_hash'] = repr(error)
    terminal = dict(identity or dict(pid=child.pid), terminal=waited, returncode=child.returncode,
        receipt_error=receipt_error, io_error=io_error, cleanup_errors=cleanup_errors, stdin_sha256=sha(program), **hashes)
    terminal_publish_error = None
    try: save(directory / 'ssh-terminal-private.json', terminal)
    except Exception as error: terminal_publish_error = repr(error)
    # Separate finalization proof prevents a full-looking terminal whose
    # publication/fsync failed from being qualified. Missing proof is unknown.
    complete = dict(pid=child.pid, stdin_sha256=sha(program), wait_returned=waited,
        cleanup_errors=cleanup_errors, terminal_publish_error=terminal_publish_error,
        cleanup_passed=waited and not cleanup_errors and terminal_publish_error is None,
        terminal_sha256=sha((directory / 'ssh-terminal-private.json').read_bytes()) if terminal_publish_error is None else None)
    save(directory / 'ssh-finalization-private.json', complete)
    if not complete['cleanup_passed']: raise RuntimeError('original SSH finalization failed; preserve and observe only')


def start_job(directory, action, request, pins, endpoint, wait_seconds=35):
    target = directory / (action + '-job-' + str(time.time_ns())); target.mkdir(mode=0o700)
    program = ('CONFIG=' + repr(dict(request=request, action=action)) + '\n').encode() + (HERE / 'remote.py').read_bytes()
    create(target / 'program-private.py', program)
    job = dict(program=str(target / 'program-private.py'), program_sha256=sha(program),
        ssh_argv=ssh_argv(pins, endpoint), controller_sha256=sha(Path(__file__).read_bytes()),
        action=action, request_sha256=sha((directory / 'request-private.json').read_bytes()))
    save(target / 'job-private.json', job)
    # Durable selection precedes Popen: controller loss cannot lose the original
    # mutator's job location or permit a second dispatch.
    selected = directory / (action + '-job-private.json' if action in MUTATING else action + '-selection-' + str(time.time_ns()) + '.json')
    save(selected, dict(job=str(target), action=action, program_sha256=sha(program)))
    argv = [sys.executable, '-B', str(HERE / 'controller.py'), '_ssh-worker', '--job', str(target / 'job-private.json')]
    with (target / 'supervisor.log').open('xb') as log:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, close_fds=True)
        receipt_error = None
        try: save(target / 'supervisor-process-private.json', dict(process_identity(child.pid), requested_argv=argv))
        except Exception as error: receipt_error = repr(error)
        try: child.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            return dict(pending=True, job=str(target), receipt_error=receipt_error, original_pid=child.pid, no_replay=True)
        if receipt_error: save(target / 'supervisor-receipt-error-private.json', dict(pid=child.pid, error=receipt_error, no_replay=True))
    return dict(pending=False, job=str(target), supervisor_returncode=child.returncode)


def terminal_job(path):
    directory = Path(path); j = load_json(directory / 'job-private.json')
    program = Path(j['program']).read_bytes(); need(sha(program) == j['program_sha256'], 'retained exact program')
    original = load_json(directory / 'ssh-process-private.json'); terminal = load_json(directory / 'ssh-terminal-private.json')
    finalization = load_json(directory / 'ssh-finalization-private.json')
    need(finalization['cleanup_passed'] is True and finalization['wait_returned'] is True and
         not finalization['cleanup_errors'] and finalization['terminal_publish_error'] is None and
         finalization['pid'] == terminal['pid'] and finalization['stdin_sha256'] == j['program_sha256'] and
         finalization['terminal_sha256'] == sha((directory / 'ssh-terminal-private.json').read_bytes()), 'original cleanup/publication proof required')
    need(terminal['terminal'] is True and type(terminal['returncode']) is int and not terminal.get('receipt_error'), 'original SSH terminal/identity required')
    need(type(original['pid']) is int and original['pid'] > 0 and type(original['startticks']) is int and original['startticks'] > 0 and original['argv'], 'real original SSH process')
    need(all(terminal[k] == original[k] for k in ('pid', 'startticks', 'argv')) and
         original['requested_argv'] == j['ssh_argv'] and
         terminal['stdin_sha256'] == original['stdin_sha256'] == j['program_sha256'], 'same original child/input')
    raw = (directory / 'stdout-private.bin').read_bytes()
    need(sha(raw) == terminal['stdout_sha256'] and sha((directory / 'stderr-private.bin').read_bytes()) == terminal['stderr_sha256'], 'original output bytes')
    return terminal, raw


def reconcile(directory):
    request = load_json(directory / 'request-private.json'); answer = {}
    for action in ('prepare', 'quiesce', 'restart'):
        selected, known = directory / (action + '-job-private.json'), directory / (action + '-known-private.json')
        if not selected.exists() or known.exists(): continue
        selection = load_json(selected); target = Path(selection['job']); j = load_json(target / 'job-private.json')
        need(j['action'] == selection['action'] == action and j['request_sha256'] == sha((directory / 'request-private.json').read_bytes()), 'selected original action/request')
        program = Path(j['program']).read_bytes(); need(sha(program) == selection['program_sha256'] == j['program_sha256'], 'selected original stdin')
        first = ast.parse(program).body[0]; need(isinstance(first, ast.Assign) and first.targets[0].id == 'CONFIG', 'original action envelope')
        envelope = ast.literal_eval(first.value)
        need(envelope == dict(request=request, action=action), 'original bound request only')
        try: terminal, raw = terminal_job(target)
        except FileNotFoundError: answer[action] = 'original_job_pending'; continue
        if action == 'restart':
            save(known, dict(job=str(target), original_ssh_returncode=terminal['returncode'], remote_outcome_unproved=True))
            answer[action] = 'terminal_remote_unproved'; continue
        if terminal['returncode'] != 0 or terminal.get('io_error'):
            answer[action] = 'original_failed_no_promotion'; continue
        value = json.loads(raw)
        need(all(value[k] == request[k] for k in ('transaction_id', 'token')) and value['boot_id'] == request['expected_boot'] and value['request_sha256'] == j['request_sha256'], 'original action reply binding')
        if action == 'prepare': need(value['prepared'] is True and value['guard_sha256'] == request['guard_sha256'], 'actual original prepare')
        else: need(value['quiesce_launched'] is True and value['supervisor']['request_sha256'] == j['request_sha256'], 'actual original supervisor launch')
        save(known, dict(job=str(target), qualified_from_original_terminal=True))
        answer[action] = 'original_terminal_rc0_and_bound_reply'
    return answer


def require_known(directory, action):
    known = load_json(directory / (action + '-known-private.json')); terminal, raw = terminal_job(known['job'])
    if known.get('qualified_from_remote_terminal') is True:
        reply = known['remote_reply']; path = Path(reply['path'])
        need(path.is_relative_to(directory) and sha(path.read_bytes()) == reply['sha256'], 'retained exact qualified remote proof')
        return load_json(path)
    need(terminal['returncode'] == 0 and not terminal.get('io_error'), 'successful original action required')
    return json.loads(raw)


def retain_fetch(directory, value):
    target = directory / ('fetch-' + str(time.time_ns()) + '-private'); target.mkdir(mode=0o700)
    for name, row in value['files'].items():
        need(name == PurePosixPath(name).name and '\\' not in name and ':' not in name and name not in ('.', '..'), 'safe raw filename')
        raw = base64.b64decode(row['base64'], validate=True); need(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'actual fetched raw')
        create(target / name, raw)
    save(target / 'fetch-private.json', value)
    return target


def copy_exact(source, target):
    raw = Path(source).read_bytes()
    if target.exists(): need(target.read_bytes() == raw, 'retained original changed')
    else: create(target, raw)


def qualify_quiesce(directory, value, target):
    request = load_json(directory / 'request-private.json'); tx = request['transaction_id']
    need(value['same_old_boot'] is True and all(value[k] == request[k] for k in ('transaction_id', 'token')), 'same source boot/transaction fetch')
    def get(name): return load_json(target / name)
    q, supervisor = value['processes']['quiesce'], value['processes']['supervisor']
    for item in (q, supervisor): need(item['status'] in ('absent', 'zombie'), 'original quiesce/supervisor not ended')
    own = get('remote-quiesce-process-private.json'); sup = get('remote-quiesce-supervisor-process-private.json')
    launch = get('remote-quiesce-worker-launch-private.json'); wt = get('remote-quiesce-worker-terminal-private.json'); st = get('remote-quiesce-supervisor-terminal-private.json')
    dispatched = get('remote-quiesce-supervisor-launch-private.json'); intent = get('remote-quiesce-intent-private.json')
    root = '/root/charging-management-20261023/' + tx
    argv = ['python3', '-B', root + '/eud-quiesce.py', '--guard', root + '/guard-private.json', '--commit-quiesce']
    need(sup['argv'] == st['argv'] == ['python3', '-B', root + '/activation-supervisor.py', '--supervise-quiesce'] and
         type(sup['pid']) is int and sup['pid'] > 0 and type(sup['startticks']) is int and sup['startticks'] > 0 and
         launch.get('capture_error') is None, 'exact original supervisor/self receipt')
    for item in (own, sup, launch, wt, st, dispatched, intent):
        need(all(item[k] == request[k] for k in ('transaction_id', 'token')) and item['boot_id'] == request['expected_boot'] and
             item['request_sha256'] == sha((directory / 'request-private.json').read_bytes()), 'original supervisor chain request')
    need(intent['request_count'] == dispatched['request_count'] == 1 and
         intent['argv'] == dispatched['argv'] == sup['argv'] and dispatched['pid'] == sup['pid'] and
         dispatched['startticks'] == sup['startticks'] and
         intent['supervisor_sha256'] == dispatched['supervisor_sha256'] == request['supervisor_sha256'], 'original once supervisor launch')
    need(own['argv'] == launch['argv'] == wt['argv'] == argv and own['worker_sha256'] == WORKER_HASHES['eud-quiesce.py'], 'exact original quiesce worker')
    need(type(own['startticks']) is int and own['startticks'] > 0 and launch['startticks'] in (None, own['startticks']), 'original quiesce ticks')
    need(own['pid'] == launch['pid'] == wt['pid'] == st['worker_pid'] and
         sup['pid'] == launch['supervisor_pid'] == wt['supervisor_pid'] and sup['startticks'] == st['startticks'], 'original supervisor/child IDs')
    need(wt['terminal'] is True and type(wt['returncode']) is int and wt['returncode'] == 0 and
         st['terminal'] is True and type(st['returncode']) is type(st['worker_returncode']) is int and st['returncode'] == st['worker_returncode'] == 0, 'both actual Popen terminal0')
    for current, original in ((q, own), (supervisor, sup)):
        need(all(current[k] == original[k] for k in ('pid', 'startticks', 'argv', 'transaction_id', 'token', 'boot_id')), 'same ended original process')
    state, summary = get('quiesce-state-private.json'), get('quiesce-summary.json')
    need(state['terminal'] is True and type(state['exit_code']) is int and state['exit_code'] == 0 and state['pid'] == own['pid'] and summary['taint'] == 0, 'successful real quiesce result')
    for item in (state, summary): need(all(item[k] == request[k] for k in ('transaction_id', 'token')) and item['boot_id'] == request['expected_boot'], 'quiesce result identity')
    for source, dest in [('quiesce-state-private.json', 'quiesce-state-private.json'), ('quiesce-summary.json', 'quiesce-summary-private.json'), ('quiesce-boot-id-private.txt', 'quiesce-boot-id-private.txt')]:
        copy_exact(target / source, directory / dest)
    need((directory / 'quiesce-boot-id-private.txt').read_text().strip() == request['expected_boot'], 'quiesce boot raw')
    path = directory / 'quiesce-process-private.json'
    if path.exists():
        previous = load_json(path)
        need(all(previous[k] == q[k] for k in ('pid', 'startticks', 'argv', 'transaction_id', 'token', 'boot_id')) and
             previous['status'] in ('absent', 'zombie'), 'retained ended process instance changed')
    else: save(path, q)
    selected = load_json(directory / 'quiesce-job-private.json')
    terminal_job(selected['job'])  # Actual original SSH wait terminal, rc255 may be explained by full remote proof.
    known = directory / 'quiesce-known-private.json'
    if not known.exists():
        proof = target / 'fetch-private.json'
        save(known, dict(job=selected['job'], qualified_from_remote_terminal=True,
                         remote_reply=dict(path=str(proof), sha256=sha(proof.read_bytes()))))
    return True


def qualify_prepare(directory, value, target):
    request = load_json(directory / 'request-private.json')
    need(value['same_old_boot'] is True, 'same original prepare boot')
    raw = (target / 'remote-activation-request-private.json').read_bytes()
    need(raw == (directory / 'request-private.json').read_bytes(), 'exact actual uploaded request')
    need((target / 'remote-guard-private.json').read_bytes() == (directory / 'guard-private.json').read_bytes(), 'original prepare guard raw')
    for name, row in request['files'].items(): need(sha((target / ('remote-' + name)).read_bytes()) == row['sha256'], 'all original uploads read back')
    proof_path = target / 'remote-prepare-result-private.json'; proof = load_json(proof_path)
    need(proof['prepared'] is True and proof['hardware_writes'] == 0 and proof['request_sha256'] == sha(raw) and
         proof['guard_sha256'] == request['guard_sha256'] and proof['boot_id'] == request['expected_boot'] and
         all(proof[k] == request[k] for k in ('transaction_id', 'token')), 'original complete prepare proof')
    selected = load_json(directory / 'prepare-job-private.json'); terminal_job(selected['job'])
    known = directory / 'prepare-known-private.json'
    if not known.exists(): save(known, dict(job=selected['job'], qualified_from_remote_terminal=True,
        remote_reply=dict(path=str(proof_path), sha256=sha(proof_path.read_bytes()))))
    return True


def host_jobs(directory):
    answer = {}
    for target in sorted(directory.glob('*-job-*')):
        if not target.is_dir(): continue
        row = {}
        for name in ('supervisor-process-private.json', 'ssh-process-private.json'):
            try:
                original = load_json(target / name); row[name] = dict(original=original, status=process_status(original))
            except FileNotFoundError: pass
            except (OSError, ValueError) as error: row[name] = dict(read_error=repr(error))
        try: row['ssh_terminal'] = load_json(target / 'ssh-terminal-private.json')
        except FileNotFoundError: pass
        except (OSError, ValueError) as error: row['terminal_error'] = repr(error)
        answer[target.name] = row
    return answer


def export_context(directory):
    g = load_json(directory / 'guard-private.json'); binding = load_json(directory / 'binding-private.json')
    need((directory / 'quiesce-process-private.json').exists(), 'actual qualified quiesce required')
    claim = load_json(directory / 'restart-claim-private.json'); selection = load_json(directory / 'restart-job-private.json')
    terminal, raw = terminal_job(selection['job'])
    need(all(claim[k] == g[k] for k in ('transaction_id', 'token', 'boot_id')), 'bound restart claim')
    dispatch = dict(schema='samurai-eud-restart-dispatch-v1', transaction_id=g['transaction_id'], token=g['token'], boot_id=g['boot_id'],
        guard_sha256=sha((directory / 'guard-private.json').read_bytes()), request_count=1, state='dispatched_once',
        worker_sha256=WORKER_HASHES['eud-restart.py'], argv=claim['argv'], host_process=terminal,
        host_claim_sha256=sha((directory / 'restart-claim-private.json').read_bytes()),
        restart_claim_intent='claimed_by_pinned_worker', restart_claim_observed=False, syscall_success_proven=False)
    if (directory / 'restart-dispatch-private.json').exists(): need(load_json(directory / 'restart-dispatch-private.json') == dispatch, 'original dispatch changed')
    else: save(directory / 'restart-dispatch-private.json', dispatch)
    files = {key: fact(directory / name) for key, name in {
        'guard':'guard-private.json', 'quiesce_state':'quiesce-state-private.json', 'quiesce_summary':'quiesce-summary-private.json',
        'quiesce_boot_id':'quiesce-boot-id-private.txt', 'quiesce_process':'quiesce-process-private.json',
        'restart_dispatch':'restart-dispatch-private.json', 'restart_claim':'restart-claim-private.json'}.items()}
    context = dict(schema='samurai-usb-irq-protection-fastboot-context-v1', transaction_id=g['transaction_id'], token=g['token'],
        old_boot_id=g['boot_id'], guard_sha256=files['guard']['sha256'], files=files,
        stage_directory=binding['stage_directory'], stage_fetch_directory=binding['stage_fetch_directory'])
    save(directory / 'host-context-private.json', context)
    return context


def run(action, tx, execute=False, window_confirmed=False, *, private=PRIVATE, start=start_job):
    need(action in ('prepare', 'quiesce', 'status', 'fetch', 'inspect', 'restart'), 'explicit action')
    need(execute and window_confirmed, 'explicit execute/current exclusive window')
    directory, request, binding, pins = bound(tx, private=private, revalidate=action not in ('status', 'fetch'))
    try: reconciliation = reconcile(directory)
    except (OSError, ValueError, KeyError, AssertionError) as error:
        if action not in ('status', 'fetch'): raise
        reconciliation = dict(read_error=repr(error), no_mutator_replayed=True)
    # The original SSH may have ended after a pending return and USB may now
    # be gone. Export from that original terminal before any new readonly SSH;
    # an unavailable network must not hide the already retained context.
    if (directory / 'restart-known-private.json').exists() and not (directory / 'host-context-private.json').exists():
        export_context(directory)
    if action not in ('status', 'fetch'):
        for other in MUTATING:
            if (directory / (other + '-intent-private.json')).exists() and not (directory / (other + '-known-private.json')).exists():
                raise ValueError('original mutation pending/unknown; status/fetch only')
        if action != 'prepare': require_known(directory, 'prepare')
    if action in ('inspect', 'restart'):
        require_known(directory, 'quiesce')
        need((directory / 'quiesce-process-private.json').exists(), 'fetch original supervisor/worker terminal proof first')
    if action == 'restart':
        selected = sorted(directory.glob('inspect-known-*-private.json')); need(selected, 'fresh readonly inspect required')
        inspected = load_json(selected[-1]); terminal, stdout = terminal_job(inspected['job'])
        need(terminal['returncode'] == 0 and json.loads(stdout)['inspect_only'] is True and 0 <= time.time() - inspected['received_at'] <= 30, 'fresh successful readonly inspect')
        root = '/root/charging-management-20261023/' + tx
        save(directory / 'restart-claim-private.json', dict(schema='samurai-eud-restart-host-claim-v1', transaction_id=tx,
            token=request['token'], boot_id=request['expected_boot'], guard_sha256=request['guard_sha256'], request_count=1,
            worker_sha256=WORKER_HASHES['eud-restart.py'], argv=['python3', '-B', root + '/eud-restart.py', '--guard', root + '/guard-private.json', '--commit-restart2-bootloader']))
    if action in MUTATING:
        save(directory / (action + '-intent-private.json'), dict(transaction_id=tx, token=request['token'], action=action,
            request_count=1, request_sha256=sha((directory / 'request-private.json').read_bytes()), guard_sha256=request['guard_sha256']))
    job = start(directory, action, request, pins, binding['endpoint'])
    if job['pending']: return job
    terminal, raw = terminal_job(job['job'])
    if action in MUTATING:
        outcome = reconcile(directory)
        if action == 'restart' and (directory / 'restart-known-private.json').exists() and not (directory / 'host-context-private.json').exists():
            export_context(directory)
        return dict(action=action, original_ssh_returncode=terminal['returncode'], reconciled=outcome,
                    remote_outcome_unproved=action == 'restart', no_replay=True)
    if terminal['returncode'] != 0:
        return dict(read_error=True, original_ssh_returncode=terminal['returncode'], host_jobs=host_jobs(directory),
                    reconciled=reconciliation, no_mutator_replayed=True)
    value = json.loads(raw)
    if action == 'fetch':
        target = retain_fetch(directory, value)
        qualifications = {}
        if (directory / 'prepare-job-private.json').exists():
            try: qualifications['prepare'] = qualify_prepare(directory, value, target)
            except (OSError, ValueError, KeyError, AssertionError) as error: qualifications['prepare'] = dict(not_yet_qualified=repr(error))
        if value['same_old_boot'] and 'quiesce' in value['processes']:
            try: qualifications['quiesce'] = qualify_quiesce(directory, value, target)
            except (OSError, ValueError, KeyError, AssertionError) as error: qualifications['quiesce'] = dict(not_yet_qualified=repr(error))
        if (directory / 'restart-known-private.json').exists() and not (directory / 'host-context-private.json').exists(): export_context(directory)
        return dict(retained=str(target), processes=value['processes'], qualifications=qualifications,
                    host_jobs=host_jobs(directory), no_cleanup_performed=True)
    if action == 'inspect': save(directory / ('inspect-known-' + str(time.time_ns()) + '-private.json'), dict(job=job['job'], received_at=time.time()))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='check-local', choices=['check-local', 'bind', 'prepare', 'quiesce', 'status', 'fetch', 'inspect', 'restart', '_ssh-worker'])
    parser.add_argument('--transaction'); parser.add_argument('--stage-directory'); parser.add_argument('--stage-fetch-directory'); parser.add_argument('--job')
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--window-confirmed', action='store_true'); args = parser.parse_args()
    if args.action == '_ssh-worker': ssh_worker(args.job); return 0
    if args.action == 'check-local':
        source_check(); print(json.dumps(dict(source_only=True, runtime_material_created=False, device_accessed=False))); return 0
    if args.action == 'bind': result = bind(args.transaction, args.stage_directory, args.stage_fetch_directory)
    else: result = run(args.action, args.transaction, args.execute, args.window_confirmed)
    print(json.dumps(result, indent=2)); return 0


if __name__ == '__main__': raise SystemExit(main())
