# 阶段142：启动中断空档与EUD控制台延迟

2026-10-12。阶段142仍为#140/software132，同内核重启一次、未写分区。96.948秒启动追踪无丢失，一个完整显示超时窗口的PP回调95.652ms、CPU0事件空档69.943ms；另一次超时早于新增追踪。空档与Q6 ready日志吻合，EUD同步日志A/B实测73.346ms对0.211ms，CPU0最大空档73.307ms对0.431ms，两条记录均保留在dmesg，配置已恢复、无新增错误。已确认控制台长延迟，原始显示故障完整因果仍待驱动修复验证。boot/logdump/liveDT/GPT18/persist/770模块及来源均通过；临时服务和两个自建追踪实例已移除。随后28.641秒8次被动观察PID/taint/计数不变，累计DPU2/DSI0/GPU0/WARN0/TXDMA0。显示、136迟发CCU GPU故障、充电控制保护及完整系统目标仍未验收。

一次完整守卫的同#140重启，EUD enable、freeze/F1、fastboot reboot各一次；没有构建142内核、修改内核源码或写boot/logdump/userdata。启动身份以私有kernel142/embedded-boot-id-private.txt和phone k142-first-runtime为准。142/source-boot-id及141/140的embedded标识均是历史，不能混用。

临时OpenRC boot服务在greetd之前启动独立追踪，新增IRQ entry/exit、softirq、CPU idle/frequency、PM和timer事件，16384KiB/CPU并持续读取trace_pipe。记录96.948秒，20个样本，首样本uptime47.90秒；8CPU的overrun/commit overrun/dropped均0。累计两个DPU超时中，独立追踪只覆盖后一次，arm到timeout95.626ms、arm到PP callback95.652ms，83ms期限未改。第一个只能由默认early追踪看到timeout及稍后PP，缺arm和IRQ前因。

完整窗口CPU0所有已启用事件出现69.943ms空档，空档前是idle唤醒及smp2p-mpss/IPI，结束时任务上下文是调制解调器SMP2P线程，随后apps_rsc、arch_timer、DSI和MDSS中断集中处理。其他7CPU空档内仍有事件，不能说整机冻结。已完成普通中断处理函数最大0.404ms，无在途长IRQ handler；IRQ trace不覆盖整个线程函数或所有关中断临界区，因此仅凭没有IRQ事件还不能证明具体关中断调用或物理TE到达时间。

本boot两次同函数timeout trace与紧邻dmesg打印的偏移均2.856829秒，只用于这两条事件，不当作通用或跨boot时钟校准。由此定位Q6 ready打印在CPU0空档开始后0.038ms。该日志按dmesg格式含换行85字节，既有EUD每4字节frame、每寄存器200us和每frame2ms的节奏估计69.8ms，接近实测空档；格式/RX/锁开销仍有不确定性。原始Q6 ready发送记录已被512条软件journal覆盖，不能伪称保留了该行或收到主机ACK。

源码明确eud_console_write把整个记录发送放在uart_port_lock_irqsave内，legacy printk还在外层关中断。实际early bootconsole早已退休，剩下的是运行期legacy EUD控制台；当前ignore_loglevel=Y，即使console level是1仍发送INFO。现有内核只有nop tracer，无function/irqsoff/kprobe能力，未假装直接追踪了console入口/出口。

随后在已idle/off的同boot做一次可逆A/B，Python固定CPU0，仅发送两条相同77字节INFO记录，不请求显示/GPU负载。A维持ignore_loglevel=Y，写入耗时73.346285ms，追踪最大CPU0事件空档73.307ms；B临时设N且原有console level1保持，耗时0.210625ms，标记区间0.431ms。两条均保留dmesg，发送journal CRC通过并有A console frames而无B frames；这证明绕过慢速控制台会消除受控日志的长延迟，不证明主机收到。参数和CPU affinity均恢复，8CPU无追踪丢失、自建实例已移除、taint0且错误计数未增长。原始显示timeout的console区间未直接测量，仍需修改驱动后的显示回归，不能把静音当修复。

普通桌面1954次GPU提交/刷新/退休对应、无fault，是本次启动证据，不能替代136专项迟发CCU故障验收。完整系统软件仍132、936包、770模块；boot132/logdump140实际读回、DTB132、GPT18/persist及NV6/source4/vendor1/GUI3均通过。本次TXDMA0，140首次NULL/BAM/挂起拒绝诊断未触发，不能宣称NGD首次NULL根因修好。

临时OpenRC recorder已确认进程结束、封存归档校验后stop并删除boot链接、init.d文件和pidfile；两个自建追踪实例都已移除。默认历史追踪没有被重置。28.641秒8次settled观察桌面PID/taint和计数不变；后续A/B也无新增错误，Phosh/Phoc存在。全审计时CRTC已随空闲关闭，未取得本轮实际像素可见性确认。

下一项用阶段143准备EUD控制台有界临界区或线程输出修改，保留既有frame节奏、RX整帧、F1恢复和journal语义；先实际函数测试/并发退出/错误路径与构建检查，再考虑带回滚的实机验证。不要简单放宽DPU期限或把降低控制台日志当成全部功能修复。仍保留139未提交TX回收、136 GPU故障和138充电阈值证据，完整goal active。

证据见reference/kernel142/startup-irq-idle-validation.json、cpu0-event-gap-validation.json、console-latency-ab-validation.json、eud-console-latency-hypothesis-validation.json、first-runtime-validation.json、recorder-cleanup-validation.json、settled-health-validation.json及[internet线索](../reference/kernel142/internet-leads.md)。所有raw日志/地址/PID/boot身份/发送journal及镜像保存在E:/edk2-samurai-out/kernel142和phone /var/lib/samurai/k142-*。142全部一次性动作已终态，不重放。

历史依据：[141](141-normal-wake-and-loss-free-startup-display-trace.md)、[139功能回收](139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[136 GPU故障](136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)、[138充电阈值](138-readonly-charger-recharge-threshold.md)。
