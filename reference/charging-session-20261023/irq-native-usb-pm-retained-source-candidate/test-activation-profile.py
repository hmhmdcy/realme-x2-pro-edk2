"""Only canonical fetch alias and the forward controller callback adaptation."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a=load(HERE/'activation-controller.py','canonical_forward_activation_profile')
r=a.review;pins=r.source_check();calls=[]
original=SimpleNamespace(fetch_raw=lambda *args:calls.append(args) or {'original_fetch_called':True})
with patch.object(r,'load',return_value=original):
 proof=r.current_stage_module()
 aliases={'update_host':copy.deepcopy(pins['stage_host']),'update_supervisor':{'sha256':'fixture-only'}}
 value=proof.fetch_raw('fixture-call',b'fixture-request',aliases,{'fixture':'original values'})
 assert value=={'original_fetch_called':True} and len(calls)==1
 assert calls[0][2]['update_host']['path']==str(r.local(pins['stage_host']['path']))
 assert calls[0][2]['update_host']['sha256']==aliases['update_host']['sha256']
 assert aliases['update_host']['path']==pins['stage_host']['path']
 bad=copy.deepcopy(aliases);bad['update_host']['path']='/unrelated/host.py'
 try:proof.fetch_raw('fixture-call',b'fixture',bad,{})
 except ValueError:pass
 else:raise AssertionError('arbitrary fetch host path accepted')
 assert len(calls)==1
projection={'fixture':'original stage projection'}
record={'stage':projection,'fixture':'current pointer gate remains in original reviewer'}
called=[]
proof=SimpleNamespace(review_stage=lambda *args:called.append(args) or copy.deepcopy(record),guard_stage_fields=lambda value:value['stage'])
with patch.object(r,'current_stage_module',return_value=proof):
 reviewed,selected=a.reviewed('/fixture-stage','/fixture-fetch')
 assert selected==projection and called==[(Path('/fixture-stage'),Path('/fixture-fetch'))]
 assert set(reviewed['source_adapter_files'])=={'reviewer.py','source-pins.json','activation-controller.py'}
 assert all(reviewed['source_adapter_files'][name]==hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in reviewed['source_adapter_files'])
 assert 'source_adapter_files' not in record
old=r.load(pins['activation_controller']['path'],'unchanged_original_controller_functions')
assert a.c.HERE==old.HERE and a.c.PRIVATE==old.PRIVATE
assert all(getattr(a.c,name).__code__.co_code==getattr(old,name).__code__.co_code for name in
 ['ssh_worker','terminal_job','start_job','bound','run','export_context'])
report=dict(passed=True,cases=2,source_path_canonicalization_only=True,
 original_current_source_pointer_gate_retained=True,original_R2_job_and_process_functions_reused=True,
 adapter_hashes_recorded_in_bound_stage_review=True,device_or_transport_accessed=False,
 tested_files={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['reviewer.py','activation-controller.py','source-pins.json','test-activation-profile.py']})
(HERE/'activation-profile-test-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':2,'device_accessed':False}))
