"""Seal the R2 teardown-only evidence without executing another test/build."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'apsd-dwc-window-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tests = json.loads((HERE / 'test-result.json').read_text())
build = json.loads((HERE / 'build-result.json').read_text())
candidate = json.loads((HERE / 'candidate-manifest.json').read_text())
assert tests['passed'] and tests['groups_count'] == 5 and not tests['original_13_groups_rerun']
assert tests['changed_actual_functions'] == ['dwc3_gadget_pullup']
assert tests['unchanged_actual_functions'] == 19
assert build['passed'] and not build['diagnostic_lines']
assert build['shared_source_unchanged'] and build['shared_config_unchanged']
for name, digest in candidate['files'].items():
    assert sha(HERE / name) == digest == tests['sources'][name]
for name, digest in build['sources'].items():
    assert sha(HERE / name) == digest
for name, digest in tests['fixtures'].items():
    assert sha(HERE / name) == digest
assert sha(HERE / 'r1-failure-review.json') == tests['independent_review_sha256']
for name in ['core.c', 'core.h', 'window-functions.c.txt']:
    assert sha(HERE / name) == sha(R1 / name)
original = json.loads((R1 / 'delivery.json').read_text())
for name, digest in original['files'].items():
    assert sha(R1 / name) == digest
files = ['core.h','core.c','gadget.c','dwc-window.patch','r1-to-r2.patch','README.md',
    'candidate-manifest.json','baseline.json','make-candidate.py','window-functions.c.txt',
    'prepare-tests.py','run-teardown-tests.py','test-teardown.c','tested-functions.inc',
    'tested-functions.json','tested-types.inc','build-private.py','test-result.json',
    'build-result.json','r1-failure-review.json','seal-delivery.py']
result = dict(passed=True, revision=2, status='offline_component_candidate',
    patch_sha256=sha(HERE / 'dwc-window.patch'), delta_from_r1_sha256=sha(HERE / 'r1-to-r2.patch'),
    files={name:sha(HERE/name) for name in files},
    r1_delivery_sha256=sha(R1/'delivery.json'), r1_known_default_teardown_regression=True,
    r1_four_object_build_sha256=sha(R1/'build-result.json'), original_13_groups_rerun=False,
    new_actual_function_groups=5, unchanged_actual_functions=19, changed_actual_functions=['dwc3_gadget_pullup'],
    new_object_targets=['drivers/usb/dwc3/gadget.o'],
    automatic_consumer=False, exported_api=False, uapi_changed=False,
    pd_or_eud_state_assumed=False, pmic_or_phy_operations_added=False,
    requires_same_kernel_internal_owner=True, requires_owner_bound_lifetime_and_work_join=True,
    lockdep_or_hardware_validated=False, frozen_r1_modified=False,
    shared_source_modified=False, sdk_invoked=False, phone_accessed=False,
    ssh_executed=False, deployed=False, image_or_package_built=False)
(HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
