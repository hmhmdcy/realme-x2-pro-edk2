"""Successful rollback and a distinct post-restore probe; no transport here."""
from pathlib import Path
import base64, hashlib, json, re, sys
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode = True
sha = lambda raw: hashlib.sha256(raw).hexdigest()
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
IRQ_BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
WORKER='6818939b88a51ccd9d0455438c73ac3ad51c26332acdf8d1ea31096bdfc80c47'
SUPERVISOR='a41fd7cae786e0acea66ef97a71bfa6cf2628a8aadfa9320f114c2c6ff2234a4'
TX_PATTERN='irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}'
PEER = 'fe80::62:bcff:fe28:a101%29'

def need(value, message):
    if not value: raise ValueError(message)

def encode(value): return (json.dumps(value, indent=2) + '\n').encode()

def remote_paths(tx):
    need(re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}', tx), 'rollback transaction')
    root = '/root/charging-management-20261023/' + tx
    names = {'request': 'request-private.json', 'worker_source': 'restore-worker.py',
             'supervisor_source': 'rollback-supervisor.py', 'supervisor_launch': 'launch-receipt-private.json',
             'worker_launch': 'worker-launch-receipt-private.json', 'worker_terminal': 'worker-terminal-private.json',
             'supervisor_process': 'supervisor-process-private.json', 'supervisor_terminal': 'supervisor-terminal-private.json'}
    paths = {key: root + '/' + name for key, name in names.items()}
    paths.update({key: root + '/device-rollback/' + name for key, name in {
        'result': 'result.json', 'worker_process': 'process-private.json',
        'before': 'before-private.json', 'stopped': 'stopped-private.json', 'after': 'after-private.json'}.items()})
    return paths

def decoded_files(response):
    raws = {}
    for name, item in response.get('files', {}).items():
        need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'bounded fetched name')
        raw = base64.b64decode(item['base64'], validate=True)
        need(len(raw) == item['bytes'] and len(raw) <= 8_000_000 and sha(raw) == item['sha256'], 'fetched bytes differ')
        raws[name] = raw
    need(sum(map(len, raws.values())) <= 16_000_000, 'bounded fetched set')
    return raws

