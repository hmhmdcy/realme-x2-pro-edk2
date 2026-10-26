"""Current IRQ adoption -> one charger-only update. Default is local checks."""
from pathlib import Path
import argparse, base64, hashlib, importlib.util, inspect, json, os, re, secrets, sys
sys.dont_write_bytecode=True
if sys.flags.optimize: raise RuntimeError('Non-optimized Python required')
HERE=Path(__file__).resolve().parent; REF=HERE.parents[1]
BASE_TEXT='E:/edk2-samurai-out/charging-management-20261023'
OLD='5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
NEW='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
PAYLOAD='0870e32b1c6f5a927a1480a4cd523c2804dc7f44fe1796e8adb2b0100ffc71ea'
KEY='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'
sha=lambda b:hashlib.sha256(b).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)
def local(path):
    value=str(path).replace('\\','/')
    if os.name!='nt' and re.match(r'^[A-Za-z]:/',value):value='/mnt/'+value[0].lower()+value[2:]
    return Path(value).resolve()
BASE=local(BASE_TEXT);PRIVATE=BASE/'charger-reattach-update'
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
def source_check():
    pins=json.loads((HERE/'source-pins.json').read_bytes());values={}
    for name,row in pins.items():
        raw=local(row['path']).read_bytes()
        need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],'Changed source: '+name);values[name]=raw
    need(pins['key_transport']['sha256']==KEY,'Original strict key source required')
    need(values['supervisor']==values['original_supervisor'],'Original owned-Popen supervisor required')
    capture=json.loads(values['capture_delivery'])
    need(capture['passed'] and capture['files']['remote.py']['sha256']==pins['base_remote']['sha256'],'Base remote is not the frozen capture transport')
    base=values['base_remote'].decode()
    for a,b in [('protection-capture-[a-z0-9-]{8,48}','charger-reattach-update-[a-z0-9-]{8,48}'),('samurai-protection-capture-request-v1','samurai-charger-reattach-update-v1'),("out = root / 'device-stage'","out = root / 'device-update'")]:
        need(base.count(a)==1,'Unexpected remote profile');base=base.replace(a,b)
    need(base.encode()==values['remote'],'Only the fixed three remote substitutions are permitted')
    need(sha(values['payload'])==PAYLOAD and len(values['payload'])==52491,'Exact forward package required')
    package=json.loads(values['payload_result']);need(package['passed'] and package['old_manifest_sha256']==OLD and package['new_manifest_sha256']==NEW,'Payload profile differs')
    for key,source in [('worker_delivery','worker'),('payload_delivery','payload_result')]:
        delivery=json.loads(values[key]);need(delivery['passed'],'Failed delivery: '+key)
        path=Path(pins[source]['path']).name
        need(delivery['files'][path]['sha256']==pins[source]['sha256'],'Delivery/source mismatch: '+source)
    old=json.loads(values['original_delivery']);need(old['passed'],'Original transport delivery failed')
    for key,filename in [('original_host','host.py'),('original_remote','remote.py'),('original_supervisor','supervisor.py')]:
        need(old['files'][filename]['sha256']==pins[key]['sha256'],'Original transfer source mismatch')
    return pins,values
def transaction_name(tx):need(re.fullmatch(r'charger-reattach-update-[a-z0-9-]{8,48}',tx),'Unique charger update transaction required')
def make_request(tx,review,worker,payload):
    transaction_name(tx);d=review['adoption']
    return {'schema':'samurai-charger-reattach-update-v1','transaction_id':tx,
      'identity':{'boot_id':review['boot_id'],'version':d['version'],'serial_sha256':d['serial_sha256'],'compatible_sha256':d['compatible_sha256'],'rootfs_sha256':d['rootfs']},
      'adoption':{'transaction_id':d['transaction_id'],'guard_path':review['guard_path'],'guard_sha256':review['guard_sha256']},
      'worker_sha256':worker,'lease_token':secrets.token_hex(24),'old_manifest_sha256':OLD,'new_manifest_sha256':NEW,
      'payload_sha256':PAYLOAD,'payload_base64':base64.b64encode(payload).decode()}
