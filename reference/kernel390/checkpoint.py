from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for leaf in ['preflight','staging','module-install','pre-transition','postboot','runtime-r2','reload','pixels','hardware','rollback','installed-packages','current-state','attempts']:
 assert read(HERE/(leaf+'-validation.json'))['passed']
assert not read(HERE/'runtime-r1-validation.json')['passed']
state=read(HERE.parent/'kernel389/source-state.json');build=read(HERE.parent/'kernel389/intree-build-validation.json');mods={r['name']:r for r in build['modules']};dt=read(HERE.parent/'kernel389/dt-build-validation.json');boot=read(HERE.parent/'kernel389/build-package-validation.json');current=read(HERE/'current-state-validation.json')
private=Path('/mnt/e/edk2-samurai-out/kernel390');camss_note=hashlib.sha256((private/'qcom-camss.note').read_bytes()).hexdigest()
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==389
 historical={k:d[k] for k in ['current_boot_tele_hardware_frames','current_boot_tele_ae_frames','current_boot_tele_ae_effective_revisions_stage306','current_boot_tele_ae_control_writes_stage306'] if k in d}
 if historical:d['prior_boot_metrics_before390']=historical
 for k in historical:d[k]=None
 d.update(stage=390,latest_work_stage=390,current_camera_evidence=prefix+'reference/kernel390/README.md',current_device_revalidated_stage=390,
  device_closeout_evidence=prefix+'reference/kernel390/current-state-validation.json',current_readonly_device_evidence=prefix+'reference/kernel390/current-state-validation.json',
  in_progress_stage=390,in_progress_installed=True,in_progress_evidence=prefix+'reference/kernel390/README.md',
  in_progress_installed_scope='normal kernel platform owner, five modules, firmware and board DT installed; IPE userspace still private387 candidate',
  kernel_boot_stage=389,boot_stage=389,boot_deployment_stage=390,current_boot_guard_stage=390,current_boot_guard_path='/var/lib/samurai/k390-active/boot-id-private.txt',
  current_boot_guard_evidence=prefix+'reference/kernel390/postboot-validation.json',current_boot_evidence=prefix+'reference/kernel390/postboot-validation.json',
  boot_sha256=boot['boot_sha256'],dtb_sha256=dt['dtb_sha256'],current_dt_stage=389,effective_dt_stage=389,logdump_dt_stage=365,
  logdump_fat_dtb_sha256=read(HERE.parent/'kernel365/dt-build-validation.json')['dtb_sha256'],
  actual_kernel_image_stage=363,kernel_image_stage=363,actual_kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',
  actual_image_source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8',actual_kernel_image_source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8',
  actual_board_dt_source_commit=state['commit'],current_camss_module_stage=389,current_camss_module_deployment_stage=390,
  current_camss_module_sha256=mods['qcom-camss']['sha256'],current_camss_module_note_sha256=camss_note,module_build_evidence=prefix+'reference/kernel389/intree-build-r4-validation.json',
  candidate_source_evidence=prefix+'reference/kernel389/source-state.json',a5_icp_candidate_source_commit=state['commit'],a5_icp_candidate_source_branch=state['branch'],a5_icp_candidate_source_installed=True,
  icp_hardware_backend_installed=True,icp_static_dt_default_disabled=True,icp_board_dt_enabled=True,icp_runtime_dt_status='okay',
  ipe_m2m_platform_owner_temporary=False,ipe_candidate_formal_platform_hardware_verified=True,ipe_normal_platform_owner_hardware_evidence=prefix+'reference/kernel390/hardware-validation.json',
  ipe_latest_hardware_stage=390,icp_latest_device_experiment_stage=390,icp_sys_init_evidence=prefix+'reference/kernel390/hardware-validation.json',
  ipe_sessions_hardware_evidence=prefix+'reference/kernel390/hardware-validation.json',ipe_config_io_hardware_evidence=prefix+'reference/kernel390/hardware-validation.json',
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel390/hardware-validation.json',ipe_m2m_evidence=prefix+'reference/kernel390/hardware-validation.json',
  ipe_image_frames_submitted=12,ipe_latest_stage_actual_frames=111,ipe_latest_stage_RT_frames=111,ipe_latest_stage_non_RT_frames=0,
  ipe_latest_stage_frames_scope='390 normal platform: native18 + pipeline81 before reload + candidate12 after reload; current counter reset to12; original IFE48 excluded',
  ipe_libcamera_pipeline_hardware_verified=True,ipe_libcamera_pipeline_evidence=prefix+'reference/kernel390/hardware-validation.json',ipe_libcamera_candidate_permanently_installed=False,
  ipe_original_standard_dma_sg_restored=False,ipe_modified_standard_dma_sg_owner_api_installed=True,
  ipe_export_fd_and_mmap_owner_lifetime_verified=True,ipe_export_lifetime_hardware_owner='qcom_camss',ipe_actual_cancel_branch_verified=False,
  installed_userspace_evidence=prefix+'reference/kernel362/install-r1-validation.json',installed_userspace_current_versions_evidence=prefix+'reference/kernel390/installed-packages-validation.json',
  current_boot_auto_af_retest_pending=True,current_boot_auto_af_retest_scope='No independent optical or AF scene retest390; prior scoped implementation evidence retained.',
  current_boot_optical_scene_retest_pending=True,current_boot_tele_delivered_test_frames=24,current_boot_tele_test_scope='Two12-frame GStreamer captures (candidate IPE and installed original IFE); no exhaustive sensor-frame or dedicated AE count claimed',
  ssc_currently_healthy=None,ssc_current_service_running=True,ssc_intermittent_failure_not_claimed_fixed=True,
  installed_module_baseline_count=778,installed_new_module_files_stage390=3,installed_replaced_module_files_stage390=2,
  module_count_scope='Derived original778 tree plus3 explicitly absent-before new modules; no new all-module hash audit',
  icp_next_step='Package and install the verified387 IPE userspace integration on the normal390 kernel/board platform; then explicit in-flight cancellation/hardware failure concurrency and OEM Gamma/LTM/CCM full IQ plus all remaining camera calibration. Normal platform111 direct frames, unload/reload and original IFE four-camera regression verified. Guard390; do not run old378 host or reflash the completed transition.',
  latest_stage_device_mutated=True,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'module_count' in d:d['module_count']=781
 if 'kernel_module_count' in d:d['kernel_module_count']=781
 if 'maintained_commit' in d:d.update(maintained_branch=state['branch'],maintained_commit=state['commit'])
 if 'kernel_source_commit' in d:d.update(kernel_source_commit=state['commit'],kernel_source_branch=state['branch'],kernel_source_scope='maintained module and board source; Image363 source separately recorded')
 if 'deployed_camera_modules' in d:
  for name in ['qcom-camss','qcom-camss-icp-a5-core','camss-icp-a5-m2m','v4l2-mem2mem','videobuf2-dma-sg']:
   d['deployed_camera_modules'][name.replace('-','_')]=dict(sha256=mods[name]['sha256'],loaded=True,loaded_note_matches_disk=True,intree='Y',parameters={},targeted_validation_stage=390)
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through389-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel390/README.md。390已实际部署389正常CAMSS/ICP同模块owner、五模块+原厂FW和正式板级DT；一次正常重启只刷boot，Image363/logdump365不变。新guard=/var/lib/samurai/k390-active/boot-id-private.txt，必须用host390，旧378guard已失效。正常icp@ac10000绑定，无test/overlay。原生18+实际四摄/RAW/隔离IPA81，再正常模块卸载重载后12，共111 direct/0copy/0cancel/0failed；原r29 IFE四摄各12回归，电源时钟归零/服务恢复。r1只因collector旧文件名在管线首帧前停，native成功保留；r2只补管线，不重复计数。模块重载后当前counter12，owner_refs53是普通桌面FD。维护源a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07 branch samurai-icp-platform389，干净；先mounted_build。原两模块和boot366离线回退保存，恢复工具未执行。用户空间仍r29/config-r24，IPE库仍387私有候选；下一步正式IPE用户空间包，显式取消/硬件错误并发、原厂完整IQ和363全部剩余范围（第五2MP/多模式/帧长/几何/同步/连续AF）。低照度按黑噪点解释，完整目标active未完成。\n')
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[389 正式CAMSS/ICP平台与板级部署候选](reference/kernel389/README.md)','[390 正式CAMSS/ICP部署与111帧实机](reference/kernel390/README.md)',1))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('389当前：')
 p.write_text('390当前：正常CAMSS/ICP与板级DT已实际部署，111帧direct及正常卸载/重载通过，原r29 IFE四摄回归通过；Image363/logdump365保持，guard390。IPE用户空间仍私有候选，完整IQ/多摄校准目标active。[390证据]('+prefix+'reference/kernel390/README.md)。以下为历史。\n'+rest)
print('Stage390 deployed normal platform checkpoint saved; full camera/ISP goal remains active.')
