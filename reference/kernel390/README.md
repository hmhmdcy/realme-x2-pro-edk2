# 390：正式 CAMSS/ICP 平台部署，111帧与卸载重载通过

已将[389正常平台驱动与板级候选](../kernel389/README.md)实际部署到手机。真实icp@ac10000绑定qcom-sm8150-icp，正常CAMSS与ICP共用模块所有者，完全不依赖测试模块或临时overlay。一次正常重启、只刷boot；Image363和logdump365保持。原生18帧、实际libcamera81帧及重载后12帧，共111个IPE作业全部direct，copy/cancel/failed均0。完整多摄／ISP校准目标继续active。

## 部署与分层

沿用已完成的仓库／方案评估、原厂ELF/HAL反编译证据和389产物，本轮不重新实现核心、改动传感器或重复构建。SoC层仍为已有A5/HFI/条带/IQ旁路与388直接DMA；正常媒体平台所有权和七SID静态板级适配现已启用。用户空间先用完全不变的387私有候选验证IPE；已安装五个libcamera包仍为99990.7.2-r29，config/stack仍0.1.0-r24，尚未永久安装IPE用户空间候选。

[预检](preflight-validation.json)核对运行中的boot366和logdump365、原CAMSS/SG加载身份及目标文件存在／缺失。Image363的实际嵌入CPIO仅含三个蓝牙模块，没有相机模块，正式驱动会从根文件系统加载。

[文件安装](module-install-validation.json)只覆盖原qcom-camss和videobuf2-dma-sg，新增A5 core、m2m adapter及标准v4l2-mem2mem，共五个模块；原厂固件写入/lib/firmware/qcom/sm8150/camera-icp.elf。精确备份原两文件、记录其余三模块及固件的原始缺失，执行depmod并核对路径／摘要。安装时旧代码仍在内存，未临时重载来冒充正式板级启用。

[停机](quiesce-validation.json)正常停止桌面／相机／音频／DSP与显示，保留相机provider，无新故障；一次restart2进入已知fastboot，核对实际身份和分区大小后只刷boot。[刷写](flash-validation.json)及[新启动读回](postboot-validation.json)证明：boot389 SHA256 e0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f，logdump365不变；实际DT、五模块文件及加载note均匹配，probe不启动固件。不是只看磁盘上存在DT文件。

当前驱动／板级维护源source354，branch samurai-icp-platform389，commit a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07；本轮没有改内核源码。Image仍来自363的ba61a62293e0f6bc5838c06f2e85e033e3d702a8，release为7.3.0-rc6-rmx1931-samurai-k363+。模块构建配置和实际驱动功能不能与未重建的Image配置混为一谈。SoC通用DTS默认disabled，Samurai实际板级DT现在okay。

## 实机验证

[汇总](hardware-validation.json)、[最终管线窗口](runtime-r2-validation.json)、[重载窗口](reload-validation.json)分开保存各次数据，没有重复累计原生阶段。

|阶段|结果|
|---|---|
|正常CAMSS owner导出生命周期|关视频FD后users0/jobs0/owner_refs1；再关导出FD只留mmap仍1；最后munmap归0|
|原生V4L2|NV12 MMAP6；NV21 DMABUF stride672/sourceoffset16四；双并发上下文各四，共18 direct|
|实际四摄libcamera→IPE|imx471/imx319/s5k3m5/s5kgw1各12帧640×480 NV12|
|主摄RAW+NV12 / RAW-only|各6请求，保留原始IFE时间戳／SOF；RAW-only IPE0|
|强制隔离IPA主摄|27帧、5控制阶段、Gamma ACK1、独立统计进程|
|正常模块卸载／重载|停相机消费者、owner_refs0且DMA回收后rmmod qcom_camss，ICP与CAMSS均注销；modprobe正常重绑，probe未启动FW|
|重载后候选IPE|广角另12帧，direct12/错误0|
|已安装原IFE路径|四摄各12帧，无bus错误，IPE作业数保持不变|

正式驱动第一次有效窗口累计99帧，显式卸载／重载后计数归0，再完成12帧；本轮合计111，不能把当前计数12误判为漏帧。最后一次FW运行单会话create/destroy/peak1，12帧、43消息／44中断，INIT/PC确认，watchdog/protocol错误0。正常卸载和已释放状态得到实测，不外推任意热拔插、强制卸载或真实硬件错误并发。

[像素对照](pixels-validation.json)独立复核原生18帧输入CRC、客户端每帧有效Y相同、各组末帧全图CRC与UV误差，UV MAE保持0.203125；padding保持调用方0xa7。去复制结论限已测m2m／候选libcamera到核心图像路径，不表示全部应用显示链路或完整implicit-fence互操作已经验证。IPE仍为1:1 NV12/NV21与IQ旁路，隔离IPA的Gamma ACK不等于IPE完整IQ校准完成。

## 失败与当前状态

runtime-r1的导出生命周期和原生18帧均通过，随后客户端在首个管线capture启动前因仍检查旧snapshot-collector.py文件名退出；新collector名为dump-collector.py。没有因此改驱动／DT、重刷或重启。[失败审计](attempts-validation.json)保留r1整体失败、已完成原生阶段及清理。r2只补跑缺失管线，复用r1原生证据，不把失败窗口整体改成成功。

标准devcoredump collector在FW运行前启动，只处理本设备新dump；最终窗口未捕获dump、未超时，worker/client/collector均终态。测试脚本的sysfs符号链接路径在首个FW作业前已按真实路径匹配。包版本查询器的一次嵌套换行转义错误只影响只读查询，改为raw字符串后7个指定版本核对通过，没有设备状态切换。

[当前状态](current-state-validation.json)：正常ICP与m2m永久注册，固件文件保留供按需启动；CPU/IRQ/PM/backing、映射、导入引用均释放，CAMSS/ICP/双CCI suspended，17相关时钟0、九路相机电源disabled/users0，taint0、PW/WP各一。owner_refs当前53来自桌面普通相机句柄，m2m users0，并非53个导出缓冲区。SLPI本次启动运行，不能据此宣布旧SSC间歇故障已修复。

## 回退与接续

[回退准备](rollback-validation.json)保存设备上的原两模块，也从原363离线模块包提取并逐摘要确认同一原件；完整原boot366已在本地。设备/var/lib/samurai/k390-deployment内有rollback-files-private.json、backup及restore-files.py。恢复文件辅助程序仅在相机消费者停止、DMA回收后使用--offline-files-only，恢复原两文件、移除原本不存在的三模块／固件并depmod；它不切换已加载代码，仍需配合已验证的boot366切换／重启。恢复程序仅准备，未执行。避免把整套778模块或旧logdump反复重装。

当前SSH使用host390与新guard /var/lib/samurai/k390-active/boot-id-private.txt；旧378guard已不适用。原密钥／known_hosts保持，未重新授权。普通底层与拍摄工作继续自动推进，照明相关光学／颜色测试按用户关灯条件后做，黑／噪点不单独判链路故障。

下一步落实正式IPE用户空间包，再补显式在途取消／硬件错误并发，并推进原厂Gamma/LTM/CCM完整IQ。继续保留[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP、更多模式、动态帧时长／防频闪、几何／多摄同步和连续AF等，不把目标缩成四摄111帧。FW/HAL/反汇编/CDM/完整日志/图像/个体校准仅private；公共镜像只本地提交，不push/PR。
