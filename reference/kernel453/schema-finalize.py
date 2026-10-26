"""Attach cached diagnostics/log fingerprints without repeating completed checks."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel453/schema')

def read(name):
    return json.loads((HERE / name).read_text())

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

logs = [(PRIVATE / (label + '-dtc-private.log')).read_bytes() for label in ['baseline', 'candidate']]
assert logs[0] == logs[1]
dt = read('schema-validation.json')
dt.update(scope='private candidate structural/dependency validation only; public binding metadata incomplete',
          original_public_binding_submission_ready=False, live_enablement_ready=False,
          private_candidate_structural_validation_passed=True,
          baseline_and_candidate_dtc_diagnostics_identical=True,
          dtc_diagnostic_sha256=hashlib.sha256(logs[0]).hexdigest())
write('schema-validation.json', dt)

compat = read('schema-core-compatibility.json')
callbacks = json.loads((PRIVATE / 'subdev-release-callbacks-private.json').read_text())
assert len(callbacks) == 2 and all('devnode' not in function for function in callbacks.values())
compat.update(callback_bodies_need_transitive_review=False,
              manual_helper_review='v4l2_get_subdevdata reads sd->dev_priv; other callback only container_of and kfree',
              current_tree_only_no_out_of_tree_or_runtime_claim=True)
write('schema-core-compatibility.json', compat)

image = read('schema-image-inspection.json')
image.update(complete_cached_object_set_not_attested_as_k363=True,
             absolute_source_and_output_paths_in_cached_commands=True,
             safe_image_target_may_rebuild_broader_dependencies=True)
write('schema-image-inspection.json', image)

proof = read('schema-pm-proof.json')
for label in ['original', 'candidate']:
    for kind in ['compile', 'run']:
        log = PRIVATE / ('release-order-' + label + '-' + kind + '-private.log')
        proof['runs'][label][kind + '_log_sha256'] = sha(log)
        proof['runs'][label][kind + '_log_bytes'] = log.stat().st_size
proof.update(public_patch='0064-media-v4l2-core-clear-devnode-before-subdev-release.patch',
             public_patch_sha256=sha(HERE / '0064-media-v4l2-core-clear-devnode-before-subdev-release.patch'),
             built_in_core_or_image_updated=False)
write('schema-pm-proof.json', proof)

build = read('module-build-validation.json')
driver_sha = sha(HERE / 'bu64253.c')
module_sha = sha(PRIVATE.parent / 'bu64253-intree-r2.ko')
assert driver_sha == build['driver_source_sha256']
assert module_sha == build['module_sha256']
report = dict(stage=453, scope='final cached-result attachment and unchanged asset checks',
              no_tests_repeated=True, driver_source_sha256=driver_sha, module_sha256=module_sha,
              public_binding_sha256=sha(HERE / 'rohm,bu64253.yaml'),
              public_dt_draft_sha256=sha(HERE / 'samurai-bu64253-lenses.dtsi'),
              driver_and_built_module_unchanged=True, actual_image_build_performed=False,
              sdk_or_phone_accessed=False, files_stable_for_parent_mirror=True)
write('schema-final-validation.json', report)
print(json.dumps(report, indent=2))
