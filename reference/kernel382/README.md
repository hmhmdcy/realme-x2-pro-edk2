# 382：内核生成 ICA 默认配置，实机 NV12 幅度恢复

修复 [381 首帧像素通路](../kernel381/README.md) 中输出幅度为输入四分之一的问题。相同 640×480 合成输入、相同原厂 striping、相同 Stream ID 与缓冲所有权下，新的内核默认配置使 **307,200 个亮度字节全部与输入相同**。色度平均绝对误差0.203125，差异全部位于输入色度阶跃附近；不能称为全平面逐字节旁路或完整 IQ 验收。[像素](pixels-validation.json)、[色度位置](chroma-validation.json)。

## 原厂证据和分层实现

优先复用了固定 CamxChi `9f17f1b568626b393e785b369c5dc94543774d7a` 的 IPENode/ICA 源码和本机 HAL、原厂固件。额外公开搜索没有取得更合适的字段定义，未把无结果视为所有仓库都没有实现。

现有源码明确将 ICA1/ICA2 的 `invalidPixelModeInterpolationEnabled` 与 `eightBitOutputAlignment` 设为1。本机 HAL 的原始指令片段进一步确认2584字节 IQ 内四个 u32 偏移为52、68、244、260，实际执行该片段得到同样四个1。只执行了该有明确入口寄存器夹具的片段，未宣称执行完整 HAL request。

原厂固件的 frame handler 将 ICA 参数偏移68的值归一化为布尔值，再交由 CDM 生成代码写入 ICA 对齐寄存器。执行原始指令片段，覆盖0、1、2、全1及两引擎寄存器0x129c/0x169c共8例。它是字段到寄存器的直接证据，完整引擎 handler 没有在模型中执行。[ABI证据](alignment-abi-validation.json)。

完整原厂 HAL striping 算法的5组差分分别设置零、ICA1对齐、ICA2对齐、双对齐、四个默认值；640×480输出与380保留结果逐字节相同。输出沿用相同脏分配器初值；这些默认值由固件在帧处理阶段消费，因此无需修改该条带夹具。其它尺寸、端口与核心的新默认配置尚未在硬件验证。

**SoC／驱动**新增 [最小 IQ 编码函数](bypass-iq.c)，在内核清零结构后写四个默认值。运行接口移除了外部 IQ 指针／长度，测试模块也不再加载零 IQ 文件；核心只生成当前已核实的8位线性YUV模块关闭配置。任意模块、CDM或光学参数仍未开放。[补丁](bypass-iq.patch)。

**板级**复用381临时overlay，未修改静态板级DT、域、时钟或电源。**主线框架**没有改动，沿用DMA/IOMMU/PM设施。**用户空间**没有修改已安装libcamera r29或配置r24；也没有通过像素乘4补偿。命令、输出完成及不确定DMA的停止／复位保留路径均沿用381。

## 实机和软件验证

一次事务 `/var/lib/samurai/k382-boot-r1`，worker11416与collector均terminal、已退出。INIT/PING、两handle各CONFIG_IO、RT单帧及72字节ACK、双destroy、PC/WFI与cooperative stop全部通过。CMD158/MSG173words、16messages/17IRQ/1debug，无watchdog或protocol error。DMA/FW映射/PM/临时模块和两份固件文件均回收，无新增相关故障、taint0。[运行](boot-runtime-validation.json)、[独立核对](io-runtime-validation.json)。

输入／输出CRC与主机重算吻合。Y全平面精确一致；UV143040/153600字节精确一致，U阶跃最大距离4个亮度横向像素，V阶跃最大距离2个色度行，离开这些邻域后色度均相同。实际滤波／舍入算法尚未推导；本次四个默认值同时改变，未在硬件隔离单字段因果。

内核 IQ 函数与原厂指令输出逐字节一致；所有不足2584字节和空指针无写入，超长缓冲尾不变，ASAN/UBSAN通过。实际传输／解析／回收函数24种情况通过，并在提交时核对全部IQ字节；所有者26、worker7、分发10种情况通过。实际 k363 配置 in-tree W=1/-Werror构建无诊断。[IQ检查](bypass-iq-validation.json)、[传输检查](transfer-validation.json)、[构建](intree-build-validation.json)。

维护源分支 `samurai-a5-ipe-alignment382`，提交 `47475238dc6a0d4b28a5db22b0c1af223dc50297`，父381 `24a9f41f97c9fbadf5f941bde2d22fe3ac59c6c8`。没有刷写、重启或永久安装。仍是378恢复后的同一启动；Image363/boot366/DT365、r29/r24及私有Preview不变。

四摄驱动、板级资源及用户空间未改，复用381同启动的四摄各12帧和主摄隔离IPA27帧/Gamma结果；本轮没有重复采集。新收尾确认CAMSS/双CCI休眠、9路相机电源disabled/users0、17个ICP/BPS/IPE时钟enable0，临时节点／模块／文件／worker无残留。SSC旧启动失败、SLPI offline与SensorProxy stopped仍未修复，桌面保持，不宣称全平台健康。[收尾](final-state-validation.json)。

## 后续与私存

当前仍依赖私存原HAL算法产生的striping测试文件。下一步优先将已核实的线性NV12模块关闭几何／条带生成收敛到内核，按原算法作差分，并覆盖更多尺寸、端口、核心和连续帧；随后接V4L2 m2m／libcamera以及原厂Gamma/LTM/CCM。第五摄、更多模式、动态帧时长／自动防频闪、几何／同步／AF和完整光学校准仍待，整体goal active。

原始源码／HAL／固件／反汇编、生成夹具、输入输出图像、完整日志、模块和overlay只私存 `/mnt/e/edk2-samurai-out/kernel382` 或原阶段目录。公开目录仅自有函数、补丁、模型与脱敏摘要。本地提交，未push。
