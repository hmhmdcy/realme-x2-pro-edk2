# 504挂起预算通知的实际唤醒栈

2026-10-24。手机仍是已采用的504/d046/34ead，充电与保护未替换。

03使用独立trace instance，仅记录三个充电电源的wakeup_source_activate及挂起阶段；samurai-usb-input最多8次栈，boot时钟、每CPU128KiB。不修改全局trace或wakeup策略，原PM primitive/collector/同child监督和once意图复用。历史启动审核仅在全部读取原件SHA不变且无反向启动动作时复用，避免重复完整审核；新设备身份与12门健康仍独立读取。

实际[结果](actual-evidence-result.json)与[首栈](actual-stack-excerpt.md)：dpm_suspend开始2945.379580，2945.386880在原PM worker中激活samurai-usb-input，栈经pm_stay_awake、power_supply_changed、samurai_usb_set_property、power_supply_set_property、dwc3_vbus_budget_close、dwc3_plat_suspend。2945.582369挂起中止，未到machine_suspend。握手count163、event state0xa30001；固定内核以高16位计完成事件、低16位计进行中事件，故在同一计数上出现1个进行中唤醒事件，满足pm_wakeup_pending中止条件。证实这条软件路径会在挂起时自发持有唤醒锁，未声称只有这一个剩余阻项。

原严格密钥R2输入/输出/同child终态、实际worker源码和supervisor PID链均核对；前后完整12门过，源/native/硬件500mA保持，alarm只清自己的且已取消。25份原件留存，trace5016B、8CPU无overrun/drop，stack触发未耗尽，过滤与启用读回保存、实例清理无错。仍是失败的PM短测，不作恢复或整机PM通过。

02在进入PM前被trace enable只认1的检查拒绝，15原件保留，未写mem；原内核实际读回初始0、触发器0*、启用1*，与当前trace_events.c一致。r1源码/报告保存history，03只接受1或1*，0*仍拒绝。三组初测、修正后的四组与历史审核复用一组分别实际wait0；设备/trace API边界为明确模型，未重跑旧矩阵。

后续修正见[USB通知候选](../../charging-oem-audit-20261023/usb-input-pm-notify-candidate/README.md)。不重派01/02/03原事务。
