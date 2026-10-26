# 阶段152：DSI竞态候选、启动接管复现及已验证回退

2026-10-13。152候选未验收，现机已回退147/software132，Mesa149修复库保持。回退启动也复现首次CTL接管失败；一次面板重新探测恢复DRM，原initial_session恢复Phosh，用户确认实体屏幕显示桌面。永久显示修复仍未完成。

- [实际函数测试](actual-function-test-validation.json)：原147源码七项同步/关时钟回归失败；候选14项普通与ASAN/UBSAN通过。测试提取九个实际函数，MMIO、IRQ取消与时钟为替身，不能替代硬件验收。
- [候选补丁](dsi-lifecycle.patch)、[源码核对](source-validation.json)及[完整构建](build-package-validation.json)：仅DSI host修改，Image/770模块/DTB/FAT/checkpatch通过；模块字节与132一致。
- [原147电源基线](baseline-displayconfig-validation.json)：24次正常DisplayConfig电源切换，DPU/DSI/WARN无新增，保留原GPU累计3。
- [桌面恢复](desktop-recovery-validation.json)、[回退收尾](rollback-closeout-validation.json)：实际logdump147读回、boot/persist/模块/NV/Mesa保护项通过，用户确认实体桌面，40.45秒九次计数保持、taint0；音频DMA prepare累计70。
- [源码收尾](source-closeout-validation.json)：候选152源码私有存档，canonical DSI源码已恢复147；构建树生成的Image仍为拒收152，不能直接打包当147。
- [互联网与GPIO线索](internet-findings.md)：区分原厂顺序、上游建议及新的板级源码推断。

第一次采集器使用错误的trace系统名，未产生电源转换；随后`wlr-randr --off`移除唯一逻辑输出引发Phosh空monitor崩溃，内核显示计数未增长，已恢复会话。wlopm请求被当前Phoc拒绝；最终使用会话DisplayConfig.PowerSaveMode成功完成基线。这些失败原件均在私有归档，不改写为通过。

152实际只刷logdump。新启动出现UFS UIC超时/异步SCSI阻塞及CTL reset -22，userdata身份未找到，355秒后进入诊断initramfs，用户报告黑屏。只有可信72诊断SSH密钥可用于该fallback，不能关闭SSH主机密钥核对。F1已受理，但device_shutdown被异步块设备探测阻塞；已保存SysRq w及完整日志，确认同一152启动、只有RAM/rootfs挂载、没有F2FS挂载后用一次SysRq b完成这次挂起切换。先前等待fastboot的只读product请求已停止，没有重复F1。

随后重新核实实际18d1:d00d、serial/product/logdump几何，只写回保留147。147新启动进入真实rootfs但CTL首次接管同样失败，无DRM/Phosh；这证明不是仅凭152新增锁就能解释失败。一次有界panel bind成功，原配置桌面恢复。恢复不是永久修复；147新boot的音频prepare70也保留。

原始身份、地址、dmesg、USB抓取、归档、候选及回退镜像只在`E:/edk2-samurai-out/kernel152`；主机私有归档为`evidence-private.tar.gz`，手机材料为`/var/lib/samurai/k152-*`。候选fallback RAM日志已经下载，紧急复位后原RAM不存在。本次OpenRC启动服务已经移除；其152首次运行没有发生，因为该boot没有进入持久rootfs。
