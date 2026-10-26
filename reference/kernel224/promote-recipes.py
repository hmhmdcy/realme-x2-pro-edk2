"""Promote only the r11/r6 sources that passed installed native regression."""
from pathlib import Path
import hashlib,json,shutil

here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel224')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
health=json.loads((here/'final-health-validation.json').read_text())
assert health['current_policy_r11_library_hashes_verified'] and health['r11_r6_camera_payload_records_verified']==49
assert health['taint']==0 and not any(health['fault_counts'].values())
for name in ['r11-candidate-native-validation.json','r11-installed-native-validation.json']:
 proof=json.loads((here/name).read_text());assert proof['capture_frames']==128 and proof['threaded_and_isolated_ipa_verified']
for flavour in ['candidate-threaded','candidate-isolated','system-threaded']:
 proof=json.loads((here/f'lifecycle-r11-{flavour}-validation.json').read_text())
 assert proof['all40_requests_completed_or_cancelled'] and proof['no_stop_hang_or_pending_request_leak_observed']
for name in ['raw-exposure-metadata-system-r11-4608x3456-validation.json','exposure-metadata-system-r11-4608x3456-validation.json']:
 proof=json.loads((here/name).read_text());assert proof['frame_count']==36 and proof['maximum_metadata_conversion_error_us']<1
assert json.loads((here/'full-finish-validation.json').read_text())['experimental_full_raw_disabled']
for client in ['cam','gstreamer']:assert json.loads((here/f'standard-{client}-validation.json').read_text())['frame_count']==6

recipe=sdk/'work/libcamera224-r11';target=repo/'linux-port/packages/libcamera'
lock=json.loads((target/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r8'
assert all(sha(recipe/name)==digest and sha(target/name)==digest for name,digest in lock['source_files_sha256'].items() if name!='APKBUILD')
patches=[('0015-simple-raw-only-statistics.patch','candidate-source-validation.json'),
         ('0016-simple-stop-live-requests.patch','stop-fix-source-validation.json'),
         ('0017-simple-capture-cancel-status.patch','cancel-status-source-validation.json')]
for name,proof_name in patches:
 assert sha(recipe/name)==json.loads((here/proof_name).read_text())['patch_sha256']
assert b'pkgrel=11\n' in (recipe/'APKBUILD').read_bytes()
for name in ['APKBUILD']+[name for name,_ in patches]:shutil.copyfile(recipe/name,target/name)
lock.update(stage=224,original_recipe_version='99990.7.2-r8',new_recipe_version='99990.7.2-r11',
 original_fourteen_patches_and_all_existing_inputs_preserved=True,
 additional_stage224_patches=[name for name,_ in patches],
 cpu_raw_only_statistics_auto_controls_and_metadata=True,raw_only_no_rgb_dma_outputs=True,
 stop_cleanup_uses_live_request_ownership=True,capture_cancel_status_propagated_to_user_outputs=True,
 manual_api_not_implemented=True,
 source_files_sha256={p.name:sha(p) for p in target.iterdir() if p.is_file() and p.name not in ['README.md','source-lock.json']})
(target/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
shutil.copyfile(target/'source-lock.json',recipe/'source-lock.json')
config=sdk/'work/samurai-camera-config224-r11';product=repo/'linux-port/packages/samurai-camera-config'
assert b'pkgrel=6\n' in (config/'APKBUILD').read_bytes()
for p in product.iterdir():
 if p.is_file() and p.name not in ['README.md','APKBUILD']:assert p.read_bytes()==(config/p.name).read_bytes()
shutil.copyfile(config/'APKBUILD',product/'APKBUILD')

manifest=json.loads((private/'camera-forward-repo-r11/package-manifest.json').read_text());assert len(manifest['packages'])==13
assert all(sha(private/'camera-forward-repo-r11'/p['file'])==p['sha256'] for p in manifest['packages'])
path=repo/'linux-port/camera/deployment-lock.json';d=json.loads(path.read_text())
assert d['framework_version']=='99990.7.2-r8' and d['camss_module_sha256']=='fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
d.update(stage=224,kernel_changed=False,framework_version='99990.7.2-r11',configuration_version='0.1.0-r6',camera_framework_deployment_stage=224,
 built_packages=[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in manifest['packages']],
 runtime_evidence='../../reference/kernel224/r11-installed-native-validation.json',
 standard_client_evidence='../../reference/kernel224/standard-gstreamer-validation.json',
 rollback_evidence='../../reference/kernel224/r11-package-install-validation.json',
 package_install_evidence='../../reference/kernel224/r11-package-install-validation.json',
 installed_stop_reconfigure_evidence='../../reference/kernel224/lifecycle-r11-system-threaded-validation.json',
 experimental_full_raw_evidence='../../reference/kernel224/raw-exposure-metadata-system-r11-4608x3456-validation.json',
 experimental_full_rgb_evidence='../../reference/kernel224/exposure-metadata-system-r11-4608x3456-validation.json',
 final_health_evidence='../../reference/kernel224/final-health-validation.json',
 stage223_historical_metadata_conversion_verified_frames=164,metadata_conversion_verified_frames=200,
 installed_stage224_default_raw_metadata_frames=64,installed_stage224_default_rgb_metadata_frames=64,
 installed_stage224_experimental_full_raw_metadata_frames=36,installed_stage224_experimental_full_rgb_metadata_frames=36,
 stage224_installed_lifecycle_completed_requests=20,stage224_installed_lifecycle_cancelled_requests=20,
 raw_only_cpu_statistics_and_automatic_exposure_gain_metadata=True,raw_only_no_rgb_dma_outputs=True,
 stop_cleanup_uses_live_request_ownership=True,capture_cancel_status_propagated=True,
 rejected_r9_and_r10_candidates_preserved=True,all_three_candidates_built_and_original214_restored=True,
 kernel_image_boot_dtb_and_all_modules_unchanged_in_stage224=True,
 rollback_framework='99990.7.2-r8',rollback_configuration='0.1.0-r3',
 rollback_keeps_current_fae1_camss_and_e49_sensor_modules=True,
 physical_optical_exposure_delay_not_calibrated=True,manual_exposure_api_not_implemented=True)
path.write_text(json.dumps(d,indent=2)+'\n')
path=repo/'linux-port/camera/libcamera/source-lock.json';d=json.loads(path.read_text())
d.update(installed_framework_version='99990.7.2-r11',deployment_stage=224,
 deployment_evidence='../../../reference/kernel224/r11-package-install-validation.json',
 capture_control_association_evidence='../../../reference/kernel224/r11-installed-native-validation.json',
 stage224_additional_patches_sha256={name:sha(target/name) for name,_ in patches},
 raw_only_cpu_statistics_and_metadata=True,manual_exposure_api_not_implemented=True)
path.write_text(json.dumps(d,indent=2)+'\n')
r=dict(stage=224,canonical_r11_r6_recipes_and_framework_deployment_locks_promoted=True,
 prior14_patches_tuning_and_all_full_feature_subpackages_preserved=True,
 kernel_source_lock_unchanged_from223=True,all13_package_hashes_verified=True,
 r8_r3_rollback_retained_and_keeps_fae1_e49=True,full_peripheral_goal_active=True)
(here/'package-integration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
