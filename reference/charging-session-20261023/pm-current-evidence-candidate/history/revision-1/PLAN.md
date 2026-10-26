# 当前 adopted boot 的 PM 定向取证：最小下一步

状态：仅核查／方案，未实现、未构建、未访问设备；不改变502启动事务。旧r5、`apsd-dwc-resume-error-candidate` 的 changes-required、`dwc-resume-device-cleanup-candidate` 的 DO NOT EXECUTE 均保持。

## 已证事实与候选完整性

- r5原件实驻留3396.192s，计划15s不通过。console提示至dpm_prepare有50.467767s，早于charger真实suspend。RTC IRQ只知+1，没有其到达时刻；不能证明alarm先消费，也不能把USB失败归因console／charger。`pm-preparation-gap/gap-audit.json`列出的五份私有原件SHA本次重新只读核对相符。
- 安全primitive `charging-ui-audit-20261023/pm-transaction.py:20` 已有27例：sync和有界wakeup_count读取在arm前，写回原计数，仅一次mem，清理只匹配自己的alarm。保持原SHA `fd3fd4be…da0a1`，无需另造算法。
- worker revision2 `charging-ui-audit-20261023/pm-worker-candidate/worker.py` 已有29例，但仍不是当前可直接运行的工具：`:272`要求r5旧PID/路径且收据boot等于新事务；`:318`要求曾实际ENOENT的pm_wakeup_irq存在；`:333`只启用三个power事件，不能区分console内部等待或RTC IRQ时点。dmesg严格prefix也会拒绝已有完整重叠的正常滚动。
- DWC同步恢复候选已实现11组／8函数并编译gadget.o，尚无一致Image／部署：`charging-oem-audit-20261023/dwc-device-sync-recovery-candidate/`。其gadget.c:2816仍忽略`__dwc3_gadget_start()`返回，因此新同步恢复只覆盖soft-connect实际返回的失败，尚未覆盖旧126例已经证明的start_config／EP0错误。此轮不修或整合DWC。

## 新叶与小差异

拟只在本新叶新增下列文件，旧worker／primitive／原件一律不改：

1. `prepare-request.py`：默认本地检查。从根明确选择的、实际passed postboot＋adoption＋当前pointer／endpoint原件生成一次新request，绑定原件SHA、boot/guard、release/version/rootfs、R8文件/loaded-note、相机481/468、startup500、boot与logdump、严格key。尚未真实adopt的502不能生成有效request；不创建guard或切pointer。旧r5终态只是已保留历史来源，不伪造为当前boot收据，不查旧PID来决定新boot存活。
2. `worker.py`：由revision2窄派生。以新request替换旧r5同boot/PID门；在任何manager/I²C读取前验证本次boot/guard/SoC/rootfs和请求，随后保留原保护、Full、源预算、音频/GNSS/相机及服务前置。新事务／唯一输出和trace instance；正常动作仍单次dispatch，无自动retry／USB恢复／重启。没有无request的自动设备入口。
3. `trace-evidence.py`：仅本次所需能力预检、定向trace配置和解析。由worker调用；不新建daemon／stopper／通用追踪框架。`pm-transaction.py`逐字复制原固定库，原27例复用。

## 实际能力与定向范围

先有只读inspect，保存实际当前`/proc/consoles`、console active、相关cmdline／printk参数、`available_events`、所选`format`、trigger catalog、trace_clock、RTC sysfs与`/proc/interrupts`。旧363配置／恢复后库存只作来源，不能替代当前runtime能力；EUD-off不沿用旧pr/eud PID或EUD MMIO。保存pid/startticks/argv，PID由当前worker及实际console producer枚举，绝不沿旧号。

采用缓存的真实事件定义，并以runtime format再次逐字段确认：

| 观测 | 精确选择／限制 |
| --- | --- |
| PM阶段及原目标回调 | 原`power:suspend_resume`与`device_pm_callback_start/end`保持；保存完整无溢出头和实例时钟。 |
| RTC alarm | `rtc:rtc_set_alarm`的secs/err、`rtc_alarm_irq_enable`的enabled/err；以本事务target/阶段核对。事件无RTC设备字段，不能仅凭一条同秒事件宣称属于rtc0；多RTC或并发设置则归属未知。 |
| RTC硬IRQ | `/proc/interrupts`唯一`pm8xxx_rtc_alarm`行实际取得IRQ号；确认entry/exit format有irq/name/ret后，仅写`irq == N`过滤并回读，才enable。缺失、歧义或过滤失败均不改成全IRQ捕获。`rtc_timer_fired`不当硬IRQ到达。 |
| console等待 | 仅实际写mem PID及确证console producer的sched_switch prev_pid/next_pid、lock common_pid过滤；有限stacktrace触发次数（上限128）并保存触发器／过滤回读。无实际producer时不编造EUD线程；缺字段/trigger就将该观测拒绝／标能力缺失。没有function_graph/kprobe退路。 |
| wakeup source旁证 | 只有从实际设备关系确认的name和format兼容时才定向过滤；不能把state组合计数当硬件原因位。未能映射则不扩大到所有source。 |

只配置本事务新建的独立trace instance，过滤／trigger全部先装并回读，再enable；任一要求项不兼容即在arm之前拒绝相关观测，保留原因。若本事务要求的RTC必要观测不完整，则不调用PM。部分设置失败也必须按已完成阶段停本实例、保存原始trace、清理自己确切添加项，主错误与清理错误分开；不碰root/global instance或他方trigger。缓冲和触发计数固定有界，overrun或栈预算耗尽必须报告覆盖不足。

trace_clock必须为当前可用、可跨CPU比较的一种明确时钟并回读；保留该选择及两时钟锚点。不能假设trace时间包含睡眠或把旧MONOTONIC换算成BOOTTIME而不记录。

## 缺失属性与结果语义

`pm_wakeup_irq`缺失记录`{available:false, errno:ENOENT, value:null}`，不代造0，也不以缺失属性硬拒所有只读取证。它若存在仍保存真实值；因果判定与收集成功分开。

输出至少独立给出：事务returned/aborted/failed、实际驻留与15秒容差、RTC事件相对machine_suspend的先后、wakeup attribution（proved／not_proved）、console等待观测、目标驱动恢复和trace/alarm清理。没有可靠原因位时，即使RTC IRQ在睡眠区间也只报告时序证据，不能机械升级为唯一唤醒原因；整机通过仍保守false／证据不足。不得再用IRQ+1、sysfs errno0或USB logical configured替代完整验收。

dmesg滚动只复用已测的完整有序尾部重叠证明；无重叠或缺基线尾仍拒绝，绝不只比较全ring计数。同步后保留真实source/native/硬件预算、Full与服务身份，不能由新工具恢复CHG或更改USB。

## 下一批准范围

下一步可离线实现上述三个小文件及本次新边界的实际函数fixture：实际adoption混淆拒绝、缺失属性不造值、IRQ歧义／format/filter失败零广域enable、部分trace setup/cleanup、RTC先于入睡与证据不足、日志滚动连续性。旧27／29／126及其它套件不重跑。不编Image、不接入DWC、不启动任何设备inspect／trace／PM。

本文不承诺当前已具备全部runtime事件：未来先由根在独占只读窗口取得真实capability原件，再按它绑定/拒绝对应观测。硬件最终仍需受控验证，但上述request、当前身份迁移与定向证据实现属于尚可离线完成的确定工作。
