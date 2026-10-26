"""Promote the exact r13/r8 inputs after installed native acceptance."""
from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel225')
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda n: json.loads((here / n).read_text())
health = read('final-health-validation.json')
assert health['current_policy_r13_library_hashes_verified']
assert health['r13_r8_camera_payload_records_verified'] == 49
assert health['taint'] == 0 and not any(health['fault_counts'].values())
assert health['experimental_full_mode_disabled'] and health['nv_sources_unchanged']
matrix = read('r13-candidate-manual-matrix-validation.json')
assert matrix['frames'] == 1024 and matrix['threaded_and_isolated_ipa_verified']
assert matrix['nine_phase_controls_restart_and_captured_source_verified_in_all_eight_cases']
installed = ['r13-system-raw-1928x1088-threaded-manual-validation.json',
             'r13-system-rgb-2296x1728-threaded-manual-validation.json']
for name in installed:
    proof = read(name)
    assert proof['frames'] == 128 and proof['installed_r13_r8_payloads_verified']
    assert proof['captured_source_cookies_and_values_match_metadata']
for flavour in ['candidate-threaded', 'candidate-isolated', 'system-threaded']:
    proof = read(f'lifecycle-r13-{flavour}-validation.json')
    assert proof['all40_requests_completed_or_cancelled']
    assert proof['no_stop_hang_or_pending_request_leak_observed']
for name in ['raw-exposure-metadata-system-r13-4608x3456-validation.json',
             'exposure-metadata-system-r13-4608x3456-validation.json']:
    proof = read(name)
    assert proof['frame_count'] == 36 and proof['maximum_metadata_conversion_error_us'] < 1
for client in ['cam', 'gstreamer']:
    assert read(f'standard-{client}-validation.json')['frame_count'] == 6
assert read('full-finish-validation.json')['experimental_full_raw_disabled']
assert read('r13-agc-control-regression-validation.json')['behavioral_assertions'] == 48

recipe = sdk / 'work/libcamera225-r13'
target = repo / 'linux-port/packages/libcamera'
lock = json.loads((target / 'source-lock.json').read_text())
assert lock['new_recipe_version'] == '99990.7.2-r11'
assert all(sha(target / n) == v for n, v in lock['source_files_sha256'].items())
assert all(sha(recipe / n) == v for n, v in lock['source_files_sha256'].items() if n != 'APKBUILD')
patches = [('0018-simple-manual-exposure-controls.patch', 'candidate-source-validation.json'),
           ('0019-ipc-threaded-start-outputs.patch', 'generator-source-validation.json'),
           ('0020-soft-invalid-statistics-hold.patch', 'statistics-hold-source-validation.json')]
for name, proof_name in patches:
    assert sha(recipe / name) == read(proof_name)['patch_sha256']
assert b'pkgrel=13\n' in (recipe / 'APKBUILD').read_bytes()
assert len(list(recipe.glob('*.patch'))) == 20
config = sdk / 'work/samurai-camera-config225-r13'
product = repo / 'linux-port/packages/samurai-camera-config'
assert b'pkgrel=8\n' in (config / 'APKBUILD').read_bytes()
for p in product.iterdir():
    if p.is_file() and p.name not in ['README.md', 'APKBUILD']:
        assert p.read_bytes() == (config / p.name).read_bytes()
manifest = json.loads((private / 'camera-forward-repo-r13/package-manifest.json').read_text())
assert len(manifest['packages']) == 13
assert all(sha(private / 'camera-forward-repo-r13' / p['file']) == p['sha256'] for p in manifest['packages'])
deployment_path = repo / 'linux-port/camera/deployment-lock.json'
deployment = json.loads(deployment_path.read_text())
assert deployment['framework_version'] == '99990.7.2-r11'
assert deployment['camss_module_sha256'] == 'fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
kernel_lock = repo / 'linux-port/camera/kernel/source-lock.json'
kernel_lock_sha = sha(kernel_lock)

for name in ['APKBUILD'] + [n for n, _ in patches]:
    (target / name).write_bytes((recipe / name).read_bytes())
