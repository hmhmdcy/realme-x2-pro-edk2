"""Recheck product payloads and resource health; don't replay prior camera tests."""
from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent
for name in ['factory-bls-capture-validation.json','factory-scene-capture-validation.json','eeprom-read-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
# Extract the verified read/check code, not its old prerequisites or old report writer.
module=ast.parse((HERE.parent/'kernel298/final-health.py').read_text())
code=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=code.replace("r/'k298-services-verified-private.json'","r/'k299-services-verified-private.json'")
code=code.replace("r/'k298-tools/final-health-private.json'","r/'k299-tools/final-health-private.json'")
code=code.replace('report=dict(stage=298,kernel_build=298','report=dict(stage=299,kernel_build=298')
code=code.replace('four_camera_raw_cpu_isp_regression_passed=True','four_camera_raw_cpu_isp_regression_passed_on_prior298=True')
q=host.ssh('python3 -',input=code.encode(),timeout=50)
(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout)
assert json.loads((HERE/'inline-capture-r3-validation.json').read_text())['passed']
report['product_hardware_isp_userspace_not_integrated']=report.pop('hardware_isp_userspace_not_integrated')
report.update(product_userspace_unchanged=True,product_uses_raw_plus_cpu_isp=True,inline_candidate_not_installed=True,
 experimental_inline_handler_real_requests_passed=True,
 factory_bls_reference_physically_tested=True,individual_eeprom_full_layout_and_checksum_unverified=True,individual_eeprom_values_not_applied=True,
 four_camera_raw_cpu_isp_regression_not_repeated_this_stage=True,full_hardware_ipa_integration_complete=False)
(HERE/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['modules','rails','package_versions']},indent=2))
