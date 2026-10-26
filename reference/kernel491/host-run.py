"""One reviewed491 host action; stateful sends are never automatically retried."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ast, base64, hashlib, importlib.util, json, os, re, shlex, sys, traceback, types, uuid, zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SOURCES = {'prepare-runtime.py', 'worker-body.py', 'runtime-common.py', 'owner-gate.py',
           'render-queries.py', 'default-probe.py', 'probe-log-audit.py'}
ACTIONS = {'stage', 'launch', 'observe', 'collect'}
digest = lambda data: hashlib.sha256(data).hexdigest()


def original_guard():
    spec = importlib.util.spec_from_file_location('storage461_host491', HERE.parent/'kernel461/storage.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.mount.mounted_build()


def verify_prepared(bound, action, now=None):
    assert action in ACTIONS
    bound = Path(bound)
    assert bound.is_absolute() and bound.is_dir() and not bound.is_symlink()
    prepared_bytes = (bound/'preparation-private.json').read_bytes()
    prepared = json.loads(prepared_bytes)
    plan_bytes = (bound/'plan-private.json').read_bytes(); plan = json.loads(plan_bytes)
    assert prepared['stage'] == plan['stage'] == 491 and prepared['prepared'] is True
    assert prepared['deployable'] is True and plan['deployable'] is True, 'Unbound templates cannot send any query'
    assert digest(plan_bytes) == prepared['plan_sha256']
    window = plan['window_id']; assert re.fullmatch(r'k491-package-only-r[1-9][0-9]*', window)
    assert plan['target_root'] == '/var/lib/samurai/' + window
    assert set(prepared['source_sha256']) == set(plan['source_sha256']) == SOURCES
    assert prepared['source_sha256'] == plan['source_sha256']
    for name, expected in plan['source_sha256'].items():
        assert digest((HERE/name).read_bytes()) == expected, 'Public source drift: ' + name
    candidate = (HERE.parent/'kernel490/candidate-state.json').read_bytes()
    assert digest(candidate) == prepared['candidate_state_sha256'] == plan['candidate_state_sha256']
    assert not plan['modules_or_private_profiles_replaced'] and not plan['persistent_repository_created'] and not plan['candidate_retained']
    worker = (bound/'worker.py').read_bytes()
    assert digest(worker) == prepared['worker_sha256'] == plan['payload_sha256']['worker.py']
    ast.parse(worker)
    assert set(prepared['query_sha256']) == ACTIONS
    queries = {}
    for name in sorted(ACTIONS):
        queries[name] = (bound/(name+'-query.py')).read_bytes()
        assert digest(queries[name]) == prepared['query_sha256'][name], 'Prepared query changed: ' + name
        ast.parse(queries[name])
    payload = (bound/'payload-private.tar.gz').read_bytes()
    assert len(payload) == prepared['archive_bytes'] < 64*1024**2 and digest(payload) == prepared['archive_sha256']
    bindings = plan['authorization_files_sha256']
    assert len(bindings) == 3
    for name, expected in bindings.items():
        path = Path(name); assert path.is_absolute() and path.is_file() and not path.is_symlink()
        assert digest(path.read_bytes()) == expected, 'Bound authorization file changed'
    # Calling only authorization() performs no boot/sysfs/device reads.
    gate = {'__name__': 'host491_authorization', 'WINDOW': window}
    exec(compile((HERE/'owner-gate.py').read_bytes(), str(HERE/'owner-gate.py'), 'exec'), gate)
    now = now or datetime.now(timezone.utc)
    if action in {'stage', 'launch'}:
        gate['authorization'](plan, now)
    else:
        issued = [datetime.fromisoformat(plan[key]['issued_at_utc'].replace('Z', '+00:00')) for key in ['handoff','owner','scoped_owner']]
        assert max(issued) <= now, 'A future authorization is not a previous authorized window'
        gate['authorization'](plan, max(issued))
    return dict(bound=bound, prepared=prepared, plan=plan, source=queries[action], payload=payload,
                preparation_sha256=digest(prepared_bytes), plan_sha256=digest(plan_bytes))


def encode_stage(source):
    ast.parse(source)
    encoded = base64.b85encode(zlib.compress(source, 9)).decode('ascii')
    assert zlib.decompress(base64.b85decode(encoded)) == source
    bootstrap = ('import base64,zlib,hashlib;s=zlib.decompress(base64.b85decode('+repr(encoded)+'))'
                 ';assert hashlib.sha256(s).hexdigest()=='+repr(digest(source))+
                 ';exec(compile(s,"<k491-reviewed-stage>","exec"))')
    command = 'python3 -B -c ' + shlex.quote(bootstrap)
    assert len(command.encode()) < 24000, 'Refuse a long SSH command; full transport argv must also be checked before real use'
    return command, encoded


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def durable_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    fsync_directory(path.parent)


def load_transport(path, source):
    # Execute exactly the previously hashed bytes, with no second file read.
    module = types.ModuleType('_491_authorized_transport_'+digest(source))
    module.__file__ = str(path)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    assert callable(module.raw_ssh)
    return module


def perform(bound, action, transport, transport_sha256, *, now=None, guard=original_guard, loader=load_transport):
    guard()
    verified = verify_prepared(bound, action, now)
    plan, prepared = verified['plan'], verified['prepared']
    source = verified['source']
    path = Path(transport)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    binding = plan['handoff']['host_transport']
    assert Path(binding['path']) == path and binding['sha256'] == transport_sha256
    assert re.fullmatch(r'[0-9a-f]{64}', transport_sha256)
    transport_source = path.read_bytes()
    assert digest(transport_source) == transport_sha256, 'Authorized transport changed'
    ast.parse(transport_source)
    command, _ = encode_stage(source) if action == 'stage' else ('python3 -B -', None)
    stdin = verified['payload'] if action == 'stage' else source
    logroot = Path(bound).parent/('transport-'+plan['window_id'])
    if not logroot.exists():
        logroot.mkdir(mode=0o700); fsync_directory(logroot.parent)
    assert logroot.is_dir() and not logroot.is_symlink()
    if action == 'launch':
        stage = json.loads((logroot/'stage-result-private.json').read_bytes())
        assert stage['transport_returncode'] == 0 and stage['transport_completed'] and not stage['target_state_unknown']
        assert stage['plan_sha256'] == verified['plan_sha256'], 'Launch must follow the same bound successful stage'
    label = action if action in {'stage','launch'} else action+'-'+uuid.uuid4().hex
    attempt_path = logroot/(label+'-attempt-private.json')
    record = dict(action=action, window_id=plan['window_id'], started_at_utc=(now or datetime.now(timezone.utc)).isoformat(),
                  preparation_sha256=verified['preparation_sha256'], plan_sha256=verified['plan_sha256'],
                  query_sha256=digest(source), stdin_sha256=digest(stdin), archive_sha256=prepared['archive_sha256'],
                  transport_sha256=transport_sha256, command_bytes=len(command.encode()),
                  command_below_24000_bytes=True, full_transport_argv_checked=False,
                  no_automatic_retry=True, transport_completed=False, target_state_unknown=True)
    # O_EXCL is the authority for stateful single-attempt behavior, before import or raw_ssh.
    durable_new(attempt_path, (json.dumps(record,indent=2)+'\n').encode())
    error = None; entered_raw_ssh = False
    stdout = stderr = b''
    try:
        host = loader(path, transport_source)
        entered_raw_ssh = True
        result = host.raw_ssh(command, input=stdin, timeout=70, check=False)
        assert isinstance(result.stdout, bytes) and isinstance(result.stderr, bytes), 'Transport must preserve binary output'
        stdout, stderr = result.stdout, result.stderr
        record.update(transport_returncode=result.returncode, transport_completed=True, target_state_unknown=result.returncode != 0)
    except BaseException as failure:
        error = failure
        record.update(error_type=type(failure).__name__, entered_raw_ssh=entered_raw_ssh)
        record['transport_traceback'] = traceback.format_exc()
        for name in ['stdout','stderr']:
            value = getattr(failure,name,None)
            if value is not None:
                assert isinstance(value,(bytes,str))
                value = value if isinstance(value,bytes) else value.encode()
                if name == 'stdout': stdout = value
                else: stderr = value
        record['partial_output'] = True
    extension = '.tar.gz' if action == 'collect' else '.bin'
    output_path = logroot/(label+'-stdout-private'+extension)
    error_path = logroot/(label+'-stderr-private.bin')
    durable_new(output_path,stdout); durable_new(error_path,stderr)
    record.update(stdout_sha256=digest(stdout),stderr_sha256=digest(stderr),stdout_bytes=len(stdout),stderr_bytes=len(stderr))
    result_path = logroot/(label+'-result-private.json')
    durable_new(result_path,(json.dumps(record,indent=2)+'\n').encode())
    if error is not None:
        raise RuntimeError('Transport outcome unknown; inspect retained bytes and only observe the same window, never replay') from error
    return dict(record, result_private=str(result_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bound',required=True,type=Path)
    parser.add_argument('--action',required=True,choices=sorted(ACTIONS))
    parser.add_argument('--transport',required=True,type=Path)
    parser.add_argument('--transport-sha256',required=True)
    args = parser.parse_args()
    result = perform(args.bound,args.action,args.transport,args.transport_sha256)
    print(json.dumps({key:result[key] for key in ['action','window_id','transport_completed','transport_returncode','target_state_unknown','result_private']}))
    return 0 if result['transport_returncode'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