def validate_records(request, request_raw, response, worker):
    """Read-only form of the frozen accept_fetch's child/result qualification."""
    worker.unpack(request)
    need(response['transaction_id'] == request['transaction_id'] and response['request_sha256'] == sha(request_raw), 'original response binding')
    need(response.get('worker_terminal_verified') is True, 'original worker terminal missing')
    raws = decoded_files(response)
    names = ('result.json', 'process-private.json', 'launch-receipt-private.json',
             'worker-launch-receipt-private.json', 'worker-terminal-private.json',
             'supervisor-process-private.json', 'supervisor-terminal-private.json',
             'before-private.json', 'stopped-private.json', 'after-private.json')
    need(all(name in raws for name in names), 'complete successful rollback originals required')
    w, launch, end, sup, se, parent = (json.loads(raws[name]) for name in (
        'process-private.json', 'worker-launch-receipt-private.json', 'worker-terminal-private.json',
        'supervisor-process-private.json', 'supervisor-terminal-private.json', 'launch-receipt-private.json'))
    tx = request['transaction_id']; boot = request['identity']['boot_id']; root = '/root/charging-management-20261023/' + tx
    argv = ['python3', '-B', root + '/restore-worker.py', '--execute-rollback']
    sargv = ['python3', '-B', root + '/rollback-supervisor.py', '--execute-supervisor']
    for row in (w, launch, end, sup, se, parent):
        need(row['transaction_id'] == tx and row['boot_id'] == boot, 'same original device transaction/boot')
    need(type(w['pid']) is int and w['pid'] > 0 and type(w['start_ticks']) is int and w['start_ticks'] > 0 and
         w['pid'] == launch['pid'] == end['pid'] == se['worker_pid'] and w['argv'] == launch['argv'] == end['argv'] == argv and
         launch['start_ticks'] in (None, w['start_ticks']), 'original rollback Popen instance')
    need(type(sup['pid']) is int and sup['pid'] > 0 and type(sup['start_ticks']) is int and sup['start_ticks'] > 0 and
         sup['pid'] == launch['supervisor_pid'] == end['supervisor_pid'] == se['pid'] == parent['pid'] and
         sup['argv'] == se['argv'] == parent['argv'] == sargv and sup['start_ticks'] == se['start_ticks'] and
         parent['start_ticks'] in (None, sup['start_ticks']), 'original supervisor instance')
    need(w['worker_sha256'] == request['worker_sha256'] == WORKER and
         all(row['request_sha256'] == sha(request_raw) for row in (launch, end, sup, se, parent)), 'original request/source chain')
    need(end['terminal'] is se['terminal'] is True and type(end['returncode']) is type(se['returncode']) is type(se['worker_returncode']) is int and
         end['returncode'] == se['returncode'] == se['worker_returncode'] == 0 and response['worker_terminal'] == end, 'both original children terminal0')
    value = json.loads(raws['result.json'])
    need(value == response['worker_result'] and value['transaction_id'] == tx and value['profile'] == request['profile'] and
         value['terminal'] is True and value['restored'] is True and value['phase'] == 'staged_original' and
         value['status'] == 'staged_original/runtime_pending' and value['runtime_pending'] is True and
         value['disk_state'] == 'all_original_fsynced' and value['stop_verified'] is True and value['primary_error'] is None and
         not value.get('receipt_error') and not value.get('close_error') and value['unknown_write_state'] is False,
         'successful original rollback terminal required')
    need(value['actual_resident_notes'] == worker.expected_profile(request)['notes'] and
         set(value['final_files']) == set(value['temporary_files']) == set(worker.ORDER), 'profile notes and exact file set')
    for name, digest in worker.OLD_FILES.items():
        need(value['final_files'][name] == dict(sha256=digest, mode='0o600', classification='original') and
             value['temporary_files'][name]['state'] == 'absent', 'original file readback/temporary')
    for role, row in (('process', w), ('supervisor_process', sup)):
        actual = response[role]
        need(actual.get('state') in ('absent', 'zombie') and actual.get('pid') == row['pid'], 'original mutator absent or same zombie')
        if actual['state'] == 'zombie': need(actual.get('start_ticks') == row['start_ticks'], 'same zombie birth')
    for name in ['before-private.json','stopped-private.json','after-private.json']:
        observation=json.loads(raws[name]);worker.validate_cache(observation['current_cache'])
        need(observation['current_cache']==request['current_cache'],'original cache across restore')
    need(not value.get('automatic_replay_or_rollback') and not value.get('module_or_carrier_action') and
         value['old_modules_resident_verified'] is False and value['original_full_runtime_accepted'] is False,
         'disk restoration is not runtime acceptance')
    return value, raws

def post_probe_request(request, result_sha, saved_binding_sha):
    binding=dict(purpose='after-successful-current-two-file-restore',rollback_transaction_id=request['transaction_id'],
        rollback_request_sha256=sha(encode(request)),rollback_result_sha256=result_sha,host_binding_sha256=saved_binding_sha)
    return dict(schema='samurai-irq-native-usb-pm-rollback-current-probe-v1',new_endpoint=PEER,profile=request['profile'],
        saved_source_binding_sha256=sha(encode(binding)))

def validate_probe(report, expected, request, after, worker):
    need(report['schema'] == expected['schema'] and report['request'] == expected, 'distinct post-restore probe binding')
    current = report['current']; identity = current['identity']
    need(report['cache_before']==current['current_cache']==report['cache_after']==after['current_cache']==request['current_cache'],
         'same held post-restore cache bracket')
    need(report['identity_before'] == identity == report['identity_after'] == request['identity'], 'same rollback boot/identity bracket')
    need(type(report['started_boottime_ns']) is type(report['ended_boottime_ns']) is int and
         0 < report['started_boottime_ns'] <= report['ended_boottime_ns'] and
         report['started_boottime_ns'] >= int(after['read_end'] * 1_000_000_000), 'probe must follow completed restore observation')
    worker.validate_profile(request, current)
    return current

