"""Authenticate saved stage originals only. No transport or activation dependency."""
from pathlib import Path, PurePosixPath
import ast
import base64
import copy
import hashlib
import importlib.util
import json
import os
import re

HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
REMOTE_ROOT = '/root/charging-management-20261023'
EVIDENCE = {
    'request': 'request-private.json', 'result': 'device-stage/result.json',
    'before': 'device-stage/before-private.json', 'stopped': 'device-stage/stopped-private.json',
    'after': 'device-stage/after-private.json', 'worker_process': 'device-stage/process-private.json',
    'adoption_proof': 'device-stage/adoption-proof-private.json',
    'worker_launch': 'worker-launch-receipt-private.json', 'worker_terminal': 'worker-terminal-private.json',
    'supervisor_launch': 'launch-receipt-private.json', 'supervisor_process': 'supervisor-process-private.json',
    'supervisor_terminal': 'supervisor-terminal-private.json',
    'worker_source': 'stage-worker.py', 'supervisor_source': 'stage-supervisor.py',
}


def need(value, message):
    if not value:
        raise ValueError(message)


def local(value):
    text = str(value).replace('\\', '/')
    return Path('/mnt/e/' + text[3:] if os.name != 'nt' and text.startswith('E:/') else text)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_check():
    pins = read_json(HERE / 'stage-source-pins.json')
    required = {'stage_host_delivery', 'stage_host', 'stage_remote', 'stage_supervisor',
                'stage_worker_delivery', 'stage_worker', 'cohort_delivery'}
    need(set(pins) == required, 'stage source pin set differs')
    for name, entry in pins.items():
        need(sha(local(entry['path']).read_bytes()) == entry['sha256'], 'source changed: ' + name)
    for name in ('stage_host_delivery', 'stage_worker_delivery', 'cohort_delivery'):
        path = local(pins[name]['path'])
        delivery = read_json(path)
        need(delivery['passed'] is True and delivery['frozen'] is True, 'source is not frozen: ' + name)
        for relative, item in delivery['files'].items():
            digest = item['sha256'] if isinstance(item, dict) else item
            need(sha((path.parent / relative).read_bytes()) == digest, 'delivery input changed: ' + relative)
    return pins


def modules():
    pins = source_check()
    host = load(local(pins['stage_host']['path']), 'irq_stage_reviewed_host_r2')
    inputs, _ = host.source_check()
    worker = load(local(pins['stage_worker']['path']), 'irq_stage_reviewed_worker')
    key = load(host.local(inputs['key_transport']['path']), 'irq_stage_original_key')
    return pins, host, worker, key


def review_source(stage, binding, request, host, host_pins):
    evidence = binding['evidence']
    need(set(evidence) == {'context', 'postboot', 'receiver', 'pointer', 'request', 'result',
                            'endpoint', 'reply', 'terminal', 'executed'}, 'source evidence set differs')
    values = {}
    for name, entry in evidence.items():
        # The current global pointer may have moved after activation. Reuse
        # adoption's actual fsynced retained pointer bytes, never fabricate it.
        path = local(entry['path'])
        if name == 'pointer':
            path = local(evidence['request']['path']).parent / 'adoption-pointer-private.json'
        raw = path.read_bytes()
        need(sha(raw) == entry['sha256'], 'source original changed: ' + name)
        values[name] = raw
    adoption = host.load_module(host_pins['adoption']['path'], 'irq_stage_source_502_adoption')
    d, src = adoption.review(local(evidence['context']['path']), local(evidence['postboot']['path']).parent)
    parsed = {name: json.loads(raw) for name, raw in values.items() if name != 'executed'}
    host.validate_adoption(d, parsed['pointer'], parsed['result'], parsed['endpoint'],
                          parsed['reply'], parsed['terminal'], parsed['request'])
    need(values['executed'] == adoption.payload(d, src), 'actual source adoption payload differs')
    need(binding['endpoint'] == parsed['endpoint'], 'source endpoint binding differs')
    expected = host.make_request(request['transaction_id'], d, request['worker_sha256'],
                                 base64.b64decode(request['payload_base64'], validate=True))
    expected['lease_token'] = request['lease_token']
    need(expected == request, 'stage request is not derived from actual full Image502 evidence')
    return d


