"""Seal a review candidate; no firmware build, deployment or hardware claims."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'test-result.json').read_text());candidate=json.loads((HERE/'candidate-result.json').read_text())
assert test['passed'] and test['case_count']==12 and test['panel_functions_and_original_call_block_byte_exact']
for name,digest in test['files'].items():assert sha(HERE/name)==digest
assert candidate['patch_sha256']==sha(HERE/'boot-policy.patch')
assert candidate['all_other_dt_properties_byte_exact'] and candidate['other_tokens_unchanged']
assert len(candidate['dt_semantic_changes'])==2
assert sha(Path(candidate['native_candidate_path']))==candidate['native_candidate_sha256']
names=['inspection.json','design-evidence.json','design-amendment.json','candidate-result.json','test-result.json','README.md',
 'boot-policy.patch','eud-handoff-fragment.inc','PlatformBm.c','PlatformBm.c.candidate','EudLogDxe.c','EudSerialPortLib.c',
 'DxeMain--DxeMain.c','Event--Event.c','Event--Tpl.c','core-functions.inc','direct-fifo.inc','launch.inc',
 'inspect-offline.py','freeze-design.py','make-candidate.py','run-tests.py','test-boot.c','seal-result.py']
names+=sorted(p.name for p in HERE.glob('evidence--*'))
r=dict(passed=True,status='frozen offline review candidate',files={n:sha(HERE/n) for n in names},
 candidate_patch_sha256=candidate['patch_sha256'],native_base_sha256=candidate['native_base_sha256'],
 native_candidate_path=candidate['native_candidate_path'],native_candidate_sha256=candidate['native_candidate_sha256'],
 kernel_image_preserved_sha256=candidate['image_preserved_sha256'],host_case_count=12,
 actual_existing_functions=test['actual_existing_EDK2_functions'],
 csr_accepts_full_words=[0,1],replica_accepted=False,
 software_scope='boot-only EDK2 handoff, two EUD tokens removed in both inputs, native COM disabled; panel unchanged',
 gates_remaining=['future exclusive-window valid-power read-only CSR full-word evidence','bind all frozen firmware inputs to new actual linked build',
  'preserve Image363/camera434 module ABI and guard baselines','independent physical fastboot/known old boot rollback path',
  'actual callback receipt and postboot no-EUD/host topology/native-budget evidence'],
 no_new_runtime_owner=True,no_kernel_helper=True,full_firmware_built=False,SDK_invoked=False,shared_tree_modified=False,
 phone_accessed=False,ssh_executed=False,usb_accessed=False,hardware_CSR_zero_proven=False,direct_USB_or_SDP500_proven=False,
 old_runtime_candidates_modified=False,old_test_suites_repeated=False)
(HERE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,result_sha256=sha(HERE/'result.json'),patch_sha256=sha(HERE/'boot-policy.patch'),test_sha256=sha(HERE/'test-result.json'))))
