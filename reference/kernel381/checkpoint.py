from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['ipe-quiesce','ipe-sids','transfer','overlay','session','owner','dispatch','worker','intree-build','boot-runtime','io-runtime','pixels','camera-runtime','final-state']:
 assert read(HERE/(name+'-validation.json'))['passed']
source=read(HERE/'source-state.json');assert read(HERE/'pixels-validation.json')['nv12_identity_or_expected_level_validation_passed'] is False
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==380
 d.update(stage=381,latest_work_stage=381,current_camera_evidence=prefix+'reference/kernel381/README.md',current_device_revalidated_stage=381,
  device_closeout_evidence=prefix+'reference/kernel381/final-state-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel381/camera-runtime-validation.json',
  in_progress_stage=381,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel381/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel381/boot-runtime-r1-validation.json',icp_latest_device_experiment_stage=381,
  icp_latest_hfi_response_latency_ms=5.522,icp_latest_hfi_response=1,icp_latest_attempt_normal_terminal=True,
  icp_latest_attempt_followed_by_system_reboot=False,icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel381/io-runtime-validation.json',
  icp_sys_init_evidence=prefix+'reference/kernel381/boot-runtime-r1-validation.json',ipe_sessions_hardware_evidence=prefix+'reference/kernel381/io-runtime-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel381/io-runtime-validation.json',ipe_frame_builder_hardware_exercised=True,
  ipe_engine_dma_hardware_verified=True,ipe_frame_control_completion_verified=True,ipe_image_frames_submitted=1,
  ipe_synthetic_pixel_transfer_verified=True,ipe_pixel_transfer_evidence=prefix+'reference/kernel381/pixels-validation.json',
  ipe_nv12_output_levels_correct=False,ipe_image_processing_hardware_verified=False,ipe_full_iq_or_optical_calibration_proven=False,
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel381/io-runtime-validation.json',ipe_failure_dma_retention_model_evidence=prefix+'reference/kernel381/transfer-validation.json',
  icp_next_step='Trace OEM FE/ICA/output format and IQ initialization to fix quarter-scale NV12 levels. Actual synthetic pixel DMA and 72-byte frame completion are verified; normal levels and IQ are not. Then integrate V4L2 m2m/libcamera and Gamma/LTM/CCM.',
  latest_stage_device_mutated=True,whole_system_healthy=False,checked_runtime_healthy=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through380-2026-10-20.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：381（首帧 IPE 实际像素 DMA 通过；输出幅度待修，目标 active）

2026-10-20。先读 WORKING-BOUNDARIES.md、reference/kernel381/README.md。优先已有仓库／原厂反编译，按 SoC、板级、主线框架、驱动与用户空间分层；本轮新增真实数据面证据，不能退回只做握手。前一完整交接保留于 archive/NEXT-SESSION-through380-2026-10-20.md。

## 当前设备与实际结果

仍是378恢复后的同一启动，guard `/var/lib/samurai/k378-recovered/boot-id-private.txt`；reference/kernel381/host.py委托380→379→378动态guard，严格原密钥USB/known_hosts不变。本轮临时运行381候选一次并重做相关四摄回归，未刷写、未重启、无永久安装。worker10189 `/var/lib/samurai/k381-boot-r1`、collector及camera-check worker10395均terminal且已退出，不能重演同名事务。

原厂FW成功INIT/PING，两路RT(type2)/非RT(type3)handle并存，各MAP/CONFIG_IO/UNMAP成功，scratch48/48。RT提交一帧640×480合成NV12，FRAME_PROCESS opcode6、间接40、ACK72实际通过；图像命令MAP/UNMAP各1。16messages/17IRQ/1debug，CMD158/MSG173words全量相符，watchdog/protocol0。逆序destroy两handle→PC/WFI→cooperative stop（无额外全局BCR）→全部DMA/PM释放与卸载。见381/boot-runtime-validation.json与io-runtime-validation.json。

**像素不是正确幅度旁路**：取回460800字节，内核CRC与主机重算均吻合。所有307200个Y字节严格等于已知输入/4；UV148320/153600字节等于输入/4，MAE0.040625，图案高度相关，无0xa5哨兵。已证明实际像素传输，但正常NV12幅度、IQ和光学校准未通过。不得把该缩放直接归因于某个位深寄存器。实际输入输出只私存381目录，公开pixels-validation.json保留摘要。

381实验后四摄imx471/imx319/s5k3m5/s5kgw1各12帧640×480，主摄隔离IPA27帧/5阶段/GammaACK1，服务恢复、无新相机故障。收尾taint0，CAMSS/双CCI休眠，9路相机电源disabled/users0，17个ICP/BPS/IPE时钟enable0，临时DT节点（包括images）/模块/三固件文件/worker无残留。见381/camera-runtime-validation.json、final-state-validation.json。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+、boot366嵌入DT365、五个libcamera包r29、config/stack r24及362四份私有Preview保持；原厂曝光/手动频闪、IFE Gamma、unitWB/CCT与动态LSC/CCM保持。静态ICP disabled，仅A5 SID2222。SSC在378恢复启动attach失败、daemon exit4、SLPI offline、SensorProxy stopped仍在；桌面379已临时nodeps恢复greetd。本轮未盲目reattach或改依赖，不宣称全平台健康。

## 源码和生命周期

维护源 `/mnt/samurai-full282/source354`，HEAD `24a9f41f97c9fbadf5f941bde2d22fe3ac59c6c8`、分支samurai-a5-ipe-transfer381，父3801f0038ccbdc2efb71d97fc85c1f64452f9ce41a6。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、DT源码e217016006e609333a715c10f2f3e442dc4da95f未变。381核心301144字节SHA853a149d2303104cd75e0b48a6bbe21feb8fd1434326f1f9bf7c5768cae05ab1，测试100336字节SHAdcf65ef39ed4be740653ec9d93f0dc65b047cd20f0ead7cdbcd1fb5c0404e7ef。实际k363配置in-tree/W1/-Werror无诊断，测试模块仅依赖核心，均临时卸载。

进入ext4前调用reference/kernel284/storage.py::mounted_build()，build在/mnt/samurai-full282/build，source354旁置，勿格式化/重建镜像。libcamera源 /mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，SDK /home/cy122/x2pro-linux/libcamera214-root，work bind串行。所有exec session都要等同一handle终态再做依赖操作。

381临时overlay使用原厂组合域七规格：2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0，与CAMSS域mask核对无交，代码要求同provider/准确七项并平衡node引用。图像IOVA预留20000000+08000000仅保留名字空间，无物理RAMcarveout；input20000000/output24000000各最大64MiB。命令parcel07800000≤1MiB在已有共享预留内，含frame/page对齐stripe/IQ/scratch/BL，使用内核DMA/IOMMU所有权。保留独立config07600000/4KiB，避免377旧debug范围冲突。

frame API只接受2584全零IQ，拒绝任意模块/CDM，空命令数组；请求/输入/输出三BO由核心管理。有效72字节ACK、token/opcode/header/payloadstatus通过后copy输出→FWUNMAP→解除映射/释放。未知/错误完成保持ipe_dma_pending与全部BO；A5停机且IRQjoin后，两IPE分别CDM reset0xf、TOP reset3取得新ACK并清除，才允许invalidate与free；任一失败保留backing/PM、下次明确重试。启动前也执行并验证两引擎ACK[3,3]，本次真实通过；没有猜测写IRQmask/CORE_EN或新增CPAS QoS。失败注入只在模型，未故意在硬件触发失败。测试模块suppress_bind_attrs和未释放资源module pin保留。

模型实际函数体：IPEquiesce16、SID51、transfer含globalfree24、session41、owner26、worker7、dispatch10；C为ASAN/UBSAN，硬件providers建模。原厂striping仍复用380完整HAL算法12组、frame分发/callback12组和55invalid编码器。380模型不代表真实引擎，381实际首帧补上DMA证据。

## 下一步

先定位并修复零IQ输出/4：从原厂FE／ICA／输出格式、模块初始化和位深打包路径获取证据，避免用用户空间乘4掩盖底层问题。固件LinearNv12FormatFe0xf87a、LinearNv12FormatWePass0xfd0a；HAL IPEICA及IPEUpscaler12/20 Execute可追踪。尚未证明根因，不要宣称已修。修正后验证实际输入输出，再扩展帧/核心/端口、V4L2 m2m及libcamera接入，然后原厂Gamma/LTM/CCM。当前并无主线media框架或libcamera修改。

保留373 reset/wake后编程并读回HFI、375正常PC/WFI/CONTROL确认关闭避免额外ICP/AHB复位、376双token/IRQjoin/错误锁存、379MAP/UNMAP ACK44仅header状态有效（12字节尾为未初始化分配器内容）。CONFIG40/ACK56 scratch偏移36、DESTROY44/ACK48有有效payload状态；FRAME40/ACK72。未知/失败复位仍按安全路径，失败retain，不能忽略。

377配置IOVA07420000撞原FW07403000起1MiB debug映射；378移位成功MAP/CONFIG却误读UNMAP尾强制清理，377/378均自动重启且事务无正常终态，具体内部机制未测，保持失败审计。372故障context解码不能退回旧SP/PC解释。EUD9505被动capture377已retire/com-off，本轮未改。

第五2MP身份未识别，OV02A1B库名不能作为识别（front共享PHY2/MCLK2/reset12，GPIO29mux待解）；更多模式、动态帧时长/自动防频闪、光学/几何/同步/连续AF仍待，见363/REMAINING-CAMERA-SCOPE.md。用户延期纯色/遮光可后做；整体goal active。

## 原始来源、私存与回退

固定Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6（381/oem IPEcore/reset/CDM头源，355/oem管理器），CamxChi9f17f1b568626b393e785b369c5dc94543774d7a（350/sources/camxipenode.cpp、377/sources/camxipenode.h私存），CAMSS原型ebd1e440443121d18f730ab2aeea5586a754f36f不完整且旧async多字段；避免partial clone全树搜索触发lazyfetch。外部ipe_data.h未取得。

本机HAL281/camera.qcom.so-private SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde，debugELF与符号350；原FW352/CAMERA_ICP.elf-private SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63，armv7完整asm370。Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python，objdump须-m armv7。381原始输出/模块/日志/DTblob在/mnt/e/edk2-samurai-out/kernel381；固件/个体校准/密钥等不入公共Git。

公共Git /home/cy122/edk2-samurai/repo，仅Platform/Realme/sm8150范围本地提交，不push/PR。boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da保持，378恢复已读回核对。旧boot276/logdump363、k298模块/logdump、362回退包均保留。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel381/README.md。381实机首帧IPE640×480合成NV12完成，实际像素已取回：Y逐字节=input/4，UV基本一致，CRC吻合；证明DMA但正常幅度/完整IQ未通过。直接从原HAL/FW FE/ICA/输出格式与IQ初始化定位位深，不用用户空间乘4掩盖。原厂striping380复用，FRAME40/ACK72；两handle并存CONFIG48/48，再一帧、销毁、PC/WFI、全部DMA/PM释放，16msgs/17IRQ CMD158/MSG173。381仅一次worker10189，已terminal/passed，四摄各12帧+主摄隔离IPA27/GammaACK通过，taint0无残留。源24a9f41f97c9fbadf5f941bde2d22fe3ac59c6c8分支samurai-a5-ipe-transfer381；guard仍378-recovered，host381，实际Image363/boot366/DT365/r29/r24保持。临时组合7SID域+128MiB IOVA预留、三BO所有权、未知完成retain直到A5停和两IPE CDM/TOP ACK，启动ACK[3,3]真机通过。静态ICPdisabled/候选未永久安装，SSC失败/SLPIoffline/SensorProxystopped仍在。接下来幅度修正再V4L2m2m/libcamera/Gamma/LTM/CCM，第五摄等待续；原数据私存，保留373/375/376/379修正和377/378失败审计。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();anchor='## 最新交接\n';assert anchor in s;p.write_text(s.replace(anchor,anchor+'\n- [381实机首帧IPE像素通路](../reference/kernel381/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[380原厂striping与内核帧编码](reference/kernel380/README.md)','[381实机首帧IPE像素通路](reference/kernel381/README.md)'))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('380当前：')
 p.write_text('381当前：实机首帧IPE合成NV12和完整生命周期通过，逐像素确认数据通路；零IQ输出幅度为输入/4，正常幅度与完整IQ待修。四摄及主摄隔离IPA/Gamma回归通过，无资源残留；SSC故障仍在。Image363/boot366/DT365/r29/r24保持，目标active。[381证据]('+prefix+'reference/kernel381/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=381,actual_pixel_transfer=True,nv12_output_levels_correct=False,normal_camera_capture_reference_stage=381,goal_status='active')))
