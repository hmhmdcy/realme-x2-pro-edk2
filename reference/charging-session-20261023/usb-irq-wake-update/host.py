"""Two-file native USB wake update on the actually adopted504/f6 cohort."""
from pathlib import Path
import argparse,ast,base64,importlib.util,inspect,json,os,secrets,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
u=load('irq_wake_original_transport',HERE.parent/'usb-pm-notify-update/host.py')
TEMPLATE=u.OUT;PREVIOUS=u.BASE/'protection-profile-update-live-20261024-03'
u.OUT=u.BASE/'usb-irq-wake-update-live-20261024-01';u.TX='irq-native-usb-pm-stage-wake-20261024-01';u.REMOTE='/root/charging-management-20261023/'+u.TX;u.LEAF=HERE
helpers=load('irq_wake_stage_text_helpers',HERE.parent/'protection-profile-update/host.py')
def bind():
 assert not u.OUT.exists(),'intent exists; observe original'
 c=json.loads((HERE/'cohort-result.json').read_bytes());assert c['passed']
 pointer=(u.BASE/'boot-adoption-private.json').read_bytes();assert pointer==(PREVIOUS/'adoption-pointer-after-pm.json').read_bytes();current=json.loads(pointer)
 assert current['PM_current_protection_profile_verified'] and current['charging_manifest_sha256']==c['source_manifest_sha256'] and current['boot_id']=='bf430d0d-571c-4b94-b7e3-e40d6f05368a'
 os.umask(0o077);u.OUT.mkdir(mode=0o700);u.create(u.OUT/'previous-pointer.json',pointer)
 cached=u.call('cache-read',('EXPECTED='+repr(current['boot_id'])+'\nEXPECTED_CACHE='+repr(current['protection_capture_cache_sha256'])+'\n').encode()+br'''
from pathlib import Path
import hashlib,json
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
raw=Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence').read_bytes()
header=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split());digest=hashlib.sha256(raw).hexdigest()
assert header['schema']=='2' and header['diagnostic_profile']=='1' and header['attempted']==header['terminal']=='1' and digest==EXPECTED_CACHE
print(json.dumps(dict(sha256=digest,header=header)))
''')
 before=(TEMPLATE/'stage-worker.py').read_bytes();assert u.sha(before)==json.loads((TEMPLATE/'request-private.json').read_bytes())['worker_sha256'];source=before.decode()
 values=dict(OLD=c['source_manifest_sha256'],NEW=c['target_manifest_sha256'],USB_OLD=c['source_usb_sha256'],USB_NEW=c['target_usb_sha256'],SERVICE_SHA=c['retained_service_sha256'],
  NOTES={'samurai-usb-input':c['source_usb_note_sha256'],'samurai-gauge-protection':c['retained_protection_note_sha256'],'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'},
  MAC_CACHE_SHA=cached['sha256'],COHORT=u.sha((HERE/'cohort-result.json').read_bytes()),PAYLOAD=c['forward']['sha256'])
 for key,value in values.items():source=helpers.assigned(source,key,value)
 source=u.replace(source,'len(raw)==27182','len(raw)=='+str(c['forward']['bytes']))
 delta='''def manifest_delta(old,new):
    expected=copy.deepcopy(old)
    need(old['release']==RELEASE and old['modules']['samurai-usb-input']=={'target':USB,'sha256':USB_OLD},'current exact USB PM fix')
    expected['adapter_revision']='usb-irq-wake-01'
    expected['modules']['samurai-usb-input']['sha256']=USB_NEW;expected['installed_files'][USB]=USB_NEW
    need(new==expected and old['installed_files'][SERVICE]==SERVICE_SHA,'only USB and cohort revision change')
    need(old['modules']['samurai-gauge-protection']['sha256']=='f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e' and old['modules']['samurai-mp2650']['sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd','retain current protection and charger')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'unchanged charging policy')'''
 source=helpers.function(source,'manifest_delta',delta);ast.parse(source)
 def bodies(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 left,right=bodies(before.decode()),bodies(source);assert set(left)==set(right) and all(right[n]==v for n,v in left.items() if n not in ['unpack','manifest_delta'])
 u.create(u.OUT/'stage-worker.py',source.encode());worker=u.load(u.OUT/'stage-worker.py','irq_wake_stage_local')
 identity=json.loads((PREVIOUS/'capture-request.json').read_bytes())['identity'];assert identity['boot_id']==current['boot_id']
 tx=Path(current['guard_path']).parent.name.removesuffix('-adopted')
 payload=(u.BASE/'usb-irq-wake-cohort-private-01/forward-two-files.tar.gz').read_bytes();assert u.sha(payload)==c['forward']['sha256']
 req=dict(schema='samurai-irq-native-usb-pm-stage-request-v1',transaction_id=u.TX,cohort_delivery_sha256=worker.COHORT,payload_sha256=c['forward']['sha256'],payload_base64=base64.b64encode(payload).decode(),
  worker_sha256=u.sha(source.encode()),lease_token=secrets.token_hex(24),identity=identity,
  adoption=dict(transaction_id=tx,guard_path=current['guard_path'],guard_sha256=u.sha((current['boot_id']+'\n').encode())))
 worker.unpack(req);worker.manifest_delta(json.loads((u.BASE/'usb-irq-wake-cohort-private-01/manifest-old.json').read_bytes()),json.loads((u.BASE/'usb-irq-wake-cohort-private-01/manifest-new.json').read_bytes()))
 u.save(u.OUT/'request-private.json',req);u.save(u.OUT/'derivation.json',dict(passed=True,base_worker_sha256=u.sha(before),worker_sha256=u.sha(source.encode()),
  all_stage_safety_atomic_manager_and_Device_functions_exact=True,changed_functions=['unpack payload length','manifest_delta exact current cohort'],
  existing_service_not_updated=True,old_query_cache_preserved=True,staged=False))
 return dict(bound=True,source_boot=current['boot_id'],device_query_issued=False)
def launch():
 body=inspect.getsource(u.launch);body=u.replace(body,"BASE/'usb-input-pm-notify-cohort-private-02/rollback-two-files.tar.gz'","BASE/'usb-irq-wake-cohort-private-01/rollback-two-files.tar.gz'")
 ns=dict(u.__dict__);exec(compile(body,'<original-two-file-supervised-launch>','exec'),ns);return ns['launch']()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bind','preflight','launch','fetch']);a=p.parse_args();f=bind if a.action=='bind' else launch if a.action=='launch' else getattr(u,a.action);print(json.dumps(f(),indent=2))
