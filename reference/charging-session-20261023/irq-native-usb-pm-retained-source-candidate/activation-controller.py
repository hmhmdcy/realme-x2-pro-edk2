"""Path-corrected current activation profile; original R2 controller owns all jobs."""
from pathlib import Path
import hashlib,importlib.util,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current_stage_path_profile',HERE/'reviewer.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
pins=review.source_check()
c=review.load(pins['activation_controller']['path'],'original_current_pm_activation_controller')
original_check=c.source_check
def source_check():
 review.source_check();return original_check()
def reviewed(stage_directory,stage_fetch_directory):
 source_check();proof=review.current_stage_module()
 result=proof.review_stage(c.local(stage_directory),c.local(stage_fetch_directory))
 result['source_adapter_files']={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
  for name in ['reviewer.py','source-pins.json','activation-controller.py']}
 return result,proof.guard_stage_fields(result)
c.source_check=source_check;c.reviewed=reviewed
if __name__=='__main__':raise SystemExit(c.main())
