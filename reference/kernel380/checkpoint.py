from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['striping','frame-abi','frame-builder','intree-build','current-state']:assert read(HERE/(name+'-validation.json'))['passed']
source=read(HERE/'source-state.json');current=read(HERE/'current-state-validation.json');assert not current['phone_mutated']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p);assert d['stage']==379 and d['ipe_config_io_hardware_verified']
 d.update(stage=380,latest_work_stage=380,current_camera_evidence=prefix+'reference/kernel380/README.md',current_device_revalidated_stage=380,
  device_closeout_evidence=prefix+'reference/kernel380/current-state-validation.json',in_progress_stage=380,in_progress_installed=False,
  in_progress_evidence=prefix+'reference/kernel380/README.md',a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],
  a5_icp_candidate_source_installed=False,ipe_frame_builder_available=True,ipe_frame_builder_evidence=prefix+'reference/kernel380/frame-builder-validation.json',
  ipe_frame_wire_abi_evidence=prefix+'reference/kernel380/frame-abi-validation.json',ipe_striping_original_algorithm_evidence=prefix+'reference/kernel380/striping-validation.json',
  ipe_frame_completion_ack_bytes=72,ipe_frame_builder_hardware_exercised=False,ipe_engine_dma_hardware_verified=False,
  ipe_image_frames_submitted=0,ipe_image_processing_hardware_verified=False,whole_system_healthy=False,checked_runtime_healthy=False,
  icp_next_step='Own/map IPE engine SID ranges and IQ/stripe/scratch/BL/input/output buffers; implement FRAME_PROCESS with a 72-byte completion ACK and reset-aware buffer lifetime. Verify real output pixels, then libcamera m2m. Existing configured sessions and offline striping do not prove image DMA.',
  latest_stage_device_mutated=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：380（原厂 striping 与内核帧编码通过；实际 IPE 图像 DMA 未接，目标 active）

2026-10-20。先读 WORKING-BOUNDARIES.md 与 reference/kernel380/README.md。379是真实两路 IO 配置通过；380完成完整原厂 striping、固件 frame 分发/callback 执行与内核帧编码器，均属实质进展。尚未提交 IPE 图像帧，不能把离线模型作为画质或完整 ISP 验收。

## 当前设备与维护源

仍是378恢复后的启动，guard `/var/lib/samurai/k378-recovered/boot-id-private.txt`；reference/kernel380/host.py委托379→378动态guard，strict原密钥USB/known_hosts保持。380仅只读观察，无安装/启动模块、刷写、重启或相机重采。379-boot-r1 worker3830与collector均已finished/terminal/passed，379四摄同启动证据复用；377/378失败事务保留且不能重演。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+，boot366嵌入DT365、libcamera五包r29、config/stack r24及362四份私有Preview保持。原厂曝光/手动频闪、IFE Gamma、unit WB/CCT与动态LSC/CCM保留。静态ICP disabled，候选未永久安装；本轮读到taint0、CAMSS/双CCI休眠、临时ICP模块/固件无残留。

SSC在378恢复启动自动attach失败，daemon exit4，清理后SLPI offline、SensorProxy stopped。379保存上下文并临时nodeps恢复greetd，依赖配置未改；没有盲目重新attach共享池或重启。本轮只读确认SSC仍stopped，不宣称全系统健康。见379/ssc-failure-validation.json、desktop-restore-validation.json和380/current-state-validation.json。

维护源 `/mnt/samurai-full282/source354`，分支samurai-a5-ipe-frame380，commit1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6，父3796b8e3b1a28ff9ea60391045b03b746499d1d9400。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、静态DT e217016006e609333a715c10f2f3e442dc4da95f未变。380 core SHA21f2e6f001b45823a6abac81d7de01587ad632458322a78cf985c9dc92cd1883，test SHAae29dd03d9fc69b368a47ec0a4db056b6bd018dd3d633c0e45810eea348cec62，实际k363配置in-tree/W1/Werror无诊断；未安装。

访问ext4前调用reference/kernel284/storage.py::mounted_build()，返回/mnt/samurai-full282/build，source354在旁；WSL退出会卸载，不重建或格式化镜像。libcamera源 /mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2；SDK /home/cy122/x2pro-linux/libcamera214-root，work bind串行。

