"""Freeze source/default-check only; no packager execution or output directory."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((HERE/'reuse-result.json').read_bytes());c=json.loads((HERE/'local-check-result.json').read_bytes())
assert r['passed'] and c['passed'] and c['original_child']['terminal'] and c['original_child']['returncode']==0
assert r['candidate_package_sha256']==c['package_sha256']==sha(HERE/'package-logdump.py')
assert c['pins_sha256']==sha(HERE/'Image504-pins.json')
assert c['unique_OUT_absent_at_check'] and not c['private_output_created']
assert not c['tools_storage_SDK_Git_or_device_invoked']
assert r['same_original_Popen_finally_wait_no_timeout'] and r['except_forces_passed_false']
files=['prepare.py','proof-gate.inc','package-logdump.py','method-delta.patch','Image504-pins.json',
       'reuse-result.json','local-check.py','local-check-result.json','README.md','freeze-source.py']
result=dict(schema='samurai-image504-budget-logdump-source-plan-v1',passed=True,
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in files},
    actual504_Image_sha256='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4',
    actual504_Image_bytes=59243008,rollback_saved502_sha256=r['rollback_saved502_sha256'],
    default_readonly_check_passed=True,packager_tools_executed=False,carrier_written=False,
    current_or_future502_adoption_claimed=False,provider2691_installed_or_bound=False,
    device_SDK_storage_or_Git_invoked=False,
    archive=dict(explicit_source_text_json_whitelist=files,recursive_scan=False))
(HERE/'source-delivery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,source_delivery_sha256=sha(HERE/'source-delivery.json'),
    package_sha256=sha(HERE/'package-logdump.py'),local_check_sha256=sha(HERE/'local-check-result.json'))))