lock.update(stage=225, original_recipe_version='99990.7.2-r11', new_recipe_version='99990.7.2-r13',
            original_seventeen_patches_and_all_existing_inputs_preserved=True,
            additional_stage225_patches=[n for n, _ in patches], manual_api_not_implemented=False,
            manual_api_scope='CPU software ISP: independent exposure/gain Auto/Manual, AeEnable preprocessing, start controls and captured-source metadata',
            threaded_start_output_arguments_forwarded=True, invalid_statistics_hold_latest_prepared_targets=True,
            source_files_sha256={p.name: sha(p) for p in target.iterdir()
                                 if p.is_file() and p.name not in ['README.md', 'source-lock.json']})
(target / 'source-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
(recipe / 'source-lock.json').write_bytes((target / 'source-lock.json').read_bytes())
(product / 'APKBUILD').write_bytes((config / 'APKBUILD').read_bytes())
deployment.update(stage=225, kernel_changed=False, framework_version='99990.7.2-r13',
    configuration_version='0.1.0-r8', camera_framework_deployment_stage=225,
    built_packages=[{k: p[k] for k in ['name', 'version', 'file', 'sha256', 'bytes']} for p in manifest['packages']],
    runtime_evidence='../../reference/kernel225/r13-system-raw-1928x1088-threaded-manual-validation.json',
    installed_rgb_control_evidence='../../reference/kernel225/r13-system-rgb-2296x1728-threaded-manual-validation.json',
    candidate_manual_matrix_evidence='../../reference/kernel225/r13-candidate-manual-matrix-validation.json',
    standard_client_evidence='../../reference/kernel225/standard-gstreamer-validation.json',
    rollback_evidence='../../reference/kernel225/r13-package-install-validation.json',
    package_install_evidence='../../reference/kernel225/r13-package-install-validation.json',
    installed_stop_reconfigure_evidence='../../reference/kernel225/lifecycle-r13-system-threaded-validation.json',
    experimental_full_raw_evidence='../../reference/kernel225/raw-exposure-metadata-system-r13-4608x3456-validation.json',
    experimental_full_rgb_evidence='../../reference/kernel225/exposure-metadata-system-r13-4608x3456-validation.json',
    final_health_evidence='../../reference/kernel225/final-health-validation.json',
    stage224_historical_metadata_conversion_verified_frames=200, metadata_conversion_verified_frames=328,
    installed_stage225_default_raw_metadata_frames=128, installed_stage225_default_rgb_metadata_frames=128,
    installed_stage225_experimental_full_raw_metadata_frames=36, installed_stage225_experimental_full_rgb_metadata_frames=36,
    stage225_candidate_manual_frames=1024, stage225_installed_manual_frames=256,
    stage225_installed_lifecycle_completed_requests=20, stage225_installed_lifecycle_cancelled_requests=20,
    manual_exposure_api_not_implemented=False, manual_exposure_api_cpu_software_path_verified=True,
    independent_auto_manual_ae_enable_priority_ignore_freeze_resume_and_start_verified=True,
    captured_source_cookie_not_current_request_echo=True, threaded_start_output_arguments_forwarded=True,
    invalid_statistics_hold_latest_prepared_targets=True, r12_rejected_algorithm_regression_retained=True,
    kernel_image_boot_dtb_and_all_modules_unchanged_in_stage225=True,
    rollback_framework='99990.7.2-r11', rollback_configuration='0.1.0-r6',
    rollback_keeps_current_fae1_camss_and_e49_sensor_modules=True)
deployment_path.write_text(json.dumps(deployment, indent=2) + '\n')
path = repo / 'linux-port/camera/libcamera/source-lock.json'
d = json.loads(path.read_text())
d.update(installed_framework_version='99990.7.2-r13', deployment_stage=225,
    deployment_evidence='../../../reference/kernel225/r13-package-install-validation.json',
    capture_control_association_evidence='../../../reference/kernel225/r13-system-raw-1928x1088-threaded-manual-validation.json',
    stage225_additional_patches_sha256={name: sha(target / name) for name, _ in patches},
    manual_exposure_api_not_implemented=False, manual_api_cpu_software_path_verified=True,
    physical_optical_delay_not_calibrated=True)
path.write_text(json.dumps(d, indent=2) + '\n')
assert sha(kernel_lock) == kernel_lock_sha
report = dict(stage=225, canonical_r13_r8_recipes_and_framework_deployment_locks_promoted=True,
    prior17_patches_tuning_and_all_full_feature_subpackages_preserved=True,
    kernel_source_lock_unchanged_from223=True, all13_package_hashes_verified=True,
    r11_r6_rollback_retained_and_keeps_fae1_e49=True, full_peripheral_goal_active=True)
(here / 'package-integration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
