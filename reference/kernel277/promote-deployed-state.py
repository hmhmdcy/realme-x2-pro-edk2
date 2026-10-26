"""Promote actual r23 userspace, leaving kernel/boot identity at verified276."""
from pathlib import Path
import hashlib,json,shutil
import host
R=Path(__file__).resolve().parent;W=R.parents[1]
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
h=read(R/'final-health-validation.json');test=read(R/'focus-metadata-r1-validation.json')
assert h['camera_idle_health']['passed'] and h['current49_payloads_verified']==49 and h['all776_modules_unchanged']
assert test['error'] is None and all(x['metadata_matches_same_request_raw'] for x in test['runs'])
assert read(R/'four-camera-regression-validation.json')['passed'] and read(R/'package-install-validation.json')['packages_verified']
archive=W/'archive/camera-before277-2026-10-18';archive.mkdir()
for p in [W/'linux-port/packages/libcamera',W/'linux-port/packages/samurai-camera-config',W/'linux-port/camera/deployment-lock.json',W/'linux-port/camera/kernel/source-lock.json',W/'NEXT-SESSION.md']:
 dest=archive/p.relative_to(W);dest.parent.mkdir(parents=True,exist_ok=True)
 if p.is_dir():shutil.copytree(p,dest)
 else:shutil.copyfile(p,dest)
write(archive/'snapshot-sha256.json',{str(p.relative_to(archive)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()})
for name,version in [('libcamera','99990.7.2-r23'),('samurai-camera-config','0.1.0-r18')]:
 dest=W/'linux-port/packages'/name
 for p in (R/'recipes'/name).iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 write(dest/'source-lock.json',dict(stage=277,build_stage=277,package_version=version,
  source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name not in ['README.md','source-lock.json']},
  actual_signed_build_validation='reference/kernel277/r23-package-build-validation.json',native_install_validation='reference/kernel277/package-install-validation.json',
  actual_current_payload_validation='reference/kernel277/final-health-validation.json',package_payload_features_preserved=True,private_keys_not_in_sources=True,
  s5k3m5_native_gain_pair_still_required=True,gw1_helper_native_gain_codes=[32,1024],
  standard_focus_fom_metadata_validation='reference/kernel277/focus-metadata-r1-validation.json',
  high_resolution_manual_transition_validation_pending=True,autofocus_algorithm_implemented=False))
 p=dest/'README.md';p.write_text('277当前：r23/config-r18已部署通用RAW空间清晰度统计和标准FocusFoM，主摄同请求RAW重算与元数据逐帧一致，失焦与恢复对照通过；保留完整功能。AF搜索/距离标定、GUI/录像和Spectra仍未完成。[实际部署](../../../reference/kernel277/README.md)。以下按历史阶段阅读。\n\n'+p.read_text())
path=W/'linux-port/camera/deployment-lock.json';d=read(path)
pkgs=read(host.PRIVATE/'camera-forward-repo-r23/package-manifest.json')['packages'];selected=set(h['package_versions'])
d.update(stage=277,kernel_boot_stage=276,current_boot_guard_stage=276,kernel_image_stage=183,
 framework_version='99990.7.2-r23',configuration_version='0.1.0-r18',
 built_packages=[{k:p[k] for k in ['name','version','arch','file','bytes','sha256']} for p in pkgs],
 installed_package_payloads=[p for p in pkgs if p['name'] in selected],current_camera_evidence='../../reference/kernel277/README.md',
 final_health_evidence='../../reference/kernel277/final-health-validation.json',goal_status='active_incomplete',
 previous_lock_archive='../../archive/camera-before277-2026-10-18/linux-port/camera/deployment-lock.json',
 current_stack_four_camera_regression='../../reference/kernel277/four-camera-regression-validation.json',
 main_camera_standard_focus_fom_verified=True,main_camera_focus_metadata_matches_same_request_raw=True,
 current_stack_main_camera_focus_evidence='../../reference/kernel277/focus-metadata-r1-validation.json',
 current_stack_visual_scene_review_pending=True,current_r23_manual_transition_validation_pending=True,
 main_camera_autofocus_verified=False,spectra_hardware_image_processing_supported=False,current_stack_gui_validation_pending=True)
if 'current_r22_manual_transition_validation_pending' in d:d['historical_r22_manual_transition_not_retested']=d.pop('current_r22_manual_transition_validation_pending')
if 'current_stack_main_camera_scene' in d:d['historical_boot276_main_camera_scene']=d.pop('current_stack_main_camera_scene')
d['system_services'].update(stage=277,new_processes=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in h['services'] if p['comm'] in ['pipewire','wireplumber']],
 current_manifest='/var/lib/samurai/k277-services-verified-private.json',ssc_running=True,temporary_nodeps_desktop_start=False)
write(path,d)
path=W/'linux-port/camera/kernel/source-lock.json';k=read(path)
k.update(stage=277,current_camera_userspace_stage=277,boot_stage=276,
 previous_lock_archive='../../../archive/camera-before277-2026-10-18/linux-port/camera/kernel/source-lock.json',
 userspace_focus_statistics_evidence='../../../reference/kernel277/focus-metadata-r1-validation.json',
 current_r23_manual_transition_retest_pending=True,autofocus_and_spectra_not_complete=True)
if 'current_r22_manual_transition_retest_pending' in k:k['historical_r22_manual_transition_not_retested']=k.pop('current_r22_manual_transition_retest_pending')
write(path,k)
for n in ['focus-source-validation.json','package-source-validation.json']:
 p=R/n;s=read(p);s.update(not_built_or_deployed=False,deployed=True,deployed_stage=277,physical_metadata_evidence='reference/kernel277/focus-metadata-r1-validation.json');write(p,s)
write(R/'source-promotion-validation.json',dict(stage=277,canonical_r23_r18_recipes_and_locks_promoted=True,
 prior_r22_r17_recipes_and_276_locks_archived=True,boot_still276=True,all776_modules_preserved=True,
 focus_fom_metadata_physically_verified=True,autofocus_and_spectra_not_complete=True,goal_status='active_incomplete'))
print('Canonical recipes r23/r18 promoted; kernel, boot and guard remain276')
