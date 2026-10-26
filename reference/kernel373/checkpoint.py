from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['intree-build','order','worker','lifecycle','final-state','camera-runtime']:assert read(HERE/(name+'-validation.json'))['passed']
runtime=read(HERE/'boot-runtime-r1-validation.json');assert runtime['actual_sys_init_acknowledged'] and not runtime['normal_terminal'] and not runtime['full_firmware_handshake_passed']
source=read(HERE/'source-state.json');final=read(HERE/'final-state-validation.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p)
 d.update(stage=373,latest_work_stage=373,current_boot_guard_stage=373,current_camera_evidence=prefix+'reference/kernel373/README.md',
  current_device_revalidated_stage=373,current_device_runtime_state_verified=True,device_current_taint=0,device_current_ssh_status='strict_original_key_usb',device_force_restart_currently_needed=False,
  current_boot_guard_evidence=prefix+'reference/kernel373/recovery-cleanup-validation.json',device_closeout_evidence=prefix+'reference/kernel373/final-state-validation.json',
  device_recovered_boot_evidence=prefix+'reference/kernel373/recovered-boot-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel373/camera-runtime-validation.json',
  device_recovered_camera_count=4,in_progress_stage=373,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel373/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel373/boot-runtime-r1-validation.json',icp_latest_attempt_recovery_evidence=prefix+'reference/kernel373/recovery-cleanup-validation.json',
  icp_latest_attempt_normal_terminal=False,icp_latest_attempt_followed_by_modem_watchdog=None,icp_latest_attempt_followed_by_system_reboot=True,
  icp_latest_hfi_response=1,icp_latest_hfi_response_latency_ms=runtime['ready_response_latency_ms'],icp_latest_deadline_expired=False,
  icp_sys_init_hardware_verified=True,icp_sys_init_evidence=prefix+'reference/kernel373/boot-runtime-r1-validation.json',icp_ping_ack_durably_verified=False,
  icp_pc_prepare_wfi_zero_return_observed=True,icp_dma_retired_and_pm_zero_return_logged=True,
  icp_standard_devcoredump_runtime_recovered=False,icp_standard_devcoredump_bytes=None,icp_last_recovered_standard_dump_stage=369,icp_last_recovered_standard_dump_bytes=568,
  icp_actual_sfr_text_recovered=False,icp_original_exception_text_recovered_from_abort_stack=True,
  icp_pre_reset_snapshot_ramoops_evidence=prefix+'reference/kernel372/pre-reset-runtime-validation.json',icp_pre_reset_snapshot_words=76,
  icp_hardware_cleanup_verified=False,icp_firmware_boot_verified=False,icp_hardware_backend_installed=False,icp_latest_device_experiment_stage=373,
  icp_next_step='Keep verified reset/wake-before-parameters and CSR readback; persist PING/PC/probe result and trace exit/bind runtime-PM/supplier/sync_state after SYS_INIT; no old startup-failure replay',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 if 'deployed_camera_modules' in d:d['deployed_camera_modules']=final['deployed_camera_modules']
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：373（就绪1与SYS_INIT实机通过；退出／绑定后仍重启，目标active）

2026-10-20。先读WORKING-BOUNDARIES.md、reference/kernel372/README.md和reference/kernel373/README.md。本轮取得真实异常并修正SoC启动顺序，属于实质进展；完整多摄／ISP目标仍active。

## 当前设备与代码

当前guard `/var/lib/samurai/k373-recovered/boot-id-private.txt`；用reference/kernel373/host.py，strict原密钥USB／known_hosts不变。371／372旧guard失效，不复用历史launcher；373实际事务/var/lib/samurai/k373-boot-r1的worker6711和collector已不在，旧state terminal=false/load-boot-test完整保留，无活动构建或实验worker。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+，778模块；boot366嵌入DT365；libcamera五包r29、config/stack r24和362四份私有Preview默认未改。原厂曝光／手动防频闪、IFE Gamma、既有个体WB/CCT／动态LSC／CCM保留。候选ICP模块未永久安装，静态ICP仍disabled。

373恢复后四颗各12帧GStreamer，主摄隔离IPA另27帧／5阶段／Gamma ACK通过，相关故障增量0；CAMSS/双CCI休眠、九相机电源disabled/users0。SSC、SensorProxy、greetd、Phoc/Phosh和adsp/slpi/modem健康，PW/WP稍后自行出现，未重启服务；最终各一uid10000、taint0，十个模块loaded note匹配磁盘，无ICP模块／临时固件／动态节点／worker。证据373/camera-runtime-validation.json、final-state-validation.json。不能外推完整光学校准。

维护源/mnt/samurai-full282/source354，samurai-a5-hfi-reset-order373／1e495f16e41b6a8198555a2c5f41b71c63527ea9；中间8450b1a89405550b5c9980f8bfa263622619966f，父372 71ca6b6361edfba4a144295656e6737d2c18e8c2。实际Image仍ba61a62293e0f6bc5838c06f2e85e033e3d702a8、DT e217016006e609333a715c10f2f3e442dc4da95f。libcamera维护源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2。进入ext4必须先storage284.mounted_build()，WSL退出后会卸载；SDK bind串行。

## 372真实异常与纠正的解析

368原厂SendSfrMessage指令证明3是故障。369标准dump568曾取回但SFR空，371用户空间held窗口未能返回。372在core start失败、CPU释放之后、devcoredump／quiesce之前增加可选owner observer；临时owner首先比对原厂ELF首4KiB代码页，匹配且归属／范围有效才打印4范围76word到已有效的ramoops。SoC核心没有原厂偏移常量，地址由临时只读参数提供，完整原始记录只私存。

原始完整ARM异常入口和rex_jettison_core指令测试只桩CP15值，发现arch_coredump_ptr指向真正异常寄存器区，不是A5ContextRegisters；ABT SP偏移0x58而非0x64。实际异常发生后，原先入口瞬间“SP+32”的PC槽被C handler覆盖，绝不能再据此直接称故障PC。只接受受界原厂异常文字中与直接FAR/FSR/type一致的PC；解码器已加入覆盖与不符反例。

372真实response3/2.712ms/expired0，代码页匹配和76word/end完整，data abort指向DALSYS_DestroyObject对象读取；ctx指针与原厂初值一致。原始异常字符串和raw栈均只私存372。进一步执行原厂fwEntryFunction→ICPHostInterface_destroy→vSYS_DestroyMutex→DALSYS_DestroyObject，在共享区地址或size为0两例复现相同故障地址／PC、尚未写失败2就异常。OS/线程/信号析构/MMU/log为桩，不能直接据此证明实机CSR为0或reset清零。

## 373真实功能进展与未完成部分

原驱动在CPU NSEC_RESET之前写HFI参数。对照原厂cam_hfi_enable_cpu/hfi_init改为reset→wake→10个HFI参数写入＋读回→INIT_REQUEST，读回任何不符拒绝初始化。实际函数体顺序／不符保护及13 start路径模型通过；两模块实际k363 in-tree W1/Werror构建无诊断，test与372逐字节相同。核心SHA391edf55268d0fecba255607d3f5834ba5b1f48387e2c92e287c9957fd17838d，test SHAe5998aef2706ea00c6434c956df87ceb9fe8de71ac9b0cc7248ca206e581d9b2。

373仅一次新实验：ramoops确认10参数读回通过、HFI就绪1/5.532ms/fw01000100/expired0、SYS_INIT acknowledged。随后pc_error=0；按已执行生产路径含PC_PREP完成和WFI等待成功，另记录DMA aliases retired及PM reference released:0。随后仍进入新启动，无完整probe／卸载终态。PING没有独立持久化回执，不宣称完整三握手或硬件清理验收。start成功未调用failure_snapshot是预期，373没有异常快照不等于观察器失效。

这次修正确认解决了旧初始化失败的实际行为，但没有直接测得旧顺序CSR被清空，机制不要过度断言。reset ID9经实际dt-binding/driver核对确为CAM_CC_ICP_BCR/c0b4。精确后续重启原因未知；fw_devlink 0x180代理日志不是单独的根因证据，未改全局框架策略。NV/OTP/校准及工厂备份未写，未发主机系统复位，未刷写。

## 下一步

保留373reset/wake后参数编程和读回，不再重演旧参数初始化故障。补齐PING ACK、PC_ACK和probe返回前结果的ramoops持久化标记／计数，再定点跟踪退出及绑定完成后的runtime PM、supplier和sync_state。区分块复位、DMA/供电退出和通用设备框架，不把PM返回0或fw_devlink日志单独当成完整清理／根因；也不把SYS_INIT一项通过当完整ISP就绪。

可优先审计原厂cam_hfi_disable_cpu/资源释放与现实现reset/clock/domain顺序，再决定新的针对性实验，不重复373原序列只为了凑次数。失败窗口必要数据仍可用372 observer，字段偏移必须来自已核对的原厂profile。复制到普通RAM devcoredump来不及用户空间持久化的问题已通过预复位ramoops解决。

## 私存与回退

公共Git /home/cy122/edk2-samurai/repo/Platform/Realme/sm8150。私存E:/edk2-samurai-out/kernel372有raw现场／原厂指令模型；kernel373有功能实验ramoops／恢复／构建。原厂ELF kernel352/CAMERA_ICP.elf-private，3,630,392字节，SHA a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。objdump用arm-linux-gnueabi-objdump -m armv7，Unicorn私有venv/home/cy122/x2pro-linux/private-k329-venv。原始固件、异常word/文本、完整日志、校准、密钥不进公共Git。

boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。373新启动读回保持；临时firmware匹配原厂／事务copy后已删，原件和所有旧事务保留。boot276+logdump363可退DT；旧k298模块/logdump和362事务r27/r22+338模块+344私有配置组合保留。不要重启AndroidR partial clone大目录git grep，复用356已保存的正确pil_camera_mem=9ab00000/5MiB证据。

## 完整目标剩余

完整HFI生命周期、IPE会话/IO/IQ及libcamera后级Gamma/LTM/CCM仍未完成。已确认三后摄＋前摄，官方另有2MP人像；vendor OV02A1B只有库名，原厂cam-sensor@4和前摄共享PHY2/MCLK2/reset12，GPIO29选择待解，不添冲突节点或等同OV02A10。动态FrameDurationLimits、自动防频闪、更多模式、绝对颜色／黑电平／阴影、几何／多摄同步及连续AF均开放，见363/REMAINING-CAMERA-SCOPE.md。延期纯色／遮光可后做。整体goal保持active。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从373继续active多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel372/README.md与373/README.md。372已取真实复位前76word/代码匹配/原厂data abort，DALSYS_DestroyObject错误清理可由共享ptr或size缺失重现；arch_coredump_ptr才是异常context，C会覆盖旧PC槽，已改用FAR/FSR/type一致的受界原厂文字解析PC。373改reset→wake→HFI10参数写入读回→INITreq，实机首次就绪1/5.532ms和SYS_INIT ACK，PC/WFI路径0、DMA退映射和PM返回0日志，但之后仍重启无probe终态，PING未持久化验证。维护源source354/1e495f16分支samurai-a5-hfi-reset-order373，父37271ca6。现guard373-recovered，host373严格USB，Image363/boot366/DT365/r29/r24；四摄及隔离/Gamma、桌面/SSC和终态通过，无需重启。下一步保留启动顺序修正，补齐PING/PC/probe结果持久化并定点审计退出／绑定sync_state、supplier和runtime PM，不重演旧初始化故障或仅凭fw_devlink日志下结论。所有raw/固件/异常文本/校准/完整日志私存。完整HFI/IPE、第五摄身份、其它模式与光学同步/AF仍未完。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text().replace('## 最新交接\n','## 最新交接\n\n- [373就绪与SYS_INIT、退出重启恢复](../reference/kernel373/README.md)\n- [372真实复位前异常现场](../reference/kernel372/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[371持有模式实验与新启动恢复](reference/kernel371/README.md)','[373就绪与SYS_INIT、退出重启恢复](reference/kernel373/README.md)');p.write_text(s)
print(json.dumps(dict(stage=373,actual_sys_init_verified=True,full_handshake_verified=False,current_guard_stage=373,device_baseline_recovered=True,goal_status='active')))
