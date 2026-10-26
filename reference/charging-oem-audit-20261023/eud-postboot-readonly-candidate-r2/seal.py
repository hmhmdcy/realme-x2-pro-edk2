"""Seal Full-only revision and preserve known remaining review boundary."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'eud-postboot-readonly-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'revision-source-result.json').read_bytes())
test=json.loads((HERE/'test-full-result.json').read_bytes())
assert test['passed'] and test['case_count']==11 and not test['old_10_group_suite_rerun']
for n,digest in test['tested_files'].items():assert sha(HERE/n)==digest
assert all(sha(OLD/n)==digest for n,digest in source['R1_files'].items())
assert sha(HERE/'payload.py')==source['R1_files']['payload.py']
result=dict(scope='Full/normal consistency only; marker-prefix review still pending',
 Full_revision_passed=True,frozen=True,R1_unchanged=True,
 device_sha256=sha(HERE/'device.py'),patch_sha256=sha(HERE/'r1-to-r2.patch'),
 test_sha256=sha(HERE/'test-full-result.json'),case_count=11,
 reused_R1_other_groups=9,old_10_group_suite_rerun=False,
 marker_prefix_issue_fixed=False,whole_postboot_chain_accepted=False,
 device_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
delivery=dict(schema=1,frozen=True,files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'})
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(result_sha256=sha(HERE/'result.json'),delivery_sha256=sha(HERE/'delivery.json')),indent=2))
