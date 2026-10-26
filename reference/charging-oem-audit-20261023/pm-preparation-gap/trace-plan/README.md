# r5 console 准备缺口：EUD、参数与最小后续证据

本轮本代理仅在 PC/WSL 离线读取实际 source354 和现有 k363 构建，没有访问手机、SDK，没有改共享树、候选、Image、参数或 raw。复用 `storage.mounted_build()`；源码 hash 见上级 source-manifest.json，配置与链接证据见本目录 capabilities.json、compiled-parameters.json。后补根会话在独占只读窗口取得的实际console采样，原件/hash见下节；它是恢复后状态，不能代替r5当时逐时证据。

## 根会话补回的当前实际证据

私有原件 `E:/edk2-samurai-out/charging-management-20261023/pm-r5-recovery/console-inventory-private.json`，SHA256 `90fe8ea9ea7af9b0a170936acce8b0b93bee4d2e7d4fac5a1165af0d3083aec4`，采样MONOTONIC 15330375207992ns；readonly=true、pm_entered=false。本代理只读取该本地缓存，不新增设备访问。

- 实际release为k363；printk四值为 **1 4 1 7**，ignore_loglevel=**Y**、console_suspend=Y。因此“console阈值1”在这一采样并不表示串口只打emerg：ignore=Y旁路了普通过滤。
- 实际启动项为 earlycon=eud,mmio,0x88e0000、console=tty0、console=eud、loglevel=7、ignore_loglevel。EUD已启用且是nbcon；绑定qcom_eud_com，compatible准确匹配。
- `/proc/consoles`还列ramoops-1及tty0；active为tty0 ttyEUD0。pr_flush等待所有usable console，不能因发现EUD就排除其他console或注册/锁路径。
- journal范围537405–537916，保留512帧/2025B，全部source=console。它证明这些最近发行帧来自console；**单次快照没有时间窗，不证明当前每秒速率、剩余backlog、持续camera日志或r5那50秒的发送量**。
- runtime available_tracers只有nop。15个所选power/sched/lock/irq/rtc/printk事件均实际可用，sched trigger catalog包含stacktrace。无需猜测function_graph可用性，也尚未arm任何事件/触发器或新PM。

这把“EUD启用、ignore确为Y、仅有事件跟踪”的前提从旧文档推测变成恢复后实测。**积压及其与r5具体50秒的因果仍未证。**

## 先收敛结论

1. 当前 `drivers/tty/serial/eud.c` 确为自定义 `qcom_eud_com`，compatible `qcom,sm8150-eud-com`（1404–1415）。`kernel367/restart-bootloader.py` 只作为原有设备绑定断言的资料读取，未执行。
2. 驱动按固定延时发送，不轮询 host ACK 或 TX FIFO 空闲。COM9505 未枚举本身不足以推出“驱动一直等电脑消费”。可以排除**本输出函数显式等待 host ACK**这一具体解释，不能排除硬件 MMIO 停顿、调度、锁等待或实际 FIFO 丢失。
3. EUD 慢输出、`pr_flush` 的进度重置及后续 SRCU 等待都与源码相容；50.468 秒究竟在哪一个分支仍缺栈/进度证据。不能把它直接归因 charger PM 回调或认作已证 EUD 因果。
4. 现有 k363 没有 FUNCTION_TRACER、FUNCTION_GRAPH_TRACER、KPROBES/FPROBE，因此这轮不能直接启用 function_graph 或用 kprobe 包 `__pr_flush`。已有事件加定向栈是无需新 Image 的备选。

## EUD 实际输出、吞吐与锁

`eud.c` 75–77、243–269：每帧最多 4 数据字节，先写 ID、LEN，再逐字节写 DAT；每次写之前 `udelay(200)`，帧后 `udelay(2000)`。完整 4 字节帧的固定延时预算为 `6*200+2000 = 3200us`，理想连续软件发行上限约 **1250 数据字节/秒**，未计 RX 采集、锁、打印格式、记录尾帧和调度开销。`udelay` 是忙等，TTY work 注释里的“sleeps”不能当实际睡眠证明。

