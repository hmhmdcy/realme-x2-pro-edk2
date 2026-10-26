"""Bind completed new receipts and reused prior evidence; no test/build entry."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

test = json.loads((HERE/'test-result.json').read_text())
build = json.loads((HERE/'build-result.json').read_text())
assert test['passed'] and test['summary']['cases']==20 and test['summary']['groups']==6
assert build['passed'] and build['phase']['terminal'] and build['phase']['returncode']==0
assert build['tracked_inputs_unchanged'] and build['parent_mounts_unchanged']
for receipt in [test,build]:
    for name,digest in receipt['files'].items():
        assert sha(HERE/name)==digest,name
reused = [
 'charging-oem-audit-20261023/dwc-device-sync-recovery-candidate/source-result.json',
 'charging-oem-audit-20261023/dwc-device-sync-recovery-candidate/test-result.json',
 'charging-oem-audit-20261023/dwc-device-sync-recovery-candidate/build-result.json',
 'charging-oem-audit-20261023/usb-resume-errors/README.md',
 'charging-oem-audit-20261023/usb-resume-errors/result-original.json',
 'charging-oem-audit-20261023/usb-resume-errors/result-propagate.json',
 'charging-oem-audit-20261023/usb-resume-errors/propagate-errors.patch',
 'charging-oem-audit-20261023/apsd-dwc-resume-error-candidate/README.md',
 'charging-session-20261023/dwc-resume-error-independent-review/review-result.json',
 'charging-session-20261023/dwc-resume-error-independent-review/short-options.md',
 'charging-session-20261023/dwc-resume-device-cleanup-candidate/README.md',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json',
]
rows = {n:sha(REF/n) for n in reused}
evidence = dict(
 source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8',
 actual_502_original_dwc_hashes=json.loads((HERE/'source-result.json').read_text())['original'],
 actual_502_verified_by='build-result.json/inputs_before+inputs_after',
 call_chain=[
  dict(path='gadget.c:dwc3_gadget_soft_connect', fact='start errno now returns before RUN_STOP; locked EP0/DEVTEN cleanup; core/event stay valid'),
  dict(path='gadget.c:dwc3_gadget_resume -> dwc3_gadget_recover_locked', fact='DEVICE first error invokes bounded existing synchronous helper; primary retained'),
  dict(path='core.c:dwc3_resume_common DEVICE', fact='unchanged gadget errno ignored; initialized core retained, common returns original success'),
  dict(path='core.c:dwc3_runtime_resume', fact='unchanged common success consumes pending_events ref and enables IRQ; negative common would skip it'),
  dict(path='drivers/base/power/runtime.c:rpm_resume', fact='prior fixed-source audit: negative callback leads RPM_SUSPENDED, not implicit driver suspend compensation'),
  dict(path='core.c:dwc3_pm_resume', fact='unchanged negative common calls pm_runtime_set_suspended; no added core teardown'),
 ],
 unresolved=['HALT/soft-reset timeout does not prove hardware quiet',
             'negative gadget failure -> safe PM/core unwind is not implemented',
             'normal existing error worker power/lifetime outside this local sync increment is not expanded'],
 rejected_cleanup_used=False, reused_evidence=rows,
 old_suites_rerun=False, physical_recovery_proved=False,
)
(HERE/'caller-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
files={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
delivery=dict(schema='samurai-dwc-device-start-recovery-candidate-v1',passed=True,
 scope='local DEVICE start-error propagation/cleanup into frozen sync recovery; PM common policy unchanged',
 files=files,test_receipt_sha256=sha(HERE/'test-result.json'),build_receipt_sha256=sha(HERE/'build-result.json'),
 candidate_gadget_sha256=sha(HERE/'gadget.c'),candidate_core_h_sha256=sha(HERE/'core.h'),
 object_sha256=build['object_sha256'],private_object=build['object_path'],
 future_complete_kernel_required=True,pm_unwind_complete=False,deployed=False,device_access=False,
 source_frozen=True,old_tests_not_rerun=True)
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(delivery_sha256=sha(HERE/'delivery.json'),gadget_sha256=sha(HERE/'gadget.c'),
                     patch_sha256=sha(HERE/'start-cleanup.patch'),tests_sha256=sha(HERE/'test-result.json'),
                     build_sha256=sha(HERE/'build-result.json'),files=len(files))))