## 已验证控制链路与须保留修正

379实机两个不同RT(type2)/非RT(type3)handle并存，各MAP→CONFIG_IO→UNMAP后逆序destroy→PC/WFI→cooperative stop→全释放/卸载，scratch48/48、13msgs/14IRQ、CMD120/MSG133words，watchdog/protocol0，image_frames0。379四摄各12帧640×480，主摄隔离IPA27帧/5阶段/GammaACK，无新增相机故障；17个ICP/BPS/IPE时钟0、9电源disabled/users0等收尾通过。380未重做这些未改动组件的硬件测试，见379/io-runtime-validation.json、camera-runtime-validation.json、final-state-validation.json。

保留373 reset/wake后编程+读回HFI参数、375 PC/WFI/CONTROL确认关闭后避免额外全局ICP/AHB复位、376双token与IRQ join/错误锁存修正。失败/未知/未清CPU使能仍强制复位，复位失败保留CPU/DMA/PM；旧复位后重启的内部总线机制未直接测定。372故障现场解码见对应README，不能退回旧context/PC解释。

create28/ACK32，destroy44/ACK48，CONFIG_IO40/ACK56、scratch回复偏移36。IOpayload1216、imageDesc84；输入0、显示输出8、视频输出9，linearNV12格式20、UVswap偏移24，stride/layout52，userArg1208。377配置别名07420000落入固件07403000起1MiB debug映射，378移至07600000/4KiB；377实际错误码未保存。378已MAP/CONFIG成功，却误读UNMAP尾后强制清理自动重启，worker未存终态。MAP/UNMAP56/ACK44仅header状态有效，12字节尾是未初始化分配器内容，379已修；CONFIG_IO/DESTROY仍检查有效payload状态。失败审计见377/378的attempt-audit-validation.json，不能混入早先成功pstore。

## 380新增实际证据与代码

原HAL静态包含完整striping算法：ContextCreate144348、Execute1448f0、Destroy144988。380/hal-machine.py加载保留HAL到Unicorn，仅提供标准malloc/free/memset/memcpy/memcmp语义；内部striping算法不是桩。12组640/1920/4608尺寸×输出8/9×核心1/2通过，dirty allocator、输出canary、全部context分配释放验证。fixture为零IQ关闭模块、合成全帧zoom；未验证实际裁剪/画质。输出1pass；640两stripe、1920六stripe、4608为15/16stripe；BL容量156512/228512/396512。

原固件完整ProcessAsyncCommand、CheckCommandSize、Create/ReleaseCallbackData与OnDone_IpeFrameProcess执行，消费真实算法输出和C编码帧；OS/cache/queue/log等是模型，自动引擎电源分支关闭，真实frame engine handler和pixel DMA未执行。确认FRAME_PROCESS opcode6，间接命令40、payload3816，IQ2584；header92、frameSet232、14ports×2planes，结构容16batch，单帧拷贝324。striping需2268+624×所有pass条数（passCount在20，每pass412、stripeCount在428+412*i）。BL size内部减32，CDM数组偏移按base修正。

FRAME_PROCESS ACK **72字节** = header32+有效callback32+清零8，不能按CONFIG的56或旧packed长度。userArg3808另由本机HAL store指令证实，完整HAL request未执行。见380/frame-abi-validation.json。原厂回包和生成blob只私存，不镜像。

新增SoC camss-icp-a5-ipe.c/h进入核心Makefile，导出striping长度检查与单帧线性NV12/NV21编码。u64检查IOVA/plane容量、两两不重叠的stripe/IQ/scratch/BL/input/output六类范围，写入前完成所有检查。55invalid无输出改写，12组实际C函数输出送原固件消费模型；ASAN/UBSAN与实际内核构建通过。此接口**只是wire builder**，不映射/提交、不检验IQ/CDM语义、不管理DMA寿命；command arrays为0，未接frame完成所有者。

## 下一步直接推进

