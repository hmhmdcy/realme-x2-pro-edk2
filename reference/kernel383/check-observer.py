"""Minimal IT/stack regression for choosing a nonperturbing observation range."""
from pathlib import Path
import importlib.util,json
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_SP
import unicorn
HERE=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('fm',HERE/'firmware-model.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
rows=[]
for kind in ['none','global','bounded-unused']:
 m=f.Machine()
 if kind=='global':m.u.hook_add(UC_HOOK_MEM_READ,lambda *args:None)
 if kind=='bounded-unused':m.u.hook_add(UC_HOOK_MEM_READ,lambda *args:None,begin=f.DATA+0x30000,end=f.DATA+0x31000)
 m.call(0xf21e,f.DATA,phase='original-empty-cdm-array-free')
 rows.append(dict(kind=kind,stack_delta=m.u.reg_read(UC_ARM_REG_SP)-(f.STACK+0xf0000),normal_return_sequence='0xf274' in m.free_trace))
assert rows==[dict(kind='none',stack_delta=0,normal_return_sequence=True),dict(kind='global',stack_delta=-32,normal_return_sequence=False),dict(kind='bounded-unused',stack_delta=0,normal_return_sequence=True)]
report=dict(stage=383,unicorn_version=unicorn.__version__,original_thumb_it_function_executed=True,empty_memory_callback=True,
 cases=rows,global_read_hook_changes_execution_and_is_rejected=True,model_observer_failure_not_hardware_failure=True,
 bounded_observer_still_requires_full_output_differential_validation=True,no_phone_operations=True,passed=True)
(HERE/'observer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
