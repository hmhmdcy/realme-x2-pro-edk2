# 355：原厂 A5／BPS／IPE 资源顺序与真实上电验证

2026-10-20。沿用原厂固件逆向路线，本轮补上 SoC 平台资源后端，并在手机验证 A5、BPS、IPE0、IPE1 上电及释放。没有启动原厂固件；完整多摄与 ISP 目标仍在进行。

从已保留的 Realme 原厂 GPL 提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 提取 ICP 管理器和 A5/BPS/IPE 驱动资源定义，[来源索引](oem-resource-sources.json)。管理器在固件启动前依次初始化 A5、BPS、IPE0、IPE1，退出按相反顺序。原始源码仅私存，未重复下载固件或读取校准分区。

核对发现 HFI 的寄存器基址必须取原厂 `A5_SIERRA_BASE`：`0x0ac10000`，大小 `0x8000`。相邻的 `0x0ac18000` CSR 资源不是原厂调用 HFI 初始化、IRQ 清除和 CPU 启停时传入的窗口。此前353/354只操作内存，没有向错误基址写寄存器。A5 SVS 核心400MHz、fast AHB200MHz；BPS400MHz，两路IPE共用475MHz源，均来自原厂 DT 和 `CAM_SVS_VOTE` 调用。

新增 [资源后端](kernel/camss-icp-a5-resources.c) 和 [接口](kernel/camss-icp-a5-resources.h)。通过 DT `qcom,camss` 引用现有 CAMSS，建立运行时 PM supplier link，由现有驱动继续管理共享 CPAS、MMCX、公共时钟及 interconnect。新后端独立管理19个时钟引用及 BPS/IPE 三个电源域，按原厂顺序开启，部分失败按逆序撤回。没有第二个 CPAS MMIO 所有者，没有替换当前 CAMSS 模块或修改主线 IOMMU 框架。拥有设备的驱动必须串行调用，并在资源断电前停止 A5；后端本身不执行固件、IRQ、HFI 或图像任务。

使用实际 resume/suspend 函数体做16项主机检查：成功开启／逆序释放、重复开启和忙状态拒绝、四项设置频率失败、四组启钟失败、三个电源域开启失败，以及三个电源域 put 错误上报。提供者是 API 桩，不能代替设备实测。[结果](resources-validation.json)。未改动的353/354 HFI、ELF、内存后端复用已有结果。

在原 `source354` 检出目录新建 `samurai-icp-a5-resources355` 分支，保留历史354提交，避免新增整棵内核副本。父提交 `ea71fa4...`，本轮提交 `0a23a25f34723a9d6fddb3a7c4e94080d0e92b7c`，五文件、tracked clean。[源码状态](source-state.json)、[补丁](a5-icp-resources.patch)。新增隐藏 power-test Kconfig 项；core 明确依赖 OF 与 generic PM domains。最后这项依赖声明收紧发生在构建后；当前构建及实机已启用这些配置，不改变模块对象。

实际 in-tree 构建 W=1／-Werror，13.66秒，无诊断。core155312字节，临时测试65904字节，Kbuild intree=Y、vermagic匹配当前k298。[构建结果](intree-build-validation.json)。共享 camera 输出、config 和关键生成文件已恢复；host tools 等准备输出可能刷新。固件、模块二进制、临时 DTBO 和原始日志仅私存。

手机当前 DT 实测 CAMSS phandle38、CAMCC206；已有 CAMSS 空闲，ICP/BPS/IPE 的17个实际时钟对象均无 enable 引用。19个后端时钟引用中，IPE1源与IPE0源是同一对象；fast AHB另计。测试覆盖只新增临时平台设备，不修改持久 DT。

R1 的主机辅助脚本误将17个对象写成18个，前置检查终止，尚未加载模块／上电；该失败保留在[报告](power-runtime-r1-validation.json)。修正对象数量后运行R2，没有修改内核代码或放宽空闲要求。

R2 worker5811终态退出。A5/BPS/IPE0/IPE1四组时钟及三个独立电源域全部开启；A5硬件版本读取 `0x10010000`，控制寄存器 `0x3000` 的 A5_EN 未置位。实际核心时钟400MHz，BPS400MHz，IPE约475000048Hz（时钟合成取整）。随后全部时钟引用和域引用归零，测试设备运行时状态 suspended。卸载临时模块和覆盖后，17个时钟 enable 计数恢复为0，原CAMSS回到 suspended，taint0→0、相关故障增量0。[实机结果](power-runtime-r2-validation.json)。频率设置保留在已门控的时钟对象中，未声称所有寄存器恢复原值。

本轮只验证资源生命周期和 A5 版本寄存器读取，没有向 A5 控制／复位寄存器写入，没有加载或启动固件，也没有证明 BPS/IPE 图像处理、SF 带宽或各端口 QoS。当前普通四摄采集仍沿用338/r27/r22及344私有默认，未安装本候选；没有停用户相机服务、重启或修改NV。

下一步356将354的固定IOVA内存后端与本轮平台资源接到同一ICP设备，按原厂HFI寄存器和队列约定实现启动／停止、IRQ、SYS_INIT及命令响应。原厂分配器实际取二级堆区域长度1MiB，不能误用头文件的2MiB宏；SFR实际分配8KiB。共享窗口0x07400000／150MiB、二级堆0x10a00000／1MiB、QDSS0x10b00000／1MiB映射物理0x16790000、IO窗口0x10c00000起，见352保留DT；完整内存布置和QDSS禁用条件还需接通。原厂CPU先enable/reset再拷贝ELF，而安全生命周期需要确保启动前固件和映射完整；应核对A5复位语义后实现，不能直接复制顺序。350～352的IPE Gamma/LTM/前摄CCM仍待实际会话和IO/IQ集成，曝光表／防频闪、更多模式、几何同步及连续AF也未完成。