def executable_envelope(path, body, action, request, request_raw, supervisor_raw, worker_raw):
    raw = Path(path).read_bytes()
    first, suffix = raw.split(b'\n', 1)
    tree = ast.parse(first)
    need(len(tree.body) == 1 and isinstance(tree.body[0], ast.Assign)
         and len(tree.body[0].targets) == 1 and isinstance(tree.body[0].targets[0], ast.Name)
         and tree.body[0].targets[0].id == 'STAGE_TRANSPORT', 'unexpected executed transport prefix')
    envelope = ast.literal_eval(tree.body[0].value)
    need(suffix == body and envelope['action'] == action and envelope['request'] == request
         and envelope['request_sha256'] == sha(request_raw)
         and base64.b64decode(envelope['request_base64'], validate=True) == request_raw,
         'executed transport source/request differs')
    need(envelope['supervisor_sha256'] == sha(supervisor_raw), 'supervisor upload identity differs')
    if action == 'launch':
        need(envelope['window_confirmed'] is True
             and base64.b64decode(envelope['worker_base64'], validate=True) == worker_raw
             and base64.b64decode(envelope['supervisor_base64'], validate=True) == supervisor_raw,
             'original launch sources differ')
    else:
        need(envelope['worker_base64'] is None and envelope['supervisor_base64'] is None,
             'read-only fetch attempted to send sources')
    return raw


def terminal(path, child_path, argv, *, require_zero):
    fact, child = read_json(path), read_json(child_path)
    need(type(child.get('pid')) is int and child['pid'] > 0 and child['argv'] == argv,
         'actual original strict-key transport child missing')
    need(fact['pid'] == child['pid'] and fact['terminal'] is True
         and type(fact['returncode']) is int, 'original transport is not terminal')
    if require_zero:
        need(fact['returncode'] == 0 and fact.get('primary_error') is None
             and not fact.get('cleanup_errors'), 'fetch transport did not finish cleanly')
    return fact


def verify_chain(raws, request, request_sha, root):
    tx, boot = request['transaction_id'], request['identity']['boot_id']
    s = {name: json.loads(raws[name]) for name in ('supervisor_launch', 'supervisor_process',
         'supervisor_terminal', 'worker_launch', 'worker_terminal', 'worker_process')}
    sup_argv = ['python3', '-B', root + '/stage-supervisor.py', '--execute-supervisor']
    worker_argv = ['python3', '-B', root + '/stage-worker.py', '--execute-stage']
    sup, own, end, launch, finish, process = [s[n] for n in ('supervisor_launch', 'supervisor_process',
         'supervisor_terminal', 'worker_launch', 'worker_terminal', 'worker_process')]
    for item in (sup, own, end, launch, finish):
        need(item['transaction_id'] == tx and item['boot_id'] == boot and item['request_sha256'] == request_sha,
             'original process chain transaction/boot/request differs')
    need(type(sup.get('pid')) is int and sup['pid'] > 0 and sup['pid'] == own['pid'] == end['pid']
         and sup['argv'] == own['argv'] == end['argv'] == sup_argv, 'supervisor original PID/argv differs')
    need(type(own['start_ticks']) is int and own['start_ticks'] > 0
         and (sup['start_ticks'] is None or type(sup['start_ticks']) is int)
         and sup['start_ticks'] in (None, own['start_ticks']) and end['start_ticks'] == own['start_ticks'],
         'supervisor start ticks differ')
    need(end['terminal'] is True and type(end['returncode']) is type(end['worker_returncode']) is int
         and end['returncode'] == end['worker_returncode'] == 0,
         'supervisor did not reach actual terminal0')
    need(type(launch.get('pid')) is int and launch['pid'] > 0
         and launch['pid'] == process['pid'] == finish['pid'] == end['worker_pid']
         and launch['supervisor_pid'] == finish['supervisor_pid'] == sup['pid']
         and launch['argv'] == process['argv'] == finish['argv'] == worker_argv,
         'original worker Popen/argv/supervisor differs')
    need(type(process['start_ticks']) is int and process['start_ticks'] > 0
         and (launch['start_ticks'] is None or type(launch['start_ticks']) is int)
         and launch['start_ticks'] in (None, process['start_ticks']), 'worker start ticks differ')
    need(process['transaction_id'] == tx and process['boot_id'] == boot
         and process['worker_sha256'] == request['worker_sha256'], 'actual worker self receipt differs')
    need(finish['terminal'] is True and type(finish['returncode']) is int
         and finish['returncode'] == 0, 'worker actual Popen terminal is not0')
    return dict(supervisor_pid=sup['pid'], supervisor_start_ticks=own['start_ticks'],
                worker_pid=process['pid'], worker_start_ticks=process['start_ticks'],
                supervisor_returncode=0, worker_returncode=0)


