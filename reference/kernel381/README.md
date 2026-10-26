# 381：实机首帧 IPE 像素通路通过，零 IQ 的输出幅度仍待修正

继 [380 原厂 striping 与帧编码](../kernel380/README.md)，本轮在手机上提交了一帧 640×480 合成 NV12，收到原厂固件的 72 字节完成回复并取回 460,800 字节。亮度平面每个字节都等于已知输入除以 4，色度图案基本对应，确认实际像素经过 IPE；尚未通过正常 NV12 幅度或画质验收。[像素检查](pixels-validation.json)。

## 分层实现

- **SoC／驱动**：沿用原厂组合 ICP 域的七个 Stream ID 规格，使用内核 DMA/IOMMU 接口管理命令、输入及输出缓冲。命令包位于已有共享 IOVA 预留中的 0x07800000；图像位于 0x20000000／0x24000000。新增 128MiB IOVA 名字空间预留，不额外保留物理 RAM。
- **板级**：只在临时测试 overlay 声明上述域与预留，离线合并确认所有已有 DT 属性不变。静态 ICP 仍 disabled；Image363、boot366、DT365 不变，未永久安装候选。
- **主线框架**：复用现有 DMA、IOMMU、PM、sysfs 和固件加载设施。未修改媒体核心或建立用户空间 MMIO 通路；V4L2 m2m 队列及 libcamera 接入尚未实现。
- **用户空间／校准**：未修改已安装的 libcamera r29、config/stack r24 或四份私有 Preview。首帧使用原厂 HAL 完整算法在 380 生成的 striping，以及 2584 字节全零 IQ，仅用于模块关闭的通路验证。

[核心改动](ipe-transfer.patch)、[传输实现](transfer-methods.c)、[IPE 停止确认](ipe-quiesce.c)、[临时测试模块](camss-icp-a5-boot-test.c)。维护源提交 `24a9f41f97c9fbadf5f941bde2d22fe3ac59c6c8`，分支 `samurai-a5-ipe-transfer381`，父为 380 的 `1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6`。

帧使用已验证的 opcode6／间接命令40／payload3816／ACK72。核心只接受全零 IQ；拒绝任意 IQ/CDM 注入。正常完成后同步并拷贝输出，再 UNMAP 及回收。完成不可信或超时时保留全部相关缓冲及电源，停止 A5 后必须取得两路 IPE 的 CDM、TOP 复位确认才能解除待 DMA 状态。复位失败保留 backing，允许后续明确重试。测试模块隐藏 bind/unbind 属性并沿用未释放资源时的模块 pin。

IPE 复位定义来自固定 Realme GPL `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的 IPE/CDM 实现，并以原厂固件 ISR 确认 TOP 清中断寄存器。两引擎分别清除旧 ACK、CDM reset0xf、TOP reset3、等待新 ACK，再清除；本次实机在 A5 释放前均确认成功（[3,3]）。没有额外写入未经验证的 IRQ mask、CORE_EN 或 CPAS QoS。失败后复位的故障注入属于模型验证，本次未故意制造硬件失败。

## 实机结果

仅启动一次 `/var/lib/samurai/k381-boot-r1`，worker10189、collector 均已终止。仍在 378 恢复后的同一启动，未发送重启或刷写。RT、非 RT 两 handle 同时存在，各 CONFIG_IO 成功（scratch48/48），随后 RT 完成一帧，再逆序销毁两个会话，PC/WFI／cooperative stop／DMA与PM回收／模块卸载均成功。

CMD 读写索引158words、MSG173words，恰好覆盖全部命令与回复；16条消息、17次IRQ、1条debug，watchdog/protocol error均0。图像命令 MAP/UNMAP 各1，最终待 DMA、FW映射、backing、时钟组和电源域均0。[事务结果](boot-runtime-validation.json)、[独立核对](io-runtime-validation.json)。

主机重建合成输入，与内核记录的输入／输出 CRC 均吻合。全部 307,200 个 Y 字节严格为输入/4；UV 有148,320/153,600字节等于输入/4，平均绝对误差0.040625，输出无0xa5哨兵残留。该非恒定图案和逐像素关系证明真实数据传输；**不能将除以4解释为已经确定某个寄存器或位深转换的根因**，也不能称为正确旁路、正常曝光或完整 IQ 支持。

硬件实验后重新采集四摄：imx471、imx319、s5k3m5、s5kgw1各12帧640×480；主摄隔离IPA27帧、5控制阶段、GammaACK1。无新增相机故障，服务恢复，CAMSS/双CCI休眠，9路相机电源disabled/users0、17个ICP/BPS/IPE时钟enable0、taint0，临时节点／模块／三份固件文件及worker无残留。[四摄回归](camera-runtime-validation.json)、[收尾](final-state-validation.json)。

SSC启动attach/daemon exit4问题仍在，SLPI offline、SensorProxy stopped；沿用379已恢复的桌面。未盲目重新attach或宣称全平台健康。

## 验证与后续

真实函数体模型覆盖停止确认16、SID解析51、传输与全局回收24、会话41、测试所有者26、worker7、启动分发10种情况；C模型使用ASAN/UBSAN。MMIO、IOMMU、IRQ、分配器和PM是模型，不等于实际故障注入。实际 k363 配置 in-tree W=1/-Werror 构建无诊断，模块依赖仅现有核心。[构建](intree-build-validation.json)。

优先从保留原厂 HAL／固件的 FE、ICA、输出格式及 IQ 初始化路径定位幅度差异。固件 `LinearNv12FormatFe` 在0xf87a，`LinearNv12FormatWePass`在0xfd0a，HAL `IPEICA::Execute` 与 `IPEUpscaler12/20::Execute`可继续作为线索；尚未完成根因分析。保持每次输出和数据所有权验证，再接 V4L2 m2m／libcamera、原厂 Gamma/LTM/CCM，并推进第五摄、更多模式、几何／同步和AF。整体目标 active。

原厂 ELF/HAL/反汇编、生成的 IQ/stripe、输入输出图像、完整日志和个体校准均只私存 `/mnt/e/edk2-samurai-out/kernel381` 或原阶段私目录。公开目录仅自有代码、补丁、模型和脱敏摘要。本地提交，未 push。