50.467767 秒若全是满帧固定节流，量级约 15,771 帧/63,085 字节；1MiB 则约 839 秒。该计算仅是量级检查，**不表示本次发送了这些字节**。r5 dmesg-before/after 文件分别 1,059,656/1,059,712 字节；它们是保留日志快照，不是 console 待输出队列。当前编译 `LOG_BUF_SHIFT=20` 是默认 1MiB 文本环形缓冲，启动参数仍可能改变分配，文本导出长度也不是实时 backlog。

`eud_send_frame` 271–282 记录的是已发行 MMIO，不是硬件 ACK；`eud_tx_empty` 328–330 也直接回 `TIOCSER_TEMT`，不能用它判定 host 已收到。

nbcon 的序号在回调 `write_thread` 返回后才推进（`kernel/printk/nbcon.c` 1058–1107）；被 loglevel 过滤的记录 `outbuf_len=0` 可以直接推进序号，而不调用驱动。`__pr_flush` 4492 捕获固定目标 seq，4540–4547 比较各 usable console seq；4551–4552 在差值变化时重置一秒预算。因此后续新消息不会无限抬高本次固定目标，但此前积压的持续推进可以让总时长超过一秒。

还有一个需要区分的等待路径：nbcon.c 1266–1273 的 console SRCU 读锁包住 `nbcon_emit_one`；其1137行会调用 EUD 的 device_lock，后者是 `eud->tx_mutex`（eud.c 503–513）。TTY work 在295–322行持同一 mutex 排空发送队列。于是若 printer 已持 console SRCU 读锁、却在等这个 mutex，即使 `pr_flush` 无进展一秒后先返回，`console_suspend_all` 的2815行 `synchronize_srcu` 仍可能等它完成。这里只证明可发生的锁关系，没有证据证明本次发生，也不能假定有限 TTY 队列单凭固定节流就够解释50秒。

## 输出过滤：编译与运行值必须分开

实际 `kernel/printk/printk.c` 1272–1289：

```c
static bool __read_mostly ignore_loglevel; /* 静态默认 false */
/* early_param("ignore_loglevel", ...) 将其置 true */
module_param(ignore_loglevel, bool, S_IRUGO | S_IWUSR);
return level >= console_loglevel && !ignore_loglevel;
```

- `/sys/module/printk/parameters/ignore_loglevel` 是 bool、0644，读值通常 Y/N；源码将其描述为忽略 loglevel、把所有内核消息交给 console。`kernel/params.c` 808–838 负责把内建模块参数按 `printk.<name>` 分组为这个 sysfs 路径。
- `/proc/sys/kernel/printk` 是四个整数，依次是当前 console 阈值、无显式级别消息的默认级别、最小 console 阈值、默认 console 阈值。映射见 include/linux/printk.h 71–74、printk.c 65–70；实际 `kernel/printk/sysctl.c` 22–29 注册0644、长度4*sizeof(int)、proc_dointvec，80–83挂到 kernel 下。
- 当前构建 `PRINTK=y SYSCTL=y SYSFS=y PROC_FS=y`，System.map 已链接 `__param_ignore_loglevel`、`__param_console_suspend`、`ignore_loglevel`、`console_printk`、`param_sysfs_builtin_init`。接口已编入；根会话后续采样已实际确认其值，见上节。
- 当前编译 console 默认7、无级别默认4。正常 `ignore_loglevel=N` 且 console 阈值7时，0–6交给 console，debug=7被滤；`ignore_loglevel=Y` 时普通阈值比较不再滤掉7。根会话现在已确认本次启动有 `console=eud loglevel=7 ignore_loglevel`，采样时ignore仍Y，使已生成的debug消息也有资格进入console；日志生成速率与具体camera来源仍未测。
- 过滤发生在 `printk_get_next_message(...may_suppress=true)`，printk.c 3060–3065；不阻止日志先进入 printk ringbuffer。降低 console 输出不关闭 dynamic debug、不消除生成日志的 CPU 开销，也不保证高流量下 ringbuffer 不覆盖旧记录。
- `LOG_FORCE_CON` 记录可绕过该普通过滤；panic/其他代码或管理员也可改变输出策略。不能将降级当绝对静默保证。

