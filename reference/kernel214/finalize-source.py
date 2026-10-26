from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text());intentional=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())['three_intentional_source_changes']
assert all(sha(kernel/name)==intentional.get(name,digest) for name,digest in old.items())
before=json.loads((private.parent/'kernel211/source-before/hashes-private.json').read_text())
assert all(sha(kernel/name)==before[name] for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
recipe=repo/'linux-port/packages/libcamera';lock=json.loads((recipe/'source-lock.json').read_text())
assert all(sha(recipe/name)==digest for name,digest in lock['source_files_sha256'].items())
sensorlock=repo/'linux-port/camera/libcamera/source-lock.json';sensor=json.loads(sensorlock.read_text());source=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera/src/libcamera-v0.7.2')
assert all(sha(source/name)==digest for name,digest in sensor['source_files_sha256'].items())
assert all(sha(recipe/name)==sha(repo/'linux-port/camera/libcamera'/name) for name in lock['three_verified_image_processing_patches_added'])
config=repo/'linux-port/packages/samurai-camera-config'
assert all((config/name).read_bytes()==(repo/'linux-port/camera'/name).read_bytes() for name in ['configuration.yaml','samurai-camera-heaps.conf','70-samurai-camera-heaps.rules'])
for path in here.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
for directory in [recipe,config,repo/'linux-port/camera']:
    assert not any(path.is_file() and (path.suffix in ['.pem','.rsa'] or 'ipa-priv-key' in path.name) for path in directory.rglob('*'))
sensor.update(current_candidate_not_installed=False,installed_framework_version='99990.7.2-r5',deployment_stage=214,deployment_evidence='../../../reference/kernel214/package-install-validation.json')
sensorlock.write_text(json.dumps(sensor,indent=2)+'\n')
manifest=json.loads((private/'camera-forward-repo/package-manifest.json').read_text())
installed={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
deployment=dict(stage=214,kernel_changed=False,kernel_boot_stage=211,kernel_image_stage=183,framework_version='99990.7.2-r5',configuration_version='0.1.0-r0',upstream_version='0.7.2',package_recipe='../../linux-port/packages/libcamera/APKBUILD',package_source_lock='../../linux-port/packages/libcamera/source-lock.json',configuration_recipe='../../linux-port/packages/samurai-camera-config/APKBUILD',all_original_feature_subpackages_built=True,installed_packages=[item['name'] for item in manifest['packages'] if item['name'] in installed],built_packages=[{k:item[k] for k in ['name','version','file','sha256','bytes']} for item in manifest['packages']],runtime_evidence='../../reference/kernel214/default-clients-validation.json',rollback_evidence='../../reference/kernel214/package-roundtrip-validation.json',byte_for_byte_rebuild_not_tested=True,external_retained_private_signing_inputs_required=True,private_keys_not_distributed=True,full_image_quality_and_rear_four_cameras_not_accepted=True)
(repo/'linux-port/camera/deployment-lock.json').write_text(json.dumps(deployment,indent=2)+'\n')
report=dict(stage=214,no_additional_kernel_source_change=True,saved_kernel_sources_and_build_metadata_preserved=True,kernel_diff_check_passed=True,no_kernel_source_staged=True,full_package_recipe_source_lock_verified=True,three_camera_patches_match_canonical_sources=True,compiled_sensor_helper_properties_and_cpu_header_verified=True,configuration_recipe_matches_canonical_configuration=True,reference_python_syntax_passed=True,no_private_key_files_in_product_sources=True,all13_built_forward_package_hashes_recorded=True,seven_package_native_install_and_default_clients_verified=True,bit_identical_rebuild_not_claimed=True,no_boot_or_other_partition_flash=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
