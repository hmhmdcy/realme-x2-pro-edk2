"""Seal exact source/board/hook-limit audit; no kernel patch or device work."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((HERE/'source-manifest.json').read_bytes())
test=json.loads((HERE/'test-result.json').read_bytes())
board=json.loads((HERE/'board-linkage.json').read_bytes())
assert test['passed'] and test['groups']==5 and test['existing_actual_functions']==9
assert board['passed'] and board['typec_status']=='disabled' and board['typec_children']==[]
for row in source['files']:assert sha(HERE/'sources'/row['snapshot'])==row['sha256']
for name,digest in test['tested_files'].items():assert sha(HERE/name)==digest
result=dict(frozen=True,source_and_boundary_audit_complete=True,
 existing_complete_safe_hook=False,PD_inactive_proven=False,gate_implemented=False,
 proposed_contract_only=True,kernel_patch_created=False,production_object_built=False,
 focused_test_passed=True,focused_existing_actual_functions=9,focused_groups=5,
 actual_PMIC_TPCP_owner_enabled_by_this_work=False,
 source_snapshot_sha256=sha(HERE/'source-manifest.json'),board_linkage_sha256=sha(HERE/'board-linkage.json'),
 contract_sha256=sha(HERE/'interface-contract.json'),test_sha256=sha(HERE/'test-result.json'),
 shared_source_or_config_modified=False,old_suites_rerun=False,
 phone_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,
 next_implementation='real TCPM locked snapshot + ingress generation/invalidation + qcom pre-reset lock-free cancel/join, before any future enabled-owner board policy')
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='delivery.json'}
(HERE/'delivery.json').write_text(json.dumps(dict(schema=1,frozen=True,files=files),indent=2)+'\n')
print(json.dumps(dict(result_sha256=sha(HERE/'result.json'),delivery_sha256=sha(HERE/'delivery.json'),
 contract_sha256=sha(HERE/'interface-contract.json'),test_sha256=sha(HERE/'test-result.json')),indent=2))
