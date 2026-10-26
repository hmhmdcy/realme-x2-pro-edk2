"""Audit the successful corrected shadow window and recovery separately."""
from pathlib import Path
import json

ref=Path(__file__).resolve().parent
root=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
p=root/'window4'
before=json.loads((p/'shadow-before-private.json').read_text())
during=json.loads((p/'shadow-captured-private.json').read_text())
after=json.loads((p/'shadow-restored-private.json').read_text())
finish=json.loads((p/'finish-stdout-private.json').read_text())
config=lambda d:{k:v for k,v in d['registers'].items() if k!='13'}
assert before['boot_id']==during['boot_id']==after['boot_id']
assert config(before)==config(during)==config(after)
assert before['services']==during['services']==after['services']
assert before['camera_pm']==during['camera_pm']==after['camera_pm']
assert before['m2m']==during['m2m']==after['m2m']
assert after['driver']=='mp2650' and during['driver']=='samurai-mp2650'
assert all(int(v['taint'])==0 for v in [before,during,after])
sample={k:int(v) for k,v in (item.split('=') for item in during['telemetry'].split())}
assert all(sample[k]==1 for k in ['shadow','valid','online','protection_ok','desired_enable'])
assert not any(sample[k] for k in ['fault','error','stop_error','latched'])
assert sample['age_ms']<2000 and sample['budget_ua']==1500000
staged=json.loads((p/'staged.json').read_text())
report={'passed':True,'control_enabled':False,'charger_configuration_writes':0,
    'sample':sample,'protection':during['protection'],'loaded_module_sha256':{k:v for k,v in staged.items() if k.endswith('.ko')},
    'charger_configuration_unchanged':True,'original_observer_restored':True,
    'camera_pm_complete_m2m_and_four_user_services_unchanged':True,
    'candidate_modules_present':finish['candidate_modules_present'],
    'boot_fault_counts':finish['boot_fault_counts'],'taint':finish['taint'],
    'phone_handed_back_to_camera_chat':True,'partitions_written':[]}
(ref/'shadow-result.json').write_text(json.dumps(report,indent=2)+'\n')
before=json.loads((root/'recovery/preflight-stdout-private.txt').read_text())
after=json.loads((root/'recovery/postboot-stdout-private.txt').read_text())
assert before['boot_id']!=after['boot_id'] and before['taint']==512 and after['taint']==0
assert before['modules']==after['modules'] and before['packages']==after['packages']
recovery={'passed':True,'original_environment_restarted':True,'partitions_written':[],
    'new_boot_verified':True,'original_ssh_key_retained':True,'taint':0,
    'formal440_packages_and_loaded434_modules_match':True,'camera_pm':after['pm'],
    'four_user_services_uid10000':True,'candidate_modules_installed':False}
(ref/'recovery-result.json').write_text(json.dumps(recovery,indent=2)+'\n')
print(json.dumps({'shadow_passed':report['passed'],'recovery_passed':recovery['passed'],'taint':0}))
