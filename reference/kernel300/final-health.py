"""Recheck unchanged product payloads and hardware idle state after the IPA probes."""
from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent
assert all(json.loads((HERE/f'ipa-capture-{run}-validation.json').read_text())['passed'] for run in ['r4','r5'])
module=ast.parse((HERE.parent/'kernel298/final-health.py').read_text())
code=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
code=code.replace("r/'k298-services-verified-private.json'","r/'k300-services-verified-private.json'")
code=code.replace("r/'k298-tools/final-health-private.json'","r/'k300-final-health-private.json'")
code=code.replace('report=dict(stage=298,kernel_build=298','report=dict(stage=300,kernel_build=298')
code=code.replace('four_camera_raw_cpu_isp_regression_passed=True','four_camera_raw_cpu_isp_regression_passed_on_prior298=True')
q=host.ssh('python3 -',input=code.encode(),timeout=50);(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout);report['product_hardware_isp_userspace_not_integrated']=report.pop('hardware_isp_userspace_not_integrated')
report.update(product_userspace_unchanged=True,product_uses_raw_plus_cpu_isp=True,experimental_manual_hardware_ipa_candidate_tested=True,
 signed_threaded_and_forced_isolated_ipa_modes_passed=True,full_automatic_hardware_ipa_complete=False,individual_eeprom_values_not_applied=True,
 four_camera_product_regression_not_repeated_this_stage=True)
(HERE/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['modules','rails','package_versions']},indent=2))
