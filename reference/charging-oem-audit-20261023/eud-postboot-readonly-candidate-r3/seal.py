"""Seal narrow marker revision, no old tests or device actions."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'revision-source-result.json').read_bytes())
test=json.loads((HERE/'test-marker-result.json').read_bytes())
assert test['passed'] and test['case_count']==6 and not test['old_suites_rerun']
for n,digest in test['tested_files'].items():assert sha(HERE/n)==digest
assert all(sha(Path(p))==digest for p,digest in source['preserved_file_hashes'].items())
result=dict(frozen=True,offline_revision_passed=True,scope='R3 decoder-prefix gate only, retained Full fix',
 files={n:sha(HERE/n) for n in ['device.py','payload.py','contract.json','r2-to-r3.patch','revision-source-result.json','test-marker-result.json','README.md']},
 changed_actual_functions=['decode_ring'],actual_marker_cases=6,
 R2_Full_11_cases_reused=True,R1_other_9_groups_reused=True,old_suites_rerun=False,
 R1_R2_unchanged=True,worker_collected=False,device_accessed=False,SSH_invoked=False,
 USB_invoked=False,SDK_invoked=False,Git_invoked=False,physical_EUD_route_or_icon_accepted=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
delivery=dict(schema=1,frozen=True,files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'})
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(result_sha256=sha(HERE/'result.json'),delivery_sha256=sha(HERE/'delivery.json'),
 device_sha256=sha(HERE/'device.py'),patch_sha256=sha(HERE/'r2-to-r3.patch'),
 test_sha256=sha(HERE/'test-marker-result.json')),indent=2))
