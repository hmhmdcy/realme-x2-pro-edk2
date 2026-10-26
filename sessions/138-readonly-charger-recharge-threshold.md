# 阶段138：本机充电恢复阈值的只读核对

2026-10-12，当前132与137回退同boot。固定已签收工具做两份12字段快照，24次I2C读，无配置数据写、fault REG14读、强制地址、new_device或保护/FET/OTG动作。同一OF观测客户端在finally恢复，解绑0.041121秒。两份配置与133全相同，包数据库、6 NV/4传感器来源/1 vendor及桌面PID不变，taint0，故障计数不增。

[原厂MP2650代码/头文件](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_mp2650.c)的固定hash重新验证，Android存档DT vbatt_num=2及REG07两节编码一致。REG04=0x68：电压code52，以3.7125V+52×12.5mV得到每节4.3625V、整包8.725V；恢复落差每节100mV，整包阈值8.525V。REG13=0x0f充电状态为termination。

两次电量计98%，27.8→27.7°C，8.624→8.547V，+1→-115mA；都尚高于名义恢复阈值。状态从Charging到Discharging，瞬时符号不能证明持续净充电；硬件Full锁存与这些读数相容。继承的电压不是推荐设置，不抬高浮充电压，不把98%停充认定为驱动故障。

当前132仍无134 USB source额度驱动；历史CDP1.5A不能作为当前预算。NTC/watchdog继承关闭、终止和12h安全计时器继承启用；保护/2719固件语义、温度链、失联行为及实际恢复充电仍待证实。[MPS官方产品](https://www.monolithicpower.com/en/mp2650.html)明确MP2650按输入/电芯数选择buck或boost；不能凭5V输入与2节电池就认定无法充电。没有控制验收。

证据：reference/kernel138/charge-threshold-validation.json。capture脚本已执行且终态，不重复解绑/交易。
