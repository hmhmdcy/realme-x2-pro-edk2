from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for leaf in ['dma','transfer','export-owner','export-client-build','intree-build','framework-runtime','framework-pixels','current-state','staging-r1']:
 assert read(HERE/(leaf+'-validation.json'))['passed']
failed=read(HERE/'dma-runtime-r1-validation.json');assert not failed['passed'] and failed['terminal'] and failed['core_absent'] and failed['test_absent'] and not failed['new_relevant_fault_count']
audit=dict(stage=388,native_r1=dict(passed=False,images_submitted=0,debug_dma_only_sg_page_assumption_fixed=True,old_errno_not_recorded=True,cleaned=True),
 pipeline_upload_r1=read(HERE/'staging-r1-validation.json'),wrapper_prototype_built_but_never_deployed=True,wrapper_reverted_due_to_deferred_inner_release=True,
 early_successes_do_not_prove_final_owner_api=True,final_framework_r1_passed=True,closeout_diff_format_comparison_fixed=True,passed=True)
(HERE/'attempts-validation.json').write_text(json.dumps(audit,indent=2)+'\n')
p=HERE/'export-owner-design.json';d=read(p);d['not_yet_runtime_verified']=False;d.update(actual_export_fd_and_vma_lifetime_verified=True,runtime_evidence='framework-runtime-r1-validation.json');p.write_text(json.dumps(d,indent=2)+'\n')
state=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==387
 d.update(stage=388,latest_work_stage=388,current_camera_evidence=prefix+'reference/kernel388/README.md',current_device_revalidated_stage=388,
  device_closeout_evidence=prefix+'reference/kernel388/current-state-validation.json',in_progress_stage=388,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel388/README.md',
  a5_icp_candidate_source_commit=state['commit'],a5_icp_candidate_source_branch=state['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_device_experiment_stage=388,ipe_latest_hardware_stage=388,
  icp_sys_init_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',ipe_sessions_hardware_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',ipe_preboot_reset_ack_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',
  ipe_image_frames_submitted=27,ipe_latest_stage_actual_frames=99,ipe_latest_stage_RT_frames=99,ipe_latest_stage_non_RT_frames=0,
  ipe_latest_stage_frames_scope='final framework-r1 native18 and libcamera81; earlier attempts excluded',
  ipe_libcamera_pipeline_integrated=True,ipe_libcamera_pipeline_hardware_verified=True,ipe_libcamera_candidate_permanently_installed=False,
  ipe_libcamera_pipeline_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',ipe_libcamera_original_sof_and_timestamp_preserved=True,ipe_libcamera_raw_only_kept=True,ipe_libcamera_isolated_ipa_verified=True,
  ipe_m2m_evidence=prefix+'reference/kernel388/framework-runtime-r1-validation.json',ipe_m2m_platform_owner_temporary=True,ipe_zero_copy_verified=True,
  ipe_zero_copy_scope='native m2m and candidate libcamera core image transfers only; no universal application/display or implicit-fence claim',
  ipe_direct_dma_owner_api_required=True,ipe_direct_dma_candidate_requires_modified_standard_dma_sg=True,ipe_original_standard_dma_sg_restored=True,
  ipe_export_fd_and_mmap_owner_lifetime_verified=True,ipe_m2m_cancel_counter_separate_from_errors=True,ipe_actual_cancel_branch_verified=False,
  icp_next_step='Formal SoC platform owner and board deployment, explicit in-flight cancel and hardware failure concurrency, then OEM Gamma/LTM/CCM full IQ and all remaining multi-camera calibration. Stage388 final framework-r1 direct99/copy0/cancel0/failed0; actual exported FD and mmap owner pins verified; original SG/CAMSS restored and installed four-camera regression passed. No permanent install.',
  latest_stage_device_mutated=True,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=state['branch'],maintained_commit=state['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through387-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel388/README.md。388已去核心图像复制，最终95caf30a629bbaf454ebfc9ed25ce16ea3a952b5 branch samurai-ipe-direct-dma388；新标准SG owner API+adapter，公共vb2 ABI不改。framework-r1临时替换SG后原生18+实际libcamera81共99 direct/0copy/0cancel/0failed；导出FD与mmap保留owner到最后munmap实测通过；原SG/CAMSS已恢复且四摄各12帧回归，临时模块FW清理、PW/WP恢复。未永久安装，Image363/boot366/DT365/r29/r24不变。原SG不能直接加载新adapter，必须完整事务或部署。libcamera复用387，源码/最终patch已核对，mounted_build保护继续。native-r1 DEBUG SG页字段错误已修，pipeline上传r1孤立接收进程已核对终止；wrapper原型从未部署且已revert。下一步正式平台owner/板级启用、实测在途取消/硬件错误并发、原厂完整IQ及363全部剩余范围；第五2MP/多模式/几何/同步/连续AF仍待。低照度按黑场噪点解释。完整目标active未完成。\n')
p=ROOT/'sessions/INDEX.md';p.write_text(p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [388 IPE直接DMA、导出所有权与99帧实机](../reference/kernel388/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[387 四摄libcamera接入IPE与82帧实机](reference/kernel387/README.md)','[388 IPE直接DMA、导出所有权与99帧实机](reference/kernel388/README.md)',1))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('387当前：')
 p.write_text('388当前：IPE核心直接DMA，原生18＋libcamera81共99帧通过，导出FD/mmap平台所有权实测；原SG/CAMSS恢复后四摄回归通过。未永久安装，正式平台/板级部署、硬件错误并发与完整IQ/多摄校准仍待，目标active。[388证据]('+prefix+'reference/kernel388/README.md)。以下为历史。\n'+rest)
(HERE/'IN-PROGRESS.md').write_text('# 388已保存检查点\n\n以README.md、handoff.md、source-state.json和framework-runtime-r1-validation.json为准。最终直接DMA与owner API实机通过，原SG/CAMSS已恢复，所有worker终态。完整多摄/ISP目标继续active，后续范围见NEXT-SESSION.md；不要再按旧进行中笔记重复运行事务。\n')
print('Stage388 saved; full camera/ISP goal remains active.')