def bind(tx,context,camera,probe,capture):
    pins,values=source_check()
    reviewer=load(pins['adoption_review']['path'],'current_irq_adoption_for_charger_update')
    reviewed=reviewer.review_adoption(context,camera,probe,capture)
    request=make_request(tx,reviewed,pins['worker']['sha256'],values['payload'])
    worker=load(pins['worker']['path'],'offline_charger_request_contract')
    worker.unpack_request(request)  # Pure archive/schema checks; no Device is created.
    # Source-level request validation is added by the worker; runtime identity is
    # never fabricated, inferred from uname alone, or taken from a test fixture.
    need(reviewed['pointer']['charging_manifest_sha256']==OLD,'Original current IRQ adoption required')
    out=PRIVATE/tx;need(not out.exists(),'Transaction exists; use status/fetch only')
    PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True);out.mkdir(mode=0o700)
    save(out/'request-private.json',request)
    save(out/'binding-private.json',{'schema':'samurai-charger-reattach-binding-v1','transaction_id':tx,
      'request_sha256':sha((out/'request-private.json').read_bytes()),'source_pins_sha256':sha((HERE/'source-pins.json').read_bytes()),
      'endpoint':reviewed['endpoint'],'review_inputs':reviewed['review_inputs'],'reviewed':reviewed,
      'generated_from_actual_IRQ_adoption':True,'device_accessed':False})
    create(out/'stage-worker.py',values['worker'])
    return {'bound':True,'private_directory':str(out),'device_accessed':False}
def bound(tx,*,launching=False):
    transaction_name(tx);pins,values=source_check();out=PRIVATE/tx
    b=json.loads((out/'binding-private.json').read_bytes());raw=(out/'request-private.json').read_bytes();r=json.loads(raw)
    need(b['transaction_id']==r['transaction_id']==tx and b['request_sha256']==sha(raw) and b['source_pins_sha256']==sha((HERE/'source-pins.json').read_bytes()),'Retained request/source differs')
    need(b['generated_from_actual_IRQ_adoption'] is True and sha((out/'stage-worker.py').read_bytes())==r['worker_sha256']==pins['worker']['sha256'],'Retained original worker differs')
    if launching:
        # Review immutable original evidence/current pointer once before dispatch;
        # it is outside the timed SSH operation and status/fetch does not redo it.
        for name,row in b['reviewed']['files'].items():need(sha(local(row['path']).read_bytes())==row['sha256'],'Original IRQ evidence changed: '+name)
        review=load(pins['adoption_review']['path'],'charger_launch_actual_irq')
        a=review.review_adoption(**{'context_path':b['review_inputs']['context'],'camera_path':b['review_inputs']['camera'],'probe_directory':b['review_inputs']['probe_directory'],'capture_directory':b['review_inputs']['capture_directory']})
        need(a==b['reviewed'],'Actual IRQ adoption/current pointer changed')
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
    code=("import io,sys\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(raw)+"))\nsys.argv=['charger-preflight','--preflight']\n__file__='charger-preflight-stdin.py'\n").encode()+(out/'stage-worker.py').read_bytes()
    call=out/('preflight-'+secrets.token_hex(8)+'-private');call.mkdir(mode=0o700)
    # Original full saved-transport provenance, fixed compression and strict key.
    profile=load(pins['preflight_profile']['path'],'charger_preflight_original_saved_transfer')
    result=profile.send_readonly(call,code)
    need(result.get('schema')=='samurai-charger-reattach-preflight-v1' and result.get('request_sha256')==sha(raw)
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',nargs='?',default='check-local',choices=['check-local','bind','preflight','launch','status','fetch'])
    for name in ['transaction','context','camera','probe','capture']:p.add_argument('--'+name)
    p.add_argument('--window-confirmed',action='store_true');a=p.parse_args()
    if a.action=='check-local':source_check();result={'source_checked':True,'device_accessed':False}
    elif a.action=='bind':result=bind(a.transaction,a.context,a.camera,a.probe,a.capture)
    elif a.action=='preflight':result=preflight(a.transaction)
    elif a.action=='launch':result=launch(a.transaction,a.window_confirmed)
    else:result=transport_module().transfer(a.action,a.transaction,a.window_confirmed)
    # Never print raw private identities, tokens or fetched evidence to the UI.
    if a.action=='preflight':
        r=result['result'];print(json.dumps({'action':'preflight','private_directory':result['private_directory'],'eligible':r.get('eligible'),'reason':r.get('reason'),'passed':r.get('passed')},indent=2))
    else:print(json.dumps({k:v for k,v in result.items() if k not in ['worker_result','worker_terminal','process','supervisor_process']},indent=2))
if __name__=='__main__':main()