def verify_stage(raws, request, worker):
    result = json.loads(raws['result'])
    expected = dict(schema='samurai-usb-irq-protection-stage-result-v1', transaction_id=request['transaction_id'],
        cohort_delivery_sha256=worker.COHORT, payload_sha256=worker.PAYLOAD,
        old_manifest_sha256=worker.OLD, new_manifest_sha256=worker.NEW,
        phase='staged', status='staged/runtime_pending', staged=True, runtime_pending=True,
        terminal=True, disk_state='all_new_fsynced', stop_verified=True, primary_error=None,
        unknown_write_state=False, source_boot_id=request['identity']['boot_id'], source_version=worker.VERSION,
        source_guard_path=request['adoption']['guard_path'], activation_attempted=False,
        new_module_loaded=False, capture_issued=False, automatic_rollback_or_replay=False)
    need(all(result.get(k) == v for k, v in expected.items()), 'stage is not the exact successful disk-only terminal')
    need(not result.get('receipt_error') and not result.get('close_error') and result.get('stop_error') is None,
         'stage has receipt/close/stop error')
    before, stopped, after = [json.loads(raws[n]) for n in ('before', 'stopped', 'after')]
    worker.healthy(before, before['read_end'])
    worker.safe_sample(stopped, stopped['read_end']); worker.unchanged(before, stopped)
    worker.safe_sample(after, after['read_end']); worker.unchanged(before, after)
    need(before['state']['boot_id'] == request['identity']['boot_id']
         and before['read_end'] <= stopped['read_start'] <= stopped['read_end'] <= after['read_start'],
         'stage observations reversed or belong to another boot')
    need(stopped['state']['registers']['08'] & 0x18 == after['state']['registers']['08'] & 0x18 == 8,
         'actual stopped/final REG08 is not INHIBIT')
    need(result['old_resident_notes'] == result['resident_notes_expected'] == after['notes'] == worker.OLD_NOTES,
         'old resident notes not retained')
    need(set(result['final_files']) == set(worker.ORDER) and set(result['temporary_files']) == set(worker.ORDER),
         'final target set differs')
    for target in worker.ORDER:
        row = result['final_files'][target]
        need(row == dict(sha256=worker.NEW_FILES[target], mode='0o600', classification='new',
             old_sha256=worker.OLD_FILES[target], new_sha256=worker.NEW_FILES[target]), 'new disk file fact differs')
        temp = result['temporary_files'][target]
        expected_temp = str(PurePosixPath(target).with_name('.' + PurePosixPath(target).name + '.' + request['transaction_id'] + '.next'))
        need(temp == dict(path=expected_temp, state='absent'), 'stage temporary output remains/unknown/differs')
        need(sha(raws['backup:' + Path(target).name]) == worker.OLD_FILES[target], 'exact original backup differs')
    adoption = json.loads(raws['adoption_proof'])
    need(adoption['postboot_raw_sha256'] == request['adoption']['postboot_raw_sha256']
         and adoption['guard_sha256'] == request['adoption']['guard_sha256']
         and adoption['actual_fresh_validation_sha256'] == result['adoption_fresh_validation_sha256']
         and re.fullmatch('[0-9a-f]{64}', adoption['actual_fresh_validation_sha256']), 'actual adoption proof hash differs')
    return result


