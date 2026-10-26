from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for leaf in ['pipeline','ipe','cancel','build','intree-build','attempts','current-state']:
 assert read(HERE/(leaf+'-validation.json'))['passed']
runtime=read(HERE/'pipeline-runtime-r5-validation.json');assert runtime['passed']
state=read(HERE/'source-state.json');last=runtime['device_result'];m2m=runtime['m2m_after_client']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==386
 d.update(stage=387,latest_work_stage=387,current_camera_evidence=prefix+'reference/kernel387/README.md',current_device_revalidated_stage=387,
  device_closeout_evidence=prefix+'reference/kernel387/current-state-validation.json',in_progress_stage=387,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel387/README.md',
  a5_icp_candidate_source_commit=state['commit'],a5_icp_candidate_source_branch=state['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_device_experiment_stage=387,ipe_latest_hardware_stage=387,
  icp_sys_init_evidence=prefix+'reference/kernel387/pipeline-runtime-r5-validation.json',ipe_sessions_hardware_evidence=prefix+'reference/kernel387/pipeline-runtime-r5-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel387/pipeline-runtime-r5-validation.json',ipe_preboot_reset_ack_evidence=prefix+'reference/kernel387/pipeline-runtime-r5-validation.json',
  ipe_image_frames_submitted=last['image_frames'],ipe_latest_stage_actual_frames=m2m['completed'],ipe_latest_stage_RT_frames=m2m['completed'],ipe_latest_stage_non_RT_frames=0,
  ipe_latest_stage_frames_scope='final successful r5 libcamera run only',ipe_libcamera_pipeline_integrated=True,ipe_libcamera_pipeline_hardware_verified=True,ipe_libcamera_candidate_permanently_installed=False,
  ipe_libcamera_pipeline_evidence=prefix+'reference/kernel387/pipeline-validation.json',ipe_libcamera_original_sof_and_timestamp_preserved=True,ipe_libcamera_raw_only_kept=True,ipe_libcamera_isolated_ipa_verified=True,
  ipe_m2m_evidence=prefix+'reference/kernel387/pipeline-runtime-r5-validation.json',ipe_m2m_platform_owner_temporary=True,ipe_zero_copy_verified=False,
  ipe_m2m_cancel_counter_separate_from_errors=True,ipe_actual_cancel_branch_verified=False,
  icp_next_step='Advance direct SG/DMABUF DMA to remove core CPU copies, formal platform ownership and board deployment; explicitly test in-flight cancellation/error concurrency, then OEM Gamma/LTM/CCM full IQ and remaining multi-camera calibration. Stage387 final r5 integrated actual libcamera: four sensors12 frames each, dual RAW6, isolated controls28 =82 IPE completed, errors0; RAW-only6 uses no IPE. No permanent install.',
  latest_stage_device_mutated=True,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=state['branch'],maintained_commit=state['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through386-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel387/README.md。387实际libcamera→IPE候选r5通过：四摄各12帧、RAW+NV12六请求/原始SOF时间戳、RAW-only六请求不启IPE、隔离IPA28帧五阶段GammaACK1，共IPE82成功/取消0/错误0。源8003933b7e31e4b5f4d27d21789d42da686831ba branch samurai-ipe-pipeline387，仅媒体driver标识/取消计数变更，core仍386二进制；libcamera387-ipe-built保存final patch，common dispatcher/IPA未改，独立timer及STREAMOFF失败拒绝复用。未永久安装，Image363/boot366/DT365/r29/r24保持，五次workers终态/临时模块FW清理/PW-WP恢复，guard378用host387。r1～r4失败保留，特别r3旧failed1不能反称取消已验证；r5未测实际取消。下一步直接SG/DMABUF去复制、正式平台owner与板级部署、显式取消/错误并发及完整IQ/剩余校准。383读hook陷阱和373/375/376/379、381DMA回收、377/378失败审计保留。现场低照度，黑噪点不单独判故障；目标active未完成。\n')
p=ROOT/'sessions/INDEX.md';p.write_text(p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [387 四摄libcamera接入IPE与82帧实机](../reference/kernel387/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[386 V4L2 m2m入口与18帧实机](reference/kernel386/README.md)','[387 四摄libcamera接入IPE与82帧实机](reference/kernel387/README.md)',1))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('386当前：')
 p.write_text('387当前：四摄实际libcamera→IPE、RAW配对及隔离IPA候选验证通过，最终82个IPE作业/处理错误0；RAW-only保持原路径。临时模块/固件已清理、服务恢复，未永久安装。零拷贝、正式平台owner与完整IQ/多摄校准仍待，目标active。[387证据]('+prefix+'reference/kernel387/README.md)。以下为历史。\n'+rest)
print('Stage387 checkpoint saved; complete camera/ISP goal remains active.')
