# 385：多尺寸、NV21与交替会话连续提交

已有原生bypass路径完成四组实际配置，共16帧，RT和非RT各8帧交替。所有帧亮度等于当帧输入，输出CRC随图案变化，正常释放资源。完整多摄／ISP目标仍active；V4L2 m2m/libcamera与完整IQ尚待接入。

只修改临时内核诊断模块，增加宽高、端口、max_cores、NV12/NV21及帧数参数，最多8帧/64MiB，非法参数在资源获取前拒绝。SoC传输、条带、IQ、DMA回收保持384，核心二进制与384完全相同。板级DT、主线框架、传感器和用户空间未改。

维护源分支samurai-a5-ipe-frames385，提交6fb4806e219998f5d06919a9b0266ff7b08867b0，父5a0df37d3e9c8971d55186e468b38b424c8387dc。候选仅临时加载并卸载，未永久安装。[变更](diagnostic-frames.patch)、[状态](source-state.json)。

每帧改变亮度/色度图案与request_id，RT/非RT交替，同步串行提交。记录输入输出CRC、Y差异字节数与UV绝对误差和，只保留末帧完整图像以控制内存。BL容量512KiB，仍在既有1MiB请求parcel内。

|事务|尺寸|端口|max_cores|格式|帧数|UV MAE|
|---|---|---|---|---|---:|---:|
|r1|128×128|8显示|1|NV12|2|0.1953125|
|r2|640×480|9视频|2|NV21|4|0.203125|
|r3|1920×1080|8显示|2|NV12|6|0.2309028|
|r4|4608×3456|9视频|2|NV21|4|0.2452257|

[coverage-validation.json](coverage-validation.json)汇总每组boot-runtime-rN-validation.json、pixels-rN-validation.json。四次同一378恢复启动，各自唯一目录/var/lib/samurai/k385-boot-rN。worker依次15018、15194、15302、15445，与collector均终态退出。

每次双会话创建/CONFIG_IO/scratch48/48、相应帧数MAP/FRAME/UNMAP、双destroy、PC/WFI/正常停机通过。每次taint0、watchdog/protocol0、新相关fault0、17相关时钟归零、临时模块/DT/FW无残留。

所有16帧共77404160个Y字节均等于当帧输入；主机独立重建输入CRC，组内输出CRC逐帧不同。每组末帧完整像素、CRC、UV误差主机复核；前面帧完整图像未保存，不称逐帧主机全图对比。UV仍有滤波差异，不是全平面identity。max_cores=2配置实机完成，未分别测量两IPE负载/吞吐，也不是持续满帧率或并发双流验证。

[diagnostic-validation.json](diagnostic-validation.json)：实际诊断C体ASAN/UBSAN，8帧变化、分配/提交失败不发布未完成帧、Y破坏记录、JSON不截断、非法参数/容量拒绝通过。[worker-validation.json](worker-validation.json)覆盖原脚本清理与错误路径及多帧判断。

[intree-build-validation.json](intree-build-validation.json)：实际k363配置in-tree/W1/-Werror无诊断。核心317008B，SHA256 b429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d；测试110008B，SHA256 f0c9378d2736fe38269e3319b5017f5ef6421ae5f1af588c544f0d3321fa0953。未重复未改的384算法和故障注入全套，实际核对核心文件相同。

[current-state-validation.json](current-state-validation.json)：源干净且等于提案，CAMSS/双CCI休眠、9电源disabled/users0、静态ICPdisabled、无临时FW/模块，四组worker/collector均不存活。Image363、DT365/boot366、libcamera r29、config/stack r24和362私有Preview保持，四摄采集复用381，SSC旧故障未修。没有真实摄像头采集或光学校准声明。

算法依据沿用[384](../kernel384/README.md)、[383](../kernel383/README.md)的原HAL/原固件差分，已有原型的缺失文件/旧接口评估见[352](../kernel352/README.md)，不当可直接部署驱动。本轮复用本地原FW，没有下载替代固件。

接续重点是V4L2 m2m/libcamera真实入口及队列、会话、取消/错误生命周期，再接原厂Gamma/LTM/CCM完整IQ。CPU-copy bring-up不是最终零拷贝视频路径，合成图不能替代真实多摄校准。[剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)中的第五2MP、多模式、动态帧长/自动频闪、光学/几何/同步/连续AF保持。

现场按低照度解释，黑/噪点不是单独故障证据。原FW、图像、完整日志和个体校准等仅私存/mnt/e/edk2-samurai-out/kernel385；公共目录只含自有代码、脚本与脱敏结果，本地提交不push/PR。
