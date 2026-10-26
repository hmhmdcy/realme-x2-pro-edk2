"""Freeze this offline source/test delivery; no runtime binding or transport."""
from pathlib import Path
import hashlib,json,os
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def local(path):
    value=str(path).replace('\\','/')
    if os.name!='nt' and value.startswith('E:/'):value='/mnt/e/'+value[3:]
    return Path(value)

def main():
    pins=json.loads((HERE/'source-pins.json').read_bytes())
    for name,row in pins.items():
        raw=local(row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
    tests=json.loads((HERE/'test-result.json').read_bytes())
    assert tests['passed'] is True and tests['new_case_count']==21 and tests['old21_26_owner_matrices_rerun'] is False
    for name,digest in tests['tested_files'].items():assert sha((HERE/name).read_bytes())==digest,name
    defaults=json.loads((HERE/'default-result.json').read_bytes())
    assert defaults['passed'] is True and all(r['status']=='fulfilled' and r['value']['result']['exit_code']==0 for r in defaults['results'])
    files=['host.py','stage-worker.py','remote.py','supervisor.py','prepare-sources.py','pin-sources.py','source-pins.json',
           'contract.json','test-delta.py','test-result.json','default-result.json','execution-receipt.json','README.md','freeze.py']
    history=['history/initial-17/'+name for name in ['host.py','stage-worker.py','remote.py','supervisor.py','prepare-sources.py',
             'test-delta.py','test-result.json','scope.json']]+['history/test-attempt-02/'+name for name in ['host.py','test-delta.py','result.json']]
    result={'schema':'samurai-protection-capture-host-delivery-v1','passed':True,'frozen':True,
       'files':{name:{'sha256':sha((HERE/name).read_bytes()),'bytes':len((HERE/name).read_bytes())} for name in files},
       'preserved_history':{name:{'sha256':sha((HERE/name).read_bytes()),'bytes':len((HERE/name).read_bytes())} for name in history},
       'new_case_count':21,'actual_parser_and_existing_C_decoder':True,'original_supervisor_actual_harmless_child_case':True,
       'stage_host_R2_transfer_and_supervisor_reused':True,'original_supervisor_sha256':pins['supervisor']['sha256'],
       'adoption_review_sha256':pins['adoption_review']['sha256'],'adoption_review_pins_sha256':pins['adoption_review_pins']['sha256'],
       'old_suites_rerun':False,'actual_IRQ_postboot_adoption_required_before_runtime_bind':True,
       'runtime_identity_request_lease_or_transport_created':False,'device_accessed':False,
       'compatibility_TCA_or_physical_acceptance':False,'charging_policy_changed':False}
    raw=(json.dumps(result,indent=2)+'\n').encode()
    with (HERE/'delivery.json').open('xb') as stream:stream.write(raw)
    print(json.dumps({'passed':True,'frozen':True,'delivery_sha256':sha(raw)}))

if __name__=='__main__':main()
