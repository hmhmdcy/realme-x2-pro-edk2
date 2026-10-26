"""Read only original adoption + one completed same-boot charger-update fetch."""
from pathlib import Path
from types import SimpleNamespace
import ast, base64, copy, hashlib, importlib.util, json, re, sys
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OLD = '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
NEW = '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
OLD_NOTE = 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'
NEW_NOTE = 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value: raise ValueError(message)


def local(value):
    text = str(value).replace('\\', '/')
    if sys.platform != 'win32' and re.match(r'^[A-Za-z]:/', text):
        text = '/mnt/' + text[0].lower() + text[2:]
    return Path(text).resolve()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, local(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def check_sources():
    pins = json.loads((HERE / 'source-pins.json').read_bytes()); values = {}
    for name, row in pins.items():
        raw = local(REF / row['path']).read_bytes()
        need(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'fixed source changed: ' + name)
        values[name] = raw
    for key, source, filename in (('base_delivery', 'base_launcher', 'launcher.py'),
                                  ('update_delivery', 'update_host', 'host.py'),
                                  ('worker_delivery', 'update_worker', 'stage-worker.py')):
        delivery = json.loads(values[key])
        need(delivery['passed'] is True and delivery['files'][filename]['sha256'] == pins[source]['sha256'],
             'source/delivery mismatch: ' + source)
    host = load(REF / pins['update_host']['path'], 'review_actual_charger_host_sources')
    host_pins, _ = host.source_check()
    need(host_pins['worker']['sha256'] == pins['update_worker']['sha256'], 'host/worker source mismatch')
    return pins, values


def base_module():
    pins, _ = check_sources()
    return load(REF / pins['base_review']['path'], 'review_original_irq_adoption')


def fetch_raw(call, request_raw, pins, values):
    """Authenticate the saved original fetch; this function never sends anything."""
    request = json.loads(request_raw); tx = request['transaction_id']
    code = (call / 'executed-remote.py').read_bytes()
    first, tail = code.split(b'\n', 1)
    prefix = b'STAGE_TRANSPORT='
    need(first.startswith(prefix) and tail == values['update_remote'], 'executed original fetch source differs')
    envelope = ast.literal_eval(first[len(prefix):].decode())
    need(set(envelope) == {'action', 'request', 'request_sha256', 'request_base64', 'worker_base64',
                          'window_confirmed', 'supervisor_base64', 'supervisor_sha256'} and
         envelope['action'] == 'fetch' and envelope['request'] == request and
         envelope['request_sha256'] == sha(request_raw) and
         base64.b64decode(envelope['request_base64'], validate=True) == request_raw and
         envelope['worker_base64'] is envelope['supervisor_base64'] is None and
         type(envelope['window_confirmed']) is bool and envelope['supervisor_sha256'] == pins['update_supervisor']['sha256'],
         'actual fetch envelope/input differs')
    need(code == (prefix.decode() + repr(envelope) + '\n').encode() + values['update_remote'], 'noncanonical fetch source')
    child = json.loads((call / 'transport-child-private.json').read_bytes())
    terminal = json.loads((call / 'transport-terminal-private.json').read_bytes())
    host = load(REF / pins['update_host']['path'], 'review_saved_update_fetch')
    key = host.load(host.source_check()[0]['key_transport']['path'], 'review_original_update_key')
    argv = [key.SSH, '-C', '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias=169.254.42.1',
            'root@fe80::62:bcff:fe28:a101%29', 'python3 -']
    need(type(child.get('pid')) is int and child['pid'] > 0 and child.get('argv') == argv and child.get('terminal') is False,
         'original fetch Popen missing')
    need(terminal.get('pid') == child['pid'] and terminal.get('terminal') is True and
         type(terminal.get('returncode')) is int and terminal['returncode'] == 0 and
         terminal.get('primary_error') is None and terminal.get('cleanup_errors') == [], 'original fetch wait not clean')
    response_raw = (call / 'stdout-private.json').read_bytes()
    need(response_raw == (call / 'received-result-private.json').read_bytes() or
         json.loads(response_raw) == json.loads((call / 'received-result-private.json').read_bytes()), 'saved fetch response differs')
    response = json.loads(response_raw)
    need(response['transaction_id'] == tx and response['request_sha256'] == sha(request_raw), 'fetch request differs')
    raw = {}
    for name, row in response['files'].items():
        need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'unsafe fetched filename')
        data = (call / 'raw' / name).read_bytes()
        need(data == base64.b64decode(row['base64'], validate=True) and sha(data) == row['sha256'] and
             len(data) == row['bytes'], 'fetched raw/hash differs: ' + name)
        raw[name] = data
    return response, raw


