"""Bind only the already completed offline candidate checks; does not run them."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tests = json.loads((HERE / 'test-result.json').read_text())
build = json.loads((HERE / 'build-result.json').read_text())
candidate = json.loads((HERE / 'candidate-manifest.json').read_text())
baseline = json.loads((HERE / 'baseline.json').read_text())
assert tests['passed'] and build['passed']
assert tests['groups_count'] == 13 and tests['actual_functions'] == 20
assert tests['mutex_destroy_after_usb_del_gadget']
assert build['shared_source_unchanged'] and build['shared_config_unchanged']
assert not build['diagnostic_lines']
for row in baseline['files']:
    assert sha(HERE / 'baseline' / row['file']) == row['sha256']
for name, digest in candidate['files'].items():
    assert sha(HERE / name) == digest == tests['sources'][name]
for name, digest in build['sources'].items():
    assert sha(HERE / name) == digest
for name, digest in tests['fixtures'].items():
    assert sha(HERE / name) == digest
files = ['core.h', 'core.c', 'gadget.c', 'dwc-window.patch', 'README.md',
         'baseline.json', 'candidate-manifest.json', 'test-result.json',
         'build-result.json', 'make-candidate.py', 'window-functions.c.txt',
         'prepare-tests.py', 'test-window.c', 'run-tests.py', 'build-private.py',
         'seal-delivery.py']
result = dict(
    passed=True, status='offline_component_candidate',
    source_commit=baseline['source_commit'],
    patch_sha256=sha(HERE / 'dwc-window.patch'),
    actual_function_groups=13, actual_functions=20,
    object_targets=[p['target'] for p in build['phases'] if p['target'].endswith('.o')],
    files={name: sha(HERE / name) for name in files},
    automatic_consumer=False, exported_api=False, uapi_changed=False,
    pd_or_eud_state_assumed=False, pmic_or_phy_operations_added=False,
    requires_same_kernel_internal_owner=True,
    requires_owner_bound_lifetime_and_work_join=True,
    lockdep_or_hardware_validated=False,
    shared_source_modified=False, sdk_invoked=False, phone_accessed=False,
    ssh_executed=False, deployed=False, image_or_package_built=False,
)
(HERE / 'delivery.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
