from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['alignment-abi','bypass-iq','transfer','owner','dispatch','worker','intree-build','boot-runtime','io-runtime','pixels','chroma','final-state']:
 assert read(HERE/(name+'-validation.json'))['passed']
source=read(HERE/'source-state.json');assert read(HERE/'pixels-validation.json')['nv12_identity_or_expected_level_validation_passed']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==381
 d.update(stage=382,latest_work_stage=382,current_camera_evidence=prefix+'reference/kernel382/README.md',current_device_revalidated_stage=382,
  device_closeout_evidence=prefix+'reference/kernel382/final-state-validation.json',in_progress_stage=382,
  in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel382/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel382/boot-runtime-r1-validation.json',icp_latest_device_experiment_stage=382,
  icp_latest_hfi_response_latency_ms=5.326,icp_latest_hfi_response=1,icp_latest_attempt_normal_terminal=True,
  icp_latest_attempt_followed_by_system_reboot=False,icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel382/io-runtime-validation.json',
  icp_sys_init_evidence=prefix+'reference/kernel382/boot-runtime-r1-validation.json',ipe_sessions_hardware_evidence=prefix+'reference/kernel382/io-runtime-validation.json',
  ipe_config_io_hardware_evidence=prefix+'reference/kernel382/io-runtime-validation.json',
  ipe_pixel_transfer_evidence=prefix+'reference/kernel382/pixels-validation.json',ipe_nv12_output_levels_correct=True,
  ipe_bypass_processing_hardware_verified=True,ipe_kernel_generated_bypass_iq=True,ipe_external_iq_input_required=False,
  ipe_default_iq_evidence=prefix+'reference/kernel382/alignment-abi-validation.json',ipe_chroma_difference_evidence=prefix+'reference/kernel382/chroma-validation.json',
  ipe_exact_full_plane_identity=False,ipe_image_processing_hardware_verified=False,ipe_full_iq_or_optical_calibration_proven=False,
  ipe_preboot_reset_ack_evidence=prefix+'reference/kernel382/io-runtime-validation.json',
  icp_next_step='Implement checked kernel-native bypass geometry/striping, differential against retained OEM algorithm; expand sizes/ports/cores/continuous frames. Then V4L2 m2m/libcamera and Gamma/LTM/CCM. ICA defaults corrected real NV12 levels, but full IQ and optical calibration remain incomplete.',
  latest_stage_device_mutated=True,whole_system_healthy=False,checked_runtime_healthy=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through381-2026-10-20.md';assert not archive.exists();archive.write_text((ROOT/'NEXT-SESSION.md').read_text())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：382（内核ICA默认配置修复幅度，实机Y精确一致；完整目标active）

先读WORKING-BOUNDARIES.md、reference/kernel382/README.md。上一轮382取得底层实机修正，属于progress。381完整交接存archive/NEXT-SESSION-through381-2026-10-20.md，380更早交接也保留；遇到未详列的生命周期、资源及失败历史先查这些文件。

## 最新结果和状态

仍是378恢复后的同一启动，guard `/var/lib/samurai/k378-recovered/boot-id-private.txt`。用reference/kernel382/host.py（委托381→380→379→378动态guard），原密钥USB/known_hosts严格验证不变。本轮一次 `/var/lib/samurai/k382-boot-r1` worker11416，collector均finished/terminal/passed且已退出。没有刷写、主机重启命令或永久安装，不可重演同名事务。

382同输入/同striping/同域与映射，内核ICA默认值使640×480 NV12的307200个Y字节全与输入一致，修正381的Y=input/4。UV143040/153600字节一致，MAE0.203125，U差异全在阶跃横向4个亮度像素内，V在2色度行内；离开这些邻域完全相同，实际滤波/舍入算法未证。不宣称全平面identity或完整IQ/光学校准。本次四默认值同时改变，未硬件隔离单字段因果。输入/输出CRC3426410711/3085177422，主机重算吻合，raw只私存382。

事务INIT/PING、两RT/非RT handle并存各CONFIG_IO（scratch48/48）、RT一帧、MAP/UNMAP、两destroy、PC/WFI、cooperative stop、所有DMA/PM与卸载通过。frame opcode6/间接40/ACK72，CMD158/MSG173words，16msgs/17IRQ/1debug，wd/protocol0，最终所有pending/FWmap/backing/PM0。见382/boot-runtime-validation.json、io-runtime-validation.json、pixels-validation.json、chroma-validation.json。

382只改IQ初始化/接口，未改四摄/板级/用户空间，复用381同启动四摄各12帧640×480、主摄隔离IPA27帧/5阶段/GammaACK1，未重复采集。新收尾taint0、CAMSS/双CCI休眠、9rails disabled/users0、17ICP/BPS/IPEclk enable0，临时DT（含images）/模块/两固件文件/worker无残留。见382/final-state-validation.json。SSC旧attach失败/daemon exit4、SLPIoffline、SensorProxystopped仍在；桌面379恢复后保持，未盲目reattach/改依赖，不宣称全平台健康。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+，boot366嵌入DT365，libcamera五包r29、config/stack r24及362四份私有Preview保持，原厂曝光/手动频闪、IFE Gamma、unitWB/CCT与动态LSC/CCM保持。静态ICP disabled，仅A5 SID2222。

## 维护源与新增实现

维护源 /mnt/samurai-full282/source354，branch samurai-a5-ipe-alignment382，HEAD47475238dc6a0d4b28a5db22b0c1af223dc50297，父38124a9f41f97c9fbadf5f941bde2d22fe3ac59c6c8。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、DT源码e217016006e609333a715c10f2f3e442dc4da95f不变。382 core302520字节SHA36bf8d8bd3a0bd0258b6303349469afedf02c13d849e3c4e851990c2161bd7b5，test100104字节SHA2281097c4c94e17a643a0bc15880ae903a3e08c6da42dc563d5d017688fe5a98。实际k363配置in-tree/W1/-Werror无诊断，临时模块已卸载。

SoC/驱动新增camss_a5_ipe_encode_bypass_iq，清零2584字节后四个u32偏移52/68/244/260置1，分别ICA1/2 invalidPixelModeInterpolationEnabled和eightBitOutputAlignment。API camss_a5_ipe_job已移除iq/iq_bytes，核心自行生成；测试模块只加载samurai-ipe382-stripe.bin，不再要外部IQ。board复用381临时overlay无改，主线框架/用户空间无改，未做软件乘4补偿。

证据：固定CamxChi IPENode源350/sources/camxipenode.cpp对应逻辑；本机HAL原指令2e08a8..2e08c4（caller x25=IQ、有效sp夹具）实际执行四store；完整HAL request未执行。原FW18b12..18b26将ICA IQ+68归一化布尔，1528e..152a4写两引擎ICA_TOP_EIGHT_BIT_OUTPUT_ALIGNMENT寄存器0x129c/0x169c，原始指令执行8cases。完整引擎handler未在模型执行。原HAL完整striping差分5cases（zero、ICA1align、ICA2align、both、fourdefaults）输出与380脏初始化baseline逐字节相同，仅640×480端口8核心1；更多新默认配置组合待扩展。

IQ实际函数体ASAN/UBSAN，所有short/null无写、oversized尾不变，输出与HAL片段2584字节一致。transfer24cases在提交时核对所有IQ字节，同时验证旧不确定DMA/复位失败retain/globalfree路径；owner26/worker7/dispatch10通过。详见382模型与补丁。381资源/SID/quiesce与380帧编码器未改，已有证据复用。

## 下一步直接推进

当前仍依赖原HAL算法生成的私存striping文件，尚不能成为独立通用m2m后端。优先把已核实的8位线性NV12模块关闭几何/striping生成收敛到内核，按保留原厂完整算法差分；扩展尺寸、端口8/9、核心1/2与连续帧，随后接V4L2 m2m/libcamera及原厂Gamma/LTM/CCM。避免只重复相同单帧作为新进展。未实现IQ模块语义/完整调优，不能将旁路验收替代全目标。

380完整算法入口HAL144348create、1448f0execute、144988destroy，reference/kernel380/hal-machine.py与check-striping.py可复用，标准malloc/free/memset/memcpy/memcmp模型、算法本身非桩；12组640×480/1920×1080/4608×3456 ×port8/9 ×cores1/2，输出1pass，stripe数2/6/15或16，BL容量156512/228512/396512。条带实际消费2268+624Σstripe（passCount20、每pass412、stripeCount428+412*i）。输出中保留未写0xa5字节，别把这些当有效字段。原框架IpeFrameDataCollator和firmware实际消费可作字段使用证据。

帧payload3816、IQ2584、header92/frameSet232，14ports×2planes及metadata，最多16batch；单帧copy324，BL内部减32、CDM数组按base修正。userArg3808。380原FW分发/callback模型12组、编码器55invalid；381实际像素补足数据面，382修幅度。原HAL params为5Q+I：IQ、ICA1、ICA2、zoom、previousZoom、cores，勿混成一份IQ直接传所有ICA结构。

## 保留的资源规则和失败纠正

381临时组合域SID2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0，mask核对与CAMSS无交，sameprovider/准确7项及node引用平衡。图像IOVA20000000+08000000只保留名字空间、不新分配RAMcarveout；input20000000/output24000000各≤64MiB。命令parcel07800000≤1MiB在已有共享预留内（frame/stripe/IQ/scratch/BL），config07600000/4KiB。

核心拥有三BO，只有合法72ACK/token/opcode/status后copy输出→FWunmap→释放。任何未知/错误完成retain pending和全部BO；A5停机/IRQjoin后，两IPE的CDM reset0xf/TOP3清旧ACK→取新ACK→清ACK均确认才可free；失败保留backing/PM供明确重试。启动前相同ACK[3,3]实际通过。未猜测写IRQmask/CORE_EN/CPASQoS；失败注入是模型，硬件未故意失败。测试module pin与suppress_bind_attrs保留。

保留373 reset/wake后HFI参数编程/readback，375正常PC/WFI/CONTROL确认关CPU后避免额外全局ICP/AHB复位，376双token/IRQjoin/错误锁存，379MAP/UNMAP56命令/ACK44仅header状态有效（尾12是未初始化分配器内容）。CONFIG40/ACK56 scratch36、DESTROY44/ACK48有效payload状态，FRAME40/ACK72。失败/未知复位仍retain。377撞原FW07403000起1MiB debug映射，378CONFIG成功却误读UNMAP尾强制清理；两轮自动重启无正常事务终态，内部原因未测，审计保留。372 context/PC解码纠正保留。EUD9505被动capture377已退役/com-off，本轮未改。

第五2MP身份未知（OV02A1B库名不算识别，front共享PHY2/MCLK2/reset12、GPIO29mux待解），更多模式、动态帧时长/自动防频闪、光学/几何/同步/连续AF见363/REMAINING-CAMERA-SCOPE.md；延期纯色/遮光可后做。整体goal active。

## 路径、来源与私存

访问ext4前调用reference/kernel284/storage.py::mounted_build()，build /mnt/samurai-full282/build、source354旁置，不重建或格式化镜像。libcamera源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，SDK/home/cy122/x2pro-linux/libcamera214-root，work bind串行。exec返回session必须等同一handle终态后再依赖操作。

原HAL281/camera.qcom.so-private SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde；350debugELF仅符号，没有可反汇编执行段，objdump应读原HAL（本轮已改fetch脚本）。FW352/CAMERA_ICP.elf-private SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63，完整armv7 asm370，objdump -m armv7。Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python。382保留ICA/upscaler片段、fixed源、probe夹具与图像私存，不进公共Git。

固定Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，CamxChi9f17f1b568626b393e785b369c5dc94543774d7a（382/sources ICA/upscaler/icasetting/icautils），原型ebd1e440443121d18f730ab2aeea5586a754f36f不完整/旧async多字段；外部ipe_data.h未取得，避免partial clone全树gitgrep触发lazyfetch。

公共Git /home/cy122/edk2-samurai/repo，范围Platform/Realme/sm8150，本地提交不push/PR。原厂固件、原始输出/日志、个体校准/密钥仅/mnt/e/edk2-samurai-out/kernelNNN私存。boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da保持，378恢复读回已核；旧boot276/logdump363、k298模块/logdump和362回退包保留。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。先读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel382/README.md。382原HAL/FW片段证实ICA默认u32 IQ偏移52/68/244/260=1，内核自生成并移除job外部IQ；实机相同640×480图案Y307200字节全等，UV MAE0.203125且差异仅阶跃附近，修复381四分之一幅度。四默认同时改，未单字段硬件因果隔离，完整IQ未验。一次worker11416 k382-boot-r1已terminal/passed，16msgs/17IRQ CMD158/MSG173，两handle/config/一帧/destroy/PC/WFI/DMA+PM全部回收、taint0无新故障。四摄基线复用381同启动。本轮源47475238dc6a0d4b28a5db22b0c1af223dc50297分支samurai-a5-ipe-alignment382，guard仍378-recovered，用host382，Image363/boot366/DT365/r29/r24保持。直接推进内核native bypass几何/striping消除私存HAL生成文件依赖，差分原完整算法，再扩尺寸/端口/核心/连续帧和V4L2m2m/libcamera/Gamma/LTM/CCM。保留381三BO/SID/复位retain与373/375/376/379修正、377/378失败审计。SSC旧故障未修，静态ICPdisabled/候选未永久装，完整goal active。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();anchor='## 最新交接\n';assert anchor in s;p.write_text(s.replace(anchor,anchor+'\n- [382内核ICA默认配置与幅度修复](../reference/kernel382/README.md)\n',1))
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[381实机首帧IPE像素通路](reference/kernel381/README.md)','[382内核ICA默认配置与幅度修复](reference/kernel382/README.md)'))
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('381当前：')
 p.write_text('382当前：原HAL/固件确认ICA默认配置并收敛到内核，实机NV12亮度逐字节相同，修复输出/4；色度少量阶跃邻域差异、完整IQ未验。完整事务与资源释放通过，复用381四摄基线，SSC旧故障仍在。Image363/boot366/DT365/r29/r24保持，goal active。[382证据]('+prefix+'reference/kernel382/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=382,actual_nv12_levels_correct=True,full_iq_or_optical_calibration_verified=False,goal_status='active')))
