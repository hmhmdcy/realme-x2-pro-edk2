from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['m2m','worker','ready','intree-build','client-build','pixels','attempts','current-state']:assert read(HERE/(name+'-validation.json'))['passed']
assert read(HERE/'m2m-runtime-r4-validation.json')['passed']
state=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==385
 d.update(stage=386,latest_work_stage=386,current_camera_evidence=prefix+'reference/kernel386/README.md',current_device_revalidated_stage=386,
  device_closeout_evidence=prefix+'reference/kernel386/current-state-validation.json',in_progress_stage=386,
  in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel386/README.md',
  a5_icp_candidate_source_commit=state['commit'],a5_icp_candidate_source_branch=state['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_device_experiment_stage=386,ipe_latest_hardware_stage=386,
  icp_sys_init_evidence=prefix+'reference/kernel386/m2m-runtime-r4-validation.json',
  ipe_sessions_hardware_evidence=prefix+'reference/kernel386/m2m-runtime-r4-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel386/m2m-runtime-r4-validation.json',
  ipe_pixel_transfer_evidence=prefix+'reference/kernel386/pixels-validation.json',
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel386/m2m-runtime-r4-validation.json',
  ipe_image_frames_submitted=8,ipe_latest_stage_actual_frames=18,ipe_latest_stage_RT_frames=18,ipe_latest_stage_non_RT_frames=0,
  ipe_v4l2_m2m_adapter_available=True,ipe_v4l2_m2m_hardware_verified=True,
  ipe_m2m_evidence=prefix+'reference/kernel386/m2m-runtime-r4-validation.json',
  ipe_m2m_mmap_and_dmabuf_export_import_verified=True,ipe_m2m_padded_stride_and_source_offset_verified=True,
  ipe_m2m_two_contexts_verified=True,ipe_m2m_platform_owner_temporary=True,
  ipe_zero_copy_verified=False,ipe_libcamera_pipeline_integrated=False,
  icp_next_step='Integrate libcamera V4L2M2MDevice into the real camera pipeline after checking CAMSS NV12 plane layout and request metadata/lifetime; validate in-flight cancellation, then direct SG/DMABUF DMA, formal platform ownership and OEM Gamma/LTM/CCM/full calibration. Stage386 V4L2 client verified18 frames via MMAP/DMABUF with source offset16/stride672/two contexts; CPU copies remain.',
  latest_stage_device_mutated=True,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=state['branch'],maintained_commit=state['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through385-2026-10-21.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel386/README.md。386新增V4L2 m2m适配/媒体拓扑，真实客户端18帧MMAP、NV21 DMABUF源offset16/stride672、双同时streaming上下文、STREAMOFF/close通过；Y逐帧客户端相等、输入CRC主机复核、每组末帧全图复核，UV MAE0.203125仍差。源ab58f554a7b9f886bd43b9c3f47d52761d9bf982 branch samurai-a5-ipe-m2m386，核心与385二进制同，未永久安装。r4 worker18051/client/collector终态清理；r1～r3观察失败未启FW也清理。media在/sys/bus/media/devices；旧probe快照groups3，读m2m_status刷新得到0/runtime suspended才过原门槛，不放宽。下一步接libcamera实际管线与metadata/取消，先核对CAMSS NV12平面布局；再SG/DMABUF直接DMA去复制、正式平台owner和完整IQ校准。暂用临时平台owner，非零拷贝、libcamera未接入。guard378-recovered用host386，Image363/boot366/DT365/r29/r24保持，SSC旧故障未修；保留381DMAretain、373/375/376/379修正、377/378审计、383读hook陷阱。现场低照度，黑噪点不单独判故障，目标active。\n')
p=ROOT/'sessions/INDEX.md';p.write_text(p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [386 V4L2 m2m入口与18帧实机](../reference/kernel386/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[385多尺寸/格式及交替会话16帧](reference/kernel385/README.md)','[386 V4L2 m2m入口与18帧实机](reference/kernel386/README.md)'))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('385当前：')
 p.write_text('386当前：V4L2 m2m/媒体入口18帧实机通过，覆盖MMAP、DMABUF导入导出/源offset16/stride672、双上下文及STREAMOFF/close；资源正常回收。libcamera、零拷贝、正式平台owner和完整IQ/多摄校准仍待，目标active，未永久安装。[386证据]('+prefix+'reference/kernel386/README.md)。以下为历史。\n'+rest)
print('Stage386 checkpoint updated; complete camera/ISP goal remains active.')
