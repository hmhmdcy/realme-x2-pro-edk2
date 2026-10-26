"""Actual IRQ adoption + completed 97c update -> cold USB disk stage only."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,inspect,json,os,re,secrets,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Non-optimized Python required')
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE_TEXT='E:/edk2-samurai-out/charging-management-20261023'
OLD='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
NEW='34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'
PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc'
COHORT='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'
KEY='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'
sha=lambda b:hashlib.sha256(b).hexdigest()

def need(value,message):
    if not value:raise ValueError(message)

def local(path):
    value=str(path).replace('\\','/')
    if os.name!='nt' and re.match(r'^[A-Za-z]:/',value):value='/mnt/'+value[0].lower()+value[2:]
    return Path(value).resolve()

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,local(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def create(path,raw):
    with Path(path).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    if os.name!='nt':
        fd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

def save(path,value):create(path,(json.dumps(value,indent=2)+'\n').encode())

BASE=local(BASE_TEXT);PRIVATE=BASE/'irq-native-usb-pm-stage'

def source_check():
    pins=json.loads((HERE/'source-pins.json').read_bytes());values={}
    for name,row in pins.items():
        raw=local(row['path']).read_bytes()
        need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],'Changed source: '+name);values[name]=raw
    need(pins['key_transport']['sha256']==KEY,'Original strict key source required')
    need(values['supervisor']==values['original_supervisor'],'Original owned-Popen supervisor required')
    capture=json.loads(values['capture_delivery'])
    need(capture['passed'] and capture['files']['remote.py']['sha256']==pins['base_remote']['sha256'],'Frozen capture transport required')
    base=values['base_remote'].decode()
    for a,b in [('protection-capture-[a-z0-9-]{8,48}','irq-native-usb-pm-stage-[a-z0-9-]{8,48}'),
                ('samurai-protection-capture-request-v1','samurai-irq-native-usb-pm-stage-request-v1')]:
        need(base.count(a)==1,'Unexpected remote profile');base=base.replace(a,b)
    need(base.encode()==values['remote'],'Only the fixed two remote substitutions are permitted')
    need(sha(values['payload'])==PAYLOAD and len(values['payload'])==27163,'Exact forward package required')
    cohort=json.loads(values['cohort_delivery']);receipt=json.loads(values['payload_result'])
    need(sha(values['cohort_delivery'])==COHORT and cohort['passed'] and receipt['passed'] and
         cohort['files']['payload-result.json']['sha256']==pins['payload_result']['sha256'] and
         receipt['files']['irq-native-pm-payload.tar.gz']=={'sha256':PAYLOAD,'bytes':27163},'Actual cohort/package differs')
    worker=json.loads(values['worker_delivery']);contract=json.loads(values['worker_contract'])
    need(worker['passed'] and worker['frozen'] and worker['files']['stage-worker.py']['sha256']==pins['worker']['sha256'] and
         worker['files']['contract.json']['sha256']==pins['worker_contract']['sha256'] and
         contract['worker_sha256']==pins['worker']['sha256'] and contract['cohort_delivery_sha256']==COHORT and
         contract['old_manifest_sha256']==OLD and contract['new_manifest_sha256']==NEW and
         contract['payload_sha256']==PAYLOAD,'Reviewed stage worker/contract differs')
    original=json.loads(values['original_delivery']);need(original['passed'],'Original transport delivery failed')
    for key,filename in [('original_host','host.py'),('original_remote','remote.py'),('original_supervisor','supervisor.py')]:
        need(original['files'][filename]['sha256']==pins[key]['sha256'],'Original transfer source mismatch')
    runtime=json.loads(values['runtime_delivery'])
    need(runtime['passed'] and runtime['files']['update-review.py']['sha256']==pins['runtime_review']['sha256'],'Actual runtime reviewer differs')
    return pins,values

def transaction_name(tx):
    need(isinstance(tx,str) and re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',tx),'Unique cold-stage transaction required')

def review_runtime(runtime_pins):
    pins,_=source_check();path=local(runtime_pins);saved=json.loads(path.read_bytes())
    need(saved.get('schema')=='samurai-icon-irq-runtime-update-v1','Actual completed update overlay required')
    reviewer=load(pins['runtime_review']['path'],'native_pm_actual_runtime_review')
    inputs=saved['review_inputs']
    base=reviewer.base_module().review_adoption(**inputs['base_adoption'])
    checked=reviewer.review_update(inputs['update_directory'],base)
    need(saved['reviewed']==checked and checked['review_inputs']==inputs and checked['manifest_sha256']==OLD and
         checked['boot_id']==base['boot_id'] and checked['guard_path']==base['guard_path'] and
         checked['guard_sha256']==base['guard_sha256'],'Actual adoption/completed update differs')
    return checked,base

def make_request(tx,base,worker,payload):
    transaction_name(tx);d=base['adoption']
    return {'schema':'samurai-irq-native-usb-pm-stage-request-v1','transaction_id':tx,
      'cohort_delivery_sha256':COHORT,'payload_sha256':PAYLOAD,'payload_base64':base64.b64encode(payload).decode(),
      'worker_sha256':worker,'lease_token':secrets.token_hex(24),
      'identity':{'boot_id':base['boot_id'],'version':d['version'],'serial_sha256':d['serial_sha256'],
                  'compatible_sha256':d['compatible_sha256'],'rootfs_sha256':d['rootfs']},
      'adoption':{'transaction_id':d['transaction_id'],'guard_path':base['guard_path'],'guard_sha256':base['guard_sha256']}}

def bind(tx,runtime_pins):
    transaction_name(tx);pins,values=source_check();checked,base=review_runtime(runtime_pins)
    request=make_request(tx,base,pins['worker']['sha256'],values['payload'])
    worker=load(pins['worker']['path'],'native_pm_pure_stage_contract');worker.unpack(request)
    # Both original IRQ adoption and the actual owned/waited charger update are
    # reviewed before any directory, request or random lease token is published.
    out=PRIVATE/tx;need(not out.exists(),'Transaction exists; use status/fetch only')
    PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True);out.mkdir(mode=0o700)
    save(out/'request-private.json',request)
    save(out/'binding-private.json',{'schema':'samurai-irq-native-usb-pm-stage-binding-v1','transaction_id':tx,
      'request_sha256':sha((out/'request-private.json').read_bytes()),'source_pins_sha256':sha((HERE/'source-pins.json').read_bytes()),
      'runtime_pins':{'path':str(local(runtime_pins)),'sha256':sha(local(runtime_pins).read_bytes())},
      'source_review_inputs':checked['review_inputs'],'reviewed':checked,'source_adoption':base['adoption'],
      'endpoint':checked['endpoint'],'generated_from_actual_runtime_update':True,'device_accessed':False})
    create(out/'stage-worker.py',values['worker'])
    return {'bound':True,'private_directory':str(out),'device_accessed':False}

def bound(tx,*,launching=False):
    transaction_name(tx);pins,values=source_check();out=PRIVATE/tx
    b=json.loads((out/'binding-private.json').read_bytes());raw=(out/'request-private.json').read_bytes();r=json.loads(raw)
    need(b['schema']=='samurai-irq-native-usb-pm-stage-binding-v1' and b['transaction_id']==r['transaction_id']==tx and
         b['request_sha256']==sha(raw) and b['source_pins_sha256']==sha((HERE/'source-pins.json').read_bytes()),'Retained request/source differs')
    need(b['generated_from_actual_runtime_update'] is True and
         sha((out/'stage-worker.py').read_bytes())==r['worker_sha256']==pins['worker']['sha256'],'Retained original worker differs')
    if launching:
        for name,row in b['reviewed']['files'].items():
            need(sha(local(row['path']).read_bytes())==row['sha256'],'Original runtime evidence changed: '+name)
        path=local(b['runtime_pins']['path']);need(sha(path.read_bytes())==b['runtime_pins']['sha256'],'Actual runtime overlay changed')
        checked,base=review_runtime(path)
        need(checked==b['reviewed'] and checked['review_inputs']==b['source_review_inputs'] and
             base['adoption']==b['source_adoption'],'Actual adoption/update originals changed')
    # Recovery observes the retained original transaction even after a new boot
    # or pointer. Never rebind a failed/unknown launch in status/fetch.
    return out,b,r,raw,pins

def transport_module():
    pins,_=source_check();m=load(pins['original_host']['path'],'original_owned_stage_transfer')
    m.HERE=HERE;m.PRIVATE=PRIVATE;m.source_check=source_check;m.bound=bound
    # Only the fixed -C envelope changes; original Popen/stdin EOF/finally-wait,
    # launch claim and status/fetch bodies remain the already proven code.
    body=inspect.getsource(m.transfer)
    old="argv = [host.SSH, '-6', '-T', *host.OPTIONS"
    need(body.count(old)==1,'Unexpected original transport argv')
    exec(compile(body.replace(old,"argv = [host.SSH, '-C', '-6', '-T', *host.OPTIONS"),'<charger-compressed-original-transfer>','exec'),m.__dict__)
    return m

def preflight(tx):
    out,b,request,raw,pins=bound(tx)
    # Fresh source/guard/health reads only: no remote files, lease, launch or
    # charging-control writes. Every retry is a new observational output folder.
    code=("import io,sys\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(raw)+"))\nsys.argv=['native-pm-stage-preflight','--preflight']\n__file__='native-pm-stage-preflight-stdin.py'\n").encode()+(out/'stage-worker.py').read_bytes()
    call=out/('preflight-'+secrets.token_hex(8)+'-private');call.mkdir(mode=0o700)
    # Original full saved-transport provenance, fixed compression and strict key.
    profile=load(pins['preflight_profile']['path'],'native_pm_preflight_original_saved_transfer')
    result=profile.send_readonly(call,code)
    need(result.get('schema')=='samurai-irq-native-usb-pm-preflight-v1' and result.get('request_sha256')==sha(raw)
         and result.get('identity_match') is True,'Preflight request/source identity differs')
    save(call/'preflight-result-private.json',result)
    return {'action':'preflight','private_directory':str(call),'result':result}

def launch(tx,window_confirmed=False):
    need(window_confirmed is True,'Current root exclusive phone window required')
    current=preflight(tx)
    if current['result'].get('eligible') is not True:
        return {'launched':False,'preflight_directory':current['private_directory'],'reason':current['result'].get('reason'),'charging_mutations':0}
    return transport_module().transfer('launch',tx,True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',default='check-local',choices=['check-local','bind','preflight','launch','status','fetch'])
    p.add_argument('--transaction');p.add_argument('--runtime-pins');p.add_argument('--window-confirmed',action='store_true');a=p.parse_args()
    if a.action=='check-local':source_check();result={'source_checked':True,'device_accessed':False}
    elif a.action=='bind':result=bind(a.transaction,a.runtime_pins)
    elif a.action=='preflight':result=preflight(a.transaction)
    elif a.action=='launch':result=launch(a.transaction,a.window_confirmed)
    else:result=transport_module().transfer(a.action,a.transaction,a.window_confirmed)
    if a.action=='preflight':
        r=result['result'];print(json.dumps({'action':'preflight','private_directory':result['private_directory'],
          'eligible':r.get('eligible'),'reason':r.get('reason'),'passed':r.get('passed')},indent=2))
    else:print(json.dumps({k:v for k,v in result.items() if k not in ['worker_result','worker_terminal','process','supervisor_process']},indent=2))
if __name__=='__main__':main()
