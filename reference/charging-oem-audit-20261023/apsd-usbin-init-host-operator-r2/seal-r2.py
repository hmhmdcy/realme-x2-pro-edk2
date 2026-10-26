"""Seal already-tested R2; no transport/build/test execution."""
from pathlib import Path
import json,common
here=Path(__file__).resolve().parent
t=json.loads((here/'test-result.json').read_text());assert t['passed']
for name,digest in t['files'].items():assert common.sha((here/name).read_bytes())==digest,name
files=dict(t['files'])
for name in ['README.md','test-result.json','seal-r2.py']:files[name]=common.sha((here/name).read_bytes())
d={'passed':True,'scope':'offline R2 host300000ms helper /480s observer; not launched','files':files,
   'controller_sha256':files['controller.py'],'protocol_sha256':files['protocol.py'],'observer_sha256':files['observer.py'],
   'worker_sha256':files['device.py'],'helper_module_sha256':files['samurai-usbin-init.ko'],'new_targeted_cases':t['case_count'],
   'R1_35_cases_reused_not_rerun':True,'helper_delivery_sha256':'d3092c1b25348bb310e956ef6a76e4903b3c051be376c8823fa4beb0458ff4b3',
   'no_phone_network_SDK_Git':True,'automatic_retry':False,'launched':False,'physical_acceptance':False}
common.save(here/'delivery.json',d)
print(json.dumps({'delivery_sha256':common.sha((here/'delivery.json').read_bytes()),'controller_sha256':d['controller_sha256'],'protocol_sha256':d['protocol_sha256'],'observer_sha256':d['observer_sha256'],'test_result_sha256':files['test-result.json']}))
