"""Record the actual r21/GW1 deployment, retaining its failed/open validations."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1]
health=json.loads((R/'final-health-validation.json').read_text());assert health['camera_idle_passed']
assert json.loads((R/'main-capture-validation.json').read_text())['all_passed']
assert json.loads((R/'four-camera-regression-validation.json').read_text())['passed']
assert json.loads((R/'packages-install-validation.json').read_text())['all_new_payloads_verified']
archive=W/'archive/camera-before273-2026-10-18';archive.mkdir()
for p in [W/'linux-port/packages/libcamera',W/'linux-port/packages/samurai-camera-config',W/'linux-port/camera/deployment-lock.json',W/'linux-port/camera/kernel/source-lock.json',W/'NEXT-SESSION.md']:
 target=archive/p.relative_to(W);target.parent.mkdir(parents=True,exist_ok=True)
 if p.is_dir():shutil.copytree(p,target)
 else:shutil.copyfile(p,target)
(archive/'snapshot-sha256.json').write_text(json.dumps({str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.rglob('*') if p.is_file()},indent=2)+'\n')
for name,version in [('libcamera','99990.7.2-r21'),('samurai-camera-config','0.1.0-r16')]:
 dest=W/'linux-port/packages'/name
 for p in (R/'recipes'/name).iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 lock=dict(stage=273,package_version=version,source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name not in ['README.md','source-lock.json']},
 actual_signed_build_validation='reference/kernel273/r21-package-build-validation.json',native_install_validation='reference/kernel273/packages-install-validation.json',
 package_payload_features_preserved=True,private_keys_not_in_sources=True,s5k3m5_native_gain_pair_still_required=True,
 gw1_helper_native_gain_codes=[32,1024],high_resolution_manual_transition_validation_pending=True)
 (dest/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
 p=dest/'README.md';p.write_text('273已部署：libcamera r21/config-r16 新增 GW1 原生增益 helper。主摄 RAW/RGB 与600帧CPU JPEG已出帧，四 sensor 238帧交替通过；高分辨率手动切换测试仍失败，AF/画质/GUI/Spectra未完成。[部署及失败范围](../../../reference/kernel273/README.md)。以下为历史阶段。\n\n'+p.read_text())
path=W/'linux-port/camera/deployment-lock.json';lock=json.loads(path.read_text())
packages=json.loads((host.PRIVATE/'camera-forward-repo-r21/package-manifest.json').read_text())['packages']
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
source=json.loads((R.parent/'kernel272/source-lock.json').read_text());boot=json.loads((R/'build-package-validation.json').read_text())
lock.update(stage=273,kernel_boot_stage=273,current_boot_guard_stage=273,kernel_image_stage=183,
 framework_version='99990.7.2-r21',configuration_version='0.1.0-r16',ko_count=775,
 built_packages=[{k:p[k] for k in ['name','version','arch','file','bytes','sha256']} for p in packages],
 installed_package_payloads=[p for p in packages if p['name'] in selected],
 boot_sha256=boot['boot_sha256'],dtb_sha256=boot['dtb_sha256'],current_camera_evidence='../../reference/kernel273/README.md',
 final_health_evidence='../../reference/kernel273/final-health-validation.json',guard_path='/var/lib/samurai/k273-work/boot-id-private.txt',goal_status='active_incomplete',
 previous_lock_archive='../../archive/camera-before273-2026-10-18/linux-port/camera/deployment-lock.json',
 current_boot_actual_capture_validation_pending=False,current_stack_gui_validation_pending=True,
 current_boot_unexpected_reboot_followup=False,planned_boot_transition_evidence='../../reference/kernel273/postboot-identity-validation.json',
 sensor_startup_fresh_boot_validation_pending=False,sensor_startup_fresh_boot_passed=False,ssc_boot_start_failed=True,
 desktop_temporary_nodeps_restore=True,automatic_rotation_currently_available=False,
 main_camera_chip_id_verified=True,main_camera_cphy_raw_capture_verified=True,main_camera_optical_scene_observed=True,
 main_camera_autofocus_verified=False,main_camera_full_manual_transition_validation_passed=False,
 main_camera_failed_manual_evidence='../../reference/kernel273/main-manual-r1-validation.json',
 current_stack_four_camera_regression='../../reference/kernel273/four-camera-regression-validation.json',
 current_stack_main_camera_scene='../../reference/kernel273/main-evidence-analysis.json',
 spectra_hardware_image_processing_supported=False,kernel_source_commit=source['commit'],kernel_source_branch=source['branch'])
for old,new in [('current_stack_three_camera_regression','historical_three_camera_regression'),('current_stack_telephoto_real_scene','historical_telephoto_real_scene'),
 ('snapshot_front_rear_gui_preview_switch_shutter_verified','historical_snapshot_front_rear_gui_verified'),('snapshot_jpeg_decode_verified','historical_snapshot_gui_jpeg_decode_verified')]:
 if old in lock:lock[new]=lock.pop(old)
lock['snapshot_front_rear_gui_preview_switch_shutter_verified']=False;lock['snapshot_jpeg_decode_verified']=False
mods=json.loads((R/'postboot-hardware-validation.json').read_text())['modules']
for name,item in mods.items():
 old=lock['kernel_modules'].get(name,{})
 old.update(loaded=item['loaded'],sha256=item['file_sha256'],loaded_note_matches_disk=item['loaded_note_matches_disk'],intree='Y');lock['kernel_modules'][name]=old
lock['system_services']=dict(stage=273,new_processes=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in health['services'] if p['comm'] in ['pipewire','wireplumber']],
 spa_path='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so',spa_candidate_active=False,normal_system_library_paths=True,
 phosh_pid=next(p['pid'] for p in health['services'] if p['comm']=='phosh'),current_manifest='/var/lib/samurai/k273-services-current-private.json',
 ssc_running=False,temporary_nodeps_desktop_start=True)
path.write_text(json.dumps(lock,indent=2)+'\n')
path=W/'linux-port/camera/kernel/source-lock.json';kernel=json.loads(path.read_text())
kernel.update(stage=273,maintained_branch=source['branch'],maintained_commit=source['commit'],boot_stage=273,module_count=775,
 deployed_camera_modules=lock['kernel_modules'],s5kgw1_source_sha256=source['source_files_sha256']['drivers/media/i2c/s5kgw1.c'],
 gw1_candidate_patch='../../../reference/kernel272/s5kgw1-candidate.patch',
 gw1_module_build_evidence='../../../reference/kernel272/current-module-build-validation.json',
 gw1_raw_capture_evidence='../../../reference/kernel273/main-capture-validation.json',
 current_boot_evidence='../../../reference/kernel273/postboot-identity-validation.json',
 previous_lock_archive='../../../archive/camera-before273-2026-10-18/linux-port/camera/kernel/source-lock.json',
 gw1_manual_transition_test_failed=True,autofocus_and_spectra_not_complete=True)
path.write_text(json.dumps(kernel,indent=2)+'\n')
report=dict(stage=273,canonical_recipes_and_actual_deployment_locks_updated=True,prior_r20_recipes_and_locks_archived=True,
 modules=775,packages=961,packages_built=13,packages_installed=7,source_commit=source['commit'],
 main_camera_basic_capture_verified=True,full_control_validation_failed=True,ssc_boot_failure_retained=True,
 full_kernel_and_rootfs_build_pending=True,goal_status='active_incomplete')
(R/'source-promotion-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
