from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());b=json.loads((HERE/'build-result.json').read_text())
assert t['passed'] and b['passed'] and t['group_count']==11 and t['actual_functions']==8
assert b['test_receipt_sha256']==sha(HERE/'test-result.json')
for name,h in t['files'].items():assert sha(HERE/name)==h,name
for name,h in b['sources'].items():assert sha(HERE/name)==h,name
source=json.loads((HERE/'source-result.json').read_text())
assert b['original_core_sha256']==source['original']['core.c']['sha256']
names=['README.md','gadget.c','core.h','baseline-gadget.c','baseline-core.h','sync-recovery.patch','prepare.py','source-result.json',
 'prepare-tests.py','test-sync.c','tested-functions.inc','function-manifest.json','run-tests.py','test-result.json','build-private.py','build-result.json','freeze.py']
r=dict(passed=True,scope='offline original-Image363 DEVICE synchronous recovery, gadget/header only',
 files={name:sha(HERE/name) for name in names},source_commit=source['source_commit'],
 original_core_unchanged=True,core_PM_success_policy_unchanged=True,PM_IRQ_pending_reference_tail_unchanged=True,
 persistent_fields_added={'err_event_seq':'u64 real IRQ generation protected by existing lock'},R2_required=False,stopped_WIP_used=False,
 old_126_rerun=False,old_caller_repros_rerun=False,new_test_groups=11,actual_functions=8,object_sha256=b['object_sha256'],
 new_retry_loop=False,new_IRQ_depth_or_PM_reference=False,new_terminal_flags=False,
 image_or_ko_linked=False,installed=False,phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,Git_invoked=False,
 hardware_validated=False,historical_r5_cause_proven=False)
(HERE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,result_sha256=sha(HERE/'result.json'),patch_sha256=sha(HERE/'sync-recovery.patch'),
 gadget_sha256=sha(HERE/'gadget.c'),header_sha256=sha(HERE/'core.h'),test_sha256=sha(HERE/'test-result.json'),
 build_sha256=sha(HERE/'build-result.json'),object_sha256=b['object_sha256']),indent=2))
