# R8 MP2650 接线与启充顺序：限定源码结论

当前精确 R8 源没有新增“安全采样完成后再等一整轮才 enable”，也没有因先 sample 后 apply 而把本次通知固定落后一轮。没有足够依据改写启充顺序或缩短硬件等待，本叶不新增短 poll、不改任何运行代码。

范围只到 MP2650 的安全采样、策略、限流和使能、REG13 读取。USB IRQ、gauge 与用户空间通知由另一条审查负责。此处不修改 Phosh、UPower，不强制 Charging，也不把静态顺序当实际图标时延根因或物理验收。

## 来源

实际 R8 编译收据 `charging-management-20261023/thermal-bands-build-result.json` 绑定 charger `ed2e1d4d…a144c`、core `df9caed5…ed4e8` 和 ko `10ec06fb…fa6297f`。本次仅读正式 `charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply/` 的同哈希字节；六个相关源逐项与 manifest 和实际 build receipt 核对。旧 kernel-v2 charger 没有替代当前源。该整合 manifest 的旧 boot/USB100 描述是历史；本叶仅使用其未变的 R8 充电源码映射，不声称当前仍运行旧 Image 或预算100。

原厂使用已缓存官方 Realme Android R 固定提交 `23172a1571bd91156032cc9fef16284a82b63d2c` 的 `drivers/power/oppo/charger_ic/oplus_mp2650.c`（`b6313a65…d123e`）和 `drivers/power/oppo/oplus_charger.c`（`6cfb97b4…aa2d4`），没有用近型号/第三方同名函数替代。准确完整哈希、路径、截取行号见 `result.json` 与 `source-excerpts.txt`。`audit-sources.py` 只读取、核哈希与摘录，没有执行驱动函数、旧测试、构建或设备入口。

## 同一次 work 内的实际路径

| 顺序 | 当前 R8 源码依据 | 结论 |
| --- | --- | --- |
| 输入与物理供电一致 | `samurai-mp2650.c:119–136` | source ONLINE 与 REG13 ACOK 一致、预算可读才继续；真实双方 off 才重置周期/锁存。 |
| 完整安全样本 | `:137–161` | 保护、温度/电压/flags/0x0c 净流、MAC 电芯、唯一 REG14 故障读取后，再核 source/预算/REG13；不一致立即抑制，不授权 enable。 |
| 温控/Full/保护策略 | `:176–256` | 同一个同步 `sm_step_locked` 取得样本并运行有效域、温区、故障/timeout、Full/再充门；没有排到下一 work。 |
| 写入并校验 | `:257–275`、`mp2650-core.h:239–278` | 同次执行 `sm_apply`：继承配置门→已同值则零写返回；否则暂停→第二/第一 IIN→CC→预充/终止→CV→enable，每步 readback。失败执行 stop 并保留错误/锁存。 |
| 通知用真实 REG13 | `samurai-mp2650.c:338–344`、`:316–327` | `sm_step_locked` 返回后立即重新读 REG13，再比较离散通知状态，锁外 `power_supply_changed`。不是把 collect 时的旧 CHG_STAT 直接当写后状态发布。 |
| 属性读取 | `:424–438` | ONLINE/STATUS getter 当下读 REG13；转换器 Charging 不覆盖 Battery 净流语义。 |

因此，把安全采样移到 enable 之后，或者把 CHG_EN/target.enable 直接当 Charging，不是消除这条路径里已有的整周期等待，而会撤掉保护证据。`sample_full` 确实来自写前完整安全样本；它供 Full 策略使用，不能换成 enable 后未经完整保护校验的状态来清周期。

常规下一轮为 `:340` 的1000ms；但真实 input/protection 事件在 `:347–351` 已 `mod_delayed_work(...,0)`，resume `:741–750` 也立刻重排并强制首次新鲜报告。源码不能保证 workqueue/I2C 调度的实际时间上界。若硬件 CHG_STAT 在即时写后读取之后才变化，当前确实可能到下一次正常观察才发现；这是剩余观察间隔，不是已经证实的本次图标根因，也没有据此添加短轮询。

## 与原厂 enable、限流、ADC 和等待的关系

原厂 `mp2650_hardware_init:1710–1752` 为停充→双 IIN 初始化→CV/CC/预充/终止等→unsuspend→enable；当前实现保留了先合法限额后 enable 的方向，但有意不重放 reset、关闭安全 timer、OTG/看门狗等整段 OEM 初始化。

原厂 `mp2650_enable_charging:890–907` 和 `mp2650_unsuspend_charger:1078–1094` 没有固定正常等待；其 masked-I/O helper `:268–306` 的10ms仅在 I/O 错误重试。`input_current_limit_without_aicl:1654–1675` 也是双 IIN 写，无固定等待。正常 AICL `:504–524` 等的90/130/50ms是在增载后读取 VBUS、回退限流的测量间隔，不能当成可删的图标等待；当前 core 没有这一 AICL 阶梯测压流程，也不存在可直接删掉的相同 sleep。

当前 ADC high/low/high 稳定读 `samurai-mp2650.c:355–373` 只被 CURRENT_NOW/VOLTAGE_NOW getter `:412–422` 调用，三次不一致即 ENODATA，既不启动一次转换后等完成，也不挡 `sm_collect`/`sm_apply`。原厂 `mp2650_get_ibus_current:975–996` 同样读现有 ADC 寄存器，没有启充后再等 ADC 的固定 sleep。当前安全采样中唯一显式短等待在 `gauge-i2c.h:32` MAC 查询后1–1.5ms，已注释匹配 OEM 查询要求；没有删改它。

## IRQ burst 不会加速软件 Full、再充或10小时上限

`sm_step_locked:178` 取得 `ktime_get_boottime_ns()`，`:222` 传给 `sm_oem_full_step`，不是用调用次数当秒。`oem-full-cycle.h:14` 定义5秒；`:189` 只有首次 tick 或距上次 tick 至少5秒才 `due`；`:198–201` 和 `:217–222` 在门后每次最多加一次，没有补算 while。相同时间戳或任意亚5秒额外 notifier/IRQ调用不会让6/11/4样本或再充 `>5` 提前成立。

精确边界是首个合格样本可计1：6个软件 Full 样本至少跨25秒、11个至少跨50秒、电压后备4个至少跨15秒，不能笼统声称它们都还要再多等首个5秒。已建立 Full 时有 `last_tick=now`；若中断/温区切换等清掉 streak，新的有效序列允许立即计首个样本，但旧计数已为0，burst仍不能保留旧证据又快速补满。非 tick 的电压/电流反证可以即时清 streak（`:192–197,212–216`），不能加计数；未知、错误、TCA、hard latch/timeout清 streak并停充（`:129–161,235–236`）。观察缺口≥10秒会清 streak，恢复后不追补遗漏样本（`:120–127`）。

新鲜硬件 Full 的即时分支 `:177–187` 是有真实终止状态的独立事件，本来就不等5秒；它仍在完整有效域/保护/故障/TCA门后，不是 IRQ计数旁路。`charge-cycle.h:79–84` 的36000秒直接来自 BOOTTIME 与 anchor 差，不是每 poll 累加一秒，额外调用不会加速。坏时钟回退按现有策略停止，不做无符号减法偷跑。

本轮未发现需先修的 MP2650 时序/计数缺陷。最小下一步保留这里的采样与写入门，优先由正在准备的真实 USB IRQ 事件刷新与 gauge 外供回调延时审查缩短底层通知链；本叶不为追速度新增短 poll，也不部署任何代码。
