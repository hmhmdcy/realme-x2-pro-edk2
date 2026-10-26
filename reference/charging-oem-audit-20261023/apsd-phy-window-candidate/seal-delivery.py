from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_bytes())
b=json.loads((HERE/'build-result.json').read_bytes())
m=json.loads((HERE/'candidate-manifest.json').read_bytes())
assert t['passed'] and b['passed'] and b['shared_source_unchanged'] and b['shared_config_unchanged']
assert not b['diagnostic_lines']
for r in [t,b,m]:
 for n,v in r['files'].items():assert sha(HERE/n)==v,n
source=(HERE/'phy-qcom-snps-femto-v2.c').read_text()
assert 'EXPORT_SYMBOL' not in source
functions=(HERE/'window-functions.c.txt').read_text()
assert not any(n in functions for n in ['phy_init(', 'reset_control_', 'clk_bulk_', 'regulator_bulk_', 'pm_runtime_resume', 'pm_runtime_get_sync'])
names=['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','phy-window.patch',
 'window-functions.c.txt','README.md','make-candidate.py','candidate-manifest.json',
 'prepare-tests.py','test-window.c','run-tests.py','function-manifest.json','test-result.json',
 'build-private.py','build-result.json','seal-delivery.py']
d=dict(passed=True,status='offline_component_candidate',source_commit=m['source_commit'],
 patch_sha256=sha(HERE/'phy-window.patch'),actual_function_groups=t['group_count'],actual_functions=t['actual_functions'],
 object_targets=['drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o'],
 files={n:sha(HERE/n) for n in names},
 automatic_consumer=False,exported_api=False,uapi_changed=False,
 no_init_reset_resume_for_detection=True,exact_old_masked_restore=True,
 initialized_active_dwc_window_caller_contract=True,independent_active_only_provider_pm_reference=True,
 failure_retains_owner_and_originals=True,requires_bound_lifetime_and_work_join=True,
 lockdep_or_hardware_validated=False,shared_source_modified=False,sdk_invoked=False,
 phone_accessed=False,ssh_executed=False,deployed=False,image_or_package_built=False)
(HERE/'delivery.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
