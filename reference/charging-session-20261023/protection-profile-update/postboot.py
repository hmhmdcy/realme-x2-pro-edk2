"""Twelve original checks, explicit schema2 cache and independent adoption."""
from pathlib import Path
import argparse,importlib.util,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('profile_host_adapter',HERE/'host.py');u=adapter.u
old=load('profile_original_postboot',HERE.parent/'usb-pm-notify-update/postboot.py');old.update=u
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-protocol-20261024-01-adopted/boot-id-private.txt'
def collector():
 source=old.DEVICE.read_bytes().split(b"\nif __name__=='__main__':",1)[0]
 source=u.replace(source.decode(),"first.get('schema')=='1' and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')]",
  "first.get('schema')=='2' and first.get('diagnostic_profile')=='1' and first.get('profile_identity_verified') in ('0','1') and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')]").encode()
 c=json.loads((HERE/'cohort-r2-result.json').read_bytes());manifest=json.loads((u.BASE/'protection-observed-2719-cohort-private-02/manifest-new.json').read_bytes())
 tail=('NEW_COHORT='+repr(c)+'\nNEW_MANIFEST='+repr(manifest)+'\n').encode()+br'''
PROFILES['forward_504']['manifest_sha256']=NEW_COHORT['target_manifest_sha256']
PROFILES['forward_504']['manifest']=NEW_MANIFEST
PROFILES['forward_504']['notes']['samurai_usb_input']='f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae'
PROFILES['forward_504']['notes']['samurai_gauge_protection']=NEW_COHORT['target_protection_note_sha256']
def validate_request(request):
 row=configure_profile(request);g=request['guard'];stage=request['stage']
 assert request['schema']=='samurai-protection-profile-postboot-v1' and request['profile']=='forward_504'
 assert request['carrier_writes']==0 and request['original_key_transport_verified'] is True
 assert g['boot_id']=='eb9e051a-da47-4d98-8c9c-cfc7f4e8664a' and g['new_boot_id']==request['new_boot_id']!=g['boot_id']
 assert g['source_kernel_version']==g['target_kernel_version']==row['version']
 assert stage['terminal'] and stage['staged'] and stage['disk_state']=='all_new_fsynced' and stage['stop_verified']
 assert stage['primary_error'] is stage['recovery_error'] is None
 assert stage['old_manifest_sha256']==NEW_COHORT['source_manifest_sha256'] and stage['new_manifest_sha256']==row['manifest_sha256']
 assert sha((json.dumps(stage,indent=2)+'\n').encode())==request['stage_result_sha256']
 return row
'''
 return source+b'\n'+tail
def prepare(new_boot):
 r=u.request();c=json.loads((HERE/'cohort-r2-result.json').read_bytes());rows=list(u.OUT.glob('raw-*/device-stage/result.json'));assert len(rows)==1
 stage_raw=rows[0].read_bytes();camera=(u.BASE.parent/'kernel481/formal-expected-private.json').read_bytes();assert u.sha(camera)==u.transport_host.CAMERA
 return dict(schema='samurai-protection-profile-postboot-v1',profile='forward_504',carrier_writes=0,original_key_transport_verified=True,new_boot_id=new_boot,
  stage=json.loads(stage_raw),stage_result_sha256=u.sha(stage_raw),camera=json.loads(camera),
  guard=dict(transaction_id=u.TX,boot_id=r['identity']['boot_id'],new_boot_id=new_boot,kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',source_kernel_version=u.VERSION,target_kernel_version=u.VERSION,
  rootfs_release_sha256=r['identity']['rootfs_sha256'],soc_serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],
  candidate_boot_sha256=c['retained_boot_sha256'],candidate_logdump_sha256=c['retained_logdump_sha256'],image_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'))
old.collector=collector;old.prepare=prepare
def local():
 source=collector();scope={};exec(compile(source,'<protocol-collector>','exec'),scope)
 assert len(scope['PROFILES'])==2 and scope['PROFILES']['forward_504']['manifest_sha256']=='8c5b7be90c4d22ba3db418c7225894e155b2cf5257eda0a681da1136081cef3c'
 u.create(u.OUT/'postboot-collector-template.py',source);return dict(prepared=True,original_twelve_checks_retained=True,cache_schema=2)
def run():
 assert collector()==(u.OUT/'postboot-collector-template.py').read_bytes();return old.run()
def adopt():
 request=json.loads((u.OUT/'postboot-request.json').read_bytes());checked=json.loads((u.OUT/'postboot-reviewed.json').read_bytes())
 assert checked['passed'] and len(checked['checks'])==12 and not checked['errors']
 source=(u.OUT/'postboot-collector.py').read_bytes();assert source==collector()
 code=('REQUEST='+repr(request)+'\nGUARD='+repr(GUARD)+'\n').encode()+source+br'''
raw={};collect(REQUEST,raw);result=audit(raw,REQUEST)
assert result['passed'] and len(result['checks'])==12 and not result['errors']
assert Path('/sys/module/samurai_gauge_protection/parameters/observed_2719_diagnostic').read_text().strip()=='Y'
guard=Path(GUARD);assert not guard.parent.exists();os.umask(0o077);guard.parent.mkdir(mode=0o700)
proof=(json.dumps(dict(request=REQUEST,raw=raw,result=result),indent=2)+'\n').encode()
for path,value in [(guard,(REQUEST['new_boot_id']+'\n').encode()),(guard.parent/'fresh-validation-private.json',proof)]:
 with path.open('xb') as f:f.write(value);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(guard_path=str(guard),boot_id=REQUEST['new_boot_id'],guard_sha256=sha(guard.read_bytes()),fresh_validation_sha256=sha(proof),twelve_passed=True,profile_parameter='Y')))
'''
 reply=u.call('adopt',code,False);assert reply['twelve_passed'] and reply['boot_id']==request['new_boot_id']
 pointer=u.BASE/'boot-adoption-private.json';before=(u.OUT/'previous-pointer.json').read_bytes();assert pointer.read_bytes()==before
 current=json.loads(before);current.update(guard_path=GUARD,boot_id=request['new_boot_id'],charging_manifest_sha256=request['stage']['new_manifest_sha256'],
  fresh_validation_sha256=reply['fresh_validation_sha256'],postboot_raw_sha256=u.sha((u.OUT/('postboot-r2' if (u.OUT/'postboot-r2').exists() else 'postboot')/'stdout-private.json').read_bytes()),
  stage_transaction_id=u.TX,profile='forward_504_protection_observed2719',PM_suspend_resume_verified=False,PM_prior_USB_fix_verified=True,
  protection_diagnostic_profile='observed-2719-0056-3',protection_normal_Health_verified=True,protection_diagnostic_capture_completed=False)
 u.save(u.OUT/'adoption-pointer.json',current);temp=u.BASE/'profile-protection-adoption-next-private.json';u.create(temp,(json.dumps(current,indent=2)+'\n').encode());assert pointer.read_bytes()==before;temp.replace(pointer)
 fd=os.open(pointer.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return dict(adopted=True,diagnostic_query_started=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['local','run','adopt']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
