"""Freeze explicitly named software-budget source/test evidence, no build/I/O."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=json.loads((HERE/'source-result.json').read_bytes())
test=json.loads((HERE/'test-result.json').read_bytes())
assert source['passed'] and test['passed'] and test['actual_result']['actual_function_cases']==20
for name,pin in source['candidate'].items():assert sha(HERE/name)==pin,name
for name,pin in source['extracts'].items():assert sha(HERE/name)==pin,name
for name,pin in test['tested_files'].items():assert sha(HERE/name)==pin,name
assert all(c['terminal'] is True and c['returncode']==0 for c in test['commands'])
assert test['actual_result']['real_pthread_block_and_cancel_join']
assert test['actual_result']['old_transient_reauthorization_reproduced']
assert test['actual_result']['new_join_before_provider_resume']
private=Path('E:/edk2-samurai-out/charging-management-20261023/readonly501-usb-pm-01-private/stdout-private.json')
assert sha(private)=='ff5349914676010add245f9ac2348d3801cdd73d5acc1233abc9cc9c690c7e4f'
raw=json.loads(private.read_bytes())
assert raw['same_adopted501'] and not raw['control_writes'] and not raw['PM_reboot_test_started']
assert raw['controller']['power']['control']=='on' and raw['controller']['power']['runtime_status']=='active'
assert raw['controller']['power']['runtime_suspended_time']=='0'
assert raw['provider']['power']['runtime_status']=='unsupported'
runtime=dict(schema='samurai-dwc-budget-fence-existing-runtime-premise-v1',
    source_raw_path=str(private),source_raw_sha256=sha(private),source_captured_by_root=True,
    same_adopted501=True,controller_power={k:raw['controller']['power'][k] for k in
        ['control','runtime_status','runtime_suspended_time','autosuspend_delay_ms']},
    provider_runtime_status='unsupported',actual_PM_or_reboot_test=False,
    current_premise_only_not_kernel_admission_guard=True,auto_or_direct_complete_supported=False,
    collector_or_device_accessed_by_this_leaf=False)
(HERE/'runtime-evidence.json').write_text(json.dumps(runtime,indent=2)+'\n',encoding='utf-8',newline='\n')
files=['prepare.py','budget-work.c.inc','core.c','core.h','gadget.c','budget-fence.patch',
    'actual-budget-core.inc','actual-budget-gadget.inc','actual-old-worker.inc','actual-old-pm.inc','actual-provider.inc',
    'source-result.json','test-budget.c','run-tests.py','test-result.json',
    'run-tests-attempt01.py.inc','test-attempt-01-result.json','runtime-evidence.json','README.md','freeze.py']
delivery=dict(schema='samurai-dwc-vbus-budget-fence-delivery-v1',passed=True,
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
    baseline=source['baseline'],candidate=source['candidate'],new_actual_function_cases=20,
    real_blocked_worker_pthread_join_tested=True,old_runtime_prepare_complete_remove_unchanged=True,
    current_runtime_on_active_DEVICE_native_PSY_scope=True,auto_or_direct_complete_supported=False,
    paired_provider_first_module_sha256='2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448',
    first_compile_only_failure_preserved=True,old_suites_rerun=False,
    kernel_object_or_Image_build_run=False,storage284_or_SDK_Git_or_device_accessed=False,
    actual_PM_or_r5_or_icon_root_cause_verified=False,
    archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False,ELF_or_raw_logs_in_public_leaf=False))
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),source=source['candidate'],test_sha256=sha(HERE/'test-result.json'))))
