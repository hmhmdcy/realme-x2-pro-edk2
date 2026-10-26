# 阶段142互联网线索与实机适用范围

2026-10-12，继续用户关于定位困难和互联网线索的问题。新增核对[Linux官方printk说明](https://cdn.kernel.org/doc/html/latest/core-api/printk-basics.html)与[官方console接口说明](https://www.kernel.org/doc/html/next/driver-api/tty/console.html)。前者说明legacy控制台同步发送可能长时间关闭中断，推荐nbcon线程输出等方法；后者要求控制台ownership/unsafe区和设备访问同步，device_lock还须禁迁移，不能只把write回调改名就算移植完成。

本机源码与实测比通用文档更具体：EUD console整行在uart_port_lock_irqsave内，每4字节frame按200us/寄存器和2ms/frame发送；受控同boot、CPU0 INFO日志A/B为73.346ms对0.211ms，两条保留dmesg，仅A出现在软件console发送journal，设置已恢复、无新增错误。确认受控日志的同步控制台延迟；启动显示timeout附近69.943ms空档与Q6 ready打印吻合，是具体因果候选，还不是驱动修复后显示验收。

沿用[141搜索线索](../kernel141/internet-leads.md)：DPU空闲timer提案的busy已清零条件和本机busy1不同；SLIMbus作者只编译验证，139本地实际函数测试/回收证据另立；Mesa CCU文档支持缓存/回写/布局/映射方向，不是本机现成修复；MPS说明MP2650支持buck或boost两至四串，不支持由5V输入直接判定不能充电。

未用搜索结果中的AI机器人评审作为已证明根因。互联网材料给机制和正确接口，设备专用补丁仍须按当前mainline/Mesa/Phosh和原厂硬件契约完成测试。
