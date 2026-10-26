"""Exercise the actual new prior-boot closure gate; no device access."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('recovered_precharge_gate',HERE/'check-recovered-precharge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
proof=dict(original_boot='075f658d-4cb9-4268-872e-5ec281d99e55',
    recovery_boot='a2c4c6f2-1652-4995-803b-e3a12f455478',
    original_records_audited=True,actual_records=1299,
    file_sha256={name:hashlib.sha256(name.encode()).hexdigest() for name in m.REQUIRED_FILES})
row=dict(boot=proof['recovery_boot'],guard_boot=proof['recovery_boot'],
    file_sha256=copy.deepcopy(proof['file_sha256']),active_original_processes=[],
    result=dict(passed=True,stop_confirmed=True,auto_restored=True,precharge_seen=True,
                constant_current_seen=True,error=None,cleanup_error=None),
    worker_terminal=dict(returncode=0,observation_passed=True),
    cpu_terminal=dict(all_joined=True,parts=[dict(pid=pid,joined=True,returncode=0) for pid in [7505,7506,7507]]),
    behaviour='auto',service_lock_free=True)
cases=[]
def case(name,change):
    p=copy.deepcopy(proof);r=copy.deepcopy(row);change(p,r);cases.append((name,p,r))
case('valid_prior_boot_without_supervisor_terminal',lambda p,r:None)
case('same_original_boot',lambda p,r:p.update(original_boot=p['recovery_boot']))
case('changed_runtime_boot',lambda p,r:r.update(boot=p['original_boot']))
case('stale_guard',lambda p,r:r.update(guard_boot=p['original_boot']))
case('audit_missing',lambda p,r:p.update(original_records_audited=False))
case('wrong_record_count',lambda p,r:p.update(actual_records=1))
case('changed_sample_file',lambda p,r:r['file_sha256'].update({'samples-private.jsonl':'0'*64}))
case('missing_original_source',lambda p,r:p['file_sha256'].pop('worker.py'))
case('live_original_worker',lambda p,r:r.update(active_original_processes=[7492]))
case('observation_failed',lambda p,r:r['result'].update(passed=False))
case('cleanup_unknown',lambda p,r:r['result'].update(auto_restored=False))
case('cleanup_error',lambda p,r:r['result'].update(cleanup_error='io'))
case('worker_failed',lambda p,r:r['worker_terminal'].update(returncode=1))
case('worker_unverified',lambda p,r:r['worker_terminal'].update(observation_passed=False))
case('load_not_joined',lambda p,r:r['cpu_terminal']['parts'][0].update(joined=False))
case('load_failed',lambda p,r:r['cpu_terminal']['parts'][0].update(returncode=-15))
case('wrong_original_load',lambda p,r:r['cpu_terminal']['parts'][0].update(pid=99))
case('current_inhibit',lambda p,r:r.update(behaviour='inhibit-charge'))
case('current_owner_busy',lambda p,r:r.update(service_lock_free=False))
for name,p,r in cases:
    try:
        answer=m.check_recovered_precharge(p,r)
    except (ValueError,KeyError):
        assert name!='valid_prior_boot_without_supervisor_terminal',name
    else:
        assert name=='valid_prior_boot_without_supervisor_terminal',name
        assert answer['original_boot_ended'] and not answer['supervisor_terminal_fabricated']
result=dict(passed=True,cases=len(cases),actual_function='check_recovered_precharge',
            source_sha256=hashlib.sha256((HERE/'check-recovered-precharge.py').read_bytes()).hexdigest(),
            device_accessed=False,original_supervisor_result_created=False)
(HERE/'recovered-precharge-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
