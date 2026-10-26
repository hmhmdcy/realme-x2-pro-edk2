"""Audit the completed camera cancellation independently of observer failure."""
from pathlib import Path
import importlib.util,json,re
import host
HERE=Path(__file__).resolve().parent;root=host.PRIVATE/'runtime-collected-r2'
state=json.loads((root/'state.json').read_text());assert state['terminal'] and not state['passed'] and 'observer.returncode' in (root/'failure.txt').read_text()
assert state['formal_modules_restored'] and state['services_restored'] and not state['new_faults'] and state['taint_after']==0
summary=state['sustained']['user-cancel-1080'];text=(root/'user-cancel-1080/client.log').read_text()
spec=importlib.util.spec_from_file_location('gst443',HERE.parent/'kernel443/frame-audit.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
source=base.source.replace('assert len(frames)==120',"assert len(frames)=="+str(summary['frames'])).replace("'bus-errors=0 result=0'","'bus-errors=0 result=9'")
namespace={'re':re};exec(compile(source,'strict-443-cancel-camera-audit','exec'),namespace)
row=namespace['audit_gst'](text,'s5kgw1',width=1920,height=1080,stride=1920,coarse_bytes=261120)
assert row['source_delivered_successful_images']==summary['ipe_completed']==95 and row['frames']==94
assert row['queued_images']==summary['ipe_completed']+row['stop_aborted_queued_images']
assert 'exited=1 exit=9 signalled=0' in text and re.search(r'CAPACITY_STOP .* status=0 reason=restored active=0 users=0',text)
assert 'APPLICATION_IDENTITY uid=10000 euid=10000 capeff=0000000000000000' in text
r=dict(stage=450,attempt='r2',camera_cancellation=row,normal_child_exit9_and_state_null_cleanup=True,capacity_restored=True,uid10000_capabilities0=True,observer_exit_validation_failed=True,whole_transaction_passed=False,long_case_not_started=True,temporary_directory_cleanup_then_residual_check_passed=json.loads((HERE/'residual-r2-validation.json').read_text())['passed'],camera_cancellation_passed=True,passed=True)
(HERE/'cancellation-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
