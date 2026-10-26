"""Seal completed source/tests/contract without running a device or old suite."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_text())
test=json.loads((HERE/'test-result.json').read_text())
assert test['passed'] and test['group_count']==10
assert sha(HERE/'device.py')==source['device_sha256']==test['tested_files']['device.py']
for name,digest in test['tested_files'].items():assert sha(HERE/name)==digest,name
result=dict(passed=True,frozen=True,scope='unrun one-shot EUD boot-only postboot readonly collector',
 files={n:sha(HERE/n) for n in ['device.py','payload.py','contract.json','source-result.json','test-result.json','README.md']},
 default='check-local',targeted_groups=10,workers_collected=False,
 host_transport_implemented=False,guard_created=False,EUD_CSR_MMIO_accessed=False,
 Image_built=False,device_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,
 old_suites_rerun=False,actual_new_boot_or_EUD_route_proven=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
delivery=dict(schema=1,frozen=True,files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'})
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(result_sha256=sha(HERE/'result.json'),delivery_sha256=sha(HERE/'delivery.json'),
 device_sha256=sha(HERE/'device.py'),payload_sha256=sha(HERE/'payload.py'),contract_sha256=sha(HERE/'contract.json'),test_sha256=sha(HERE/'test-result.json')),indent=2))
