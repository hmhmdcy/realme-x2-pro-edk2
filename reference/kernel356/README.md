# 356：A5 固件启动后端与板级内存修正（尚未打通）

2026-10-20。新增 A5 固件启动、IRQ/HFI 命令响应和停止后端，已完成候选构建；实机各次启动没有完成 SYS_INIT、PING、PC_PREP 握手，不能视为 ICP 或 IPE 已可用。R5 启动后 USB/Wi-Fi SSH 握手无响应，进程和系统状态仍未知。

本轮发现一个板级适配错误：最初沿用通用 SM8150 的固件物理地址 `0x8b700000`。匹配 Realme X2 Pro 的原厂 AndroidR 源码 `23172a1571bd91156032cc9fef16284a82b63d2c`、`arch/arm64/boot/dts/19781/sm8150.dtsi` 实际定义 `0x9ab00000`／5 MiB；当前 k298 DTB 也已有完全相同的独立 no-map 保留区。旧地址位于 `memory@86200000` 的大块保留区内，不能作为相机 RAM 使用。[来源及 DTB 对照](board-memory-validation.json)。保留区地址正确仍不等于 CPU 访问和固件执行已通过。

当前实现改用 `memory-region-names = "firmware"` 解析专用 DT 节点，不再接受“MMIO reg 落在任意 no-map 区内部”。要求该节点可用、no-map、页面对齐且恰好 5 MiB，并独占申请对应内存资源。临时 DT 覆盖引用现有 `memory@9ab00000`，没有新增物理保留区；主机实际合并后检查引用解析通过。12 项实际选择函数体检查覆盖正确／缺失／非首项引用、禁用／缺 no-map、地址解析失败、尺寸／对齐错误和旧大块区域拒绝。[选择检查](board-region-selection-validation.json)。旧的内存生成脚本已删除，避免覆盖后来修正。

[启动后端](kernel/camss-icp-a5-boot.c) 复用355的 CAMSS supplier PM／ICP/BPS/IPE 资源，实现复位、ELF 加载、固件 privileged IOVA 映射、共享队列与 1 MiB 堆、上电、IRQ、SYS_INIT／PING／PC_PREP 响应匹配和停机。只在完整类型及错误码匹配后认定命令成功。停止前保留内存所有权，复位成功并断电后才撤销映射；失败不强行释放。没有图像会话或 IPE IO/IQ 命令。QDSS 保留地址空间但未启用传输。

启动加入500ms内核 hrtimer，超时清 A5 EN/WAKE 和中断使能，正常清理仍负责复位、断电及释放。它只覆盖 CPU 启动后的等待，不能保护此前发生的物理内存访问。9 项实际回调及 PM 包装函数体检查通过。[结果](boot-timeout-validation.json)。R2 暴露 ICP BCR 在置位时 AHB 分支无法开启，现改为先释放 BCR 再开时钟，上电后再执行启动复位脉冲；移除时也处理 driver core 自动 runtime-resume。

[内存后端](kernel/camss-icp-a5-memory.c) 支持固定非零 IOVA 的共享／堆 coherent RAM，以及独立固件 carveout；固件映射增加原厂要求的 IOMMU_PRIV。实际函数体在主机和 ARM 环境各51项检查通过，覆盖逐页映射、外来映射拒绝、失败回滚、撤销失败保留 RAM 及重试。[内存检查](memory-validation.json)。这些 API 桩检查不能替代真实 SMMU 或固件执行。

实际设备尝试均保留失败：

| 尝试 | 已观察结果 |
| --- | --- |
| R1 | 缺 privileged 的取指映射出现 SID2222／IOVA0 权限 fault；随后有 modem watchdog，设备自动重启。恢复后读取到旧 pstore，原工作目录未持久化。不能声称正常清理完成。 |
| R2 | 在 CPU 释放前失败；AHB 分支时钟等待超时，出现 WARN，taint0→512。终态进程退出，临时模块／节点／固件文件移除，时钟引用归零。 |
| R3 | 读到 firmware-version `0x01000100` 和 init-response3，但无 IRQ／SYS_INIT 响应，超时失败。版本寄存器值不证明固件初始化成功。清理完成，taint512未增加。 |
| R4 | IOVA `0x00500000` 取指 translation fault，500ms超时回调实际触发；失败后复位、断电及映射释放。没有完整握手。动态覆盖移除仍有 OF 引用计数错误，不能称为无内核资源泄漏。 |
| R5 | 使用了错误的通用物理 carveout 地址，worker7780启动后 SSH 握手无响应。最近只读查询仍超时；无法确认进程是否终止、是否重启或哪些阶段已执行。没有重启同一事务。 |

R2～R4 原报告分别见 [R2](boot-runtime-r2-validation.json)、[R3](boot-runtime-r3-validation.json)、[R4](boot-runtime-r4-validation.json)；[汇总](boot-attempts.json) 明确区分终态失败和未观察状态。OF 引用错误后来才识别，旧报告的相关故障计数没有包含它；当前辅助脚本已将 OF ERROR 纳入统计。

修正后的第7次构建 W=1／-Werror 通过，无诊断：core229000字节、test66824字节，匹配 k298／intree=Y。[构建](intree-build-validation.json)。源码提交 `3a485310daa7baed7d1f0d1798ded15cc85ad1ab`，父355，七文件，当前分支干净。[源码](source-state.json)、[补丁](a5-icp-bootstrap.patch)。仅 BUILD 保存私有 DTBO 头；原厂 ELF、源码原件、反汇编、日志和模块二进制继续私存。

修正候选未发送到手机，没有修改持久 DT、已安装模块或 NV。此前试验确有自动重启及当前连接异常；此时不能用旧部署快照声称设备仍正常取流。恢复 SSH 后先读同一 R5 事务、boot ID 和 pstore，再判断是否可以清理或重新实验。

完整目标继续：实际 ICP/HFI 启动、IPE 会话及 IO/IQ、libcamera 图像处理接入和原厂 Gamma/LTM/前摄 CCM，另有曝光表／防频闪、模式、光学、几何同步与连续 AF。四摄旧有硬件采集、AE/AWB、主摄单次 AF 及原厂／个体校准集成属于此前已验证能力，本轮没有重新验证它们。
