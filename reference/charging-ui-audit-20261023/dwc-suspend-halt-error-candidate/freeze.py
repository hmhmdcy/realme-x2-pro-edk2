"""Bind completed source/tests/single-object receipts only; no tools replay."""
from pathlib import Path
import difflib
import hashlib
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):return json.loads(p.read_bytes())


def main():
 if sys.flags.optimize:raise RuntimeError('nonoptimized interpreter required')
 assert not (HERE/'delivery.json').exists(),'Preserve frozen delivery'
 source=read(HERE/'source-result.json');tests=read(HERE/'test-result.json');build=read(HERE/'build-result.json')
 assert tests['passed'] is True and tests['summary']['cases']==13
 assert tests['summary']['current_failed_attempt_core_exit_prevented'] is True
 assert tests['summary']['later_false_pullup_retry_gap_fixed'] is False
 assert build['passed'] is True and build['phase']['terminal'] is True and build['phase']['returncode']==0
 assert build['tracked_inputs_unchanged'] and build['parent_mounts_unchanged_after_helper']
 assert build['aarch64_relocatable'] and not build['diagnostic_lines']
 for receipt in [tests,build]:
  for name,digest in receipt['files'].items():assert sha(HERE/name)==digest,name
 old=REF/'charging-session-20261023/dwc-device-start-recovery-candidate/gadget.c'
 core=HERE.parent/'dwc-pm-error-unwind-candidate/core.c'
 header=old.with_name('core.h')
 for name,path in {'gadget.c':old,'core.c':core,'core.h':header}.items():assert sha(path)==source['inputs'][name]
 assert sha(HERE/'gadget.c')==source['candidate_gadget_sha256']
 patch=''.join(difflib.unified_diff(old.read_text().splitlines(True),(HERE/'gadget.c').read_text().splitlines(True),
       fromfile='Image503/drivers/usb/dwc3/gadget.c',tofile='candidate/drivers/usb/dwc3/gadget.c'))
 assert patch==(HERE/'suspend-halt-error.patch').read_text()
 reused=[HERE.parent/'dwc-pm-error-unwind-candidate/delivery.json',
       REF/'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json',
       REF/'charging-session-20261023/dwc-image503-start-recovery-candidate/delivery.json']
 result=dict(schema=1,passed=True,frozen=True,
  scope='current failed gadget suspend errno return only; no full PM/retry unwind',
  files={str(p.relative_to(HERE)).replace('\\','/'):dict(sha256=sha(p),bytes=p.stat().st_size)
      for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
  source_inputs=source['inputs'],candidate_gadget_sha256=sha(HERE/'gadget.c'),
  actual_new_cases=13,old_24_20_126_suites_rerun=False,
  actual_object=dict(sha256=build['object_sha256'],bytes=build['object_size'],phase=build['phase']),
  historical_receipts={str(p.relative_to(REF)).replace('\\','/'):sha(p) for p in reused},
  core_resume_unwind_complete=False,later_false_pullup_retry_gap_fixed=False,
  original_softconnect_true_recovery_policy_unchanged=True,Image_or_module_linked=False,
  device_SSH_USB_SDK_Git_used=False,deployed=False)
 (HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),
   source_sha256=sha(HERE/'gadget.c'),test_sha256=sha(HERE/'test-result.json'),build_sha256=sha(HERE/'build-result.json'))))


if __name__=='__main__':main()