先落实ICP引擎SID与内核域/范围所有权，准备受控IQ/stripe、scratch、BL与输入输出图像，再接opcode6/72字节ACK与失败/复位缓冲保留，验证真实输出像素，再接libcamera m2m及原厂Gamma/LTM/CCM组合。不要继续重复379相同握手/配置作为新的数据面进展。

当前live静态ICP node只有A5 SID2222。原厂SM8150-v2组合ICP域SID规格为2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0；380按mask与实际CAMSS SID组核对无相交。逐引擎SID归属尚未识别，未附着/映射，A5映射成功不代表IPE引擎DMA可见。优先查固定GPL CPAS/设备资源源，避免抢现有CAMSS stream；复用内核DMA/IOMMU接口与明确寿命，不能用户态MMIO。

既有源：352固定CAMSS原型ebd1e440443121d18f730ab2aeea5586a754f36f（不完整、async多一字段）；Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6（352/oem DT/HFI、355/oem/cam_icp_hw_mgr.c）；CamxChi9f17f1b568626b393e785b369c5dc94543774d7a（350/sources/camxipenode.cpp、377/sources/camxipenode.h私存）。外部ipe_data.h未取得。按固定文件取源，禁止partial clone全树git grep触发海量lazyfetch。

第五2MP身份未知（OV02A1B库名非识别，front共享PHY2/MCLK2/reset12、GPIO29 mux待解），更多模式、动态帧时长/自动防频闪、光学/几何/同步/连续AF见363/REMAINING-CAMERA-SCOPE.md。延期纯色/遮光可后做，完整goal active。

## 私存与回退

公共Git /home/cy122/edk2-samurai/repo，范围Platform/Realme/sm8150；根目录不是Git。原HAL kernel281/camera.qcom.so-private SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde，debugELF/符号350。原FW kernel352/CAMERA_ICP.elf-private SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63，完整armv7 asm370。Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python，objdump -m armv7。380完整算法输出/编码帧/回包/模块在对应私人目录；raw固件、完整日志/异常/个体校准与密钥不进公共Git。

boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924，logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da，378恢复读回核对。旧回退boot276/logdump363、k298模块/logdump、362回退包均保留。未请求push/PR，仅本地提交。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel380/README.md。380新增内核帧wire builder，原HAL完整striping12组与原FW frame分发/callback/C编码12组通过，55invalid ASAN/UBSAN、k363内核构建无诊断；没有实际frame提交或设备修改。payload3816/IQ2584/header92/frameSet232、FRAME_PROCESS间接40/ACK72；striping2268+624Σstripe。源1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6分支samurai-a5-ipe-frame380。guard仍378-recovered，用host380，Image363/boot366/DT365/r29/r24保持。379两路MAP/CONFIG_IO/UNMAP/销毁与四摄真实证据复用。直接落实引擎SID/映射与IQ/stripe/scratch/BL/图像所有权、opcode6完成与故障保留、真实像素，再libcamera m2m/Gamma/LTM/CCM；当前只A5 SID2222，原厂组合域7规格与CAMSS无交但引擎归属/DMA未验。保留373/375/376/379修正，MAP/UNMAP ACK tail未初始化不可读状态。SSC attach/exit4未解决、SensorProxy stopped、桌面379已恢复。第五摄/模式/校准/同步/AF仍待，原始固件与输出仅私存。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();anchor='## 最新交接\n';assert anchor in s;s=s.replace(anchor,anchor+'\n- [380原厂striping与内核帧编码](../reference/kernel380/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[379两路IPE IO配置实机通过](reference/kernel379/README.md)','[380原厂striping与内核帧编码](reference/kernel380/README.md)');p.write_text(s)
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('379当前：')
 p.write_text('380当前：完整原厂striping与固件frame分发模型、内核帧编码/边界检查通过并构建；尚无引擎DMA或图像帧提交。本轮未改设备，复用379两路IO配置和四摄实机结果；SSC启动故障仍在。Image363/boot366/DT365/r29/r24保持，完整目标active。[380证据]('+prefix+'reference/kernel380/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=380,frame_builder_built=True,offline_striping_and_frame_abi_verified=True,last_device_experiment=379,current_boot_guard_stage=378,hardware_images_verified=False,goal_status='active')))
