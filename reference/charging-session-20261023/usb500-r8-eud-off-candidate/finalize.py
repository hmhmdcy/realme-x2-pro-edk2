"""Bind completed new checks, no test or device entry is invoked."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((HERE/'device-candidate/test-result.json').read_bytes())
h=json.loads((HERE/'host-test-result.json').read_bytes())
p=json.loads((HERE/'root-reader-test-result.json').read_bytes())
g=json.loads((HERE/'generation-result.json').read_bytes())
assert d['passed'] and h['passed'] and p['passed']
for n,digest in g['device_files'].items():assert sha(HERE/'device-candidate'/n)==digest
for n,digest in d['tested_files'].items():assert sha(HERE/'device-candidate'/n)==digest
for receipt in [h,p]:
 for n,digest in receipt['tested_files'].items():assert sha(HERE/n)==digest
assert sha(HERE/'test-migration.py')==d['test_source_sha256']
assert sha(HERE/'test-host.py')==h['test_source_sha256']
assert sha(HERE/'test-root-reader.ps1')==p['test_source_sha256']
old=REF/'charging-oem-audit-20261023/usb500-r7-candidate/orchestration-test-result.json'
old_result=json.loads(old.read_bytes())
r={'schema':'usb500-r8-eud-off-orchestration-v1','passed':True,
 'scope':'R8/EUD-off identity and direct-root discovery/byte-port migration only; not hardware acceptance',
 'cases':{'device_identity':d['cases'],'host':h['cases'],'root_reader_parent':p['cases']},
 'tested_files':h['tested_files'],'device_files':g['device_files'],'manifest_sha256':g['manifest'],
 'transport_sha256':g['transport_sha256'],'guard':g['guard'],
 'receipts':{n:sha(HERE/n) for n in ['device-candidate/test-result.json','host-test-result.json','root-reader-test-result.json']},
 'reused_r7_orchestration_sha256':sha(old),'reused_original_receipts':old_result['frozen_reference_receipts'],
 'old_suites_rerun':False,'coordinator_executed':False,'collector_executed':False,'native_GET_called':False,
 'device_access':False,'usb_access':False,'sdk_access':False,'USB500_accepted':False}
(HERE/'orchestration-test-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':r['cases'],'source_sha256':r['tested_files'],'receipt_sha256':sha(HERE/'orchestration-test-result.json')},indent=2))
