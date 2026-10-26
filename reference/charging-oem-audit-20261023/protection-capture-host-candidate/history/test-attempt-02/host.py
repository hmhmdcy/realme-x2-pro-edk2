"""Thin once-capture adapter. Default checks source only; never synthesizes adoption."""
from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, os, re, secrets, sys

sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('optimized interpreter unsupported')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OLD = HERE.parent / 'usb-irq-protection-stage-host-candidate-r2'
PRIVATE_TEXT = 'E:/edk2-samurai-out/charging-management-20261023/protection-capture'
DECODER_TEXT = '/home/cy122/charging-management-20261023/protection-evidence-parser-01/frame-decoder'
DECODER_SHA = '58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2'
REMOTE_ROOT = '/root/charging-management-20261023'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def need(ok, message):
    if not ok: raise ValueError(message)

def local(path):
    value = str(path).replace('\\', '/')
    if os.name != 'nt' and value.startswith('E:/'): value = '/mnt/e/' + value[3:]
    return Path(value)

PRIVATE = local(PRIVATE_TEXT)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, local(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def source_check():
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    values = {}
    for name, entry in pins.items():
        raw = local(entry['path']).read_bytes()
        need(sha(raw) == entry['sha256'] and len(raw) == entry['bytes'], 'frozen source changed: ' + name)
        values[name] = raw
    need(values['supervisor'] == values['original_supervisor'], 'unique original Popen supervisor must be byte-exact')
    need(pins['key_transport']['sha256'] == '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c', 'original strict key source')
    need(pins['parser']['sha256'] == json.loads(values['parser_delivery'])['files']['parse-evidence.py']['sha256'], 'actual parser source delivery')
    old = json.loads(values['original_delivery'])
    need(old['passed'] is True and old['frozen'] is True and all(pins[key]['sha256'] == old['files'][filename]['sha256']
         for key, filename in [('original_host','host.py'),('original_remote','remote.py'),('original_supervisor','supervisor.py')]), 'original R2 delivery differs')
    need(json.loads(values['parser_tests'])['decoder_sha256'] == DECODER_SHA, 'actual decoder receipt differs')
    return pins, values

def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

def save(path, value): create(path, (json.dumps(value, indent=2) + '\n').encode())

def make_request(transaction, reviewed, worker_sha):
    need(re.fullmatch(r'protection-capture-[a-z0-9-]{8,48}', transaction), 'unique capture transaction')
    d = reviewed['adoption']
    return {'schema': 'samurai-protection-capture-request-v1', 'transaction_id': transaction,
            'identity': {'boot_id': reviewed['boot_id'], 'version': d['version'], 'serial_sha256': d['serial_sha256'],
                         'compatible_sha256': d['compatible_sha256'], 'rootfs_sha256': d['rootfs']},
            'adoption': {'transaction_id': d['transaction_id'], 'guard_path': reviewed['guard_path'],
                         'guard_sha256': reviewed['guard_sha256'], 'postboot_raw_sha256': d['postboot_raw_sha256'],
                         'fresh_validation_sha256': reviewed['pointer']['fresh_validation_sha256']},
            'worker_sha256': worker_sha, 'lease_token': secrets.token_hex(24)}

def bind(transaction, context, camera, probe, capture):
    pins, values = source_check()
    reviewer = load(pins['adoption_review']['path'], 'capture_actual_irq_adoption')
    reviewed = reviewer.review_adoption(context, camera, probe, capture)
    request = make_request(transaction, reviewed, pins['worker']['sha256'])
    worker = load(HERE / 'stage-worker.py', 'capture_validate_request'); worker.validate_request(request)
    endpoint = reviewed['endpoint']
    need(endpoint['kind'] == 'usb-ipv6' and endpoint['peer'] == 'fe80::62:bcff:fe28:a101%29' and
         endpoint['host_key_alias'] == '169.254.42.1' and endpoint['original_key_verified'] is True and
         endpoint['observed_new_boot'] == request['identity']['boot_id'], 'actual original-key endpoint required')
    out = PRIVATE / transaction
    need(not out.exists(), 'capture transaction already exists; never replay')
    # ALL actual postboot/adoption/current-pointer/endpoint evidence was reviewed above.
    # No runtime directory, request or lease exists on a missing/future identity.
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True); out.mkdir(mode=0o700)
    save(out / 'request-private.json', request)
    save(out / 'binding-private.json', {'schema': 'samurai-protection-capture-binding-v1', 'transaction_id': transaction,
         'request_sha256': sha((out / 'request-private.json').read_bytes()), 'source_pins_sha256': sha((HERE / 'source-pins.json').read_bytes()),
         'endpoint': endpoint, 'review_inputs': reviewed['review_inputs'], 'evidence': reviewed['files'],
         'generated_from_actual_IRQ_adoption': True})
    create(out / 'stage-worker.py', values['worker'])
    return {'bound': True, 'private_directory': str(out), 'device_accessed': False}

