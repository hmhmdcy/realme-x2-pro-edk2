# 429 r3：新增 PPS 诊断越过映射窗口；后续四摄恢复已核实

当前状态：用户已强制重启进入 Linux，[新启动](postboot-validation.json)与[正式四摄](camera-recovery-validation.json)均通过核验，48 帧 IPE 完成，服务恢复、taint 0。修正版 build r3 的 r4 单核回放也已完成 4 作业并恢复正式模块／服务，无新增 fault；[统计与重复性仍未通过](single-core-hardware-validation.json)。下文保留故障发生时的事实，其中“尚未恢复”指当时状态。

r3 在原厂支持的单核双遍请求后添加了一个错误的只读诊断：直接以 IPE TOP 映射基址加固件 PPS 寄存器偏移读取 LTM 控制。该偏移不在现有内核映射窗口内。实际 Oops 为 `readl` 的 level 3 translation fault，调用者是 `run_colour_status`，与新增诊断代码和故障地址对应。**这是本轮加入的诊断错误，不是原厂固件、PD10 像素或用户环境导致。**

当前修正版已完全删除该读取，没有尝试扩大 MMIO 映射或用未知寄存器覆盖问题。维护源码、补丁和最新 build r3 均不包含该读取；**build r2 的 core 不能再次加载**。r3 设备事务已终态失败，但客户端卡在 `v4l2_m2m_cancel_job`，不能以 worker 终态声称客户端、DMA 和模块已释放。

故障前最后通过的是双核 r2 回放：四个 direct IPE 作业完成，正常恢复正式模块／服务，无新 fault，taint 512。其 DC 统计和重复性没有通过：71488 byte scratch 保持预填值，相同真实输入两次输出不同。因此 r2 的作业完成与统计链路验收分别记录。

r3 新增 Oops 后 taint 为 640，锁和引用无法通过终止进程释放。已保存日志、worker 状态、模块身份与重启前磁盘摘要。正式三模块文件仍与 420／419 锁定摘要一致；未刷写或改动 NV／OTP／persist。未强制卸载模块、退映射或提前归还未知 DMA backing。

设备使用 BusyBox init。最先探测的 `systemctl` 不存在，没有执行重启；随后确认实际 init 与 `/usr/sbin/reboot`，正常 reboot 返回 0。之后 USB NCM 仍可见，SSH TCP 22 明确拒绝连接，保存的 Wi-Fi 地址连接超时；USB 最后枚举时间未更新，**尚未证实新启动完成，不能声称正式模块或桌面服务已恢复**。已请求用户在方便时执行一次硬件强制重启并进入现有 Linux。连接恢复后须先验证启动变更、正式模块／配置、资源释放及四摄，再继续实验。

完整日志、故障地址、旧启动 ID、模块与图像只私存。正常重启请求执行一次，没有重复请求或猜测新启动成功。
