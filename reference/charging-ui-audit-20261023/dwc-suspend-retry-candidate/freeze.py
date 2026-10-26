"""Bind completed new retry source/tests/object only; never replay a tool."""
from pathlib import Path
import difflib,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def main():
 assert not sys.flags.optimize and not (HERE/'delivery.json').exists()
 source=read(HERE/'source-result.json');test=read(HERE/'test-result.json');build=read(HERE/'build-result.json')
 assert test['passed'] is True and test['summary']['cases']==15
 assert test['summary']['old_two_attempt_failure_reproduced'] is True
 assert test['summary']['post_snapshot_producer_lifetime_not_serialized'] is True
 assert test['post_snapshot_producer_control_not_a_safety_pass'] is True
 assert build['passed'] is True and build['phase']['terminal'] is True and build['phase']['returncode']==0
 assert build['tracked_inputs_unchanged'] and build['parent_mounts_unchanged_after_helper']
 assert build['aarch64_relocatable'] and not build['diagnostic_lines']
 for receipt in [test,build]:
  for name,digest in receipt['files'].items():assert sha(HERE/name)==digest,name
 paths={'gadget.c':HERE.parent/'dwc-suspend-halt-error-candidate/gadget.c',
        'core.c':HERE.parent/'dwc-pm-error-unwind-candidate/core.c',
        'core.h':REF/'charging-session-20261023/dwc-device-start-recovery-candidate/core.h'}
 for name,path in paths.items():assert sha(path)==source['inputs'][name]
 assert sha(HERE/'gadget.c')==source['candidate_gadget_sha256']
 patch=''.join(difflib.unified_diff(paths['gadget.c'].read_text().splitlines(True),(HERE/'gadget.c').read_text().splitlines(True),
       fromfile='halt-error-candidate/drivers/usb/dwc3/gadget.c',tofile='retry-candidate/drivers/usb/dwc3/gadget.c'))
 assert patch==(HERE/'suspend-retry.patch').read_text()
 reused=[HERE.parent/'dwc-suspend-halt-error-candidate/delivery.json',HERE.parent/'dwc-pm-error-unwind-candidate/delivery.json',
         REF/'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json',
         REF/'charging-session-20261023/dwc-image503-start-recovery-candidate/delivery.json']
 result=dict(schema=1,passed=True,frozen=True,
  scope='active software-no-pullup suspend retry requires hardware HALT and RUN_STOP clear',
  files={str(p.relative_to(HERE)).replace('\\','/'):dict(sha256=sha(p),bytes=p.stat().st_size)
       for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
  source_inputs=source['inputs'],candidate_gadget_sha256=sha(HERE/'gadget.c'),actual_new_cases=15,
  old_13_24_20_126_suites_rerun=False,
  actual_object=dict(sha256=build['object_sha256'],bytes=build['object_size'],phase=build['phase']),
  historical_receipts={str(p.relative_to(REF)).replace('\\','/'):sha(p) for p in reused},
  no_repeated_request_teardown_reset_or_new_poll=True,
  full_run_stop_writer_or_PM_lifetime_serialization=False,explicit_post_snapshot_limitation_control=True,
  full_resume_unwind_complete=False,Image_or_module_linked=False,device_SSH_USB_SDK_Git_used=False,deployed=False)
 (HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),source_sha256=sha(HERE/'gadget.c'),
      test_sha256=sha(HERE/'test-result.json'),build_sha256=sha(HERE/'build-result.json'))))


if __name__=='__main__':main()
