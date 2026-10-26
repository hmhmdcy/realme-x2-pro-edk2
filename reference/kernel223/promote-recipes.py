from pathlib import Path
import hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'final-health-validation.json').read_text())['deployed_camss_file_and_loaded_note_verified']
assert json.loads((here/'installed-control-validation.json').read_text())['frame_count']==64
assert json.loads((here/'full-finish-validation.json').read_text())['experimental_full_raw_disabled']
for client in ['cam','gstreamer']:assert json.loads((here/f'standard-{client}-validation.json').read_text())['frame_count']==6
source=sdk/'work/libcamera223';target=repo/'linux-port/packages/libcamera';lock=json.loads((target/'source-lock.json').read_text())
assert lock['new_recipe_version']=='99990.7.2-r7'
assert all(sha(source/name)==digest and sha(target/name)==digest for name,digest in lock['source_files_sha256'].items() if name!='APKBUILD')
proof=json.loads((here/'candidate-source-validation.json').read_text());built=sdk/'work/libcamera223-built/src/libcamera-v0.7.2'
assert all(sha(built/name)==digest for name,digest in proof['source_files'].items())
for name in ['APKBUILD','0014-simple-capture-control-snapshot.patch']:shutil.copyfile(source/name,target/name)
assert sha(target/'0014-simple-capture-control-snapshot.patch')==proof['patch_sha256']
lock.update(stage=223,original_recipe_version='99990.7.2-r7',new_recipe_version='99990.7.2-r8',
 original_thirteen_patches_and_all_existing_inputs_preserved=True,additional_stage223_patches=['0014-simple-capture-control-snapshot.patch'],
 capture_time_controls_snapshotted_by_capture_sequence=True,request_keyed_ipa_context_preserved=True,
 source_files_sha256={p.name:sha(p) for p in target.iterdir() if p.is_file() and p.name not in ['README.md','source-lock.json']})
(target/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n');shutil.copyfile(target/'source-lock.json',source/'source-lock.json')
config=sdk/'work/samurai-camera-config223';product=repo/'linux-port/packages/samurai-camera-config'
assert (config/'configuration.yaml').read_bytes()==(product/'configuration.yaml').read_bytes();shutil.copyfile(config/'APKBUILD',product/'APKBUILD')
kernel=repo/'linux-port/camera/kernel';patch=kernel/'0005-camss-sm8150-paired-sof.patch';shutil.copyfile(here/'camss-sm8150-paired-sof-candidate.patch',patch)
base=json.loads((here/'sof-candidate-source-validation.json').read_text());build=json.loads((here/'sof-candidate-build-validation.json').read_text())
assert sha(patch)==base['patch_sha256']
path=kernel/'source-lock.json';d=json.loads(path.read_text());d.update(stage=223,sensor_deployment_stage=219,
 camss=dict(deployment_stage=223,patch=patch.name,patch_sha256=sha(patch),
           base_source_sha256=base['original_sources_sha256'],current_source_sha256=base['candidate_sources_sha256'],
           module_sha256=build['compiled_module_sha256'],module_bytes=build['module_bytes'],
           base_kernel_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd='/home/cy122/pmos-samurai-kernel136/kernel',text=True).strip(),
           sm8150_vfe170_only=True,completion_timestamp_remains_eof=True,missing_sof_tag_is_buffer_error=True,
           runtime_evidence='../../../reference/kernel223/control-snapshot-native-validation.json',
           deployment_evidence='../../../reference/kernel223/coherent-install-validation.json',
           original_module_sha256='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58',
           canonical_camss_sources_still_original=True),
 driver_patch_sets_require_full_kernel_rootfs_integration=True)
path.write_text(json.dumps(d,indent=2)+'\n')
manifest=json.loads((private/'camera-forward-repo/package-manifest.json').read_text());path=repo/'linux-port/camera/deployment-lock.json';d=json.loads(path.read_text())
d.update(stage=223,framework_version='99990.7.2-r8',configuration_version='0.1.0-r3',camera_framework_deployment_stage=223,
 built_packages=[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in manifest['packages']],
 camss_module_sha256=build['compiled_module_sha256'],camss_module_deployment_stage=223,
 paired_camss_and_framework_required=True,runtime_evidence='../../reference/kernel223/installed-control-validation.json',
 standard_client_evidence='../../reference/kernel223/standard-gstreamer-validation.json',
 rollback_evidence='../../reference/kernel223/coherent-install-validation.json',
 metadata_conversion_verified_frames=164,stage220_historical_metadata_conversion_verified_frames=288,
 capture_control_history_gap_test_candidate_rgb_frames=64,capture_control_history_gap_test_installed_rgb_frames=64,
 frame_sync_and_buffer_pairing_candidate_frames=160,physical_optical_exposure_delay_not_calibrated=True,
 manual_exposure_api_not_implemented=True,kernel_image_or_boot_changed_in_stage223=False,
 camss_module_changed_in_stage223=True,boot_and_dtb_changed_in_stage223=False)
path.write_text(json.dumps(d,indent=2)+'\n')
path=repo/'linux-port/camera/libcamera/source-lock.json';d=json.loads(path.read_text());d.update(installed_framework_version='99990.7.2-r8',deployment_stage=223,
 deployment_evidence='../../../reference/kernel223/coherent-install-validation.json',stage223_capture_snapshot_patch_sha256=proof['patch_sha256'],
 capture_control_association_evidence='../../../reference/kernel223/installed-control-validation.json');path.write_text(json.dumps(d,indent=2)+'\n')
raw=json.loads((here/'installed-dark-raw-validation.json').read_text());rgb=json.loads((here/'installed-dark-rgb-validation.json').read_text())
assert not any(f['all_zero'] for r in [raw,rgb] for f in r['frames'])
dark=dict(stage=223,room_lights_off=True,scene_images_not_saved=True,no_flash_or_external_illumination=True,
 raw_frames=6,raw_pixel_min=min(f['byte_min'] for f in raw['frames']),raw_pixel_max=max(f['byte_max'] for f in raw['frames']),
 raw_stddev_range=[min(f['stddev'] for f in raw['frames']),max(f['stddev'] for f in raw['frames'])],
 raw_adjacent_changed_fraction_range=[min(f['changed_fraction'] for f in raw['frames'][1:]),max(f['changed_fraction'] for f in raw['frames'][1:])],
 rgb_frames=6,raw_and_rgb_all_zero_frames=0,raw_and_rgb_have_temporal_variation=True,
 conclusion='Observed dark output contains nonzero signal and temporal noise; these samples do not reproduce a fixed all-zero frame.',
 real_colour_exposure_quality_and_optical_delay_not_accepted=True)
(here/'dark-frame-classification-validation.json').write_text(json.dumps(dark,indent=2)+'\n')
r=dict(stage=223,canonical_r8_r3_recipes_promoted=True,canonical_camss_patch_and_deployment_locks_promoted=True,
 previous_thirteen_patches_and_all_tuning_inputs_preserved=True,capture_control_association_verified_in_threaded_and_isolated_ipa=True,
 actual_original_camss_and_r7_r2_rollback_retained=True,full_peripheral_goal_active=True)
(here/'package-integration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
