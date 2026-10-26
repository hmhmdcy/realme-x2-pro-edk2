# 充电周期计时修正候选

2026-10-23。只在PC离线实现，尚未集成或加载；没有访问手机、SSH、SDK或共享内核存储。根会话负责与温控修正合并、增量构建和验收。

后续：根会话已将周期、温控和变化通知合并到生产源码；本目录另增[真实step整合测试](integration-test-result.json)，直接抽取生产`sm_step_locked`函数体及生产头文件，以fake采集/BOOTTIME/记录式寄存器作为边界。12条定向序列、65个断言通过ASan/UBSan：冷/热迟滞恢复、暖区OVP恢复、旧fault保持、热hold期间MAC及stop失败锁存、Full多日再充、已超时后Full/AUTO不清、Full且热hold不重置、两类source未知保留周期、同时全局电压故障不能伪装为温控。生产源码和实际提取函数SHA均写入结果；未执行实机状态切换。本目录旧C候选/导出补丁只保留为候选形成历史，不应用它覆盖已合并生产源码。

最初审查发现当前`session_start`保存在充电模块的实例中：服务stop/start不卸载时自然保留，模块重载或重启会初始化。进一步核对固定原厂资料后，**不把跨启动持久化增加为默认要求**。原厂充满处理`oplus_chg_full_action()`每次将`total_time=0`，再充是新充电周期；整段USB连接的不可重置10小时期限会使长时间充满待机后无法再充。原厂本身没有掉电持续计时账本；增加“换boot必须先拔线”也会改变正常开机充电行为。

已完成：

- [charge-cycle.h](charge-cycle.h)：实际可移植的易失周期计时器。继续使用BOOTTIME，包含同一周期内的休眠；Full重置本轮，UNKNOWN/无效采样不重置，已建立的超时保持到真实断源。服务启停和AUTO不会初始化它；冷启动按原厂初始化。
- Full只接受MP2650 REG13 CHG_STAT==3、当轮完整新鲜采样、其它实际策略谓词通过及无现有硬故障锁存。`sm_cycle_full_allowed()`不接收SOC100或零净电流作为Full证据。计时器自身也不因Full清除已有`timed_out`。
- [98个定向断言](test-result.json)通过ASan/UBSan：正常/超时边界、长期充满后再充、已有超时后Full/AUTO不能恢复、未知源与真实断源、BOOTTIME跳变/反向输入、uint64边界，以及实际`sm_policy`拒绝十类失效Full证据。没有把仿真称为实机再充通过。
- [最小接入差异](charger-cycle.patch)和[独立C候选](samurai-mp2650.candidate.c)由[导出器](export-candidate.py)产生；原充电目录未修改。[来源指纹](integration-source.json)固定生成时的原C源码，根会话合并前检查并处理并行温控修改。

计时裁决顺序：先确认当轮非计时保护均通过；新确认的健康Full建立周期边界。如果之前样本已确认超时，Full不能解除。Full期间无故障的正常再次采样保持周期为0；第一次再充样本从最后确认Full的BOOTTIME继续计时。任何先前IO/electrical故障由原`c->latched`继续控制，计时器不读写该锁存。

根会话最小集成：新增头文件到同一驱动目录；将`session/session_start`替换为`sm_charge_cycle`并只在probe初始化；读取最终REG13时缓存`sample_full`；每次`sm_collect`后使用独立双源断开证据/UNKNOWN、完整非计时策略结论推进周期，再把返回秒数交给现有`sm_policy`。候选使用两次纯策略计算，不增加I2C事务、sysfs写入、持久化服务或新硬件写范围。

同boot模块热替换若需要保持旧周期，应由根会话在停充/卸载前保存内核周期字段、明确导入同boot状态，或把周期置于原有常驻输入提供器；本候选没有假称已解决热替换连续性。依据原厂行为，该扩展不应阻塞本轮Full/温控修复，不能用墙钟猜测掉电窗口。真实再充、温区恢复和模块集成仍由根会话验证。

复用资料：原厂固定提交`23172a1571bd91156032cc9fef16284a82b63d2c`的`drivers/power/oppo/oplus_charger.c`（本机kernel83缓存）。Full重置5306–5318、保护计时4540–4564、保护先于Full/时间更新7351–7378；更完整来源/hash由同轮[OEM审查](../charging-oem-audit-20261023/README.md)保存。原厂`oplus_chg_get_curr_time_ms()`用易失`local_clock()`；本机已验证BOOTTIME/RTC仅证明同boot休眠计时和闹钟，不证明跨掉电单调时钟。现有NTP/chronyd会调整墙钟，因此不将墙钟或一次RTC timestamp用于放宽剩余预算。
