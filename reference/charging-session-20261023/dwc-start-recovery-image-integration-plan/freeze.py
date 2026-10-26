"""Bind the read-only dependency scope and existing source receipts."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((HERE/'dependency-result.json').read_text())
assert r['passed'] and len(r['required_object_targets'])==8
assert not r['global_dwc3_module_targets'] and not r['new_Image_built']
refs=[
 'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json',
 'charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review-result.json',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/run-502.py',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json',
 'charging-session-20261023/gauge-image363-baseline/run-baseline.py',
 'charging-oem-audit-20261023/gauge-image363-integration-plan/link-inputs.json',
 'charging-oem-audit-20261023/gauge-image363-integration-plan/final-link-inputs.json',
]
result=dict(schema='samurai-dwc-start-recovery-image-scope-v1',passed=True,
 files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'},
 reused={n:sha(REF/n) for n in refs},required_object_targets=r['required_object_targets'],
 source_delta=r['proposed_changed_sources'],new_Image_built=False,build_authorized_here=False,
 old_suites_rerun=False,device_access=False)
(HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(delivery_sha256=sha(HERE/'delivery.json'),dependency_result_sha256=sha(HERE/'dependency-result.json'),
                     plan_sha256=sha(HERE/'PLAN.md'),targets=8)))
