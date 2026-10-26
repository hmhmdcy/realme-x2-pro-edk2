"""Reuse twelve checks; require the new charger note, not the current97c proof."""
from pathlib import Path
import argparse,ast,copy,importlib.util,inspect,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=load('timer_postboot_adapter',HERE/'host.py');u=adapter.u
prior=load('timer_original_postboot_owner',HERE.parent/'protection-profile-update/postboot.py')
old=prior.old;old.update=u
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-timer-20261024-01-adopted/boot-id-private.txt'
def collector():
    source=(adapter.PREVIOUS/'postboot-collector.py').read_text()
    c=json.loads((HERE.parent/'charge-timer-hold-r2-candidate/cohort-result.json').read_bytes())
    manifest=json.loads((u.BASE/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes())
    row={**c,'target_usb_note_sha256':'028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6',
         'target_protection_note_sha256':'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd'}
    source=adapter.adapter.helpers.assigned(source,'NEW_COHORT',row)
    source=adapter.adapter.helpers.assigned(source,'NEW_MANIFEST',manifest)
    source=u.replace(source,"'samurai-usb-irq-wake-postboot-v1'","'samurai-charger-timer-postboot-v1'")
    old_boot=json.loads((adapter.PREVIOUS/'request-private.json').read_bytes())['identity']['boot_id']
    source=u.replace(source,"g['boot_id']=="+repr(old_boot),"g['boot_id']=="+repr(u.request()['identity']['boot_id']))
    marker="PROFILES['forward_504']['notes']['samurai_gauge_protection']=NEW_COHORT['target_protection_note_sha256']"
    source=u.replace(source,marker,marker+"\nPROFILES['forward_504']['notes']['samurai_mp2650']=NEW_COHORT['target_charger_note_sha256']")
    ast.parse(source);return source.encode()
def prepare(new_boot):
    r=u.request();rows=list(u.OUT.glob('raw-*/device-stage/result.json'));assert len(rows)==1
    stage=rows[0].read_bytes();camera=(u.BASE.parent/'kernel481/formal-expected-private.json').read_bytes()
    assert u.sha(camera)==u.transport_host.CAMERA
    existing=json.loads((adapter.PREVIOUS/'postboot-request.json').read_bytes())['guard']
    return dict(schema='samurai-charger-timer-postboot-v1',profile='forward_504',carrier_writes=0,
        original_key_transport_verified=True,new_boot_id=new_boot,stage=json.loads(stage),stage_result_sha256=u.sha(stage),camera=json.loads(camera),
        guard=dict(transaction_id=u.TX,boot_id=r['identity']['boot_id'],new_boot_id=new_boot,kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',
            source_kernel_version=u.VERSION,target_kernel_version=u.VERSION,rootfs_release_sha256=r['identity']['rootfs_sha256'],
            soc_serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],
            candidate_boot_sha256=existing['candidate_boot_sha256'],candidate_logdump_sha256=existing['candidate_logdump_sha256'],image_sha256=existing['image_sha256']))
old.collector=collector;old.prepare=prepare
def local():
    source=collector();scope={};exec(compile(source,'<timer-postboot-template>','exec'),scope)
    row=scope['PROFILES']['forward_504']
    assert row['notes']['samurai_mp2650']=='1df00d554b85aa45d4bbbc0d1a6a7a4cbd56ba4da45ae48d54bb8ae1f3434d08'
    assert row['manifest']['modules']['samurai-mp2650']['sha256']=='bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f'
    scope['configure_profile']({'profile':'forward_504'})
    actual=json.loads((adapter.PREVIOUS/'postboot/reply.json').read_bytes())['raw']
    try:scope['check_install'](actual)
    except AssertionError:pass
    else:raise AssertionError('current97c must not pass candidate install check')
    modeled=copy.deepcopy(actual);new=row['manifest'];charger=new['modules']['samurai-mp2650']['target']
    modeled['manifest']['sha256']=row['manifest_sha256'];modeled['manifest_text']=json.dumps(new)
    modeled['installed_files'][charger]['sha256']=new['installed_files'][charger]
    modeled['charging_modules']['samurai-mp2650'].update(sha256=new['installed_files'][charger],loaded_note_sha256=row['notes']['samurai_mp2650'])
    assert scope['check_install'](modeled)=={'cohort_disk_and_new_live_notes':True}
    u.create(u.OUT/'postboot-collector-template.py',source)
    result=dict(prepared=True,original_twelve_checks=True,current97c_rejected=True,modeled_new_install_profile_accepted=True,
                device_accessed=False,new_boot_checked=False,guard_created=False)
    u.save(HERE/'postboot-local-result.json',result);return result
def run():
    assert collector()==(u.OUT/'postboot-collector-template.py').read_bytes()
    return old.run()
prior.u=u;prior.collector=collector;prior.GUARD=GUARD
body=inspect.getsource(prior.adopt)
body=u.replace(body,"profile='forward_504_protection_observed2719'","profile='forward_504_charger_timer_hold'")
point="u.save(u.OUT/'adoption-pointer.json',current)"
extra="""previous=json.loads(before)
 current['previous_runtime_evidence']={key:previous.get(key) for key in ['boot_id','charging_manifest_sha256','PM_suspend_resume_verified','PM_single_RTC_residency_seconds','PM_result_sha256']}
 current['protection_capture_cache_sha256']=json.loads((u.OUT/('postboot-r2' if (u.OUT/'postboot-r2').exists() else 'postboot')/'reply.json').read_bytes())['raw']['protection_cache_after']['sha256']
 current['protection_capture_source_authenticated']=False
 current.pop('protection_capture_result_sha256',None)
 current['PM_single_RTC_residency_seconds']=None
 current.pop('PM_result_sha256',None)
 current['PM_current_protection_profile_verified']=False
 current['PM_current_USB_irq_wake_cohort_verified']=False
 current['USB_physical_wakeup_verified']=False
 current['charger_timer_hold_candidate_loaded']=True
 current['charger_timer_hold_transition_verified']=False
 """+point
body=u.replace(body,point,extra)
body=u.replace(body,"'profile-protection-adoption-next-private.json'","'charger-timer-adoption-next-private.json'")
exec(compile(body,'<original-newboot-adopt-with-current-timer-fields>','exec'),prior.__dict__)
def adopt():return prior.adopt()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='local',choices=['local','run','adopt']);a=p.parse_args()
    print(json.dumps(globals()[a.action](),indent=2))
