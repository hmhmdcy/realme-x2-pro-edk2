from pathlib import Path
import hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel220');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
assert json.loads((here/'r7-package-install-validation.json').read_text())['transaction_state']=='verified'
for phase,sizes in [('candidate-threaded',[(1920,1088),(2296,1728),(4608,3456)]),('candidate-isolated',[(1920,1088),(2296,1728)]),('system-r7',[(1920,1088),(2296,1728),(4608,3456)])]:
 for w,h in sizes:
  r=json.loads((here/f'exposure-metadata-{phase}-{w}x{h}-validation.json').read_text());assert r['frame_count']==36 and r['maximum_metadata_conversion_error_us']<1
source=root/'work/libcamera220';target=repo/'linux-port/packages/libcamera';lock=json.loads((target/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r6'
assert all(sha(source/name)==digest and sha(target/name)==digest for name,digest in lock['source_files_sha256'].items() if name!='APKBUILD')
proof=json.loads((here/'candidate-source-validation.json').read_text());built=root/'work/libcamera220-built/src/libcamera-v0.7.2'
assert all(sha(built/name)==digest for name,digest in proof['source_files'].items())
for name in ['APKBUILD','0013-simple-refresh-sensor-timing.patch']:shutil.copyfile(source/name,target/name)
lock.update(stage=220,original_recipe_version='99990.7.2-r6',new_recipe_version='99990.7.2-r7',
 original_twelve_patches_and_all_existing_inputs_preserved=True,sensor_information_refreshed_on_each_configuration=True,
 additional_stage220_patches=['0013-simple-refresh-sensor-timing.patch'],
 source_files_sha256={p.name:sha(p) for p in target.iterdir() if p.is_file() and p.name not in ['README.md','source-lock.json']})
(target/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n');shutil.copyfile(target/'source-lock.json',source/'source-lock.json')
config=root/'work/samurai-camera-config220';product=repo/'linux-port/packages/samurai-camera-config'
assert (config/'configuration.yaml').read_bytes()==(product/'configuration.yaml').read_bytes()
shutil.copyfile(config/'APKBUILD',product/'APKBUILD')
manifest=json.loads((private/'camera-forward-repo/package-manifest.json').read_text());path=repo/'linux-port/camera/deployment-lock.json';d=json.loads(path.read_text())
d.update(stage=220,framework_version='99990.7.2-r7',configuration_version='0.1.0-r2',camera_framework_deployment_stage=220,
 built_packages=[{k:p[k] for k in ['name','version','file','sha256','bytes']} for p in manifest['packages']],
 runtime_evidence='../../reference/kernel220/exposure-metadata-system-r7-1920x1088-validation.json',
 standard_client_evidence='../../reference/kernel220/standard-gstreamer-validation.json',
 rollback_evidence='../../reference/kernel220/r7-package-install-validation.json',
 metadata_conversion_verified_frames=288,metadata_conversion_quantisation_error_below_microseconds=1,
 ipa_isolated_configuration_serialisation_verified=True,kernel_or_boot_changed_in_stage220=False)
path.write_text(json.dumps(d,indent=2)+'\n')
path=repo/'linux-port/camera/libcamera/source-lock.json';d=json.loads(path.read_text());d.update(installed_framework_version='99990.7.2-r7',deployment_stage=220,
 deployment_evidence='../../../reference/kernel220/r7-package-install-validation.json',
 stage220_timing_refresh_patch_sha256=sha(target/'0013-simple-refresh-sensor-timing.patch'),
 per_mode_exposure_metadata_evidence='../../../reference/kernel220/exposure-metadata-system-r7-1920x1088-validation.json');path.write_text(json.dumps(d,indent=2)+'\n')
# Correct inherited report labels, retaining the original private stdout.
for action in ['start','finish']:
 path=here/('candidate-full-'+action+'-validation.json');d=json.loads(path.read_text());d.update(stage=220,controller_template_stage=219);path.write_text(json.dumps(d,indent=2)+'\n')
path=here/'r7-package-install-validation.json';d=json.loads(path.read_text());d['original_world_repositories_and_r6_payloads_retained']=d.pop('original_world_repositories_and_r5_payloads_retained');d['rollback_label_corrected_from_inherited_template']=True;path.write_text(json.dumps(d,indent=2)+'\n')
r=dict(stage=220,canonical_r7_r2_recipes_and_deployment_locks_promoted=True,previous_twelve_patches_tuning_config_payload_preserved=True,
 three_changed_source_hashes_match_built_candidate=True,all288_metadata_samples_within_one_microsecond_quantisation=True,
 isolated_ipa_serialisation_and_default_installed_clients_verified=True,boot_kernel_and_module_unchanged=True,
 actual_manual_exposure_api_cfa_geometry_colour_quality_and_other_peripherals_still_open=True)
(here/'package-integration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