def process_chain(response, raw, request, request_raw):
    tx, boot = request['transaction_id'], request['identity']['boot_id']
    root = '/root/charging-management-20261023/' + tx
    argv = ['python3', '-B', root + '/stage-worker.py', '--execute-stage']
    sup_argv = ['python3', '-B', root + '/stage-supervisor.py', '--execute-supervisor']
    launch, term, own, supterm, proc = [json.loads(raw[name]) for name in
        ('worker-launch-receipt-private.json', 'worker-terminal-private.json', 'supervisor-process-private.json',
         'supervisor-terminal-private.json', 'process-private.json')]
    for item, expected in ((launch, argv), (proc, argv), (own, sup_argv), (supterm, sup_argv)):
        need(item['transaction_id'] == tx and item['boot_id'] == boot and item['argv'] == expected and
             type(item['pid']) is int and item['pid'] > 0 and type(item['start_ticks']) is int and item['start_ticks'] > 0,
             'original worker/supervisor identity missing')
    for item in (launch, term, own, supterm):
        need(item['request_sha256'] == sha(request_raw), 'worker/supervisor request differs')
    need(all(term[k] == launch[k] for k in ('transaction_id', 'boot_id', 'request_sha256', 'pid', 'argv', 'supervisor_pid')) and
         all(proc[k] == launch[k] for k in ('pid', 'start_ticks', 'argv')) and
         launch['supervisor_pid'] == own['pid'] == supterm['pid'] and own['start_ticks'] == supterm['start_ticks'] and
         supterm['worker_pid'] == launch['pid'], 'original owned-Popen chain differs')
    sup_launch = json.loads(raw['launch-receipt-private.json'])
    need(response['supervisor_receipt'] == sup_launch and all(sup_launch[k] == own[k] for k in
         ('transaction_id', 'boot_id', 'request_sha256', 'pid', 'start_ticks', 'argv')), 'original supervisor launch differs')
    need(type(term['returncode']) is int and term['returncode'] == 0 and term['terminal'] is True and
         type(supterm['returncode']) is int and type(supterm['worker_returncode']) is int and
         supterm['terminal'] is True and supterm['returncode'] == supterm['worker_returncode'] == 0 and
         response['worker_terminal_verified'] is True and response['worker_terminal'] == term,
         'original worker/supervisor unknown or failed')
    need(response['process']['state'] in ('absent', 'zombie') and response['supervisor_process']['state'] in ('absent', 'zombie'),
         'same-boot terminal processes required')
    for key in ('identity_observation', 'identity_after'):
        observation = response[key]
        need(observation.get('boot_id') == boot and observation.get('source_boot_same') is True and
             observation.get('guard_matches') is True, 'same source boot/guard not retained')
    need(not response.get('identity_changed_during_observation'), 'identity changed during fetch')


