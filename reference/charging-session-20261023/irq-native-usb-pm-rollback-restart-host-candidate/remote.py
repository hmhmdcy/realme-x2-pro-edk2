"""Explicit pinned stdin transport. No default device access; no automatic retry."""
from pathlib import Path
import base64, hashlib, json, os, re, runpy, subprocess, sys, time

if sys.flags.optimize: raise RuntimeError('optimized interpreter is unsupported')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
OWNER = Path('/run/samurai-irq-native-usb-pm-rollback-activation-owner-private.json')


def need(value, message):
    if not value: raise ValueError(message)


def raw_request(request): return (json.dumps(request, indent=2) + '\n').encode()


def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def save(path, value): create(path, (json.dumps(value, indent=2) + '\n').encode())


def process(receipt, same_boot):
    if not same_boot: return dict(receipt, status='source_boot_ended')
    try:
        path = Path('/proc', str(receipt['pid'])); fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        argv = [x.decode() for x in (path / 'cmdline').read_bytes().split(b'\0') if x]
        ticks = int(fields[19])
        status = 'pid_reused' if ticks != receipt['startticks'] else 'zombie' if fields[0] == 'Z' else 'alive' if argv == receipt['argv'] else 'unknown'
        return dict(receipt, status=status, observed_argv=argv)
    except FileNotFoundError: return dict(receipt, status='absent')
    except (OSError, ValueError, KeyError, IndexError): return dict(receipt, status='unknown')


def preflight(request, root, allow_inhibit=False):
    raw=(root/'common.py').read_bytes();need(sha(raw)==request['common_sha256'],'exact current device common')
    ns={};exec(compile(raw,'pinned-current-stage-guard','exec'),ns)
    primary=None
    try:
        meta,output,phase=ns['validate_activation_guard'](root/'guard-private.json',allow_inhibit=allow_inhibit)
        need(meta['transaction_id']==request['transaction_id'] and meta['token']==request['token'] and
             meta['boot_id']==request['expected_boot'],'fresh current activation identity')
        return meta,output,phase
    except BaseException as error:
        primary=error;raise
    finally:
        errors=[]
        for name in ['_MAC_FD','_SERVICE_FD']:
            fd=ns.get(name)
            if fd is not None:
                try:ns['os'].close(fd)
                except BaseException as error:errors.append((name,repr(error)))
                finally:ns[name]=None
        if errors:
            if primary is not None:primary.add_note('owned preflight descriptor close errors: '+repr(errors))
            else:raise RuntimeError('owned preflight descriptor close errors: '+repr(errors))


def verify_owner(request, root):
    need(json.loads(OWNER.read_bytes()) == {k: request[k] for k in ('transaction_id', 'token', 'expected_boot')}, 'existing exact remote owner')
    need((root / 'activation-request-private.json').read_bytes() == raw_request(request), 'original complete remote request')
    need(sha((root / 'guard-private.json').read_bytes()) == request['guard_sha256'], 'original remote guard')
    for name, item in request['files'].items(): need(sha((root / name).read_bytes()) == item['sha256'], 'uploaded original changed: ' + name)


def collect(request, root, include_files):
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip(); same = boot == request['expected_boot']
    output = Path('/var/lib/samurai') / request['transaction_id']; files = {}; processes = {}; errors = []
    if include_files:
        for prefix, directory in (('remote-', root), ('quiesce-', output)):
            if not directory.exists(): continue
            for path in sorted(directory.iterdir()):
                try:
                    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 20000000, 'bounded regular evidence')
                    raw = path.read_bytes(); files[prefix + path.name] = dict(base64=base64.b64encode(raw).decode(), sha256=sha(raw), bytes=len(raw))
                except (OSError, ValueError) as error: errors.append(dict(path=str(path), error=repr(error)))
        phase = Path('/run') / (request['transaction_id'] + '-reboot-phase-private.json')
        if phase.exists():
            raw = phase.read_bytes(); files['restart-phase-private.json'] = dict(base64=base64.b64encode(raw).decode(), sha256=sha(raw), bytes=len(raw))
    for role, name in (('quiesce', 'quiesce-process-private.json'), ('supervisor', 'quiesce-supervisor-process-private.json')):
        path = root / name
        try:
            receipt = json.loads(path.read_bytes())
            need(all(receipt[k] == request[k] for k in ('transaction_id', 'token')) and receipt['boot_id'] == request['expected_boot'], 'original process identity')
            processes[role] = process(receipt, same)
        except FileNotFoundError: pass
        except (OSError, ValueError, KeyError) as error: errors.append(dict(path=str(path), error=repr(error)))
    return dict(transaction_id=request['transaction_id'], token=request['token'], boot_id=boot,
                same_old_boot=same, files=files, processes=processes, errors=errors,
                no_cleanup_or_control_action=True)


