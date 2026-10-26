"""Freeze the reviewed plan and actual default local check, no execution."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((HERE/'prepare-result.json').read_bytes())
c=json.loads((HERE/'local-check-result.json').read_bytes())
assert p['passed'] and c['passed'] and c['original_child']['terminal'] and c['original_child']['returncode']==0
assert p['candidate_runner_sha256']==c['runner_sha256']==sha(HERE/'run-504.py')
assert p['metadata_sha256']==sha(HERE/'metadata-proof.py')
assert c['output_absent_at_check'] and not c['private_output_created']
assert not c['storage_or_build_or_device_invoked']
files=['prepare-runner.py','prepare-result.json','run-504.py','metadata-proof.py','runner-delta.patch',
       'local-check.py','local-check-result.json','README.md','freeze-plan.py']
result=dict(schema='samurai-private-image504-budget-fence-plan-delivery-v1',passed=True,
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
    actual_base='gauge-image502-notify-01',new_sources=p['new_DWC_sources'],identity='#504',
    default_local_check_passed=True,unique_private_output_absent_at_check=True,
    actual_Kbuild_eight_then_Image_planned=True,raw_GCC_objects_imported=False,
    Image_build_executed=False,storage_or_SDK_or_device_or_Git_invoked=False,
    archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False))
(HERE/'plan-delivery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,plan_delivery_sha256=sha(HERE/'plan-delivery.json'),
    runner_sha256=sha(HERE/'run-504.py'),local_check_sha256=sha(HERE/'local-check-result.json'))))