## 无需再次整机待机的最小只读项

优先在下一次已有设备窗口一次性保存，而不是现在单独进入设备：

| 项目 | 用途/限制 |
| --- | --- |
| `/proc/consoles`、`/sys/class/tty/console/active` | 实际注册/启用 console；不能仅看 DTS 认定 GENI 或 EUD。 |
| `/proc/cmdline` 中 console/earlycon/keep_bootcon、loglevel/ignore_loglevel/printk.*、log_buf_len 项 | 确认启动配置；运行参数读值仍优先于旧命令行。 |
| `/sys/module/printk/parameters/ignore_loglevel`、`console_suspend`；`/proc/sys/kernel/printk` 四值 | 区分过滤被旁路、普通阈值、console suspend。只读。 |
| `/sys/bus/platform/devices/88e0000.serial/driver`、`of_node/compatible` | 当前绑定；不执行 unbind、retire、重启或任何367脚本。 |
| 同设备 `tx_journal` 的 first_seq/last_seq/count、源1/2尾部帧数/字节数 | 最多512帧，48字节LE头+6字节记录，最长3120字节、CRC32/IEEE。两次已有窗口的 last_seq 差只表示混合TTY/console发行帧的进展，不是 console 消息序号/host ACK。保留尾帧有 source，可区分当前活动来源；窗口超过512帧时不能还原全部字节。 |
| 同设备 `rx_stats`、`irq_watch`、`console_rx` | 仅软件统计，驱动明确读时不碰硬件（1067–1135）。它们不能替代 TX backlog；本方案不读有 live GIC MMIO 的 `irq_state`。 |
| 实际 `pr/eud<index>` PID 的 comm/wchan/stack/stat | 线程名格式由nbcon.c1384决定，先识别实际PID；两个已有时点的栈/CPU计数可区分当前忙打印、mutex等待和空闲，不能补造r5当时栈。 |

`read-only-inventory.py` 只读显式传入的文件系统根，不设置 trace、不写 sysfs、不触发 PM、不等待；输出只保留相关 cmdline 项，journal 不输出日志正文。17项离线 fixture 验证了报文/CRC拒绝、字段筛选与读后文件内容不变，见 inventory-test-result.json；根会话后续已另行提供上节实际运行采样。**离线测试与实际采样均非低功耗验收**。脚本不能在 userspace 已冻结的50秒中持续采集，因此若重现才需要内核已预置事件。

## 若后续确需短暂降低 console 输出

这是候选受控实验，**本轮没有执行，也不因此开启新整机待机**。必须先与相机会话约好短窗口；该设置影响所有 console 的可见输出，可能减少它依赖的实时 info/debug 串口诊断。

1. 在同 boot 保存 ignore_loglevel 原值与 printk 四值，并记录对应 EUD journal 序号、当前 console 清单和时间。保证唯一参数写入者。
2. 仅准备把 printk 的第一个值临时设为5，后三值逐字保持；再将 ignore_loglevel 设 N，使普通0–4级（含 warning）仍交 console。先写阈值、后去掉 ignore，避免短暂使用原高阈值。只降低阈值而保留 ignore=Y不会达到目的。
3. 回读两项确认；在短暂**清醒**窗口用既有工作负载、journal进展和已有 dmesg 采集比较，不写 /dev/kmsg 制造流量，不清 dmesg、不重新绑定、不改 console_suspend 或串口节流。若参数被其他任务改写，停止实验，避免恢复动作覆盖对方新值。
4. 以保存的四值完整恢复，再恢复 ignore 原值并回读。恢复高输出可能重新形成积压；这一点也需在窗口内观察。保存值只能用于同 boot/同一实验。

