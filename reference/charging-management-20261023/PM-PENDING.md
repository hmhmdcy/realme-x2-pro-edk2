# r5 SDP待机：已恢复，计划验证失败

部署manifest f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf，charger9d9e1cd7…31016，native USB/保护模块不变。短时运行/标准INHIBIT/AUTO均通过后，独立PM worker PID21491启动；USB随后不可达，Windows仅枚举05c6:9500/9501 EUD，没有0525 NCM。用户现已确认短按电源能正常亮屏；紧接着主机枚举仍仅EUD，原key严格SSH fetch仍不可达。已请求保持亮屏、同电脑口拔插10秒以恢复数据连接，尚未启动任何新测试。

最新：用户同口重插后NCM/严格SSH已恢复，同原boot，原21491确认退出且原件全部取回。raw脚本误标runtime_passed=true，但实际驻留3396.192秒远非计划15秒，**本轮计划RTC待机不通过**。完整trace5222/5222，freezer结束至dpm_prepare有50.468秒console准备缺口，charger实际suspend在其后才开始；RTC IRQ+1不能单独证明它从本次睡眠唤醒。原raw保留，正在另作限定审计。

[恢复只读收据](pm-r5-recovery-result.json)确认实装manifest/三模块精确、充电fresh/native100/同boot/taint0/指定新增fault0/相机与4服务保持。原rtc alarm为空，pm_wakeup_irq属性不存在。手机已明确交回相机会话，充电停止实机访问；当前窗口以[协调记录](COORDINATION.md)为准。

新增USB线索：原dmesg在12083.320060记录`dwc3-qcom-legacy a6f8800.usb: port-1 HS-PHY not in L2`。实际source354的`drivers/usb/dwc3/dwc3-qcom-legacy.c` suspend路径会记录此dev_err，然后仍关闭时钟并返回0，因此所有PM callback err=0不能认证USB状态或数据恢复。该告警不在旧严重fault计数五项中；回调/充电恢复证据与“无需重插自动恢复USB”必须分开，后者本轮未通过。具体PHY/主机/EUD因果仍在审查，不据此盲改时序或重放待机。

后续只读console取证确认`printk=1/4/1/7`但`ignore_loglevel=Y`，实际EUD console仍会跳过阈值过滤；恢复后journal尾512帧/2025字节均为console。这一单点不是r5准备缺口时的速率或backlog，不能补造50秒因果。实际trace仅nop，lock/sched/IRQ/RTC事件及stacktrace trigger可用；[只读库存和来源](../charging-oem-audit-20261023/pm-preparation-gap/trace-plan/README.md)。[DWC3实际函数审计](../charging-oem-audit-20261023/usb-resume-errors/README.md)另发现core/gadget真实错误返回被丢弃，提供了未部署的诊断候选；没有证明本次触发这些错误。r6充电模块更新及停充/恢复已通过，但未重做整机PM，不覆盖本页失败。

失联时没有把USB不可达直接等同内核死锁、关机或PM成功；未重启、未卸模块、未重放。现已取回既有/root/charging-management-20261023/charging-pm-r5全部原件，确认原进程结束，恢复核对后才明确交回相机。[限定审计](../charging-ui-audit-20261023/pm-r5-qualified-result.json)保留raw true但判计划失败，回调/配置恢复证据另列；旧audit-charging-pm.py的r5入口现已关闭，防止再把IRQ+1及任意长驻留当计划RTC通过。

离线审查尚未找到新增静态锁环：c锁→bq锁→adapter；没有bq→charger回调，通知只排异步work，suspend释放c锁后才等待poll结束，已有c→gauge PM依赖没有新增反边。这不能排除真实总线或PM故障。

测试工具存在确定的时序缺口：先将RTC设为当前+15秒，再os.sync，随后才写mem；没有在sync后核对剩余时间。若sync耗尽窗口，会先消费alarm再进入睡眠。当前没有设备phase/trace，不能认定这就是本次原因。后续新实验应先完成sync，再设置alarm；紧邻mem核对alarm仍存在且剩余时间充足，不满足则取消本轮，不进入睡眠。还应根据trace/RTC事件核实唤醒来源，不能仅凭IRQ计数+1便认定RTC确实从本次睡眠唤醒。

已离线实现[安全PM事务primitive](../charging-ui-audit-20261023/pm-transaction.py)，27个实际实现边界测试通过：sync及有界wakeup_count读取均在arm前；入睡前核对剩余/IRQ/alarm，写回原count握手后仅一次mem，拒绝/错误不自动重试；仅取消仍匹配自己target的alarm。库无自动入口、未部署、整机验收始终false。接入须新事务并继续独占RTC，不能把该修正当本轮原因或恢复结果。

原r5 worker源码及启动/连接失败输出保留在私有pm-r5目录；新实验必须新建事务名，不覆盖原件。
