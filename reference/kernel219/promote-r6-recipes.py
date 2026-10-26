"""Promote only the fully built, installed and physically verified package inputs."""
from pathlib import Path
import hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel219');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'r6-package-install-validation.json').read_text())['transaction_state']=='verified'
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
for phase in ['isolated-r6','installed-r6']:
 for kind,pattern,w,h,config in [('raw',0,2304,1728,'default'),('raw',2,2304,1728,'default'),('rgb',2,2296,1728,'default'),('rgb',0,2296,1728,'default'),('raw',0,4608,3456,'full'),('raw',2,4608,3456,'full'),('rgb',2,4608,3456,'full'),('rgb',0,4608,3456,'full')]:
  r=json.loads((here/f'{phase}-{w}x{h}-{kind}-pattern{pattern}-{config}-validation.json').read_text());assert r['program_exit']==0 and len(r['frames'])==6 and r['taint']==0 and not any(r['fault_delta'].values())
source=root/'work/libcamera219';target=repo/'linux-port/packages/libcamera'
lock=json.loads((target/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r5'
before=lock['source_files_sha256'].copy()
assert all(sha(source/name)==digest for name,digest in before.items() if name!='APKBUILD')
for name in ['APKBUILD','0011-imx471-native-quad-cpu.patch','0012-software-isp-dma-heap-selection.patch']:shutil.copyfile(source/name,target/name)
lock.update(stage=219,original_recipe_version='99990.7.2-r5',new_recipe_version='99990.7.2-r6',
 original_ten_patches_and_all_existing_source_inputs_preserved=True,full_auto_virtual_features_and_all_eleven_subpackages_retained=True,
 experimental_native_quad_default_false=True,configurable_software_isp_dma_heap=True,
 source_files_sha256={p.name:sha(p) for p in target.iterdir() if p.is_file() and p.name not in ['README.md','source-lock.json']},
 additional_stage219_patches=['0011-imx471-native-quad-cpu.patch','0012-software-isp-dma-heap-selection.patch'])
(target/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n');shutil.copyfile(target/'source-lock.json',source/'source-lock.json')
config=root/'work/samurai-camera-config219';product=repo/'linux-port/packages/samurai-camera-config'
for name in ['APKBUILD','configuration.yaml']:shutil.copyfile(config/name,product/name)
for name in ['70-samurai-camera-heaps.rules','samurai-camera-heaps.conf']:assert (config/name).read_bytes()==(product/name).read_bytes()
shutil.copyfile(config/'configuration.yaml',repo/'linux-port/camera/configuration.yaml')
manifest=json.loads((private/'camera-forward-repo/package-manifest.json').read_text())
deploy=repo/'linux-port/camera/deployment-lock.json';d=json.loads(deploy.read_text())
d.update(stage=219,kernel_boot_stage=219,framework_version='99990.7.2-r6',configuration_version='0.1.0-r1',
 built_packages=[{key:p[key] for key in ['name','version','file','sha256','bytes']} for p in manifest['packages']],
 runtime_evidence='../../reference/kernel219/standard-gstreamer-validation.json',
 rollback_evidence='../../reference/kernel219/r6-package-install-validation.json',camera_framework_deployment_stage=219,
 sensor_kernel_module_sha256='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1',sensor_kernel_module_deployment_stage=219,
 boot_sha256='156f0370fff6a65babc14738a62e4e2291594fe74f680cf3f62317dd0291198a',
 dtb_sha256='a214fd6b2ccb93e5bbb5adc774e7c510398541e8fab286832682cc6bbd76ca42',
 native_full_raw_and_rgb_experiment_verified=True,native_quad_default_enabled=False,
 product_software_isp_heap='system',four_mp_default_rgb_four_buffer_validation=True,
 geometry_standard_cfa_and_image_quality_not_accepted=True)
deploy.write_text(json.dumps(d,indent=2)+'\n')
path=repo/'linux-port/camera/libcamera/source-lock.json';d=json.loads(path.read_text());d.update(installed_framework_version='99990.7.2-r6',
 deployment_stage=219,deployment_evidence='../../../reference/kernel219/r6-package-install-validation.json',
 source_files_sha256_scope='Historical stage213 three-patch source snapshot before native Quad changes; full current recipe inputs are locked separately',
 current_full_recipe_source_lock='../../packages/libcamera/source-lock.json',
 stage219_native_quad_patch_sha256=sha(source/'0011-imx471-native-quad-cpu.patch'),stage219_dma_heap_patch_sha256=sha(source/'0012-software-isp-dma-heap-selection.patch'),
 native_quad_default_enabled=False,stage219_runtime_evidence='../../../reference/kernel219/installed-r6-4608x3456-rgb-pattern2-full-validation.json');path.write_text(json.dumps(d,indent=2)+'\n')
r=dict(stage=219,canonical_full_feature_r6_and_config_r1_recipes_promoted=True,original_ten_patch_and_tuning_inputs_preserved=True,
 both_source_and_deployment_locks_updated=True,no_private_keys_copied=True,kernel_patch_chain_matches_deployed_module=True,
 host_canonical_kernel_source_still216=True,byte_identical_rebuild_not_yet_tested=True)
(here/'package-integration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
