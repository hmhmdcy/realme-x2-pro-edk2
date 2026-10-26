from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['diagnostic','worker','intree-build','coverage','current-state']:assert read(HERE/(name+'-validation.json'))['passed']
source=read(HERE/'source-state.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==384
 d.update(stage=385,latest_work_stage=385,current_camera_evidence=prefix+'reference/kernel385/README.md',current_device_revalidated_stage=385,
  device_closeout_evidence=prefix+'reference/kernel385/current-state-validation.json',in_progress_stage=385,
  in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel385/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_device_experiment_stage=385,ipe_latest_hardware_stage=385,
  icp_sys_init_evidence=prefix+'reference/kernel385/boot-runtime-r4-validation.json',
  icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel385/boot-runtime-r4-validation.json',
  ipe_sessions_hardware_evidence=prefix+'reference/kernel385/coverage-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel385/coverage-validation.json',
  ipe_pixel_transfer_evidence=prefix+'reference/kernel385/coverage-validation.json',
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel385/boot-runtime-r4-validation.json',
  ipe_image_frames_submitted=4,ipe_latest_stage_actual_frames=16,ipe_latest_stage_RT_frames=8,ipe_latest_stage_non_RT_frames=8,
  ipe_native_striping_multisize_evidence=prefix+'reference/kernel385/coverage-validation.json',
  ipe_nv21_hardware_verified=True,ipe_max_cores_two_configuration_hardware_verified=True,ipe_per_engine_load_measured=False,
  ipe_sustained_frame_rate_verified=False,
  icp_next_step='Integrate V4L2 m2m and libcamera with queue/session/error lifetime on the SoC core, then OEM Gamma/LTM/CCM and full calibration. Stage385 verified16 changing frames, sizes128..4608, NV12/NV21, ports8/9 and max_cores1/2 with alternating RT/nonRT. CPU-copy bring-up is not the final zero-copy stream.',
  latest_stage_device_mutated=True,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through384-2026-10-20.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text((HERE/'handoff.md').read_text())
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel385/README.md。385只改诊断，核心与384二进制同；4次实机128/640/1920/4608、port8/9、NV12/NV21、max_cores1/2，共16变化帧RT8/nonRT8，Y共77404160B等于当帧输入，输入CRC主机独立校对、各组末帧全图校对，UV MAE0.195..0.245尚有滤波差。r1..r4 workers15018/15194/15302/15445与collector均终态退出，正常回收/newfault0/taint0，未永久安装。源6fb4806e219998f5d06919a9b0266ff7b08867b0 branch samurai-a5-ipe-frames385。下一步重点V4L2m2m/libcamera实际入口和队列/会话/错误生命周期，再原厂Gamma/LTM/CCM完整IQ；CPUcopy不是最终零拷贝流，max_cores2非各引擎负载/满帧率测量。现场关灯按低照度，黑噪点非单独故障。guard378-recovered用host385，Image363/boot366/DT365/r29/r24保持，SSC旧故障未修；保留381DMAretain/quiescence和373/375/376/379修正、377/378失败审计、383MEM_READ观察陷阱及完整多摄校准范围。\n')
p=ROOT/'sessions/INDEX.md';p.write_text(p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [385多尺寸/格式及交替会话16帧](../reference/kernel385/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[384原生完整bypass条带与实机像素](reference/kernel384/README.md)','[385多尺寸/格式及交替会话16帧](reference/kernel385/README.md)'))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;first,rest=p.read_text().split('\n',1);assert first.startswith('384当前：')
 p.write_text('385当前：原生bypass四尺寸/两端口/NV12-NV21/max_cores1-2配置共16变化帧实机通过，RT/非RT交替、Y等于当前输入、正常回收；待接V4L2m2m/libcamera与完整IQ，多摄校准目标active。未永久安装。[385证据]('+prefix+'reference/kernel385/README.md)。以下为历史。\n'+rest)
print('Stage385 checkpoint updated; full goal remains active.')
