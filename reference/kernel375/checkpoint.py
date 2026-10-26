from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['intree-build','stop','dispatch','worker','boot-runtime','lifecycle-runtime','camera-runtime','final-state']:
 assert read(HERE/(name+'-validation.json'))['passed']
runtime=read(HERE/'boot-runtime-validation.json');assert runtime['same_boot'] and runtime['firmware_handshake_passed']
source=read(HERE/'source-state.json');guard='/var/lib/samurai/k374-recovered/boot-id-private.txt'
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p)
 d.update(stage=375,latest_work_stage=375,current_boot_guard_stage=374,current_boot_guard_path=guard,
  current_camera_evidence=prefix+'reference/kernel375/README.md',current_device_revalidated_stage=375,current_device_runtime_state_verified=True,
  device_current_taint=0,device_current_ssh_status='strict_original_key_usb',device_force_restart_currently_needed=False,
  current_boot_guard_evidence=prefix+'reference/kernel374/recovery-cleanup-validation.json',device_closeout_evidence=prefix+'reference/kernel375/final-state-validation.json',
  device_recovered_boot_evidence=prefix+'reference/kernel374/recovered-boot-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel375/camera-runtime-validation.json',
  device_recovered_camera_count=4,in_progress_stage=375,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel375/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel375/boot-runtime-r1-validation.json',icp_latest_attempt_recovery_evidence=None,
  icp_last_recovery_stage=374,icp_last_recovery_evidence=prefix+'reference/kernel374/recovery-cleanup-validation.json',
  icp_latest_attempt_normal_terminal=True,icp_latest_attempt_followed_by_modem_watchdog=False,icp_latest_attempt_followed_by_system_reboot=False,
  icp_latest_hfi_response=1,icp_latest_hfi_response_latency_ms=read(HERE/'lifecycle-runtime-validation.json')['ready_response_latency_ms'],icp_latest_deadline_expired=False,
  icp_sys_init_hardware_verified=True,icp_sys_init_evidence=prefix+'reference/kernel375/boot-runtime-r1-validation.json',
  icp_ping_ack_durably_verified=True,icp_pc_prepare_ack_durably_verified=True,icp_pc_prepare_wfi_zero_return_observed=True,
  icp_dma_retired_and_pm_zero_return_logged=True,icp_hardware_cleanup_verified=True,icp_firmware_boot_verified=True,
  icp_full_hfi_lifecycle_verified=True,icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel375/lifecycle-runtime-validation.json',
  icp_cooperative_stop_without_global_reset_verified=True,icp_image_sessions_hardware_tested=0,ipe_image_processing_hardware_verified=False,
  icp_hardware_backend_installed=False,icp_latest_device_experiment_stage=375,
  icp_next_step='Implement strictly matched IPE session create/destroy using retained OEM ABI and firmware symbols; then IO/IQ/frame completion and libcamera m2m. Preserve verified startup and cooperative shutdown; no replay of old failing boot sequence.',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：375（原厂A5/HFI完整启停通过；IPE图像会话待实现，目标active）

2026-10-20。先读WORKING-BOUNDARIES.md和reference/kernel375/README.md；372异常现场、373启动修正、374绑定外诊断按需阅读。不要重复失败启动序列或因历史权限说明反复确认。

## 当前设备

当前仍是374恢复后的同一启动，guard `/var/lib/samurai/k374-recovered/boot-id-private.txt`；使用reference/kernel375/host.py，strict原密钥USB/known_hosts不变。375没有重启，也不存在375-recovered启动。375-boot-r1 worker6686与collector已结束，state finished/terminal/pass；375-camera-check-r1 worker6861也完成，旧373/374失败事务原样保留。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+，boot366嵌入DT365；五个libcamera包r29、config/stack r24及362四份私有Preview默认保持。原厂曝光/手动防频闪、IFE Gamma、既有unit WB/CCT、动态LSC/CCM保持。候选ICP模块未永久安装；静态ICP仍disabled。375完整退出后临时固件、overlay、core/test模块全无，17个ICP/BPS/IPE时钟enable0、CAMSS/双CCI休眠、九相机电源disabled/users0、taint0。

375随后四颗各12帧GStreamer、主摄独立IPA27帧/5阶段/Gamma ACK通过，相关故障0。SSC、SensorProxy、greetd、PW/WP/Phoc/Phosh各正常，adsp/slpi/modem running。证据375/boot-runtime-validation.json、camera-runtime-validation.json、final-state-validation.json。无需重启或重复无关基线测试。

## 源码与实机证据

维护源 `/mnt/samurai-full282/source354`，分支samurai-a5-cooperative-stop375，提交94a92da1da7d6e5418e284b4a0c858100fa74fd9；父374 8bbd1f3d63e740dbf45918e785f763a9b9dde3be，再父373 1e495f16e41b6a8198555a2c5f41b71c63527ea9。源码干净，候选尚未正式安装。实际Image源码仍ba61a62293e0f6bc5838c06f2e85e033e3d702a8，静态DT e217016006e609333a715c10f2f3e442dc4da95f。

访问ext4先用reference/kernel284/storage.py::mounted_build()（WSL退出后会卸载），返回/mnt/samurai-full282/build，source354在其旁。不要重建或格式化镜像。libcamera源 /mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2；SDK /home/cy122/x2pro-linux/libcamera214-root，work bind串行。

372在core start失败、devcoredump/quiesce之前用可选owner observer核对原厂首4KiB代码页，ramoops取回4范围76word；真实data abort指向DALSYS_DestroyObject，原厂fwEntry错误清理在共享ptr/size缺失时可复现。正确异常context来自arch_coredump_ptr，不是A5ContextRegisters；ABT SP偏移0x58，原先SP+32槽被C handler覆盖，故障PC只从与直接FAR/FSR/type一致的受界原厂异常文本接受。原始word/文本仅私存，不要退回旧错误解码。

373将HFI参数编程移到CPU reset/wake之后、INIT_REQUEST之前，10个参数逐一读回，首次响应1与SYS_INIT通过。没有测得旧CSR复位前后的值，不宣称reset清空寄存器已证实。

374只在资源probe返回、普通BUS_BOUND/overlayapply返回并持久化后显式sysfs run，三项INIT/PING/PC ACK与WFI0均有ramoops，仍在全局块复位之后、DMA开始之前重启。不是仅probe绑定内启动的问题；没有改fw_devlink框架。

375对照已保存原厂cam_hfi_disable_cpu及资源停机，正常路径不额外断言全局ICP_BCR：PC_ACK/WFI/CONTROL enable+wake读回清除后，保持ICP/AHB可访问，退映射再释放PM；runtime_suspend也不在正常路径额外assert。未初始化/命令或WFI失败/CONTROL未清则仍强制reset；失败保留CPU、RAM、PM；已关IRQ的失败重试跳过依赖IRQ的PC命令。实际quiesce/stop/runtime_suspend 13路径模型+旧代码反例、ASAN/UBSAN通过；MMIO等为桩。两实际k363 in-tree W1/Werror模块无诊断，test与374逐字节相同。

375唯一针对性实机：就绪1/5.270ms/fw01000100，INIT/PING/PC均ACK，4IRQ/3msgs/1debug，watchdog/proto0；cooperative1/blockreset0，DMA退映射、PM0、run ret0、overlay remove0、module exit end完整。终态backing/mapped/CPU/IRQ/PM/groups/domains均0；三个队列读写索引收敛，image_sessions=0。完整HFI生命周期已通过，但没有任何IPE处理图像证据。不能进一步声称已测得旧重启的总线/看门狗内部机制。

## 下一步

停止反复追旧启动错误。优先复用352保存的CAMSS维护者固定原型与355原厂ICP管理器，核对原厂会话ABI及原始固件符号，再实现IPE create/destroy严格类型、长度、token、handle、opcode与error应答匹配，处理timeout/中途失败所有权；随后IO/IQ映射、frame completion与libcamera m2m。

原厂头文件私存kernel352/oem/hfi_session_defs.h、hfi_sys_defs.h；实际管理器kernel355/oem/cam_icp_hw_mgr.c中create在4555附近、destroy2731、ACK解析1758/1875/2084。现核心send_command/IRQ解析只含SYS_INIT/PING/PC，需要扩展而不是直接伪造成功字段。上游原型kernel352/upstream固定ebd1e440...，其缺少5项会话API和Makefile源，不能当完整可部署驱动；目标A5 ELF与X1E MDT/PAS/CSR有差别。新会话必须保留373启动顺序及375正常/强制停机区分，不更改现有板级或用户空间调校掩盖差异。

完整目标仍有IPE图像会话/IO/IQ/Gamma/LTM/CCM、第五颗2MP身份（OV02A1B库名不是传感器识别证明，前摄共享PHY2/MCLK2/reset12，GPIO29选择待解）、更多模式、动态FrameDurationLimits/自动防频闪、正常照明光学/黑电平/阴影、几何同步/连续AF。延期纯色遮光可后做。参见363/REMAINING-CAMERA-SCOPE.md。goal保持active。

## 私存与回退

公共Git /home/cy122/edk2-samurai/repo，范围Platform/Realme/sm8150；根工作区不是Git。私存E:/edk2-samurai-out/kernel374保存ramoops/原事务，375保存模块/完整成功日志/模型与采集事务。原厂ELF kernel352/CAMERA_ICP.elf-private，3,630,392 bytes SHA a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。objdump -m armv7，Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python。raw固件、异常文本/word、完整日志、个体校准和密钥绝不进公共Git。

boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924，logdump365 aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da，374恢复读回保持，375无刷写。boot276+logdump363、旧k298模块/logdump与362 r27/r22+338module+344private组合保留。禁止对Realme partial clone全目录git grep触发海量lazyfetch；复用356已核pil_camera_mem=9ab00000/5MiB证据。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel375/README.md。375已实机完整INIT/PING/PC/WFI、DMA/PM释放与模块卸载通过，same boot、故障/taint0，四摄与主摄隔离Gamma回归通过；guard仍374-recovered，用host375，不需重启。维护源source354/94a92da1分支samurai-a5-cooperative-stop375，实际Image363/boot366/DT365/r29/r24保持，候选未永久安装。保留373 reset/wake后HFI参数编程与读回，保留375正常停机不额外全局块复位、失败强制reset及所有权保护。下一步直接核对保存原厂session ABI/管理器/固件符号，做IPE create/destroy及IO/IQ/帧完成和libcamera m2m；尚无IPE图像会话或处理图像，不能把HFI成功当完整ISP完成。第五摄、模式、光学/几何/同步/AF仍未完。raw固件/异常/校准/完整日志只私存。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [375原厂A5/HFI完整启停与四摄回归](../reference/kernel375/README.md)\n- [374绑定后三握手与停机重启](../reference/kernel374/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[373就绪与SYS_INIT、退出重启恢复](reference/kernel373/README.md)','[375原厂A5/HFI完整启停](reference/kernel375/README.md)');p.write_text(s)
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1)
 assert first.startswith('367当前：')
 first='375当前：原厂A5固件INIT/PING/PC/WFI、DMA/PM释放和模块卸载实机完整通过，same boot、fault/taint0；四摄与主摄隔离Gamma回归通过。Image363/boot366/DT365/r29/r24保持，候选未永久安装。IPE图像会话及完整多摄光学校准仍未完成，目标active。[375证据]('+prefix+'reference/kernel375/README.md)。以下为历史。'
 p.write_text(first+'\n'+rest)
print(json.dumps(dict(stage=375,current_boot_guard_stage=374,full_hfi_lifecycle_verified=True,ipe_images_verified=False,goal_status='active')))