def review_stage(stage_directory, fetch_directory, *, expected_transaction=None):
    pins, host, worker, key = modules()
    stage, fetched = Path(stage_directory).resolve(), Path(fetch_directory).resolve()
    request_raw = (stage / 'request-private.json').read_bytes(); request = json.loads(request_raw)
    tx = request['transaction_id']
    need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}', tx)
         and stage == (host.PRIVATE / tx).resolve(), 'actual stage-host private directory differs')
    need(expected_transaction is None or expected_transaction == tx, 'expected stage transaction differs')
    need(fetched.parent == stage and re.fullmatch(r'fetch-[0-9a-f]{16}-private', fetched.name), 'actual original fetch directory differs')
    host_pins, _ = host.source_check()
    binding_raw = (stage / 'binding-private.json').read_bytes(); binding = json.loads(binding_raw)
    need(binding['transaction_id'] == tx and binding['request_sha256'] == sha(request_raw)
         and binding['source_pins_sha256'] == sha((Path(host.__file__).parent / 'source-pins.json').read_bytes()),
         'actual stage binding differs')
    need(request['worker_sha256'] == pins['stage_worker']['sha256'], 'stage worker identity differs')
    worker.unpack(request)  # Actual fixed recipe/payload validator, not a hash-shaped permission.
    review_source(stage, binding, request, host, host_pins)
    worker_raw = (stage / 'stage-worker.py').read_bytes()
    supervisor_raw = local(pins['stage_supervisor']['path']).read_bytes()
    remote_raw = local(pins['stage_remote']['path']).read_bytes()
    need(sha(worker_raw) == request['worker_sha256'], 'actual uploaded worker source differs')
    argv = [key.SSH, '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias=' + host.ALIAS,
            'root@' + host.PEER, 'python3 -']
    launch = stage / 'launch-transport-private'
    launch_raw = executable_envelope(launch / 'executed-remote.py', remote_raw, 'launch', request,
                                      request_raw, supervisor_raw, worker_raw)
    intent = read_json(stage / 'launch-intent-private.json')
    need(intent['transaction_id'] == tx and intent['request_count'] == 1 and intent['argv'] == argv
         and intent['request_sha256'] == sha(request_raw) and intent['code_sha256'] == sha(launch_raw),
         'actual once dispatch intent differs')
    launch_terminal = terminal(launch / 'transport-terminal-private.json', launch / 'transport-child-private.json', argv, require_zero=False)
    executable_envelope(fetched / 'executed-remote.py', remote_raw, 'fetch', request,
                        request_raw, supervisor_raw, worker_raw)
    terminal(fetched / 'transport-terminal-private.json', fetched / 'transport-child-private.json', argv, require_zero=True)
    response = read_json(fetched / 'stdout-private.json')
    need(response == read_json(fetched / 'received-result-private.json')
         and response['transaction_id'] == tx and response['request_sha256'] == sha(request_raw), 'actual fetched response differs')
    files = {}
    for name, item in response['files'].items():
        need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'unsafe fetched evidence filename')
        raw = base64.b64decode(item['base64'], validate=True)
        need(len(raw) == item['bytes'] and sha(raw) == item['sha256']
             and raw == (fetched / 'raw' / name).read_bytes(), 'fetched raw bytes differ: ' + name)
        files[name] = raw
    root = REMOTE_ROOT + '/' + tx
    raws, facts = {}, {}
    for name, relative in EVIDENCE.items():
        if name == 'request':
            raw, path, origin = request_raw, stage / 'request-private.json', 'original-upload-retained-request'
        elif name == 'worker_source':
            raw, path, origin = worker_raw, stage / 'stage-worker.py', 'uploaded-source-bound-by-executed-remote'
        elif name == 'supervisor_source':
            raw, path, origin = supervisor_raw, local(pins['stage_supervisor']['path']), 'uploaded-source-bound-by-executed-remote'
        else:
            raw, path, origin = files[Path(relative).name], fetched / 'raw' / Path(relative).name, 'actual-strict-key-fetch-raw'
        raws[name] = raw
        facts[name] = dict(path=str(path), sha256=sha(raw), origin=origin, remote_path=root + '/' + relative)
    for target in worker.ORDER:
        raws['backup:' + Path(target).name] = files[Path(target).name + '.before']
    chain = verify_chain(raws, request, sha(request_raw), root)
    result = verify_stage(raws, request, worker)
    redacted_request = {k: v for k, v in request.items() if k != 'payload_base64'}
    need(json.loads(files['request-private.json']) == redacted_request, 'worker actual saved request differs')
    need(response['worker_result'] == result and response['worker_terminal_verified'] is True,
         'fetch observation does not match authenticated worker result/terminal')
    need(response['worker_terminal'] == json.loads(raws['worker_terminal']), 'fetched terminal observation differs')
    for role, pid, ticks in (('process', chain['worker_pid'], chain['worker_start_ticks']),
                             ('supervisor_process', chain['supervisor_pid'], chain['supervisor_start_ticks'])):
        current = response[role]
        need(current['state'] in ('absent', 'zombie', 'source_boot_ended'), 'original stage process not ended/known')
        if current['state'] == 'source_boot_ended':
            need(current['source_boot_id'] == request['identity']['boot_id']
                 and current['current_boot_id'] != current['source_boot_id'], 'source boot-ended observation differs')
        else:
            need(current['pid'] == pid, 'current ended-process PID differs')
            if current['state'] == 'zombie':
                need(current['start_ticks'] == ticks, 'current zombie start ticks differ')
    return dict(schema='samurai-authenticated-stage-review-v1', transaction_id=tx,
        source_boot_id=request['identity']['boot_id'], source_version=request['identity']['version'],
        identity=copy.deepcopy(request['identity']),
        adoption=dict(request['adoption'], actual_fresh_validation_sha256=result['adoption_fresh_validation_sha256']),
        request_sha256=sha(request_raw), result_sha256=sha(raws['result']), host_binding_sha256=sha(binding_raw),
        worker_sha256=sha(worker_raw), supervisor_sha256=sha(supervisor_raw),
        evidence=facts, stage_result=result, process_chain=chain,
        source_stage_directory=str(stage), source_fetch_directory=str(fetched),
        launch_transport_returncode=launch_terminal['returncode'], source_stage_authenticated=True,
        current_freshness_or_new_boot_verified=False, activation_or_postboot_authorized=False)


def guard_stage_fields(review):
    need(review.get('schema') == 'samurai-authenticated-stage-review-v1'
         and review.get('source_stage_authenticated') is True and set(review['evidence']) == set(EVIDENCE),
         'use the actual review_stage output')
    result = {key: review[key] for key in ('transaction_id', 'request_sha256', 'result_sha256',
              'host_binding_sha256', 'worker_sha256', 'supervisor_sha256')}
    result['evidence'] = {name: dict(path=review['evidence'][name]['remote_path'],
                                  sha256=review['evidence'][name]['sha256']) for name in EVIDENCE}
    return result


if __name__ == '__main__':
    source_check()
    print(json.dumps(dict(source_only=True, source_stage_reviewed=False, request_or_guard_created=False, device_accessed=False)))
