"""Re-use twelve original device checks for a module-only reboot on Image504."""
from pathlib import Path
import ast,base64,copy,importlib.util,json,sys,types
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('notify_update',Path(__file__).resolve().parent/'host.py')
update=importlib.util.module_from_spec(spec);spec.loader.exec_module(update)
DEVICE=update.HERE.parent/'irq-native-usb-pm-postboot-device-candidate/device.py'
def collector():
 source=DEVICE.read_bytes().split(b"\nif __name__=='__main__':",1)[0]
 c=json.loads((update.LEAF/'cohort-result.json').read_bytes());manifest=json.loads((update.BASE/'usb-input-pm-notify-cohort-private-02/manifest-new.json').read_bytes())
 tail=('NEW_COHORT='+repr(c)+'\nNEW_MANIFEST='+repr(manifest)+'\n').encode()+br'''
PROFILES['forward_504']['manifest_sha256']=NEW_COHORT['target_manifest_sha256']
PROFILES['forward_504']['manifest']=NEW_MANIFEST
PROFILES['forward_504']['notes']['samurai_usb_input']=NEW_COHORT['target_module_note_sha256']
def validate_request(request):
 row=configure_profile(request);g=request['guard'];stage=request['stage']
 assert request['schema']=='samurai-usb-pm-notify-postboot-v1' and request['profile']=='forward_504'
 assert request['carrier_writes']==0 and request['original_key_transport_verified'] is True
 assert g['boot_id']=='a13eab37-b5b3-4365-b1bd-8a7345290ae0' and g['new_boot_id']==request['new_boot_id']!=g['boot_id']
 assert g['source_kernel_version']==g['target_kernel_version']==row['version']
 assert stage['terminal'] and stage['staged'] and stage['disk_state']=='all_new_fsynced' and stage['stop_verified']
 assert stage['primary_error'] is stage['recovery_error'] is None
 assert stage['old_manifest_sha256']==NEW_COHORT['source_manifest_sha256'] and stage['new_manifest_sha256']==row['manifest_sha256']
 assert sha((json.dumps(stage,indent=2)+'\n').encode())==request['stage_result_sha256']
 return row
'''
 return source+b'\n'+tail
def prepare(new_boot):
 r=update.request();c=json.loads((update.LEAF/'cohort-result.json').read_bytes());rows=list(update.OUT.glob('raw-*/device-stage/result.json'));update.need(len(rows)==1,'one actual stage')
 stage_raw=rows[0].read_bytes();stage=json.loads(stage_raw)
 camera_raw=(update.BASE.parent/'kernel481/formal-expected-private.json').read_bytes()
 update.need(update.sha(camera_raw)==update.transport_host.CAMERA,'481 formal baseline')
 return dict(schema='samurai-usb-pm-notify-postboot-v1',profile='forward_504',carrier_writes=0,original_key_transport_verified=True,new_boot_id=new_boot,
  stage=stage,stage_result_sha256=update.sha(stage_raw),camera=json.loads(camera_raw),
  guard=dict(transaction_id=update.TX,boot_id=r['identity']['boot_id'],new_boot_id=new_boot,kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',source_kernel_version=update.VERSION,target_kernel_version=update.VERSION,
  rootfs_release_sha256=r['identity']['rootfs_sha256'],soc_serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],
  candidate_boot_sha256=c['retained_boot_sha256'],candidate_logdump_sha256=c['retained_logdump_sha256'],image_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'))
def run():
 probe_code=br'''
from pathlib import Path
import json,os
print(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version)))
'''
 prior=update.OUT/'new-boot-probe/reply.json'
 probe=json.loads(prior.read_bytes()) if prior.exists() else update.call('new-boot-probe',probe_code)
 update.need(probe['boot_id']!=update.request()['identity']['boot_id'] and probe['version']==update.VERSION,'fresh actual504')
 request=prepare(probe['boot_id']);source=collector();scope={};exec(compile(source,'<same-collector>','exec'),scope);scope['validate_request'](request)
 if (update.OUT/'postboot-collector.py').exists():
  update.need((update.OUT/'postboot-collector.py').read_bytes()==source and json.loads((update.OUT/'postboot-request.json').read_bytes())==request,'retained read-only inputs changed')
 else:update.create(update.OUT/'postboot-collector.py',source);update.save(update.OUT/'postboot-request.json',request)
 code=('REQUEST='+repr(request)+'\n').encode()+source+br'''
raw={}
try:
 collect(REQUEST,raw);result=audit(raw,REQUEST)
except Exception as e:result=dict(passed=False,collection_error=repr(e))
print(json.dumps(dict(request=REQUEST,raw=raw,result=result)))
'''
 reply=update.call('postboot-r2' if (update.OUT/'postboot').exists() else 'postboot',code)
 update.need(reply['request']==request,'request changed');actual=scope['audit'](reply['raw'],request)
 update.need(actual==reply['result'],'independent original audit differs')
 update.save(update.OUT/'postboot-reviewed.json',actual)
 return actual
if __name__=='__main__':print(json.dumps(run(),indent=2))
