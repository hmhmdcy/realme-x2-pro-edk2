"""Promote verified 275 packages and 276 kernel/board state, preserving history."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;W=R.parents[1]
def read(p):return json.loads(p.read_text())
def write(p,o):p.write_text(json.dumps(o,indent=2)+'\n')
h=read(R/'final-health-validation.json');boot=read(R/'build-package-validation.json')
assert h['camera_idle_health']['passed'] and h['current49_payloads_verified']==49
assert h['module_count']==776 and h['package_count']==961 and h['other775_modules_unchanged']
assert h['ssc_started'] and h['normal_desktop_start_observed']
assert read(R/'four-camera-regression-validation.json')['passed']
assert read(R/'manager-lifetime-validation.json')['lens_fd_not_retained_by_manager']
assert read(R/'standard-focus-validation.json')['standard_v4l2_focus_control']
assert read(R.parent/'kernel275/packages-install-validation.json')['all_new_payloads_verified']
source=read(R/'source-candidate-validation.json')
archive=W/'archive/camera-before276-2026-10-18';archive.mkdir()
for p in [W/'linux-port/packages/libcamera',W/'linux-port/packages/samurai-camera-config',W/'linux-port/camera/deployment-lock.json',W/'linux-port/camera/kernel/source-lock.json',W/'NEXT-SESSION.md']:
 dest=archive/p.relative_to(W);dest.parent.mkdir(parents=True,exist_ok=True)
 if p.is_dir():shutil.copytree(p,dest)
 else:shutil.copyfile(p,dest)
write(archive/'snapshot-sha256.json',{str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()})
for name,version in [('libcamera','99990.7.2-r22'),('samurai-camera-config','0.1.0-r17')]:
 dest=W/'linux-port/packages'/name
 for p in (R.parent/'kernel275/recipes'/name).iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 write(dest/'source-lock.json',dict(stage=276,build_stage=275,package_version=version,
  source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name not in ['README.md','source-lock.json']},
  actual_signed_build_validation='reference/kernel275/r22-package-build-validation.json',native_install_validation='reference/kernel275/packages-install-validation.json',
  actual_current_payload_validation='reference/kernel276/final-health-validation.json',package_payload_features_preserved=True,private_keys_not_in_sources=True,
  s5k3m5_native_gain_pair_still_required=True,gw1_helper_native_gain_codes=[32,1024],
  standard_lens_stream_lifetime_validation='reference/kernel276/manager-lifetime-validation.json',
  high_resolution_manual_transition_validation_pending=True,autofocus_algorithm_implemented=False))
 p=dest/'README.md'
 p.write_text('276当前部署：libcamera r22/config-r17，新增通用 Simple 镜头流生命周期；CameraManager常驻枚举四摄后镜头fd释放，供电/时钟回收。标准V4L2手动对焦已有光学响应，四摄238帧回归通过；AF算法、画质、GUI/录像、Spectra及r22完整手动曝光矩阵仍待验收。[现机证据](../../../reference/kernel276/README.md)。以下为历史阶段。\n\n'+p.read_text())
path=W/'linux-port/camera/deployment-lock.json';lock=read(path)
pkgs=read(Path('/mnt/e/edk2-samurai-out/kernel275/camera-forward-repo-r22/package-manifest.json'))['packages']
selected={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
lock.update(stage=276,kernel_boot_stage=276,current_boot_guard_stage=276,kernel_image_stage=183,
 framework_version='99990.7.2-r22',configuration_version='0.1.0-r17',ko_count=776,
 built_packages=[{k:p[k] for k in ['name','version','arch','file','bytes','sha256']} for p in pkgs],
 installed_package_payloads=[p for p in pkgs if p['name'] in selected],boot_sha256=boot['boot_sha256'],dtb_sha256=boot['dtb_sha256'],
 current_camera_evidence='../../reference/kernel276/README.md',final_health_evidence='../../reference/kernel276/final-health-validation.json',
 guard_path='/var/lib/samurai/k276-work/boot-id-private.txt',goal_status='active_incomplete',
 previous_lock_archive='../../archive/camera-before276-2026-10-18/linux-port/camera/deployment-lock.json',
 planned_boot_transition_evidence='../../reference/kernel276/postboot-identity-validation.json',
 kernel_source_commit=source['candidate_commit'],kernel_source_branch=source['branch'],
 sensor_startup_fresh_boot_validation_pending=False,sensor_startup_fresh_boot_passed=True,ssc_boot_start_failed=False,
 desktop_temporary_nodeps_restore=False,automatic_rotation_currently_available=None,physical_rotation_retest_pending=True,
 historical_ssc_boot273_eperm_cause_unresolved=True,main_camera_autofocus_verified=False,
 main_camera_full_manual_transition_validation_passed=None,current_r22_manual_transition_validation_pending=True,
 main_camera_failed_manual_evidence='../../reference/kernel273/main-manual-r1-validation.json',
 later_same_matrix_two_passes_evidence='../../reference/kernel274/README.md',
 current_stack_four_camera_regression='../../reference/kernel276/four-camera-regression-validation.json',
 current_stack_main_camera_scene='../../reference/kernel276/standard-focus-optical-analysis.json',
 standard_v4l2_manual_focus_verified=True,standard_lens_lifetime_verified=True,shared_cci_io_supply_pm_verified=True,
 spectra_hardware_image_processing_supported=False,current_stack_gui_validation_pending=True)
for name,item in h['modules'].items():
 old=lock['kernel_modules'].get(name,{})
 old.update(item,intree='Y');lock['kernel_modules'][name]=old
lock['system_services']=dict(stage=276,new_processes=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in h['services'] if p['comm'] in ['pipewire','wireplumber']],
 spa_path='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so',spa_candidate_active=False,normal_system_library_paths=True,
 phosh_pid=next(p['pid'] for p in h['services'] if p['comm']=='phosh'),current_manifest='/var/lib/samurai/k276-services-current-private.json',
 ssc_running=True,temporary_nodeps_desktop_start=False,physical_rotation_retest_pending=True)
write(path,lock)
path=W/'linux-port/camera/kernel/source-lock.json';kernel=read(path)
kernel.update(stage=276,maintained_branch=source['branch'],maintained_commit=source['candidate_commit'],boot_stage=276,module_count=776,
 deployed_camera_modules=lock['kernel_modules'],current_boot_evidence='../../../reference/kernel276/postboot-identity-validation.json',
 previous_lock_archive='../../../archive/camera-before276-2026-10-18/linux-port/camera/kernel/source-lock.json',
 lc898219xi_source_sha256=hashlib.sha256((R.parent/'kernel274/lc898219xi.c').read_bytes()).hexdigest(),
 cci_source_sha256=source['source_files_sha256']['drivers/i2c/busses/i2c-qcom-cci.c'],
 lc898219xi_patch='../../../reference/kernel274/lc898219xi-candidate.patch',cci_io_patch='../../../reference/kernel276/cci-io-candidate.patch',
 cci_module_build_evidence='../../../reference/kernel276/current-module-build-validation.json',
 standard_focus_evidence='../../../reference/kernel276/standard-focus-validation.json',
 camera_lifetime_evidence='../../../reference/kernel276/manager-lifetime-validation.json',
 gw1_raw_capture_evidence='../../../reference/kernel276/main-capture-validation.json',gw1_manual_transition_test_failed=True,
 gw1_manual_failure_stage=273,current_r22_manual_transition_retest_pending=True,autofocus_and_spectra_not_complete=True,
 complete_new_image_and_rootfs_not_deployed=True,source_tree_intree_is_not_upstream_acceptance=True)
write(path,kernel)
source.update(built_not_deployed=False,deployed=True,deployed_stage=276,physical_lens_with_all_sensors_suspended_verified=True,
 physical_vio_only_intervention_not_yet_verified=True,
 physical_evidence='reference/kernel276/lens-initial-validation.json',deployment_evidence='reference/kernel276/postboot-identity-validation.json')
write(R/'source-candidate-validation.json',source)
report=dict(stage=276,canonical_recipes_and_actual_deployment_locks_updated=True,prior_r21_recipes_and_boot273_locks_archived=True,
 modules=776,packages=961,packages_built=13,packages_installed=7,source_commit=source['candidate_commit'],
 standard_manual_focus_verified=True,autofocus_algorithm_not_implemented=True,ssc_normal_start_observed=True,
 old_eperm_root_cause_unresolved=True,physical_rotation_retest_pending=True,full_kernel_and_rootfs_build_pending=True,goal_status='active_incomplete')
write(R/'source-promotion-validation.json',report);print(json.dumps(report,indent=2))
