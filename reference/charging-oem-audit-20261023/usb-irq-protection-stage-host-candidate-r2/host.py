"""Default: source-only checks. Actual adopted Image502 evidence is required to bind.
Explicit launch is once-only; status/fetch never start or stop a worker.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import uuid

if sys.flags.optimize:
    raise RuntimeError('optimized Python disables reviewed evidence checks')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PEER = 'fe80::62:bcff:fe28:a101%29'
ALIAS = '169.254.42.1'
ADOPTION_TX = 'image502-notify-live-001'
GUARD = '/var/lib/samurai/' + ADOPTION_TX + '-adopted/boot-id-private.txt'
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT = '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
R8 = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
KEY_SHA = '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'
COHORT_SHA = '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b'
PAYLOAD_SHA = '9dee06ddea1190ea70a188efe47742afb8b104bf53ac31cb57598f079ee4fb3c'
sha = lambda data: hashlib.sha256(data).hexdigest()


def local(path):
    value = str(path).replace('\\', '/')
    if os.name != 'nt' and value.startswith('E:/'):
        value = '/mnt/e/' + value[3:]
    return Path(value)


BASE = local('E:/edk2-samurai-out/charging-management-20261023')
PRIVATE = BASE / 'usb-irq-protection-stage'
POINTER = BASE / 'boot-adoption-private.json'


def need(value, message):
    if not value:
        raise ValueError(message)


def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def save(path, value):
    create(path, (json.dumps(value, indent=2) + '\n').encode())


def source_check():
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    expected = {'adoption', 'key_transport', 'cohort_delivery', 'cohort_payload_result',
                'cohort_protocol', 'cohort_payload', 'worker', 'worker_delivery', 'worker_contract', 'host', 'remote', 'supervisor'}
    need(set(pins) == expected, 'source pin set differs')
    values = {}
    for name, entry in pins.items():
        data = local(entry['path']).read_bytes()
        need(sha(data) == entry['sha256'], 'frozen source changed: ' + name)
        values[name] = data
    need(pins['key_transport']['sha256'] == KEY_SHA, 'strict original-key source differs')
    need(sha(values['cohort_delivery']) == COHORT_SHA and sha(values['cohort_payload']) == PAYLOAD_SHA,
         'cohort pins differ')
    cohort = json.loads(values['cohort_delivery'])
    need(cohort['passed'] is True and cohort['frozen'] is True
         and cohort['forward_payload']['sha256'] == PAYLOAD_SHA
         and cohort['old_manifest_sha256'] == R8, 'cohort materialization unproved')
    need(json.loads(values['cohort_payload_result'])['passed'] is True, 'payload result failed')
    worker_delivery = json.loads(values['worker_delivery'])
    need(worker_delivery['passed'] is True and worker_delivery['frozen'] is True
         and worker_delivery['files']['stage-worker.py']['sha256'] == pins['worker']['sha256']
         and worker_delivery['files']['contract.json']['sha256'] == pins['worker_contract']['sha256'],
         'worker delivery/source binding differs')
    return pins, values


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, local(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_adoption(d, pointer, result, endpoint, reply, terminal, actual_request):
    need(actual_request == d, 'saved actual adoption request differs from complete postboot review')
    need(d['transaction_id'] == ADOPTION_TX and d['guard'] == GUARD
         and d['candidate_boot_sha256'] == BOOT and d['candidate_logdump_sha256'] == LOGDUMP
         and d['manifest'] == R8 and d['version'] == VERSION, 'adopted Image502 profile differs')
    need(str(uuid.UUID(d['boot'])) == d['boot'] and d['boot'] != d['old_boot'], 'new boot identity invalid')
    expected = dict(guard_path=GUARD, original_key_verified=True, baseline481_verified=True,
                    charging_manifest_sha256=R8, candidate_boot_sha256=BOOT,
                    candidate_logdump_sha256=LOGDUMP, Image502_verified=True,
                    postboot_raw_sha256=d['postboot_raw_sha256'])
    need(pointer == expected and result.get('pointer') == expected, 'current adoption pointer differs')
    need(all(result.get(k) is True for k in ('passed', 'guard_created', 'old_pointer_backup_preserved',
                                            'old_guards_preserved')), 'actual adoption result failed')
    need(terminal.get('terminal') is True and terminal.get('returncode') == 0
         and type(terminal.get('pid')) is int and terminal['pid'] > 0, 'actual adoption child not terminal0')
    need(all(reply.get(k) == v for k, v in dict(guard_created=True, old_guards_preserved=True,
         transaction_id=ADOPTION_TX, boot_id=d['boot'], guard=GUARD,
         boot_and_logdump_verified=True, postboot_raw_sha256=d['postboot_raw_sha256'],
         fresh_validation_passed=True, charging_controls_written=False).items()), 'actual adoption reply differs')
    need(endpoint == dict(kind='usb-ipv6', peer=PEER, interface_index=29, host_key_alias=ALIAS,
         original_key_verified=True, observed_new_boot=d['boot'], guard_path=GUARD,
         postboot_Image502_passed=True), 'actual original-key endpoint differs')


def make_request(transaction, d, worker_sha, payload):
    return dict(schema='samurai-usb-irq-protection-stage-request-v1', transaction_id=transaction,
        cohort_delivery_sha256=COHORT_SHA, payload_sha256=PAYLOAD_SHA,
        payload_base64=base64.b64encode(payload).decode(), worker_sha256=worker_sha,
        identity=dict(boot_id=d['boot'], version=VERSION, serial_sha256=d['serial_sha256'],
                      compatible_sha256=d['compatible_sha256'], rootfs_sha256=d['rootfs']),
        adoption=dict(transaction_id=ADOPTION_TX, guard_path=GUARD,
                      guard_sha256=sha((d['boot'] + '\n').encode()), postboot_raw_sha256=d['postboot_raw_sha256']),
        lease_token=secrets.token_hex(24))


def bind(transaction, context, observed, adopted):
    need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}', transaction), 'new stage transaction name')
    pins, raw = source_check()
    # The reviewed adoption module rechecks the actual seven context originals,
    # exact collector source/request, full postboot audit and new-boot identity.
    module = load_module(pins['adoption']['path'], 'stage_reviewed_image502_adoption')
    d, src = module.review(context, observed)
    a = Path(adopted).resolve()
    need(a == Path(context).resolve().parent / 'adoption-01-private', 'actual adoption directory differs')
    inputs = {'context': Path(context).resolve(), 'postboot': Path(observed).resolve() / 'stdout-private.json',
              'receiver': Path(observed).resolve() / 'receiver-result-private.json', 'pointer': POINTER,
              'request': a / 'adopt-request-private.json', 'result': a / 'adoption-result-private.json',
              'endpoint': a / 'new-endpoint-private.json', 'reply': a / 'adopt-stdout-private.json',
              'terminal': a / 'adopt-transport-terminal-private.json', 'executed': a / 'executed-adoption-source.py'}
    bytes_ = {name: path.read_bytes() for name, path in inputs.items()}
    data = {name: json.loads(value) for name, value in bytes_.items() if name != 'executed'}
    validate_adoption(d, data['pointer'], data['result'], data['endpoint'], data['reply'], data['terminal'], data['request'])
    need(bytes_['executed'] == module.payload(d, src), 'actual adoption payload/source differs')
    out = PRIVATE / transaction
    need(not out.exists(), 'new stage directory already exists; never replay')
    request = make_request(transaction, d, pins['worker']['sha256'], raw['cohort_payload'])
    # No file or directory for this runtime transaction exists until every
    # actual evidence gate above passed. No future identity is synthesized.
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    out.mkdir(mode=0o700)
    save(out / 'request-private.json', request)
    binding = dict(schema='samurai-stage-host-binding-v1', transaction_id=transaction,
                   request_sha256=sha((out / 'request-private.json').read_bytes()),
                   source_pins_sha256=sha((HERE / 'source-pins.json').read_bytes()),
                   evidence={name: dict(path=str(inputs[name]), sha256=sha(value)) for name, value in bytes_.items()},
                   endpoint=data['endpoint'], generated_from_actual_Image502=True, device_accessed=False)
    save(out / 'binding-private.json', binding)
    create(out / 'stage-worker.py', raw['worker'])
    return dict(bound=True, transaction_id=transaction, private_directory=str(out), device_accessed=False)


def bound(transaction, *, launching=False):
    need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}', transaction), 'stage transaction name')
    pins, _ = source_check()
    out = PRIVATE / transaction
    binding = json.loads((out / 'binding-private.json').read_bytes())
    request_raw = (out / 'request-private.json').read_bytes()
    request = json.loads(request_raw)
    need(binding['transaction_id'] == request['transaction_id'] == transaction
         and binding['generated_from_actual_Image502'] is True
         and binding['source_pins_sha256'] == sha((HERE / 'source-pins.json').read_bytes())
         and binding['request_sha256'] == sha(request_raw), 'bound request changed')
    need(sha((out / 'stage-worker.py').read_bytes()) == request['worker_sha256'] == pins['worker']['sha256'],
         'bound worker source changed')
    if launching:
        for name, entry in binding['evidence'].items():
            need(sha(local(entry['path']).read_bytes()) == entry['sha256'], 'actual bound evidence changed: ' + name)
    # Fetch retains this original binding if the current adoption pointer or
    # a later observation changed. Remote same-boot/guard/request/PID gates stay.
    return out, binding, request, request_raw, pins


def transfer(action, transaction, window_confirmed=False):
    need(action in ('launch', 'status', 'fetch'), 'transport action')
    out, binding, request, request_raw, pins = bound(transaction, launching=action == 'launch')
    if action == 'launch':
        need(window_confirmed is True, 'root current exclusive window not supplied')
        need(not (out / 'launch-intent-private.json').exists(), 'launch already claimed; status/fetch only')
    host = load_module(pins['key_transport']['path'], 'stage_original_key')
    endpoint = binding['endpoint']
    need(endpoint['peer'] == PEER and endpoint['host_key_alias'] == ALIAS
         and endpoint['observed_new_boot'] == request['identity']['boot_id'], 'retained endpoint binding differs')
    argv = [host.SSH, '-6', '-T', *host.OPTIONS, '-o', 'HostKeyAlias=' + ALIAS, 'root@' + PEER, 'python3 -']
    envelope = dict(action=action, request=request, request_sha256=sha(request_raw),
                    request_base64=base64.b64encode(request_raw).decode(),
                    worker_base64=base64.b64encode((out / 'stage-worker.py').read_bytes()).decode() if action == 'launch' else None,
                    window_confirmed=window_confirmed is True)
    envelope['supervisor_base64'] = base64.b64encode((HERE / 'supervisor.py').read_bytes()).decode() if action == 'launch' else None
    envelope['supervisor_sha256'] = pins['supervisor']['sha256']
    remote = (HERE / 'remote.py').read_bytes()
    code = ('STAGE_TRANSPORT=' + repr(envelope) + '\n').encode() + remote
    if action == 'launch':
        call = out / 'launch-transport-private'
        save(out / 'launch-intent-private.json', dict(transaction_id=transaction, request_count=1,
             request_sha256=sha(request_raw), code_sha256=sha(code), argv=argv, unknown_means_fetch_only=True))
    else:
        call = out / (action + '-' + secrets.token_hex(8) + '-private')
    call.mkdir(mode=0o700)
    create(call / 'executed-remote.py', code)
    with (call / 'stdout-private.json').open('xb') as stdout, (call / 'stderr-private.txt').open('xb') as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, close_fds=True)
        primary_error = None
        cleanup_errors = []
        terminal = False
        try:
            # If publication fails, no stateful code has been sent. Close the
            # owned stdin to EOF before waiting; do not leave SSH waiting for it.
            save(call / 'transport-child-private.json', dict(pid=child.pid, argv=argv, terminal=False))
            child.communicate(input=code)
        except BaseException as error:
            primary_error = error
        finally:
            try:
                if child.stdin is not None and not child.stdin.closed:
                    child.stdin.close()
            except BaseException as error:
                cleanup_errors.append(dict(phase='owned_stdin_close', error=repr(error)))
            try:
                child.wait()
                terminal = True
            except BaseException as error:
                cleanup_errors.append(dict(phase='same_child_wait', error=repr(error)))
            try:
                stdout.flush(); stderr.flush(); os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
            except BaseException as error:
                cleanup_errors.append(dict(phase='transport_log_fsync', error=repr(error)))
            try:
                save(call / 'transport-terminal-private.json', dict(pid=child.pid, terminal=terminal,
                     returncode=child.returncode, primary_error=repr(primary_error) if primary_error else None,
                     cleanup_errors=cleanup_errors))
            except BaseException as error:
                cleanup_errors.append(dict(phase='terminal_receipt', error=repr(error)))
        if primary_error is not None:
            raise primary_error
        need(terminal and not cleanup_errors, 'transport terminal/receipt uncertain; inspect original child only')
    need(child.returncode == 0, 'transport outcome unverified; retain this child/evidence and fetch only')
    response = json.loads((call / 'stdout-private.json').read_bytes())
    need(response['transaction_id'] == transaction and response['request_sha256'] == sha(request_raw), 'remote binding differs')
    if action == 'fetch':
        files = response.get('files', {})
        raw_directory = call / 'raw'
        raw_directory.mkdir(mode=0o700)
        for name, entry in files.items():
            need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'unsafe fetched filename')
            data = base64.b64decode(entry['base64'], validate=True)
            need(sha(data) == entry['sha256'] and len(data) == entry['bytes'], 'fetched raw bytes differ')
            create(raw_directory / name, data)
    save(call / 'received-result-private.json', response)
    return dict(action=action, private_directory=str(call), process=response.get('process'),
                worker_result_retained=response.get('worker_result') is not None,
                runtime_validation_accepted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('check-local', 'bind', 'launch', 'status', 'fetch'), default='check-local')
    parser.add_argument('--transaction')
    parser.add_argument('--context')
    parser.add_argument('--postboot-directory')
    parser.add_argument('--adoption-directory')
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    if args.action == 'check-local':
        source_check()
        result = dict(source_checks_passed=True, device_accessed=False, runtime_request_generated=False)
    elif args.action == 'bind':
        result = bind(args.transaction, args.context, args.postboot_directory, args.adoption_directory)
    else:
        result = transfer(args.action, args.transaction, args.window_confirmed)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
