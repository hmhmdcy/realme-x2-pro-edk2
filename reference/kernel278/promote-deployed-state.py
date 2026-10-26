"""Promote verified r24 single-auto AF while retaining the exact276 kernel identity."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1]
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
h=read(R/'final-health-validation.json');af=read(R/'native-af-r1-validation.json');ae=read(R/'ae-af-r1-validation.json')
assert h['camera_idle_health']['passed'] and h['current50_payloads_verified']==50 and h['all776_modules_unchanged']
assert af['error'] is None and len(af['runs'])==5 and ae['error'] is None and ae['standard_single_auto_af_focused']
assert read(R/'four-camera-regression-validation.json')['passed'] and read(R/'package-install-validation.json')['packages_verified']
assert read(R/'af-selected-preview-validation.json')['error'] is None
archive=W/'archive/camera-before278-2026-10-18';archive.mkdir()
for p in [W/'linux-port/packages/libcamera',W/'linux-port/packages/samurai-camera-config',W/'linux-port/camera/deployment-lock.json',W/'linux-port/camera/kernel/source-lock.json',W/'NEXT-SESSION.md']:
 dest=archive/p.relative_to(W);dest.parent.mkdir(parents=True,exist_ok=True)
 if p.is_dir():shutil.copytree(p,dest)
 else:shutil.copyfile(p,dest)
write(archive/'snapshot-sha256.json',{str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()})
for name,version in [('libcamera','99990.7.2-r24'),('samurai-camera-config','0.1.0-r19')]:
 dest=W/'linux-port/packages'/name
 for p in (R/'recipes'/name).iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 write(dest/'source-lock.json',dict(stage=278,build_stage=278,build_attempt=3,package_version=version,
  source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name not in ['README.md','source-lock.json']},
  actual_signed_build_validation='reference/kernel278/r24-package-build-validation.json',native_install_validation='reference/kernel278/package-install-validation.json',
  actual_current_payload_validation='reference/kernel278/final-health-validation.json',package_payload_features_preserved=True,private_keys_not_in_sources=True,
  s5k3m5_native_gain_pair_still_required=True,gw1_helper_native_gain_codes=[32,1024],
  autofocus_supported_modes=['Auto'],autofocus_algorithm_implemented=True,continuous_af_implemented=False,manual_distance_map_calibrated=False,
  standard_af_validation='reference/kernel278/native-af-r1-validation.json',auto_exposure_af_validation='reference/kernel278/ae-af-r1-validation.json',
  high_resolution_manual_transition_validation_pending=True,profile_only_in_device_data_package=True))
 p=dest/'README.md';p.write_text('278当前：r24/config-r19已部署通用单次AF、帧携带清晰度统计与串号回执的标准镜头控制，原生触发/取消/重触发/停流及自动曝光下AF通过。模组行程/搜索参数仅在设备数据包。配对测试单次AF约9–12秒，仍需加速；连续AF、距离标定、完整画质、GUI/录像和Spectra未完成。[278证据](../../../reference/kernel278/README.md)。以下按历史阶段阅读。\n\n'+p.read_text())
path=W/'linux-port/camera/deployment-lock.json';d=read(path)
pkgs=read(host.PRIVATE/'camera-forward-repo-r24/package-manifest.json')['packages'];selected=set(h['package_versions'])
d.update(stage=278,kernel_boot_stage=276,current_boot_guard_stage=276,kernel_image_stage=183,
 framework_version='99990.7.2-r24',configuration_version='0.1.0-r19',
 built_packages=[{k:p[k] for k in ['name','version','arch','file','bytes','sha256']} for p in pkgs],installed_package_payloads=[p for p in pkgs if p['name'] in selected],
 current_camera_evidence='../../reference/kernel278/README.md',final_health_evidence='../../reference/kernel278/final-health-validation.json',goal_status='active_incomplete',
 previous_lock_archive='../../archive/camera-before278-2026-10-18/linux-port/camera/deployment-lock.json',
 current_stack_four_camera_regression='../../reference/kernel278/four-camera-regression-validation.json',
 main_camera_autofocus_verified=True,main_camera_single_auto_af_verified=True,main_camera_continuous_af_verified=False,main_camera_manual_distance_map_verified=False,
 autofocus_verified_scope='GW1: standard Auto trigger/cancel, fixed and automatic exposure; full AF feature set and calibration incomplete',
 current_stack_main_camera_focus_evidence='../../reference/kernel278/native-af-r1-validation.json',
 current_stack_main_camera_auto_exposure_af='../../reference/kernel278/ae-af-r1-validation.json',
 current_stack_main_camera_scene='../../reference/kernel278/af-selected-preview-validation.json',current_stack_visual_scene_review_pending=False,
 current_stack_main_camera_scene_is_later_session=True,current_r24_manual_transition_validation_pending=True,
 spectra_hardware_image_processing_supported=False,current_stack_gui_validation_pending=True,immutable_focus_metric_transport_verified=True,
 af_profile_sha256=hashlib.sha256((R/'s5kgw1.yaml').read_bytes()).hexdigest(),af_profile_not_factory_distance_calibration=True)
if 'current_r23_manual_transition_validation_pending' in d:d['historical_r23_manual_transition_not_retested']=d.pop('current_r23_manual_transition_validation_pending')
d['system_services'].update(stage=278,new_processes=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in h['services'] if p['comm'] in ['pipewire','wireplumber']],
 current_manifest='/var/lib/samurai/k278-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False)
write(path,d)
path=W/'linux-port/camera/kernel/source-lock.json';k=read(path)
k.update(stage=278,current_camera_userspace_stage=278,boot_stage=276,
 previous_lock_archive='../../../archive/camera-before278-2026-10-18/linux-port/camera/kernel/source-lock.json',
 userspace_focus_statistics_evidence='../../../reference/kernel278/native-af-r1-validation.json',
 current_r24_manual_transition_retest_pending=True,single_auto_af_implemented_in_userspace=True,
 autofocus_full_feature_set_not_complete=True,spectra_not_complete=True)
if 'current_r23_manual_transition_retest_pending' in k:k['historical_r23_manual_transition_not_retested']=k.pop('current_r23_manual_transition_retest_pending')
if 'autofocus_and_spectra_not_complete' in k:k['autofocus_and_spectra_not_complete']=True
write(path,k)
for n in ['af-source-validation.json','package-source-validation.json']:
 p=R/n;s=read(p);s.update(not_built_or_deployed=False,deployed=True,deployed_stage=278,physical_af_evidence='reference/kernel278/native-af-r1-validation.json');write(p,s)
write(R/'source-promotion-validation.json',dict(stage=278,canonical_r24_r19_recipes_and_locks_promoted=True,prior_r23_r18_recipes_and_277_locks_archived=True,
 boot_still276=True,all776_modules_preserved=True,standard_single_auto_af_physically_verified=True,automatic_exposure_af_verified=True,
 continuous_af_and_manual_distance_not_implemented=True,spectra_not_complete=True,goal_status='active_incomplete'))
print('Canonical r24/r19 promoted with module-only AF data; kernel/boot guard remain276')
