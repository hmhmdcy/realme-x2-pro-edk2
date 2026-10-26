# 153：面板 GPIO 接管候选与首次启动欠载

2026-10-13。当前手机运行 #153，自动进入桌面；**显示修复未完成**。用户看到锁屏，但电源键开屏时有短暂花屏闪烁。

候选只修改 SOFEF03F 面板：probe 用 GPIOD_ASIS 保留固件 reset/VCI/VDDD 状态，prepare 才设输出方向和关断初值；保留原厂电源、复位和 DSC 序列。152 的 DSI worker 串行化补丁未混入。实际函数及 probe GPIO 片段测试 11 项普通与 ASAN/UBSAN通过；旧实现失败5项。测试硬件和 component attach 为桩，不能代替实机验证。初版测试桩错误重置 GPIO 方向导致 baseline abort，修正后重新验证，不把该 abort 算作驱动故障。

完整 Image、DTB、770 模块、checkpatch、FAT 检查通过；模块与132逐字节一致。只刷 logdump153，首次真实启动无需 panel rebind，CTL0成功清空，面板 power mode 0x9c，Phoc/Phosh自动启动。实际 logdump153读回一致，boot/persist、模块132、NV来源和 Mesa149修复库核验通过。[构建](build-package-validation.json)、[补丁](panel-gpio-handoff.patch)

启动记录器从 uptime18.31秒采集91.85秒，无丢失，868次 DSI错误 IRQ对应870次 DPU提交；FIFO原始状态863次为0x99991090、5次为0x88881090，错误聚合0xc。ACK/TIMEOUT为0，未映射出PLL解锁或DLN0 PHY错误。DPU提交仍收到frame-done，故不能凭timeout0宣称画面正常。启动结束dmesg有186条限频worker错误，随后累计199条。早期bootconfig和实时实例时钟基准不同，不能直接跨实例比较时间戳。

一次标准 DisplayConfig关屏、开屏观察15秒，无新增欠载；接着12轮、24次电源转换保持桌面进程和boot，taint0，DPU/DSI/GPU/WARN计数未增长。实际 MDP 时钟仍为200MHz，没有修改性能时钟或带宽。这只是运行时恢复，不能清除已发生的首次启动失败，也未证明实体唤醒闪烁消失。

首次runtime核验工具漏上传依赖文件，在写入私有身份文件后失败；保留原目录，补传依赖后用retry1新目录重跑。分区、模块、NV、Mesa和27.49秒稳定采样通过，最终全boot DSI零错误验收按预期失败，保留退出码1。临时启动记录服务已从boot runlevel删除并停止，采集实例已移除。

私有首次启动归档39,904,034字节，SHA256 `4c7b7393a1ab4f0aa7fcaaa5e2f81b7f5603633281847b99c7f62b68d35dfc76`。身份、原始日志和完整trace保留在 `E:/edk2-samurai-out/kernel153/`，不得公开。下一步比较固件首次初始化与正常DPMS重启的DSI寄存器配置，优先审查时序编程前仍启用的固件控制器，以及soft-reset重新恢复旧CTRL的路径。
