"""Original twelve checks for actual old97c residency after inverse cold boot."""
from pathlib import Path
import argparse,ast,copy,importlib.util,inspect,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('timer_restored_postboot_host',HERE/'host.py');u=h.u
prior=load('timer_restored_original_adoption',HERE.parent/'protection-profile-update/postboot.py')
old=prior.old;old.update=u
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-timer-restored-20261024-01-adopted/boot-id-private.txt'
def collector():
    base=u.BASE/'usb-irq-wake-update-live-20261024-01'
    source=(base/'postboot-collector.py').read_text();m=h.worker()
    helpers=h.adapter.adapter.helpers
    manifest=json.loads((u.BASE/'charge-timer-hold-cohort-private-02/manifest-old.json').read_bytes())
    row=dict(target_manifest_sha256=m.OLD_FILES[m.MANIFEST],target_usb_note_sha256=m.OLD_NOTES['samurai-usb-input'],target_protection_note_sha256=m.OLD_NOTES['samurai-gauge-protection'])
    source=helpers.assigned(source,'NEW_COHORT',row);source=helpers.assigned(source,'NEW_MANIFEST',manifest)
    source+='\nRESTORED_FILES='+repr(m.OLD_FILES)+'\n'
    matches=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='validate_request'];assert len(matches)==2
    previous=ast.get_source_segment(source,matches[-1])
    validation='''def validate_request(request):
 row=configure_profile(request);g=request['guard'];stage=request['stage']
 assert request['schema']=='samurai-charger-timer-restored-postboot-v1' and request['profile']=='forward_504'
 assert request['carrier_writes']==0 and request['original_key_transport_verified'] is True
 assert g['boot_id']==request['source_identity']['boot_id'] and g['new_boot_id']==request['new_boot_id']!=g['boot_id']
 assert g['transaction_id']==stage['transaction_id'] and g['source_kernel_version']==g['target_kernel_version']==row['version']
 assert stage['schema']=='samurai-charger-timer-cold-rollback-result-v1' and stage['terminal'] and stage['restored'] and stage['stop_verified']
 assert stage['disk_state']=='all_original_fsynced' and stage['primary_error'] is None and not stage['unknown_write_state'] and not stage['module_or_carrier_action']
 assert set(stage['final_files'])==set(RESTORED_FILES)
 for path,digest in RESTORED_FILES.items():
  fact=stage['final_files'][path];assert fact['sha256']==digest and int(fact['mode'],8)==0o600 and fact['classification']=='original'
 assert sha((json.dumps(stage,indent=2)+'\\n').encode())==request['stage_result_sha256']
 return row'''
    source=u.replace(source,previous,validation);ast.parse(source);return source.encode()
def prepare(new_boot):
    r=h.request();rows=list(u.OUT.glob('raw-*/device-rollback/result.json'));assert len(rows)==1
    stage=rows[0].read_bytes();terminal=json.loads((rows[0].parent.parent/'worker-terminal-private.json').read_bytes())
    assert terminal['terminal'] and terminal['returncode']==0 and terminal['receipt_error'] is None
    camera=(u.BASE.parent/'kernel481/formal-expected-private.json').read_bytes();assert u.sha(camera)==u.transport_host.CAMERA
    m=h.worker()
    return dict(schema='samurai-charger-timer-restored-postboot-v1',profile='forward_504',carrier_writes=0,original_key_transport_verified=True,
        new_boot_id=new_boot,source_identity=r['identity'],stage=json.loads(stage),stage_result_sha256=u.sha(stage),camera=json.loads(camera),
        guard=dict(transaction_id=u.TX,boot_id=r['identity']['boot_id'],new_boot_id=new_boot,kernel_release=m.RELEASE,source_kernel_version=m.VERSION504,target_kernel_version=m.VERSION504,
            rootfs_release_sha256=r['identity']['rootfs_sha256'],soc_serial_sha256=r['identity']['serial_sha256'],compatible_sha256=r['identity']['compatible_sha256'],
            candidate_boot_sha256=m.BOOT,candidate_logdump_sha256=m.LOGDUMP504,image_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'))
old.collector=collector;old.prepare=prepare
def local():
    source=collector();scope={};exec(compile(source,'<restored-profile-checks>','exec'),scope);scope['configure_profile']({'profile':'forward_504'})
    row=scope['PROFILES']['forward_504'];assert row['manifest']['modules']['samurai-mp2650']['sha256']==h.worker().OLD_FILES[h.worker().TARGET]
    actual=json.loads((u.BASE/'usb-irq-wake-update-live-20261024-01/postboot/reply.json').read_bytes())['raw']
    assert scope['check_install'](actual)==dict(cohort_disk_and_new_live_notes=True)
    candidate=copy.deepcopy(actual);candidate['charging_modules']['samurai-mp2650']['loaded_note_sha256']=h.worker().NEW_NOTES['samurai-mp2650']
    try:scope['check_install'](candidate)
    except AssertionError:pass
    else:raise AssertionError('new charger note must not pass old restored profile')
    u.create(u.OUT/'postboot-collector-template.py',source)
    result=dict(prepared=True,current_old97c_install_evidence_accepted=True,new_bef_note_rejected=True,original_twelve_checks=True,
                newboot_checked=False,phone_accessed=False,guard_created=False)
    u.save(HERE/'postboot-local-result.json',result);return result
def run():
    assert collector()==(u.OUT/'postboot-collector-template.py').read_bytes();return old.run()
prior.u=u;prior.collector=collector;prior.GUARD=GUARD
body=inspect.getsource(prior.adopt)
body=u.replace(body,"profile='forward_504_protection_observed2719'","profile='forward_504_timer_restored97c'")
body=u.replace(body,"request['stage']['new_manifest_sha256']","request['stage']['final_files']['/usr/share/samurai-charging/manifest.json']['sha256']")
point="u.save(u.OUT/'adoption-pointer.json',current)"
extra="""current['previous_runtime_evidence']={key:json.loads(before).get(key) for key in ['boot_id','charging_manifest_sha256','PM_suspend_resume_verified','PM_result_sha256']}
 current['protection_capture_cache_sha256']=json.loads((u.OUT/'postboot/reply.json').read_bytes())['raw']['protection_cache_after']['sha256']
 current['protection_capture_source_authenticated']=False
 current.pop('protection_capture_result_sha256',None)
 current.pop('PM_result_sha256',None)
 current['PM_single_RTC_residency_seconds']=None
 current['PM_current_protection_profile_verified']=False
 current['PM_current_USB_irq_wake_cohort_verified']=False
 current['PM_current_charger_timer_cohort_verified']=False
 current['USB_physical_wakeup_verified']=False
 current['charger_timer_hold_candidate_loaded']=False
 current['charger_timer_hold_transition_verified']=False
 """+point
body=u.replace(body,point,extra);body=u.replace(body,"'profile-protection-adoption-next-private.json'","'timer-restored-adoption-next-private.json'")
exec(compile(body,'<original-fresh-adopt-restored97c>','exec'),prior.__dict__)
def adopt():return prior.adopt()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='local',choices=['local','run','adopt']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
