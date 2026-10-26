from pathlib import Path
import copy,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
assert json.loads((HERE/'current-state-validation.json').read_text())['passed']
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
artifacts=json.loads((HERE/'package-artifact-validation.json').read_text())
installed=json.loads((HERE/'install-r2-validation.json').read_text());current=json.loads((HERE/'current-state-validation.json').read_text())
for package in ['libcamera','samurai-camera-config']:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';d=json.loads(p.read_text())
 d.update(candidate_only=False,installed=True,native_install_validation='reference/kernel391/install-r2-validation.json',actual_current_payload_validation='reference/kernel391/current-state-validation.json',candidate_package_validation='reference/kernel391/package-artifact-validation.json',matched_camss_driver_stage=389,matched_platform_deployment_stage=390,combined_candidate_hardware_verified=True,ipe_pipeline_included=True)
 save(p,d)
 dest=ROOT/'linux-port/packages'/package
 for file in recipe.iterdir():
  if file.is_file():shutil.copyfile(file,dest/file.name)
kernel=json.loads((ROOT/'linux-port/camera/kernel/source-lock.json').read_text())
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(stage=391,in_progress_stage=391,latest_work_stage=391,current_device_revalidated_stage=391,icp_latest_device_experiment_stage=391,framework_version='99990.7.2-r30',configuration_version='0.1.0-r25',candidate_framework_version='99990.7.2-r30',candidate_configuration_version='0.1.0-r25',ipe_latest_hardware_stage=391,ipe_latest_stage_actual_frames=94,ipe_latest_stage_frames_scope='391 newly installed r30/r25: r1 camera suite82 + r2 ordinary-user PipeWire12; r1 reused in r2 without rerun; previous counter12 excluded; final cumulative106',ipe_libcamera_candidate_permanently_installed=True,in_progress_installed_scope='normal kernel platform owner, five modules, firmware and board DT390; signed IPE userspace r30/r25 now installed391',current_boot_auto_af_retest_scope='No new optical or AF scene validation391; previous scoped implementation evidence retained.',icp_next_step='Explicit in-flight cancellation and hardware-error concurrency; OEM Gamma/LTM/CCM full IQ and all363 remaining camera scope. Signed IPE userspace r30/r25 installed391; same390 boot guard. Do not replay completed390 deployment or391 package transactions.')
 for key,name in [('current_camera_evidence','README.md'),('in_progress_evidence','README.md'),('device_closeout_evidence','current-state-validation.json'),('current_readonly_device_evidence','current-state-validation.json'),('installed_userspace_current_versions_evidence','install-r2-validation.json'),('ipe_libcamera_pipeline_evidence','hardware-validation.json')]:d[key]=prefix+'kernel391/'+name
 d['ipe_installed_default_gstreamer_pipewire_verified']=True;d['ipe_userspace_deployment_stage']=391
 if relative.endswith('deployment-lock.json'):
  d.update(built_packages=artifacts['packages'],installed_camera_packages=installed['packages'],ko_count=781,kernel_modules=copy.deepcopy(kernel['deployed_camera_modules']),guard_path='/var/lib/samurai/k390-active/boot-id-private.txt',final_health_evidence=prefix+'kernel391/current-state-validation.json',system_services=dict(stage=391,services=current['services'],evidence=prefix+'kernel391/current-state-validation.json',current_boot_revalidated=True))
 save(p,d)
archive=ROOT/'archive/NEXT-SESSION-through390-2026-10-21.md'
assert not archive.exists();shutil.copyfile(ROOT/'NEXT-SESSION.md',archive)
for relative,link in [('linux-port/camera/README.md','../../reference/kernel391/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel391/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel391/README.md')]:
 p=ROOT/relative;s=p.read_text();s=s.split('\n\n',1)[1]
 lead='391当前：正式r30/r25 IPE用户空间已安装，默认四摄／RAW／隔离IPA82作业＋普通用户PipeWire12，共94新增direct、错误0；r1错误进程映射检查已审计并回退，r2修正复用82作业。内核／板级390与个体配置保持，完整IQ／多摄校准目标active。'
 p.write_text(lead+'[391证据]('+link+')。以下为历史。\n\n'+s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[390 正式CAMSS/ICP部署与111帧实机](reference/kernel390/README.md)','[391 正式IPE用户空间与94作业实机](reference/kernel391/README.md)');p.write_text(s)
print(json.dumps(dict(recipes_updated=True,locks_updated=True,prior_checkpoint_archived=True,passed=True)))