此法只检验 console 输出负荷路径；不修复驱动锁、实际 RTC 唤醒、USB恢复，也不构成正式省电方案或整机待机通过。

## 现有事件能区分到什么程度

不要把 `printk:console` 当 FIFO/seq 进展。实际 printk.c 2216–2243在 `printk_sprint` 格式化文本时就调用 trace_console；事件只带文本，没有 console 名、seq 或 ACK。`RCU_TRACE=y` 也不表示有 console SRCU grace-period事件；本次 srcutree.c 没有 trace_* 调用，不能用普通 rcu 事件冒充SRCU边界。

若未来独立PM窗口批准重现，先只读 available_events、available_tracers、所选format/trigger；确认已有 `power:suspend_resume`、`sched:sched_switch`、`lock:contention_begin/end` 及 stacktrace trigger。不要尝试不可用的 function_graph/kprobe，也不写共享 trace 实例。最小现有事件方案是：

- 对**实际写mem的线程PID**与实际EUD printer PID，记录 sched_switch/wakeup；在 sched_switch 的 `prev_pid==P && prev_state!=0` 条件触发定向 stacktrace，才能在切出时抓到 `__pr_flush→msleep`、`console_lock→semaphore`、`console_list_lock→mutex` 或 `__synchronize_srcu→wait_for_completion`。SCHED_TRACER=n只禁调度延迟tracer；sched_switch事件定义在 include/trace/events/sched.h220–267，TRACING选择TRACEPOINTS，不能据此误判事件一定不存在，仍需runtime目录确认。
- 对这些PID记录 lock contention并给begin附少量定向栈。lock.h的contention事件在CONFIG_LOCKDEP条件外；mutex.c648/694/793、semaphore.c317–319确有调用。console_lock是console_sem，console_list_lock是console_mutex，EUD tx_mutex需靠栈/lock_addr区分。mutex在自旋到阻塞转换会有多个begin，不应机械地当一对事件就是全部等待。
- 事件过滤字符串示例只有在format确认后才可采用：sched_switch过滤 `prev_pid == P || next_pid == P || prev_pid == E || next_pid == E`；其stacktrace触发示例 `stacktrace:128 if (prev_pid == P || prev_pid == E) && prev_state != 0`；lock事件按 `common_pid == P || common_pid == E`。128次是有限证据，可能先被pr_flush循环耗尽，**缺后段栈不能排除后段SRCU**。若要覆盖完整间隔必须据实际调度频率预算有界缓冲/栈次数，检查trace overruns；本次不提供自动arm脚本或扩大跟踪。
- 这能识别被调度切出的等待栈；持续忙等而不切出、硬件MMIO停顿、每个console精确diff仍可能缺证据。不能把“未抓到某栈”解释为机制已排除。

RTC只需补与该窗口同时间基的 `rtc_set_alarm`（secs/err）、`rtc_alarm_irq_enable`（enabled/err）、RTC实际alarm IRQ号的 `irq_handler_entry/exit`（irq/name/ret）、power wakeup_source activate/deactivate（name/state），配合power:suspend_resume、写入前RTC target/剩余时间、wakeup_count握手。pm8xxx.c644–651注册名 `pm8xxx_rtc_alarm` 并设置wake IRQ；IRQ须先从实际/proc/interrupts识别，不能硬编码旧号。rtc_timer_fired 是 rtc_timer_do_work 在延期work中、时间判断和callback之后的事件（interface.c979–999），不等于硬IRQ到达时刻；rtc_irq_set_freq/state是周期IRQ设置，也不等于alarm触发。wakeup_source的state是组合计数值（wakeup.c568–570），不是“硬唤醒原因”位；active/deactive也可能只说明入睡前事件被处理。缺失的pm_wakeup_irq不会由计数+1补出来源。
