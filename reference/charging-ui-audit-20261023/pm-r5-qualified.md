# r5 实测重新定级：恢复有证据，15秒 RTC 计划失败

新取回的原 r5 文件保持原样，包括错误偏宽的 `runtime_passed=true` 和终态 phase 的 `passed=true`。本审计另写 [pm-r5-qualified-result.json](pm-r5-qualified-result.json)，明确 **passed=false、planned_15_second_rtc_s2idle_passed=false**；没有执行主目录旧 audit 脚本，没有再次调用 PM。

## 时间证据

- 原 worker 已终态，fetch 记录 `alive=false`。
- sysfs mem 调用确实返回 errno0，suspend_stats success+1、fail不变；但 BOOTTIME 为3447.679秒，MONOTONIC为51.486秒，差值 **3396.192秒**，远超计划15秒及5秒容差。
- 完整 trace 为5222/5222，无环形溢出。kernel sync为1.063ms，freezer区间为14.467ms。
- `suspend_enter end=12032.535761` 到 `dpm_prepare begin=12083.003530` 有 **50.467769秒**。这在所有设备 PM 回调之前；charger 实际 suspend 回调直到12083.014380才开始，97.693ms后结束，resume回调20µs返回。
- 当前 source354 `suspend_devices_and_enter` 在这个区间包含 `platform_suspend_begin()`、`console_suspend_all()`，之后才 `dpm_suspend_start()`；dmesg在间隔开始处印出了“Suspending console(s)”。没有函数级跟踪，不能把整个50秒无条件归因于某个console函数内部，更不能归因于还没有开始的 charger suspend 回调。

所以，旧审计器“sysfs errno0、success+1、驻留>=1、IRQ+1即通过”的条件不足，无法判断是否在预定 RTC 窗口唤醒。本轮计划失败已经由远超时长证明，无需猜测根因。

## 可以保留的恢复结论

原始 trace 的2552个callback_end全部error0。charger先于USB/protection/gauge挂起，供应者先于charger恢复；目标driver/bus回调与prepare/complete包装分开审核。前后charger配置寄存器（除实时REG13状态）一致，原生额度仍100mA，结束鲜样age134ms、保护/控制正常、错误/锁存为0，camera PM/M2M和四用户服务PID/UID保持，taint0。

dmesg不是简单prefix，因为环形日志淘汰了旧头44行；但旧尾到新头有13054行逐字匹配的完整有序重叠，基线结束后的48条新记录仍全部保留。本次这些新记录没有目标WARNING/Oops/refcount/GPU/NGD故障。审计只保留“没有新增被记录目标故障”，不根据原始总计数相同去掩盖日志滚动。

`post_resume_restoration_observed=true` 只覆盖这些已取得的恢复证据，不包括cache中没有记录的结束模块loaded-note／manifest再次核验。原before样本age2102ms也单独标出，不能冒认符合新worker小于2000ms的鲜样前置。

## 仍不能证明的事

RTC IRQ计数加1不能说明它在何时发生、是否已在50秒前置间隔中被处理，或是否直接造成了后来的恢复。本轮没有alarm IRQ事件时间戳，也没有`pm_wakeup_irq`，因此RTC因果归属未证明。用户短按可亮屏、拔插后恢复NCM属于根会话另行取得的后续事实；本cache没有记录这些物理动作的精确时间，不能将它们与某个trace时间点强行等同。

先前 [纯静态审计](pm-r5-offline-audit.md) 中“alarm可能先消费”仍是机制假设；现在可以定位50秒发生在设备回调之前，并证明15秒计划失败，但还不能把RTC提前消费写成已观测事实。

## 可复用审计

`audit-pm-r5-qualified.py` 只读取保留cache，在本目录导出独立结果，包含输入及审计器哈希，并确认输入字节未改变；`test-pm-r5-qualified.py` 的5项证据边界测试通过。它明确区分完整有序日志重叠与丢失基线尾部，拒绝“IRQ+1覆盖超长驻留”，也拒绝“时间相符但没有RTC归属”冒认通过。

新worker revision2仍冻结，只按根会话要求扩展了Full健康兼容；其dmesg严格prefix门槛会保守拒绝这类仍有完整有序重叠的日志滚动，本轮没有擅自放宽。若后续修正，应单独使用已测试的有序重叠证明，而不是忽略日志连续性。