def bound(transaction, *, launching=False):
    need(re.fullmatch(r'protection-capture-[a-z0-9-]{8,48}', transaction), 'capture transaction')
    pins, values = source_check(); out = PRIVATE / transaction
    binding = json.loads((out / 'binding-private.json').read_bytes())
    raw = (out / 'request-private.json').read_bytes(); request = json.loads(raw)
    need(binding['transaction_id'] == request['transaction_id'] == transaction and binding['generated_from_actual_IRQ_adoption'] is True and
         binding['request_sha256'] == sha(raw) and binding['source_pins_sha256'] == sha((HERE / 'source-pins.json').read_bytes()), 'retained binding changed')
    need(sha((out / 'stage-worker.py').read_bytes()) == request['worker_sha256'] == pins['worker']['sha256'], 'retained worker changed')
    if launching:
        for name, entry in binding['evidence'].items():
            need(sha(local(entry['path']).read_bytes()) == entry['sha256'], 'actual evidence changed: ' + name)
        review = load(pins['adoption_review']['path'], 'capture_recheck_irq_adoption')
        inputs = binding['review_inputs']
        actual = review.review_adoption(inputs['context'], inputs['camera'], inputs['probe_directory'], inputs['capture_directory'])
        need(actual['endpoint'] == binding['endpoint'] and actual['boot_id'] == request['identity']['boot_id'] and
             actual['guard_path'] == request['adoption']['guard_path'], 'current IRQ adoption changed before launch')
    return out, binding, request, raw, pins

def transport_module():
    """Reuse actual R2 transfer function, including exact original stdin EOF/finally-wait path."""
    module = load(OLD / 'host.py', 'capture_original_stage_r2')
    module.HERE = HERE; module.PRIVATE = PRIVATE
    module.source_check = source_check; module.bound = bound
    return module

