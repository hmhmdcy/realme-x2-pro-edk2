# 阶段152：显示生命周期候选、真实接管失败与桌面恢复

2026-10-13。当前内核仍为147/software132加Mesa149修复库，但已经是本轮回退后的新启动。152候选实际部署后未验收，已只写logdump回退147，源码DSI改动撤回。回退147也复现CTL首次接管失败，一次有界面板重新探测和原initial_session恢复桌面；用户确认实体屏幕显示桌面。40.45秒九次收尾taint0、DPU/DSI/GPU/WARN0，音频DMA prepare70保持。显示永久修复仍开放，goal active。

152提取九个DSI实际函数，复现旧源码并发reset恢复禁用前CTRL、关时钟后MMIO等七项回归；修复14项普通及ASAN/UBSAN通过。仅DSI host修改，完整Image/DTB/770模块/FAT/checkpatch通过，模块与132字节一致。147原boot用DisplayConfig完成24次正常电源转换，没有显示新增错误。GPIO和物理时序是宿主替身，不把这些结果算作真实启动修复。

候选152新boot先UFS UIC超时和SCSI异步阻塞、再INTF帧停滞/CTL reset -22；355秒后进入RAM诊断fallback，未挂userdata/F2FS，实体黑屏。F1已经受理，却在device_shutdown等待异步探测；保存完整dmesg和SysRq w后，核实当前152身份与RAM-only状态，用一次SysRq b完成挂起切换。真实bootloader身份/产品/几何重新核实后只刷回147。没有重复F1、写userdata或改boot/NV/persist。

147新boot具备持久rootfs、USB网络与Wi-Fi，却同样CTL首次接管失败、无DRM/Phosh。一次panel bind恢复DRM，重触发现有initial_session恢复桌面，配置哈希不变。旧包数据库151差异不在本轮解释范围，Mesa149库核对保持；常规Mesa升级覆盖风险仍在。

本轮另保存了测试方法失败：最初trace系统名错误；wlr-randr移除唯一逻辑输出导致Phosh空monitor崩溃；wlopm请求失败。后采用DisplayConfig电源属性完成基线，不把桌面崩溃或工具失败写作DSI故障。临时152启动服务已移除，未在fallback里执行；原系统trace不重置。

新的优先线索是面板probe过早assert reset并关闭VCI/VDDD，而DPU boot CTL清理发生在后续mipi_dsi_attach/component_add。第一轮将对probe保持GPIO、prepare才设置方向与电平形成独立候选，保留原厂DSC和上电复位序列；仅源码推断，尚未验收。原厂autorefresh顺序和其它机型MDSS reset资料不能当作本机永久修复。

详见[证据索引](../reference/kernel152/README.md)、[检索记录](../reference/kernel152/internet-findings.md)。原始身份、地址和镜像只在私有输出；生成的内核Image仍152，源码DSI已回147，不能把现有生成物当147。