def review_update(update_directory, base_review):
    """update_directory is ONE original host fetch-* directory, never a guessed latest."""
    pins, values = check_sources(); call = local(update_directory)
    need(re.fullmatch(r'fetch-[0-9a-f]{16}-private', call.name), 'explicit original fetch directory required')
    tx = call.parent.name
    host = load(REF / pins['update_host']['path'], 'review_bound_charger_transaction')
    out, binding, request, request_raw, host_pins = host.bound(tx)
    need(local(out) == call.parent and binding['reviewed'] == base_review and
         base_review['pointer']['charging_manifest_sha256'] == OLD, 'original actual IRQ adoption/binding differs')
    d = base_review['adoption']
    expected_identity = {'boot_id': base_review['boot_id'], 'version': d['version'], 'serial_sha256': d['serial_sha256'],
                         'compatible_sha256': d['compatible_sha256'], 'rootfs_sha256': d['rootfs']}
    need(request['identity'] == expected_identity and request['adoption'] == {
         'transaction_id': d['transaction_id'], 'guard_path': base_review['guard_path'], 'guard_sha256': base_review['guard_sha256']},
         'update is not from the original same-boot guard/identity')
    worker = load(REF / pins['update_worker']['path'], 'review_actual_completed_update_worker')
    payload, new_manifest = worker.unpack_request(request)
    need(request['worker_sha256'] == pins['update_worker']['sha256'] == host_pins['worker']['sha256'], 'worker source differs')
    response, raw = fetch_raw(call, request_raw, pins, values)
    process_chain(response, raw, request, request_raw)
    need(raw['request-private.json'] == request_raw, 'executed worker request differs')
    result = json.loads(raw['result.json'])
    need(response['worker_result'] == result and result.get('schema') == 'samurai-charger-reattach-update-result-v1' and
         result.get('transaction_id') == tx and result.get('request_sha256') == sha(request_raw), 'actual result/request differs')
    need(all(result.get(k) is True for k in ('passed', 'terminal', 'installed_new', 'native_usb_and_protection_kept_loaded', 'camera_services_unchanged')) and
         all(result.get(k) is False for k in ('runtime_validation_pending', 'mutating_process_unknown')) and
         all(result.get(k) is None for k in ('primary_error', 'stop_error', 'recovery_error', 'recovery_state')) and
         result.get('close_error') is None and result.get('pending_child_pid') is None and
         result.get('before_state') == 'managed' and result.get('accepted_state') in ('managed', 'full_holding') and
         result.get('old_manifest_sha256') == OLD and result.get('new_manifest_sha256') == NEW,
         'only a clean completed managed update may create an overlay; preflight is insufficient')
    before_file = json.loads(raw['before-private.json']); before = before_file['observation']
    old_paused, new_paused, after = [json.loads(raw[name]) for name in
        ('old-inhibited-private.json', 'new-inhibited-private.json', 'after-private.json')]
    need(before_file['modes'] == worker.MODES, 'old two-file modes differ')
    old_manifest_raw = raw['manifest.json.before']; old_manifest = json.loads(old_manifest_raw)
    need(sha(old_manifest_raw) == OLD and sha(raw['samurai-mp2650.ko.before']) == worker.OLD_CHARGER,
         'actual old disk backups differ')
    worker.manifest_delta(old_manifest, new_manifest)
    need(result['final_files'] == {path: {'sha256': worker.HASHES[path], 'mode': oct(mode)} for path, mode in worker.MODES.items()},
         'final disk tuple/modes differ')
    expected_old = worker.NOTES
    expected_new = dict(expected_old, **{'samurai-mp2650': NEW_NOTE})
    for index, snapshot in enumerate((before, old_paused, new_paused, after)):
        need(snapshot['identity'] == dict(expected_identity, guard_sha256=base_review['guard_sha256']) and
             snapshot['state']['boot_id'] == base_review['boot_id'] and snapshot['state']['release'] == d['release'] and
             snapshot['notes'] == (expected_old if index < 2 else expected_new), 'snapshot identity/live tuple differs')
        # Replay only the saved sample's internal bounds at its read_end. This is
        # not current-device freshness and does not grant a future update/launch.
        worker.time = SimpleNamespace(CLOCK_BOOTTIME=7, clock_gettime=lambda _, s=snapshot: s['read_end'])
        worker.safe_sample(snapshot); worker.source_limits(snapshot); worker.unchanged(before, snapshot)
    worker.time = SimpleNamespace(CLOCK_BOOTTIME=7, clock_gettime=lambda _: before['read_end'])
    need(worker.healthy(before, False) == 'managed', 'Full preflight cannot be promoted')
    worker.time = SimpleNamespace(CLOCK_BOOTTIME=7, clock_gettime=lambda _: after['read_end'])
    need(worker.healthy(after, True) == result['accepted_state'], 'final complete protection/charging evidence differs')
    need(before['limits'] == after['limits'] and before['source'] == after['source'] and
         result['sample'] == after['sample'] and result['limits'] == after['limits'] and
         result['old_stopped_sample'] == old_paused['sample'] and result['new_inhibited_sample'] == new_paused['sample'],
         'saved complete before/after sample, source or budget differs')
    for snapshot in (old_paused, new_paused):
        need(snapshot['registers']['08'] & 0x18 == 8 and snapshot['sample']['desired_enable'] == 0,
             'synchronous inhibited boundary missing')
    rows = (before, old_paused, new_paused, after)
    need(all(a['read_end'] <= b['read_start'] for a, b in zip(rows, rows[1:])), 'observation order differs')
    mac = before['mac_evidence']; cached = base64.b64decode(mac['raw_base64'], validate=True)
    need(0 < len(cached) < 16384 and cached.endswith(b'\n') and sha(cached) == mac['sha256'] == worker.MAC_CACHE_SHA and
         type(mac['attribute_dev']) is int and mac['attribute_dev'] >= 0 and
         all(type(mac[k]) is int and mac[k] > 0 for k in ('attribute_inode', 'instance_inode')), 'cached bound-instance bytes/identity invalid')
    first = dict(x.split('=', 1) for x in cached.decode().splitlines()[0].split())
    need(first.get('attempted') == first.get('terminal') == '1', 'original consumed cache not preserved')
    events = json.loads(raw['events-private.json'])
    need(all(isinstance(event, list) and event and (event[0] != 'fresh-manager' or
             event == ['fresh-manager', worker.SERVICE_SHA]) for event in events), 'unexpected fresh-manager source')
    need([event for event in events if event[0] != 'fresh-manager'] == [
         ['manager-command', worker.SERVICE_SHA, 'stop'], ['process', 'rmmod', 'samurai_mp2650'],
         ['process', 'insmod', worker.KO, 'runtime_board=1', 'control=1'], ['manager-command', worker.SERVICE_SHA, 'start']],
         'only the charger stop/unload/load/start sequence is permitted')
    last = json.loads(raw['last-process-private.json'])
    need(last['args'] == ['insmod', worker.KO, 'runtime_board=1', 'control=1'] and type(last['returncode']) is int and
         last['returncode'] == 0 and 'pending-process-private.json' not in raw, 'mutating child did not finish')
    runtime = copy.deepcopy(base_review['runtime_expected'])
    need(runtime['notes']['samurai_mp2650'] == OLD_NOTE, 'base live charger note differs')
    runtime['notes']['samurai_mp2650'] = NEW_NOTE
    files = copy.deepcopy(base_review['files'])
    for name in ('binding-private.json', 'request-private.json', 'stage-worker.py'):
        path = call.parent / name; files['update_' + name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    for name in ('executed-remote.py', 'transport-child-private.json', 'transport-terminal-private.json',
                 'stdout-private.json', 'stderr-private.txt', 'received-result-private.json'):
        path = call / name; files['update_fetch/' + name] = {'path': str(path), 'sha256': sha(path.read_bytes())}
    for name, data in raw.items():
        files['update_raw/' + name] = {'path': str(call / 'raw' / name), 'sha256': sha(data)}
    return {'schema': 'samurai-icon-runtime-overlay-review-v1', 'boot_id': base_review['boot_id'],
            'guard_path': base_review['guard_path'], 'guard_sha256': base_review['guard_sha256'],
            'manifest_sha256': NEW, 'base_adoption_manifest_sha256': OLD, 'update_transaction_id': tx,
            'runtime_expected': runtime, 'pointer': base_review['pointer'], 'endpoint': base_review['endpoint'],
            'review_inputs': {'base_adoption': dict(zip(('context_path', 'camera_path', 'probe_directory', 'capture_directory'),
                                                     (base_review['review_inputs'][k] for k in ('context', 'camera', 'probe_directory', 'capture_directory')))),
                              'update_directory': str(call)}, 'files': files,
            'same_boot_runtime_overlay': True, 'boot_adoption_pointer_rewritten': False,
            'update_result_sha256': sha(raw['result.json']), 'consumed_cache_sha256': mac['sha256']}


if __name__ == '__main__':
    check_sources()
    print(json.dumps({'source_only': True, 'runtime_overlay_created': False, 'device_accessed': False}))
