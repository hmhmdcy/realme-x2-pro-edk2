from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];read=lambda p:json.loads(p.read_text())
for name in ['firmware-io','negative-control','session','owner','dispatch','worker','intree-build','boot-runtime','io-runtime','camera-runtime','final-state']:assert read(HERE/(name+'-validation.json'))['passed']
runtime=read(HERE/'boot-runtime-validation.json');assert runtime['same_boot'] and runtime['ipe_io_config_passed']
source=read(HERE/'source-state.json');audit=read(HERE/'io-runtime-validation.json')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=read(p)
 d.update(stage=379,latest_work_stage=379,current_boot_guard_stage=378,current_boot_guard_path='/var/lib/samurai/k378-recovered/boot-id-private.txt',
  current_boot_guard_evidence=prefix+'reference/kernel378/recovery-cleanup-validation.json',current_camera_evidence=prefix+'reference/kernel379/README.md',
  current_device_revalidated_stage=379,current_device_runtime_state_verified=True,device_closeout_evidence=prefix+'reference/kernel379/final-state-validation.json',
  device_recovered_boot_evidence=prefix+'reference/kernel378/recovered-boot-validation.json',device_recovered_baseline_capture_evidence=prefix+'reference/kernel379/camera-runtime-validation.json',
  in_progress_stage=379,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel379/README.md',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  icp_latest_attempt_evidence=prefix+'reference/kernel379/boot-runtime-r1-validation.json',icp_latest_attempt_recovery_evidence=None,
  icp_latest_attempt_normal_terminal=True,icp_latest_attempt_followed_by_system_reboot=False,icp_latest_attempt_followed_by_modem_watchdog=False,
  icp_latest_hfi_response_latency_ms=audit['ready_response_latency_ms'],icp_sys_init_evidence=prefix+'reference/kernel379/boot-runtime-r1-validation.json',
  icp_full_hfi_lifecycle_verified=True,icp_full_hfi_lifecycle_evidence=prefix+'reference/kernel379/io-runtime-validation.json',icp_hardware_cleanup_verified=True,
  icp_latest_device_experiment_stage=379,icp_last_recovery_stage=378,icp_last_recovery_evidence=prefix+'reference/kernel378/recovery-cleanup-validation.json',
  icp_image_sessions_hardware_tested=2,ipe_sessions_created_destroyed_hardware_verified=True,ipe_sessions_hardware_evidence=prefix+'reference/kernel379/io-runtime-validation.json',
  ipe_max_simultaneous_sessions_tested=2,ipe_config_io_hardware_verified=True,ipe_config_io_hardware_evidence=prefix+'reference/kernel379/io-runtime-validation.json',
  ipe_config_maps_hardware_verified=2,ipe_config_unmaps_hardware_verified=2,ipe_scratch_bytes_observed=[48,48],
  ipe_image_frames_submitted=0,ipe_image_processing_hardware_verified=False,icp_hardware_backend_installed=False,
  whole_system_healthy=False,checked_runtime_healthy=False,ssc_failure_evidence=prefix+'reference/kernel379/ssc-failure-validation.json',
  desktop_recovery_evidence=prefix+'reference/kernel379/desktop-restore-validation.json',ssc_currently_healthy=False,sensor_proxy_currently_running=False,
  icp_previous377_failure_evidence=prefix+'reference/kernel377/attempt-audit-validation.json',icp_previous378_failure_evidence=prefix+'reference/kernel378/attempt-audit-validation.json',
  icp_next_step='Implement image DMA/IQ/CDM/striping and frame completion from retained OEM HAL/firmware and GPL manager; verify independent A5 and IPE engine SMMU SID ownership, then libcamera m2m. Two configured sessions have submitted zero image frames.',
  current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：379（两路 IPE IO 配置实机通过；图像数据面未接，目标 active）

2026-10-20。先读 WORKING-BOUNDARIES.md、reference/kernel379/README.md。优先复用固定仓库和原厂提取证据，按 SoC、板级、主线框架、驱动、用户空间区分修改。不要将会话配置成功视作图像处理或校准完成。

## 当前设备与源码

当前是378失败后恢复的启动，guard `/var/lib/samurai/k378-recovered/boot-id-private.txt`，用reference/kernel379/host.py（委托378的动态恢复guard），strict原密钥USB/known_hosts保持。377与378都自动重启；379没有重启，379-boot-r1 worker3830与collector均结束，finished/terminal/passed。失败事务保留，不重跑377/378。

实际Image363／7.3.0-rc6-rmx1931-samurai-k363+、boot366嵌入DT365、libcamera五包r29、config/stack r24及362四份私有Preview保持。原厂曝光/手动频闪、IFE Gamma、unit WB/CCT与动态LSC/CCM保留。静态ICP disabled，候选未永久安装。378恢复核对boot/logdump原始读回，379无刷写，无NV/OTP/工厂校准写入。

维护源 `/mnt/samurai-full282/source354`，分支samurai-a5-ack-status379，commit6b8e3b1a28ff9ea60391045b03b746499d1d9400；父3783347022f42202b9823b6945c6878189d3d64527d、3777ccaf8db4690cbedba43d44d065ccd93c119b30b。实际Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8，静态DT源码e217016006e609333a715c10f2f3e442dc4da95f未变。379 core SHAfb98ea6014318d46816505daf45a12e3fc9a364aff24561003b0c66c21d4d2a1、test SHAae29dd03d9fc69b368a47ec0a4db056b6bd018dd3d633c0e45810eea348cec62，in-treeY/W1/Werror无诊断。

访问ext4前先调用reference/kernel284/storage.py::mounted_build()，返回/mnt/samurai-full282/build，source354在旁；WSL退出会卸载，不重建/格式化镜像。libcamera源 /mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2；SDK /home/cy122/x2pro-linux/libcamera214-root，work bind串行。

## 本轮实际能力与现存降级

379 RT(type2)create→MAP→CONFIG_IO→UNMAP→非RT(type3)create→MAP→CONFIG_IO→UNMAP→逆序destroy→PC/WFI→cooperative stop→全释放/卸载通过，两个handle同时存在。实际scratch各48字节，13msgs/14IRQ/1debug，watchdog/protocol0；CMD读写120words、MSG133words按实际长度精确吻合，剩余会话/CPU/IRQ/backing/PM/mapping均0。证据379/boot-runtime-validation.json、io-runtime-validation.json。image_frames仍0。

同启动379新采四摄各12帧640×480，主摄隔离IPA27帧/5阶段/GammaACK，无新增故障/taint0。17个ICP/BPS/IPE时钟enable0、9相机电源disabled/users0、CAMSS/双CCI休眠，临时core/test/DT/固件/worker无残留。四摄与ICP证据均新生成，不能继续写“复用375同启动”。

378恢复启动时SSC自动启动出现旧FastRPC attach EPERM/daemon exit4模式，清理后SLPI offline、SensorProxy stopped、桌面未自动启动。379保存上下文，按实际状态临时nodeps启动greetd，依赖配置未改；桌面PW/WP/phoc/phosh各一进程已恢复。没有盲目重新attach共享池，没有重启整机。自动旋转/SSC尚不可用，不能把whole_platform_healthy写true。见379/ssc-failure-validation.json、desktop-restore-validation.json、final-state-validation.json；final-state passed仅相机/ICP收尾。

## 原厂ABI与必须保留的底层修正

372异常现场解码、373 reset/wake后编程并读回HFI参数、375 PC/WFI/CONTROL关闭确认后避免额外全局ICP/AHB块复位、376双token与IRQ join/错误锁存修正均保留，细节见376/README与旧NEXT对应文档。失败/未知/未清CPU使能仍强制复位；复位失败保留CPU/DMA/PM。旧强制复位后重启的具体总线/看门狗机制未直接测定。

优先已有352固定CAMSS原型ebd1e440443121d18f730ab2aeea5586a754f36f、Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6（352/oem与355/oem/cam_icp_hw_mgr.c），CamxChi9f17f1b568626b393e785b369c5dc94543774d7a（350/sources/camxipenode.cpp与377/sources/camxipenode.h私存）。原型不完整且async多一字段，不能直接套本机。CamxChi的ipe_data.h外部依赖未取得，优先本机HAL实际指令。

本机HAL camera.qcom.so-private在kernel281，SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde，debugELF/符号在350；原始SetConfigIOData0x2e4b88..0x2e4f00完整执行18例，确认image_desc84、format20、Y stride52/height56、UV stride60/height64、uvSwap24。payload1216（旧GPL头文件848不适用），maxBatch1192、尾userArg1208。自写encoder12组14592字节与原HAL完整输出相同，13invalid不改输出。

create命令28/ACK32，destroy44/实际ACK48，CONFIG_IO间接命令40/ACK56、scratch在reply36；MAP/UNMAP直接命令56/ACK44。MAP/UNMAP **只有header状态有效，12字节tail是未初始化分配器内容**，不得再读作payload错误；CONFIG_IO与DESTROY仍检查有效payload状态。379原厂指令模型改用dirty allocator，旧parser反例失败，新parser与40会话/25owner场景通过ASAN/UBSAN。

377配置槽07420000落入固件debug映射：debug存储100KiB但原始HFI_QueueGetQHdr建立07403000起1MiB映射，原始重叠检查复现首次MAP拒绝；实际377未记录精确HFI错误码。378移至07600000实机MAP/CONFIG成功，却误读UNMAP尾，二次UNMAP被拒绝，强制清理后自动重启。377/378各自attempt-audit-validation.json严格只取最新窗口，worker未落终态，不冒充正常清理成功。

## 下一步直接工作

进入IPE frame处理所需的图像/命令/IQ/striping/CDM布局、DMA所有权与完成通知；控制配置已有真实硬件证据，无需重复同一握手/配置来回扫描。核对原厂GPL管理器buffer patch、acquire/config/frame流程和HALSetup/striping路径，按固定文件取源，禁止partial clone全树git grep导致海量lazyfetch。

A5当前SID2222只证明控制CPU映射，IPE/BPS引擎SID、上下文/共享域不能等同。图像缓冲走内核DMA/IOMMU和明确寿命/缓存/错误回滚，不能抢CAMSS现有stream，不能用户空间MMIO。命令别名07600000/4KiB已避开固件队列映射，处于既有shared保留窗口；没有新板级DT保留区。确认引擎帧完成与输出后再接libcamera m2m及Gamma/LTM/CCM。

第五2MP身份仍未知，OV02A1B库名不算识别；共享front PHY2/MCLK2/reset12与GPIO29 mux待解。更多模式、动态帧时长、自动防频闪、光学/几何/同步/连续AF等见363/REMAINING-CAMERA-SCOPE.md。延期纯色/遮光可后做，整体goal active。

## 私存、工具与回退

公共Git /home/cy122/edk2-samurai/repo，范围Platform/Realme/sm8150；根目录不是Git。原厂ELF kernel352/CAMERA_ICP.elf-private，3630392bytes SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。完整汇编370/firmware-armv7-private.asm，objdump -m armv7；Unicorn /home/cy122/x2pro-linux/private-k329-venv/bin/python。377/378失败pstore与379成功日志/模型/模块均私存kernel对应目录。raw固件、回包、异常、校准、密钥不进公共Git。

boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924；logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。旧boot276+logdump363、旧k298模块/logdump与362回退包均保留。未请求push/PR，仅本地提交。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel379/README.md。379实机两个IPE RT/非RT会话均MAP/CONFIG_IO/UNMAP后销毁，scratch48/48、13msgs/14IRQ、CMD120/MSG133，全HFI/协作停机/卸载及新四摄各12帧/主摄隔离27帧Gamma通过；图像帧仍0。guard378-recovered，用host379；379无重启/刷写/永久安装，Image363/boot366/DT365/r29/r24保持。源6b8e3b1a分支samurai-a5-ack-status379。保留373启动与375停机、376双token/IRQ join；IOpayload1216、imageDesc84，CONFIG ACK56，MAP/UNMAP ACK44的tail未初始化不可当状态。377槽在debug的1MiB映射内已移到07600000；378误读UNMAP已修，失败事务/重启如实记录。直接做IPE图像DMA/IQ/CDM/striping/frame completion，核对独立引擎SID与缓冲所有权，再接libcamera m2m和Gamma/LTM/CCM。SSC恢复启动attach EPERM/exit4未解决，SLPI offline/SensorProxy stopped；桌面已nodeps恢复，别宣称全系统健康或盲目attach。第五摄/更多模式/光学校准/同步/AF仍待。原固件/日志/回包/个体校准仅私存。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();anchor='## 最新交接\n';assert anchor in s;s=s.replace(anchor,anchor+'\n- [379两路IPE IO配置实机通过](../reference/kernel379/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[376两IPE会话实机生命周期](reference/kernel376/README.md)','[379两路IPE IO配置实机通过](reference/kernel379/README.md)');p.write_text(s)
for relative,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=ROOT/relative;s=p.read_text();first,rest=s.split('\n',1);assert first.startswith('376当前：')
 p.write_text('379当前：两路IPE会话各MAP/CONFIG_IO/UNMAP并销毁，完整HFI/停机/卸载实机通过，图像帧仍0；新四摄取流及主摄隔离Gamma通过。Image363/boot366/DT365/r29/r24保持，候选未永久安装。恢复启动SSC attach失败未解决，桌面已恢复，SensorProxy未运行。目标active。[379证据]('+prefix+'reference/kernel379/README.md)。以下为历史。\n'+rest)
print(json.dumps(dict(stage=379,current_boot_guard_stage=378,ipe_io_config_hardware_verified=True,ipe_images_verified=False,ssc_healthy=False,goal_status='active')))
