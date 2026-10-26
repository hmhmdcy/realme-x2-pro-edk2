"""Combine only completed directed offline migration checks; no test reruns."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('qualified_r7_host',HERE/'host-launcher.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
d=json.loads((HERE/'device-candidate/test-result.json').read_text())
host=json.loads((HERE/'host-migration-test-result.json').read_text())
parent=json.loads((HERE/'parent-migration-test-result.json').read_text())
assert d['passed'] and host['passed'] and parent['passed']
assert d['schema']=='usb500-r7-migration-v1' and d['cases']==14 and host['cases']==7 and parent['cases']==3
for n,digest in h.REVIEWED.items():assert sha(HERE/'device-candidate'/n)==digest
for n,digest in d['tested_files'].items():assert sha(HERE/'device-candidate'/n)==digest
for n,digest in host['tested_files'].items():assert sha(HERE/n)==digest
assert sha(HERE/'test-device-migration.py')==d['test_source_sha256']
assert sha(HERE/'test-host-migration.py')==host['test_source_sha256']
assert sha(HERE/'host-parent.ps1')==parent['parent_sha256']
assert sha(HERE/'test-parent-migration.ps1')==parent['test_sha256']
g=json.loads((HERE/'generation-result.json').read_text())
assert h.REVIEWED==g['device_files']
result={'schema':'usb500-r7-directed-orchestration-v1','passed':True,
 'scope':'offline R6->R7 identity/IPv6/source-receiver port only; not a USB500 runtime result',
 'cases':{'device_migration':d['cases'],'host_migration':host['cases'],'parent_gate_migration':parent['cases']},
 'tested_files':host['tested_files'],'device_files':h.REVIEWED,
 'r7_manifest_sha256':h.MANIFEST,'r7_transport_helper_sha256':h.TRANSPORT_SHA,
 'component_receipts':{n:sha(HERE/n) for n in ['device-candidate/test-result.json','host-migration-test-result.json','parent-migration-test-result.json']},
 'frozen_reference_receipts':{'device51_sha256':'faf128cf133e0c91127d1d7cef466a402abdc23c93f02d46d1a9bc5910d42348',
  'decoder62_sha256':'4c1984e557dfd6fff70d0adcb6202f91912302c9aa0cb4f2137a838cb9a25338',
  'host11_parent12_sha256':'0302a1e89aa06c9952bf3595c7684532ab73befe35a9053c874af3f3a4f9d4eb'},
 'frozen_full_suites_rerun':False,'coordinator_executed':False,'collector_executed':False,
 'ssh_called':False,'device_access':False,'usb_access':False,'sdk_access':False}
(HERE/'orchestration-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