def review_completed(rollback_directory, fetch_directory, probe_directory=None):
    """Only original clean host waits + original source chain can authorize bind."""
    import sources
    sources.source_check(); host = sources.load('rollback_host'); host.source_check()
    directory = sources.local(rollback_directory).resolve(); tx = directory.name
    need(directory == (host.PRIVATE / tx).resolve(), 'original rollback host directory')
    original, binding, request, request_raw, _ = host.bound(tx, launching=True)
    need(original.resolve() == directory and request_raw == encode(request), 'retained original request bytes')
    fetch = sources.local(fetch_directory).resolve()
    need(fetch.parent == directory and fetch.name.startswith('fetch-'), 'original same-transaction fetch job')
    terminal, response = host.terminal_job(fetch)
    job = json.loads((fetch / 'job-private.json').read_bytes())
    need(terminal['returncode'] == 0 and job['action'] == 'fetch', 'original clean fetch transport')
    host.review_launch_transport(directory, request, request_raw, response)
    worker = sources.load('rollback_worker')
    value, raws = validate_records(request, request_raw, response, worker)
    need(response['identity_observation'] == response['identity_after'] and
         response['identity_observation'].get('source_boot_same') is True and
         response['identity_observation'].get('identity_matches') is True, 'fetch must observe original rollback boot')
    review = dict(request=request, request_sha256=sha(request_raw), result_sha256=sha(raws['result.json']),
                  rollback_directory=str(directory), rollback_fetch_directory=str(fetch),
                  host_binding_sha256=sha((directory / 'binding-private.json').read_bytes()),
                  result=value, endpoint=binding['endpoint'], identity=request['identity'])
    paths = remote_paths(tx)
    names = {'result':'result.json', 'worker_process':'process-private.json', 'before':'before-private.json',
             'stopped':'stopped-private.json', 'after':'after-private.json', 'supervisor_launch':'launch-receipt-private.json',
             'worker_launch':'worker-launch-receipt-private.json', 'worker_terminal':'worker-terminal-private.json',
             'supervisor_process':'supervisor-process-private.json', 'supervisor_terminal':'supervisor-terminal-private.json'}
    raw_evidence = {key:raws[name] for key,name in names.items()}
    raw_evidence.update(request=request_raw, worker_source=(directory / 'restore-worker.py').read_bytes(),
                        supervisor_source=sources.local(sources.pins()['baseline']['rollback_supervisor']['path']).read_bytes())
    review['rollback'] = dict(transaction_id=tx, request_sha256=sha(request_raw), result_sha256=sha(raws['result.json']),
        host_binding_sha256=review['host_binding_sha256'], worker_sha256=WORKER, supervisor_sha256=SUPERVISOR,
        evidence={key:dict(path=paths[key],sha256=sha(raw)) for key,raw in raw_evidence.items()})
    if probe_directory is not None:
        probe_directory = sources.local(probe_directory).resolve()
        auth = sources.load('rollback_binder').auth_module()
        expected = post_probe_request(request, review['result_sha256'], review['host_binding_sha256'])
        code = ('PROBE_REQUEST=' + repr(expected) + '\n').encode() + sources.local(sources.pins()['baseline']['current_probe']['path']).read_bytes()
        stdout, _, end = auth.saved_transport(probe_directory, code, PEER)
        need(end['returncode'] == 0 and end.get('primary_error') is None and not end.get('cleanup_errors'), 'post-restore probe transport not clean terminal0')
        current = validate_probe(json.loads(stdout), expected, request, json.loads(raws['after-private.json']), worker)
        review.update(current=current, post_restore_probe_directory=str(sources.local(probe_directory).resolve()),
            post_restore_probe=dict(stdin_sha256=sha(code),stdout_sha256=sha(stdout),
              child_sha256=sha((Path(probe_directory)/'child-private.json').read_bytes()),
              terminal_sha256=sha((Path(probe_directory)/'terminal-private.json').read_bytes())))
    return review

def make_guard(tx, token, review):
    import sources
    need(re.fullmatch(TX_PATTERN,tx) and re.fullmatch('[0-9a-f]{48}',token),'new rollback restart identity')
    request=review['request'];current=review['current'];identity=review['identity']
    need(tx!=request['transaction_id'] and identity==current['identity']==request['identity'],'independent same-current-boot restart')
    worker=sources.load('rollback_worker');worker.validate_profile(request,current)
    return dict(schema='samurai-irq-native-usb-pm-rollback-restart-v1',transaction_id=tx,token=token,
        boot_id=identity['boot_id'],kernel_release=RELEASE,kernel_version=identity['version'],
        soc_serial_sha256=identity['serial_sha256'],compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'],
        profile=request['profile'],current_boot_sha256=current['boot']['sha256'],current_logdump_sha256=current['logdump']['sha256'],
        unchanged_boot_sha256=BOOT,rollback_logdump_sha256=LOGDUMP,boot_bytes=100663296,logdump_bytes=67108864,
        resident_notes=current['notes'],current_cache=current['current_cache'],rollback=review['rollback'],post_restore_probe=review['post_restore_probe'],
        partitions=['logdump'],disk_state='all_original_fsynced',runtime_validation_accepted=False)