def prepare(request, root):
    tx = request['transaction_id']; output = Path('/var/lib/samurai') / tx
    need(not root.exists() and not output.exists() and not OWNER.exists() and
         not (Path('/run') / (tx + '-reboot-phase-private.json')).exists(), 'new independent remote transaction only')
    rows = [line.split() for line in Path('/proc/mounts').read_text().splitlines()]
    need(any(row[1:3] == ['/run', 'tmpfs'] for row in rows), 'run tmpfs')
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        if path.parent.name == str(os.getpid()): continue
        try: raw = path.read_bytes()
        except (FileNotFoundError, ProcessLookupError): continue
        if b'python' in raw and any(item in raw for item in (b'/root/charging-', b'/var/lib/samurai/camera-', b'/var/lib/samurai/k481-')):
            raise ValueError('prior finite transaction still exists; no overlap')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == request['expected_boot'], 'same actual adopted source boot')
    need(set(request['files']) == {'eud-quiesce.py', 'eud-restart.py', 'camera481-expected-private.json', 'common.py', 'proof.py', 'activation-supervisor.py'}, 'exact upload set')
    decoded = {name: base64.b64decode(row['base64'], validate=True) for name, row in request['files'].items()}
    for name, raw in decoded.items(): need(sha(raw) == request['files'][name]['sha256'], 'exact uploaded source')
    guard = base64.b64decode(request['guard_base64'], validate=True); need(sha(guard) == request['guard_sha256'], 'exact new guard')
    # Partial upload/validation retains owner and all raw files. Never clear or
    # replay a failed prepare automatically.
    save(OWNER, {k: request[k] for k in ('transaction_id', 'token', 'expected_boot')})
    root.mkdir(mode=0o700)
    for name, raw in decoded.items(): create(root / name, raw)
    create(root / 'guard-private.json', guard); create(root / 'activation-request-private.json', raw_request(request))
    verify_owner(request, root); preflight(request, root)
    result = dict(prepared=True, transaction_id=tx, token=request['token'], boot_id=request['expected_boot'],
                  request_sha256=sha(raw_request(request)), guard_sha256=request['guard_sha256'], hardware_writes=0)
    save(root / 'prepare-result-private.json', result)
    return result


def launch_quiesce(request, root):
    preflight(request, root)
    output = Path('/var/lib/samurai') / request['transaction_id']; need(not output.exists(), 'quiesce output already exists')
    argv = ['python3', '-B', str(root / 'activation-supervisor.py'), '--supervise-quiesce']
    claim = dict(transaction_id=request['transaction_id'], token=request['token'], boot_id=request['expected_boot'],
        request_sha256=sha(raw_request(request)), request_count=1, argv=argv, supervisor_sha256=request['supervisor_sha256'])
    save(root / 'quiesce-intent-private.json', claim)
    with (root / 'quiesce-supervisor-private.log').open('xb') as log:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, close_fds=True)
        try:
            path = Path('/proc', str(child.pid)); fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            receipt = dict(claim, pid=child.pid, startticks=int(fields[19]))
            save(root / 'quiesce-supervisor-launch-private.json', receipt)
        finally:
            # Do not abandon a live handle or kill on a transport deadline. The
            # independently detached supervisor keeps its own original child.
            child.wait()
    return dict(quiesce_launched=True, transaction_id=request['transaction_id'], token=request['token'],
        boot_id=request['expected_boot'], request_sha256=sha(raw_request(request)), supervisor=receipt,
        supervisor_returncode=child.returncode)


def restart(request, root, inspect=False):
    preflight(request, root, allow_inhibit=True)
    if inspect:
        sys.argv = [str(root / 'eud-restart.py'), '--guard', str(root / 'guard-private.json'), '--inspect']
        runpy.run_path(str(root / 'eud-restart.py'), run_name='__main__'); return
    argv = ['python3', '-B', str(root / 'eud-restart.py'), '--guard', str(root / 'guard-private.json'), '--commit-restart2-bootloader']
    save(root / 'restart-intent-private.json', dict(transaction_id=request['transaction_id'], token=request['token'],
        boot_id=request['expected_boot'], request_sha256=sha(raw_request(request)), guard_sha256=request['guard_sha256'],
        worker_sha256=request['worker_hashes']['eud-restart.py'], argv=argv, request_count=1))
    # Replace this exact transport process, no new Popen to lose across EUD/USB.
    # The pinned worker rechecks actual quiesce/hardware, claims once, then uses
    # the existing freeze/RESTART2 tail. A returned/unknown exec is never retried.
    os.execvp('python3', argv)


def execute(data):
    os.umask(0o077); need(os.geteuid() == 0, 'root transport')
    request, action = data['request'], data['action']; tx = request['transaction_id']
    need(re.fullmatch(r'irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}', tx) and re.fullmatch('[0-9a-f]{48}', request['token']), 'new activation identity')
    root = Path('/root/charging-management-20261023') / tx
    if action in ('status', 'fetch'):
        return collect(request, root, action == 'fetch')
    if action == 'prepare': return prepare(request, root)
    verify_owner(request, root)
    if action == 'quiesce': return launch_quiesce(request, root)
    if action in ('inspect', 'restart'): return restart(request, root, action == 'inspect')
    raise ValueError('unknown explicit action')


if __name__ == '__main__':
    if 'CONFIG' not in globals(): print(json.dumps(dict(source_only=True, device_accessed=False)))
    else:
        result = execute(CONFIG)
        if result is not None: print(json.dumps(result), flush=True)