def review_fetch(call, request, request_raw, *, decoder=DECODER_TEXT):
    """Only saved bytes and saved original-child receipts; no transport or kernel read."""
    pins, _ = source_check(); call = Path(call); rawdir = call / 'raw'
    response = json.loads((call / 'received-result-private.json').read_bytes())
    need(response['transaction_id'] == request['transaction_id'] and response['request_sha256'] == sha(request_raw), 'fetch request binding')
    raw = {}
    for name, entry in response['files'].items():
        need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', name), 'unsafe fetched name')
        value = rawdir.joinpath(name).read_bytes()
        need(sha(value) == entry['sha256'] and len(value) == entry['bytes'] and
             value == base64.b64decode(entry['base64'], validate=True), 'fetched raw/hash differs')
        raw[name] = value
    # Retain raw first; even unknown/failed original processes must never be relaunched.
    result = {'source_authenticated': False, 'batch_time_bound': False, 'compatibility_verified': False,
              'TCA_classification': 'UNVERIFIED', 'runtime_retry_permitted': False, 'errors': []}
    try:
        need(request['worker_sha256'] == pins['worker']['sha256'], 'actual frozen capture worker required')
        tx = request['transaction_id']; root = REMOTE_ROOT + '/' + tx
        argv = ['python3', '-B', root + '/stage-worker.py', '--execute-stage']
        sup_argv = ['python3', '-B', root + '/stage-supervisor.py', '--execute-supervisor']
        launch, term, sup, supterm, proc, worker = [json.loads(raw[name]) for name in
            ('worker-launch-receipt-private.json', 'worker-terminal-private.json', 'supervisor-process-private.json',
             'supervisor-terminal-private.json', 'process-private.json', 'result.json')]
        for receipt, expected_argv in [(launch, argv), (proc, argv), (sup, sup_argv), (supterm, sup_argv)]:
            need(receipt['transaction_id'] == tx and receipt['boot_id'] == request['identity']['boot_id'] and receipt['argv'] == expected_argv and
                 type(receipt['pid']) is int and receipt['pid'] > 0 and type(receipt['start_ticks']) is int and receipt['start_ticks'] > 0, 'original process identity incomplete')
        for receipt in [launch, term, sup, supterm]: need(receipt['request_sha256'] == sha(request_raw), 'original request/child binding')
        need(all(term[k] == launch[k] for k in ('transaction_id', 'boot_id', 'request_sha256', 'pid', 'argv', 'supervisor_pid')) and
             all(proc[k] == launch[k] for k in ('pid', 'start_ticks', 'argv')) and
             launch['supervisor_pid'] == sup['pid'] == supterm['pid'] and sup['start_ticks'] == supterm['start_ticks'] and
             supterm['worker_pid'] == launch['pid'], 'worker/supervisor chain differs')
        original_sup = json.loads(raw['launch-receipt-private.json'])
        need(response['supervisor_receipt'] == original_sup and
             all(original_sup[k] == sup[k] for k in ('transaction_id','boot_id','request_sha256','pid','start_ticks','argv')), 'original supervisor launch differs')
        need(type(term['returncode']) is int and type(supterm['returncode']) is int and type(supterm['worker_returncode']) is int and
             term['terminal'] is True and term['returncode'] == 0 and supterm['terminal'] is True and
             supterm['returncode'] == supterm['worker_returncode'] == 0, 'original child unknown/failed; raw retained only')
        need(response['worker_terminal_verified'] is True and response['worker_terminal'] == term and response['worker_result'] == worker and
             response['process']['state'] in ('absent', 'zombie', 'source_boot_ended') and
             response['supervisor_process']['state'] in ('absent', 'zombie', 'source_boot_ended'), 'original processes not terminal/finished')
        need(raw['request-private.json'] == request_raw and proc['worker_sha256'] == request['worker_sha256'], 'worker request/source differs')
        need(worker['transaction_id'] == tx and worker['request_sha256'] == sha(request_raw) and worker['terminal'] is True and
             worker['identity_before'] == worker['identity_after'] and worker['identity_match'] is True and
             not worker['errors'], 'worker identity changed or incomplete')
        i = worker['identity_before']
        need(all(i[k] == v for k, v in request['identity'].items()) and i['guard_sha256'] == request['adoption']['guard_sha256'] and
             i['manifest_sha256'] == '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417' and
             i['protection_ko_sha256'] == '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044' and
             i['loaded_note_sha256'] == 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'raw source cohort identity differs')
        need(worker['raw_after_sha256'] == sha(raw['cache-after-private.txt']) and worker['raw_before_sha256'] == sha(raw['cache-before-private.txt']), 'worker raw cache hashes differ')
        parser = load(pins['parser']['path'], 'capture_actual_saved_parser')
        # This is the original parse_saved, including its actual C decoder/36-byte/echo/length/checksum checks.
        before = parser.parse_saved(raw['cache-before-private.txt'], local(decoder), DECODER_SHA)
        need(before['header']['attempted'] == 0, 'original cache already attempted')
        parsed = parser.parse_saved(raw['cache-after-private.txt'], local(decoder), DECODER_SHA)
        result['parsed'] = parsed
        h = parsed['header']
        need(worker['capture_write_attempted'] is True and h['attempted'] == h['terminal'] == 1, 'no batch attributable to this store')
        write_error = worker['write_error']
        if write_error is None:
            need(worker['write_return'] == 8 and h['error'] == 0, 'successful store/cache result differs')
        else:
            code = write_error.get('errno')
            need(type(code) is int and 0 < code <= 4095 and code != 114 and worker['write_return'] is None and
                 h['error'] == -code, 'failed/unknown/EALREADY store cannot claim another batch')
        need(worker['started_ns'] <= worker['write_started_ns'] <= h['started_ns'] <= h['ended_ns'] <= worker['write_ended_ns'] <=
             worker['cache_after_read_ns'] <= worker['ended_ns'], 'batch outside original store BOOTTIME interval')
        result['source_authenticated'] = True; result['batch_time_bound'] = True
        result['sequence_complete'] = parsed['sequence_complete']
    except (OSError, KeyError, TypeError, ValueError) as error:
        result['source_authenticated'] = False; result['batch_time_bound'] = False
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--action', choices=['check-local','bind','launch','status','fetch'], default='check-local')
    for name in ['transaction','context','camera','probe-directory','capture-directory']: p.add_argument('--' + name)
    p.add_argument('--window-confirmed', action='store_true'); args = p.parse_args()
    if args.action == 'check-local':
        source_check(); result = {'source_checks_passed': True, 'runtime_request_generated': False, 'device_accessed': False}
    elif args.action == 'bind': result = bind(args.transaction,args.context,args.camera,args.probe_directory,args.capture_directory)
    else:
        result = transport_module().transfer(args.action,args.transaction,args.window_confirmed)
        if args.action == 'fetch':
            _, _, request, raw, _ = bound(args.transaction)
            result['saved_capture_review'] = review_fetch(result['private_directory'],request,raw)
            save(Path(result['private_directory']) / 'capture-analysis-private.json', result['saved_capture_review'])
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
