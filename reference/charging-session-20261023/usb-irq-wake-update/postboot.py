"""Original twelve checks, current USB note and the existing PSY wake policy."""
from pathlib import Path
import argparse,ast,importlib.util,inspect,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('irq_wake_postboot_adapter',HERE/'host.py');u=adapter.u
prior=load('irq_wake_prior_postboot_owner',HERE.parent/'protection-profile-update/postboot.py')
old=prior.old;old.update=u
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-wake-20261024-01-adopted/boot-id-private.txt'
def collector():
 source=(adapter.PREVIOUS/'postboot-collector.py').read_text();c=json.loads((HERE/'cohort-result.json').read_bytes());manifest=json.loads((u.BASE/'usb-irq-wake-cohort-private-01/manifest-new.json').read_bytes())
 # Alias unchanged protection fields for the shared twelve-check profile.
 row={**c,'target_protection_note_sha256':c['retained_protection_note_sha256'],'target_service_sha256':c['retained_service_sha256']}
 source=adapter.helpers.assigned(source,'NEW_COHORT',row);source=adapter.helpers.assigned(source,'NEW_MANIFEST',manifest)
 source=u.replace(source,"'samurai-protection-profile-postboot-v1'","'samurai-usb-irq-wake-postboot-v1'")
 source=u.replace(source,"g['boot_id']=='eb9e051a-da47-4d98-8c9c-cfc7f4e8664a'","g['boot_id']=='bf430d0d-571c-4b94-b7e3-e40d6f05368a'")
 source=u.replace(source,"PROFILES['forward_504']['notes']['samurai_usb_input']='f3c8d708a7122549a8733b5c171a2c2895e63eccaa76e31e5dfdbd9ca2ff46ae'","PROFILES['forward_504']['notes']['samurai_usb_input']=NEW_COHORT['target_usb_note_sha256']")
 source=u.replace(source,"raw['protection_cache_after']=reader.cache_evidence()\n  raw['identity_after']=identity()", "raw['protection_cache_after']=reader.cache_evidence()\n  raw['usb_PSY_wakeup_policy']=read('/sys/class/power_supply/samurai-usb-input/power/wakeup')\n  raw['identity_after']=identity()")
 source+='''
_irq_wake_topology_base=check_pm_topology
def check_pm_topology(raw,request):
 result=_irq_wake_topology_base(raw,request)
 assert raw['usb_PSY_wakeup_policy']=='enabled','current RTC/USB wake test requires existing PSY wake policy'
 result['PSY_wakeup_policy_enabled']=True
 result['IRQ_wake_API_or_physical_delivery_not_proven_by_postboot']=True
 return result
'''
 ast.parse(source);return source.encode()
def prepare(new_boot):
 r=u.request();c=json.loads((HERE/'cohort-result.json').read_bytes());rows=list(u.OUT.glob('raw-*/device-stage/result.json'));assert len(rows)==1
 stage=rows[0].read_bytes();camera=(u.BASE.parent/'kernel481/formal-expected-private.json').read_bytes();assert u.sha(camera)==u.transport_host.CAMERA
 return dict(schema='samurai-usb-irq-wake-postboot-v1',profile='forward_504',carrier_writes=0,original_key_transport_verified=True,new_boot_id=new_boot,
  stage=json.loads(stage),stage_result_sha256=u.sha(stage),camera=json.loads(camera),
  guard=dict(transaction_id=u.TX,boot_id=r['identity']['boot_id'],new_boot_id=new_boot,kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',source_kernel_version=u.VERSION,target_kernel_version=u.VERSION,
  rootfs_release_sha256=r['identity']['rootfs_sha256'],soc_serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],
  candidate_boot_sha256=c['retained_boot_sha256'],candidate_logdump_sha256=c['retained_logdump_sha256'],image_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'))
old.collector=collector;old.prepare=prepare
def local():
 source=collector();scope={};exec(compile(source,'<wake-collector>','exec'),scope)
 assert scope['PROFILES']['forward_504']['notes']['samurai_usb_input']=='028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6'
 u.create(u.OUT/'postboot-collector-template.py',source);return dict(prepared=True,original_twelve_checks=True,wakeup_policy_checked=True)
def run():
 assert collector()==(u.OUT/'postboot-collector-template.py').read_bytes();return old.run()
prior.u=u;prior.collector=collector;prior.GUARD=GUARD
body=inspect.getsource(prior.adopt)
body=u.replace(body,"profile='forward_504_protection_observed2719'","profile='forward_504_usb_irq_wake'")
needle="u.save(u.OUT/'adoption-pointer.json',current)"
extra="""previous=json.loads(before)
 historical={key:previous.get(key) for key in ['boot_id','charging_manifest_sha256','protection_diagnostic_capture_completed','protection_capture_source_authenticated','protection_capture_cache_sha256','protection_capture_result_sha256','PM_suspend_resume_verified','PM_single_RTC_residency_seconds','PM_result_sha256']}
 current['previous_boot_protocol_and_PM']=historical
 current['protection_capture_cache_sha256']=json.loads((u.OUT/('postboot-r2' if (u.OUT/'postboot-r2').exists() else 'postboot')/'reply.json').read_bytes())['raw']['protection_cache_after']['sha256']
 current['protection_capture_source_authenticated']=False
 current.pop('protection_capture_result_sha256',None)
 current['PM_single_RTC_residency_seconds']=None
 current.pop('PM_result_sha256',None)
 current['PM_current_protection_profile_verified']=False
 current['USB_irq_wake_candidate_loaded']=True
 current['USB_physical_wakeup_verified']=False
 """+needle
body=u.replace(body,needle,extra)
exec(compile(body,'<current-wake-guard-adoption>','exec'),prior.__dict__)
def adopt():return prior.adopt()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['local','run','adopt']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
