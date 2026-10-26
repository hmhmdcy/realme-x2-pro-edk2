"""Review one original current-stage fetch. No transport or device operation."""
from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
SOURCE_MANIFEST='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
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

def source_check():
    pins=json.loads((HERE/'stage-source-pins.json').read_bytes());values={}
    for name,row in pins.items():
        data=local(row['path']).read_bytes()
        need(sha(data)==row['sha256'],'fixed source changed: '+name);values[name]=data
    for delivery_name,source_name,filename in [('stage_host_delivery','stage_host','host.py'),
        ('stage_worker_delivery','stage_worker','stage-worker.py')]:
        delivery=json.loads(values[delivery_name])
        need(delivery['passed'] and delivery['frozen'] and delivery['files'][filename]['sha256']==pins[source_name]['sha256'],'frozen stage source mismatch')
    return pins,values

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

def review_stage(stage_directory,fetch_directory):
 pins,values=source_check();host=load(local(pins['stage_host']['path']),'current_stage_host_originals')
 stage=local(stage_directory);call=local(fetch_directory)
 need(call.parent==stage and re.fullmatch(r'fetch-[0-9a-f]{16}-private',call.name),'one explicit original fetch directory')
 out,binding,request,request_raw,host_pins=host.bound(stage.name,launching=True)
 need(local(out)==stage and binding['reviewed']['manifest_sha256']==SOURCE_MANIFEST,'actual current stage binding')
 aliases={'update_host':pins['stage_host'],'update_supervisor':pins['stage_supervisor']}
 response,raw=fetch_raw(call,request_raw,aliases,{'update_remote':values['stage_remote']})
 process_chain(response,raw,request,request_raw)
 need(raw['request-private.json']==request_raw and response['worker_result']==json.loads(raw['result.json']),'actual executed stage result/request')
 common=load(HERE/'common.py','current_stage_device_receipt_rules')
 evidence={};records={}
 binary={'old_usb','old_manifest'}
 for key,path in common.stage_paths(stage.name).items():
  if key=='worker_source':data=(stage/'stage-worker.py').read_bytes()
  elif key=='supervisor_source':data=values['stage_supervisor']
  elif key=='request':data=request_raw
  else:data=raw[Path(path).name]
  evidence[key]={'path':path,'sha256':sha(data)}
  if key not in ['worker_source','supervisor_source']:records[key]=data if key in binary else json.loads(data)
 fields={'transaction_id':stage.name,'request_sha256':sha(request_raw),'result_sha256':sha(raw['result.json']),
  'host_binding_sha256':sha((stage/'binding-private.json').read_bytes()),'worker_sha256':pins['stage_worker']['sha256'],
  'supervisor_sha256':pins['stage_supervisor']['sha256'],'evidence':evidence}
 identity=request['identity']
 meta=dict(stage=fields,boot_id=identity['boot_id'],soc_serial_sha256=identity['serial_sha256'],
  compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'],adoption=request['adoption'])
 observed={k:dict(response[k+'_process'] if k=='supervisor' else response['process']) for k in ['worker','supervisor']}
 # Host has the original transfer and two true wait receipts. The original
 # device launch-claim is not exported by R2. It is reread independently by
 # read_stage() on the phone; this reviewer does not fabricate that raw file.
 common.validate_stage_receipts(meta,records,observed)
 for k,v in [('boot_id',identity['boot_id']),('guard_path',request['adoption']['guard_path']),('guard_sha256',request['adoption']['guard_sha256'])]:
  need(binding['reviewed'][k]==v,'current runtime source identity differs')
 return {'schema':'samurai-irq-native-usb-pm-stage-review-v1','stage':fields,'request':request,
  'source_review_inputs':binding['source_review_inputs'],'source_runtime':binding['reviewed'],
  'stage_directory':str(stage),'stage_fetch_directory':str(call),
  'device_launch_claim_not_exported':True,'actual_device_launch_claim_still_required':True}

def guard_stage_fields(review):
 need(review['schema']=='samurai-irq-native-usb-pm-stage-review-v1','current stage review required')
 return copy.deepcopy(review['stage'])

if __name__=='__main__':
    source_check();print(json.dumps({'source_only':True,'device_accessed':False,'stage_or_runtime_identity_created':False}))
