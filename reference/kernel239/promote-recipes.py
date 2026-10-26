"""Promote the already installed, fully built r15/r10 recipes with backups."""
from pathlib import Path
import hashlib
import json
import shutil

R = Path(__file__).resolve().parent
ROOT = R.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel239')
health = json.loads((R / 'final-health-validation.json').read_text())
assert health['installed_r15_r10'] and health['default_runtime_two_start_diagnostic_and_policy_reload_verified']
qa = json.loads((R / 'r15-complete-host-qa-validation.json').read_text())
assert all(qa[key] for key in ['all_original_features_verified', 'all13_apk_signatures_verified',
    'all_five_ipa_signatures_verified_against_current_core', 'arm_user_entrypoints_checked'])
backup = P / 'public-recipes-before239-private'
assert not backup.exists()
backup.mkdir(mode=0o700)
records = {}
for name in ['libcamera', 'samurai-camera-config']:
    source = R / 'recipes' / name
    target = ROOT / 'linux-port/packages' / name
    shutil.copytree(target, backup / name)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}
    for path in source.iterdir():
        assert path.is_file() and path.suffix not in ['.pem', '.key']
        shutil.copy2(path, target / path.name)
    records[name] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
    if name == 'libcamera':
        assert sum(p.suffix == '.patch' for p in source.iterdir()) == 22
        assert all(records[name][n] == digest for n, digest in before.items() if n.endswith(('.patch', '.yaml', '.desktop')))
        lock_path = target / 'source-lock.json'
        lock = json.loads(lock_path.read_text())
        lock.update(stage=239, original_recipe_version='99990.7.2-r13', new_recipe_version='99990.7.2-r15',
                    source_files_sha256=records[name],
                    additional_stage238_patches=['0021-imx319-gain-helper.patch'],
                    additional_stage239_patches=['0022-soft-initial-parameters.patch'],
                    imx319_gain_formula='1024/(1024-code)', initial_ipa_parameters_snapshotted_after_start=True,
                    initial_combined_matrix_published=True, black_level_and_tuning_not_changed=True,
                    actual_processing_frame_sequence_timestamp_logged=True,
                    original_twenty_patch_and_all_tuning_inputs_preserved=True,
                    complete_thirteen_packages_built_seven_runtime_packages_installed=True,
                    all_five_ipa_signatures_verified=True, default_stop_start_twice_initial_parameters_verified=True,
                    rear_scene_optical_response_and_colour_still_open=True)
        lock_path.write_text(json.dumps(lock, indent=2) + '\n')
    else:
        (target / 'source-lock.json').write_text(json.dumps(dict(stage=239, config_version='0.1.0-r10',
            pins_libcamera_version='99990.7.2-r15', source_files_sha256=records[name],
            cpu_system_heap_configuration_unchanged=True, no_private_keys=True), indent=2) + '\n')
report = dict(stage=239, previous_public_recipes_privately_backed_up=True,
              frozen_r15_r10_recipes_promoted=True, source_files_sha256=records,
              old_twenty_patches_and_tuning_preserved=True, source_locks_updated=True,
              rootfs_kernel_integration_not_claimed=True)
(R / 'recipe-promotion-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'stage':239, 'recipe_promotion_passed':True, 'libcamera_patches':22}))
