"""Only new delegated source pin and cached CDP/Full acceptance; no collection."""
from pathlib import Path
import ast,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('adopt_cdp_source_binding',HERE/'adopt.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
device,src=m.load_device()
assert sha(src['postboot_device'])=='be1b56a1fe38fd46cd8c58e303a8d98c38b6fd154b8db0a32231095b97418eea'
old=HERE/'before-cdp-profile/source-pins.json';a=json.loads(old.read_bytes());b=json.loads((HERE/'source-pins.json').read_bytes())
a['postboot_device']['sha256']=b['postboot_device']['sha256'];assert a==b
path=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-03-private/stdout-private.json')
report=json.loads(path.read_bytes());assert report['result']['passed'] is False
verdict=device.check_gauge(report['raw'])
assert verdict['startup500_descriptor_and_native500_preserved'] is True
assert verdict['source_type']=='CDP' and verdict['source_budget_ua']==1500000 and verdict['hardware_input_ua']==900000
assert verdict['SDP_hardware500_observed'] is False
t=device.parse_kv(report['raw']['telemetry_after']);assert t['logical_full']==1 and device.healthy_charge_mode(t)
code=m.payload({},src);ast.parse(code)
assert code.startswith(b'import sys\nif sys.flags.optimize:raise RuntimeError(')
root_test=HERE.parents[1]/'charging-management-20261023/image501-postboot-readonly/test-result.json'
result={'passed':True,'scope':'source-pin/delegation delta only, cached r1-03 is not relabeled a new runtime pass',
 'delegate_device_sha256':sha(src['postboot_device']),'root_new_test_receipt_sha256':sha(root_test.read_bytes()),
 'cached_input_sha256':sha(path.read_bytes()),'cached_mode':verdict,'cached_Full_mode_healthy':True,
 'old_actual_report_still_failed':True,'adopt_source_unchanged_sha256':sha((HERE/'adopt.py').read_bytes()),
 'files':{n:sha((HERE/n).read_bytes()) for n in ['source-pins.json','test-cdp-binding.py']},
 'old_three_and_optimize_cases_not_rerun':True,'no_network_device_guard_or_runtime_identity_generated':True}
(HERE/'test-cdp-binding-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'source_mode':'CDP','actual_hardware_input_ua':verdict['hardware_input_ua'],'actual_adoption_executed':False}))
