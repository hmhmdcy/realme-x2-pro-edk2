"""Promote the physically verified source recipes and reconcile the current locks."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1]
install=json.loads((R/'gain-install-r2-validation.json').read_text())
assert install['paired_update_verified'] and json.loads((R/'gain-response-validation.json').read_text())['physical_fractional_gain_verified']
assert json.loads((R/'three-camera-regression-validation.json').read_text())['passed']
health=json.loads((R/'final-r1-validation.json').read_text());assert health['passed']
commit=json.loads((R/'kernel-commit-validation.json').read_text())
archive=W/'archive/camera-before271-2026-10-18';archive.mkdir()
old_paths=[W/'linux-port/packages/libcamera',W/'linux-port/packages/samurai-camera-config',W/'linux-port/camera/deployment-lock.json',W/'linux-port/camera/kernel/source-lock.json']
for p in old_paths:
 dest=archive/p.relative_to(W);dest.parent.mkdir(parents=True,exist_ok=True)
 if p.is_dir():shutil.copytree(p,dest)
 else:shutil.copyfile(p,dest)
(archive/'snapshot-sha256.json').write_text(json.dumps({str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.rglob('*') if p.is_file()},indent=2)+'\n')
shutil.copyfile(W/'NEXT-SESSION.md',W/'archive/NEXT-SESSION-before271-update-2026-10-18.md')
for name,version in [('libcamera','99990.7.2-r20'),('samurai-camera-config','0.1.0-r15')]:
 dest=W/'linux-port/packages'/name
 for p in (R/'recipes'/name).iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 lock=dict(stage=271,package_version=version,source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name not in ['README.md','source-lock.json']},
  actual_signed_build_validation='reference/kernel271/r20-package-build-validation.json',native_install_validation='reference/kernel271/gain-install-r2-validation.json',
  package_payload_features_preserved=True,private_keys_not_in_sources=True,paired_s5k3m5_gain_control_driver_required=True)
 (dest/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
 old=(dest/'README.md').read_text()
 intro=('271（2026-10-18）：当前原生部署libcamera r20/config-r15，新增标准S5K3M5原生gain code/32 helper，配套内核控件32…512。481码factory测试、96组物理细分增益、三摄193帧与600帧普通预览通过；初始AE慢、画质/AF/GUI/主摄/ISP仍开放。必须和新sensor模块配套更新或回退。[271](../../../reference/kernel271/README.md)、[当前源锁](source-lock.json)。下列r19及更早叙述按历史解释。\n\n')
 (dest/'README.md').write_text(intro+old)
lock_path=W/'linux-port/camera/deployment-lock.json';lock=json.loads(lock_path.read_text())
complete=json.loads((host.PRIVATE/'camera-forward-repo-r20/package-manifest.json').read_text())['packages']
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
lock.update(stage=271,kernel_boot_stage=270,current_boot_guard_stage=270,kernel_image_stage=183,
 framework_version='99990.7.2-r20',configuration_version='0.1.0-r15',ko_count=774,
 built_packages=[{k:p[k] for k in ['name','version','arch','file','bytes','sha256']} for p in complete],
 installed_package_payloads=[p for p in complete if p['name'] in selected],
 current_camera_evidence='../../reference/kernel271/README.md',final_health_evidence='../../reference/kernel271/final-r1-validation.json',
 guard_path='/var/lib/samurai/k270-work/boot-id-private.txt',goal_status='active_incomplete',
 previous_lock_archive='../../archive/camera-before271-2026-10-18/linux-port/camera/deployment-lock.json',
 current_boot_actual_capture_validation_pending=False,current_stack_gui_validation_pending=True,
 snapshot_gui_evidence_stage=270,snapshot_gui_evidence_deployment='r19/r14 pre-boot270 session, two sensors only',
 snapshot_gui_evidence='../../reference/kernel270/snapshot-gui-r1-validation.json',
 s5k3m5_native_gain_code_range=[32,512],s5k3m5_real_gain_range=[1,16],s5k3m5_real_gain_step=0.03125,
 s5k3m5_driver_and_userspace_must_be_updated_together=True,
 s5k3m5_control_evidence='../../reference/kernel271/gain-response-validation.json',
 current_stack_three_camera_regression='../../reference/kernel271/three-camera-regression-validation.json',
 current_stack_telephoto_real_scene='../../reference/kernel271/ae-optical-review.json',
 current_stack_automatic_exposure_startup_slow=True,kernel_source_commit=commit['commit'],kernel_source_branch=commit['branch'])
boot=json.loads((R.parent/'kernel270/build-package-validation.json').read_text())
lock.update(boot_sha256=boot['boot_sha256'],dtb_sha256=boot['dtb_sha256'])
modules=json.loads((R.parent/'kernel270/postboot-hardware-validation.json').read_text())['modules']
for name,item in modules.items():
 old=lock['kernel_modules'].get(name,{})
 old.update(loaded=True,sha256=install['new_module_sha256'] if name=='s5k3m5' else item['file_sha256'],loaded_note_matches_disk=True,intree='Y')
 lock['kernel_modules'][name]=old
lock['system_services']=dict(stage=271,new_processes=install['new_processes'],spa_path='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so',spa_candidate_active=False,
 normal_system_library_paths=True,phosh_pid=next(p['pid'] for p in health['services'] if p['comm']=='phosh'),
 current_manifest='/var/lib/samurai/k271-services-current-private.json')
lock_path.write_text(json.dumps(lock,indent=2)+'\n')
kernel_lock=dict(stage=271,upstream_base='a90ee4305c4a5df72c11b31dacfdc76e00fcf78a',maintained_branch=commit['branch'],maintained_commit=commit['commit'],
 actual_kernel_image_stage=183,actual_kernel_release=health['release'],boot_stage=270,module_count=774,
 deployed_camera_modules=lock['kernel_modules'],s5k3m5_source_sha256=commit['source_sha256'],
 native_gain_patch='../../../reference/kernel271/s5k3m5-native-gain-code.patch',
 physical_gain_evidence='../../../reference/kernel271/gain-response-validation.json',
 module_build_evidence='../../../reference/kernel271/current-module-build-validation.json',
 current_boot_evidence='../../../reference/kernel270/postboot-identity-validation.json',
 complete_new_image_and_rootfs_not_deployed=True,full_kernel_candidate_evidence='../../../reference/kernel269/full-build-validation.json',
 previous_lock_archive='../../../archive/camera-before271-2026-10-18/linux-port/camera/kernel/source-lock.json',
 source_tree_intree_is_not_upstream_acceptance=True)
(W/'linux-port/camera/kernel/source-lock.json').write_text(json.dumps(kernel_lock,indent=2)+'\n')
for path in ['linux-port/camera/README.md','linux-port/camera/kernel/README.md']:
 p=W/path;old=p.read_text();intro='271（2026-10-18）：当前S5K3M5原生32…512增益码与libcamera r20/config-r15已配套部署；前摄/两后摄原生回归通过，长焦持续预览已有明亮实景，首次AE慢、画质/AF/主摄/Spectra仍待完成。当前身份与源码见[271](../../'+('reference/kernel271/README.md' if path=='linux-port/camera/README.md' else '../reference/kernel271/README.md')+')。下文旧阶段按历史解释。\n\n'
 p.write_text(intro+old)
report=dict(stage=271,canonical_recipes_promoted=True,deployment_lock_and_camera_kernel_lock_reconciled=True,
 original_source_and_locks_archived=True,packages_installed=7,packages_built=13,
 full_image_and_rootfs_still_pending=True,source_commit=commit['commit'])
(R/'source-promotion-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
