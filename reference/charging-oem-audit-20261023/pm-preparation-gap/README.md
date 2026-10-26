# r5进入设备PM前50.468秒缺口

纯PC离线审计。复用root的 `storage.mounted_build()` 验证并复用原挂载，仅定向读取source354的PM／printk／console／serial小文件；未访问手机、SDK、改共享树或raw记录。源码路径和hash见 [source-manifest.json](source-manifest.json)，原件hash和计算见 [gap-audit.json](gap-audit.json)。

## 可以准确定位到哪里

| 原始事件 | MONOTONIC时间 |
| --- | ---: |
| freeze_processes end | 12032.535758 |
| suspend_enter end | 12032.535761 |
| dmesg `printk: Suspending console(s)` | 12032.535763 |
| dpm_prepare begin | 12083.003530 |
| charger真实driver suspend begin/end | 12083.014380／12083.112073 |

freeze→dpm_prepare缺口为 **50.467772秒**，console提示→dpm_prepare为50.467767秒。charger真实回调直到其后才开始，实际耗97.693ms、返回0；它的新增回调不能解释此前的50秒。

实际 `kernel/power/suspend.c` 的顺序是：`suspend_prepare`冻结完成（386–390），`enter_state`在616行发suspend_enter end，随后进入 `suspend_devices_and_enter`；517行先platform_suspend_begin，521行 `console_suspend_all()`，522行只记录测试起点，523行才 `dpm_suspend_start`。`drivers/base/power/main.c` 2354调用dpm_prepare，后者2288行入口立刻发trace。

console提示已出现，说明此前platform begin已返回。现有证据把大缺口收敛到**已经进入console_suspend_all、但尚未进入dpm_prepare的路径**。它不在freezer内，也不在任何设备suspend回调内。没有函数图／调度栈，仍不能精确断言50秒都耗在哪一个console子步骤或锁。

## console为何不保证一秒内返回

实际 `kernel/printk/printk.c` 2785–2816：

```text
pr_info(Suspending console)               // 自身也可能触发同步打印
pr_flush(1000, true)
console_irqwork_blocked = true
if console suspend disabled: return
console_list_lock → 给各console置CON_SUSPENDED → unlock
synchronize_srcu(console_srcu)
```

`__pr_flush` 4473–4571会获取console_lock、可能同步flush；4551–4552在进展时重置一秒预算。扣减预算只围绕4561–4565的msleep等待，不包含所有锁获取／打印耗时。故“pr_flush参数1000”不能推导整个console阶段最多一秒。慢打印、console锁等待、不断有进展的backlog flush、后面的SRCU等待均是源码允许的位置；现有trace未区分它们。

当前缓存没有本次active console清单，也缺函数图／阻塞栈，**不能据此断言是UART／fbcon、哪个console驱动或哪个线程**。`pm_prepare_console()`在冻结之前调用，是另一个阶段，不能把这里的缺口错放到它的VT切换。

## 默认值、运行期参数和串口PM的边界

- `printk.c` 2754默认 `console_suspend_enabled=true`；2757–2762的启动参数 `no_console_suspend` 将其置false。
- 2763–2764以bool `console_suspend`、权限0644导出运行期参数。该内建printk对象对应通常的只读确认位置 `/sys/module/printk/parameters/console_suspend`，值Y/N；本子任务没有访问该文件或改它。实际r5出现2790行受 `console_suspend_enabled` 条件控制的提示，说明执行到提示时该值为true。
- **即使设成false，2798行仍先执行pr_flush，再到2801–2802返回。** 因此不能预设关闭console suspend会消除本次flush等待，也不能以参数绕过来认证正式低功耗修复。
- `serial_core.c` 2368–2375：仅当该UART是console且该布尔false时，停止RX（若支持后续start_rx）、设置awake path并提前返回；不会执行正常端口suspended/关闭流程。resume的2460–2479也按此值选择电源和console恢复分支。
- `qcom_geni_serial.c` 2088–2115：先为console设置ACTIVE_ONLY interconnect tag，调用uart_suspend_port；false且该UART是console时跳过 `pm_runtime_force_suspend`。2125–2131的resume也跳过对应force_resume。这会改变串口PM前提，不能把它当成零副作用的日志开关或正式省电方案。

以上只证明当前源码分支，不证明本机当时注册的是哪一个console。后续如定位该子问题，先只读确认运行参数、cmdline中的console相关项、`/proc/consoles`，以及当前内核是否已有可用的定向函数跟踪；不应先改参数或重建Image。

## RTC可能在实际入睡前到期／被消费

取回的worker在74–78行先设置RTC当前秒+15，再phase写入、用户态全局sync，然后写mem；没有保存实际target值／进入mem前剩余秒数，也没有wakeup_count握手。

这次**仅已证实的内核console准备缺口就有50.468秒，大于已设置的15秒**。在RTC正常前进的前提下，deadline可以在真正进入设备PM／s2idle前已经过去；不需要再假定用户态sync消耗了50秒。若中断当时已经被处理、又没有wakeup_count事件防丢握手，随后仍进入睡眠时就可能已无未来RTC alarm可唤醒。

但raw只有整个区间RTC IRQ delta=1，没有IRQ时间戳／唤醒源trace，不能证明这唯一中断确在console阶段被消费，而不是之后才处理。缺实际RTC target／剩余时间也限制更强断言。根会话恢复时确认 `pm_wakeup_irq` 属性不存在（ENOENT），不能靠它补造旧唤醒来源。用户亮屏／重插发生在取回前，同样不能单独证明旧RTC的实际处理时点。

因此目前结论是：**与证据高度相容的失效机制，尚未证明具体RTC因果和console内部等待点。** 源码 `pm_wakeup_pending()` 877–882仅在events_check_enabled时比较已保存事件计数；worker未建立该握手。未来事务应复用已修正的wakeup_count primitive，至少防止alarm已到后再继续入睡，而不能仅把alarm加大来掩盖50秒问题。

## 验收与问题分离

raw记录3396.192秒睡眠驻留、51.486秒非睡眠单调时间、same boot、success+1/fail0、taint0，charger回调均返回0且醒后数据健康。raw的 `runtime_passed=true` 条件没有检查计划15秒驻留或自动唤醒，因此**这次计划15秒PM不能算通过**。

console准备50秒、RTC计划唤醒未满足、醒后NCM未恢复／同口重插才恢复是应分别定位的事实。不能把前者直接归因charger新回调，也不能仅凭后者证明一直没有退出系统睡眠。

当前新PM保持暂停。若后续已有安全窗口且需要继续，应先定向记录 `console_suspend_all/__pr_flush/console_lock/SRCU` 边界与调度等待，并同时记录RTC deadline／IRQ时间、wakeup_count和真正唤醒原因；保留原记录，不重放已经终态的r5。

后续离线补充见 [EUD／过滤参数／最小取证](trace-plan/README.md)：实际qcom_eud_com输出是固定节流、不等待host ACK；当前k363没有function_graph或kprobe，需使用已有事件与定向栈。该补充明确区分GENI条件参考和实际EUD路径，仍未认定50秒的具体因果。
