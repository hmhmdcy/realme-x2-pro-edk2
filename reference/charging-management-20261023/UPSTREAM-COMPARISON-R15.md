# R15 主线/开源实现对照（充电管理）

范围：只读比较 `reference/charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply/` 的 `samurai-mp2650.c`、`mp2650-core.h`、`oem-full-cycle.h`、`samurai-usb-input.c`、bq27xxx 补丁，以及 WSL 内 7.3.0-rc6 的 `qcom_smbx.c`、`qcom_battmgr.c`、`bq27xxx_battery.c`、`tcpm.c` 路径。结论按可日用工况风险排序；当前实现的关键字是“OEM 参数 + mainline 外壳”，不能把它当成标准的 bq27xxx 或 qcom 充电状态机。

核对边界：WSL 的 7.3.0-rc6 树里没有独立的 `smb5_charger.c`；`qcom_smbx.c` 的匹配表只有 `qcom,pmi8998-charger` 和 `qcom,pm660-charger`，因此下面关于 SMB5 的“mainline 做法”只作为同系列 charger 的属性/状态机参照，不冒充已核对过的 `smb5` 实现。PM8150B 的 USB 输入寄存器仍由本项目的 `samurai-usb-input.c` 直接解码，mainline 对应路径是 `tcpm` + `qcom_pmic_typec`，两者不能按同一寄存器表套用。

另有一条必须写清的版本边界：本报告的只读基线是 `charging-session-20261023/r8-source-integration` 快照，它的 `sm_suspend()` 确实会在 `control` 时无条件 `sm_stop()`。同工作区更新的 `charging-management-20261023/charging-integration-20261026-01/source/.../samurai-mp2650.c:430` 已增加 `sm_suspend_needs_stop()`，正常 active 充电在 suspend 时不写停充位；因此 suspend 不再是当前最新候选的 P0，只在旧快照中成立。下面的风险排序针对 r8 快照；移植结论必须按实际部署的 Image/module 版本复核。

## 结论先行

1. **最高风险是输入预算的重复确认被当成一致性证明**。`samurai-mp2650` 要求 TCPM 的整组 `online/usb_type/voltage/max/now` 在两次读取间完全相等，否则 `-EAGAIN`；但 `tcpm.c` 的 `CURRENT_MAX` 与 `CURRENT_NOW` 当前都返回 `port->current_limit`，重复读同一值并未独立证明 PD 合同稳定。PD 重新协商、NCM 枚举或 1 秒窗口内的状态切换仍会被放大成 inhibit。`samurai_usb_input` 又以 1 秒轮询把 APSD 的 `CURRENT_MAX` 和 DWC3 的 `INPUT_CURRENT_LIMIT` 混在同一 psy 上。mainline 把“合同上限”和“软件限流”分开，并且不会用两次相同读取代替状态确认。
2. **第二风险是 `CURRENT_NOW` 语义混用**。`mp2650-input/current_now` 返回的是 MP2650 输入 ADC，而 battery psy 的 `current_now` 是 bq28z610 的电池净电流；二者方向、量纲和用途不同。mainline 始终把 battery `CURRENT_NOW` 与 charger/USB 输入电流分开，用户空间不会把输入电流当成“电池正在充电”的证据。
3. **第三风险是 Full/recharge 的判定过强地绑定 OEM 计数器**。`oem-full-cycle.h` 用 5 秒 tick、软件/电压双计数器、`recharge_count > 5` 和 `gauge_current_ua` 的 ±110 mA 窗口，且把 TCA 当作 stop；mainline bq27xxx 的 `POWER_SUPPLY_STATUS_FULL` 来自 gauge 的 FC/CHGS 标志，recharge 由 charger 的 `CONSTANT_CHARGE_VOLTAGE` 与 `RECHARGE` 阈值/硬件行为决定，不会在驱动层重建一套“数到第 6 个 5 秒样本才允许再充”的状态机。当前实现与 OEM 参数接近，但抗采样抖动和 suspend 断点能力弱。

## 逐项对照

### 1. 充电状态机

**当前实现**
- `sm_step_locked()` 是唯一状态推进点：`sm_collect()` 读 gauge/charger，`sm_policy_with_reason()` 给出目标，`sm_oem_full_step()` 再叠加 Full/recharge 状态，最后才 `sm_apply()` 或 `sm_apply_charge_hold()`。
- `sm_apply()` 在每次轮询都读回 0x00/0x0f/0x02/0x04/0x03/0x07/0x08，只有全部匹配才跳过写；不匹配就先 `sm_stop()` 再逐项写，最后 `sm_update(0x08, 0x18, 0x10)`。
- `sm_apply_charge_hold()` 先清 CHG_EN，再验证输入限制/CC/CV/预充/终止配置，最后只恢复输入转换器，保持 CHG_EN=0。
- 错误路径统一 `sm_stop()` 并把 `c->latched` 置位，只有物理 detach、显式 AUTO、或重新 probe 才清除；`sm_sample_latch()` 明确区分 `source_inhibit` 和电气 fault。

**mainline/开源做法**
- `qcom_smbx.c` 是 QCOM SMB2/SMBx 系列（PMI8998、PM660）的 charger 驱动，使用 `power_supply_desc` 的 `get_property`/`set_property` 映射 `CURRENT_MAX`、`CURRENT_NOW`、`VOLTAGE_NOW`、`ONLINE`、`STATUS`、`HEALTH`、`USB_TYPE`；`smb_init_seq()` 在 probe 时初始化 AICL、Type-C 角色、recharge 阈值、CHG_EN、termination 和 watchdog。它不是 SMB5，也没有本机 MP2650 的寄存器序列。
- `qcom_battmgr.c` 的 `qcom_battmgr_bat_get_property()` 把 `STATUS`、`CHARGE_TYPE`、`CURRENT_NOW`、`TEMP` 等直接从电池管理固件响应里读出；状态机在固件侧，驱动不做 5 秒计数。
- `bq27xxx_battery.c` 的 `STATUS` 由 gauge 的 `FC`/`CHGS`/`DSC` 标志和 `bq27xxx_battery_get_property()` 计算；`POWER_SUPPLY_STATUS_FULL` 不要求 charger 驱动额外计数。
- `tcpm.c`/`usb power supply` 把 Type-C/PD 的“已协商合同”作为 `CURRENT_MAX`/`VOLTAGE_NOW` 的来源，充电器只消费该预算，不在 charger 里等待两次 TCPM 采样完全相等。

**实质差异**
- 当前实现把“硬件状态机”和“软件 Full/recharge 状态机”叠在一起，且软件状态机有 5 s tick、计数器、band 变化清 streak 等历史；mainline 更依赖 gauge/charger 的硬件状态，软件只做属性映射和异常处理。
- 当前实现的 `sm_step_locked()` 在持锁状态下做多次 I2C 事务，`sm_apply()` 又在同一轮里先 stop 再写 7 个寄存器；mainline 的 set_property 是单属性、短事务，状态变化通过 IRQ/regmap 缓存和 workqueue 合并。当前路径在 I2C 抖动时更容易把一次瞬时读错放大成 stop+latched。
- 当前实现的 `sm_preconditions()` 要求充电器寄存器处于一组非常具体的继承状态（`control & 0xe0 == 0`、`(control & 0x26) == 0x06`、`timers & 0x48 == 0x48` 等），否则拒绝 probe/写入；mainline 驱动通常会在 probe 时初始化到已知状态，或允许运行时修正，而不是把“继承状态不符合”当作不可用。

**日用工况风险**
- 高：I2C 瞬时错误 → `sm_stop()` + latch，后续必须拔插或显式 AUTO 才恢复；用户感知为“突然不充了，重启/拔插才好”。
- 中高：`sm_preconditions()` 对 watchdog/termination 位的严格要求，在固件已启用 watchdog 或残留 OEM 配置时会导致 probe 失败，表现为模块加载但无充电控制。

**建议补丁**
- `samurai-mp2650.c:sm_step_locked()`：把“采样错误”和“策略错误”分开；`-EAGAIN`/`-ENODATA` 只 inhibit 本周期，不进入 `latched`；只有 `sm_apply()` 的写失败或 `sample.fault`/OCA 才 latch。
- `samurai-mp2650.c:sm_collect()`：把 `sm_read(0x13)`、`sm_input_budget()` 的二次读取改为“带时间戳的同一快照”，或允许 `source_inhibit` 只影响本轮，不把 `-EAGAIN` 写进 `last_error` 的持久错误。
- `mp2650-core.h:sm_preconditions()`：保留 watchdog/termination 的只读检查，但把“timers 必须 0x48”改成“若 watchdog 已启用则只验证不写，若 termination 关闭则拒绝启用”的分级约束。

**可安全移植性**
- 可安全移植：`sm_sample_latch()` 的“瞬时 source inhibit 不 latch”原则、`sm_apply()` 的写后读回、`sm_apply_charge_hold()` 的“先清 CHG_EN 再动配置”。
- 不应直接移植：把 mainline 的 `qcom_battmgr` 充电参数接口整套搬进 MP2650；MP2650 不是 SMB5，寄存器/OTG/输入路径不同，直接套用会写错寄存器。

### 2. `current_now` 语义

**当前实现**
- `sm_gauge_sample()` 明确读 bq28z610 的 `0x0c` 瞬时净电流，并在注释里指出 OEM FFA5 的 `get_average_current` 实际映射到 `0x0c`，不是 mainline 的 `0x14` 平均电流。
- `sm_oem_gauge_current_ua()` 把 16 位有符号数按 mA 转 uA：正数=充电，负数=放电；`sm_oem_full_current_qualifies()` 只接受 `[-110000, 110000]` uA。
- `sm_get_property(CURRENT_NOW)` 返回的是 **MP2650 输入 ADC 的电流**，不是电池净电流；`samurai-usb-input` 也没有导出 `CURRENT_NOW`，只有 `CURRENT_MAX`/`INPUT_CURRENT_LIMIT`。
- `sm_read_typec_allowance()` 从 TCPM 的 `CURRENT_NOW` 读“operating_ua”，再读 `CURRENT_MAX` 做上限；但 `sm_input_allowance_equal()` 要求两次完全一致。

**mainline/开源做法**
- bq27xxx 的 `POWER_SUPPLY_PROP_CURRENT_NOW` 由 `bq27xxx_battery_current_and_status()` 读取 `BQ27XXX_REG_AI`（bq28z610 默认 `0x14`）并转成带符号的 uA；注意 mainline 在这个函数里的注释仍写“battery average current”，而本项目的 samurai 补丁把 `CURRENT_NOW` 改成读 `0x0c`、把 `0x14` 留给 `CURRENT_AVG`。这是 OEM 芯片行为差异，不是 mainline 的通用语义。
- `qcom_smbx.c` 的 `CURRENT_NOW` 明确走 `chip->usb_in_i_chan` IIO ADC，是输入电流；`qcom_battmgr` 的 battery `CURRENT_NOW` 是固件报告的电池侧电流，两者不在同一 psy 上混用。
- mainline 的 `usb power supply` 把 `CURRENT_MAX` 定义为“协商合同允许的最大电流”，`INPUT_CURRENT_LIMIT` 是“软件设置的输入限流”；两者不是同一个量，也不要求每轮相等。

**实质差异**
- 当前实现正确识别了 OEM 的 0x0c 瞬时电流，但 **`CURRENT_NOW` 在 charger psy 上被复用为输入 ADC**，与 battery psy 的 `CURRENT_NOW` 语义不一致；用户空间如果按“电池净电流”读取 `mp2650-input/current_now`，会得到输入电流，符号/量纲可能相反。mainline 的 bq28z610 默认 `CURRENT_NOW` 是 `0x14`，本项目的 0x0c 覆盖只应存在于 samurai opt-in，不应回灌到通用 bq27xxx。
- 当前 Full 判定用 `gauge_current_ua`，这是对的；但 `sm_oem_full_current_qualifies()` 的 ±110 mA 窗口对 2-cell 高压电池偏窄，mainline bq27xxx 不会用固定的 ±110 mA 判断 Full，而是用 gauge 的 FC/CHGS 与终止电流。
- `sm_input_allowance_equal()` 要求 TCPM 两次采样完全相等；`tcpm.c:tcpm_psy_get_current_max()` 与 `tcpm_psy_get_current_now()` 目前都返回 `port->current_limit * 1000`，所以二者并非独立证据。当前实现把同一值的两次读取当作“充分确认”，既没有增加信息量，又在真实协商切换时放大 `-EAGAIN`。

**日用工况风险**
- 高：用户空间/UPower 读取 `mp2650-input/current_now` 得到的是输入 ADC 而非电池净电流，电量/功率显示可能方向错误；如果上层用该值做“是否在充电”的判断，会出现“插着电但显示放电”。
- 中高：±110 mA 的 Full 窗口在轻载/屏幕亮起/热降额时可能长期不满足，导致 Full 永远不进入，或进入后 recharge 计数被反复清零。

**建议补丁**
- `samurai-mp2650.c:sm_get_property()`：`POWER_SUPPLY_PROP_CURRENT_NOW` 应返回 `c->sample.gauge_current_ua`（电池净电流），或者把该属性改名为 `INPUT_CURRENT_NOW`（若 ABI 允许）；`mp2650-input` 的 `CURRENT_NOW` 不应与 ADC 输入电流混用。
- `oem-full-cycle.h:sm_oem_full_current_qualifies()`：不要用固定 ±110 mA 作为唯一 Full 条件；改为 `fabs(current) <= termination_current_ua` 且 `gauge_flags & FC`，或把窗口做成 DT 参数（OEM 终止电流 110 mA 是充电器配置，不是 gauge 的 Full 判据）。
- `samurai-mp2650.c:sm_read_typec_allowance()`：只对 `CURRENT_MAX` 做一致性检查，`CURRENT_NOW` 允许变化；`sm_input_allowance_equal()` 不应比较 `operating_ua`。

**可安全移植性**
- 可安全移植：bq27xxx 的“`CURRENT_NOW` = 电池净电流、`CURRENT_AVG` = 平均电流”语义；把 `gauge_current_ua` 暴露到 battery psy 而不是 charger psy。
- 不应直接移植：把 `qcom_smbx` 的 `CURRENT_NOW` 分支直接套到 MP2650；MP2650 的 ADC 是输入侧，量纲/校准不同。

### 3. Full/recharge

**当前实现**
- `sm_oem_full_step()` 先用 `hardware_full && current_qualifies` 立即进入 Full（`SM_FULL_HARDWARE`），否则用 5 s tick 累计 `sw_count`/`voltage_count`；`sw_count > 5`（充电中）或 `> 10`（放电中）才 `SM_FULL_SOFTWARE`，`voltage_count >= 4` 才 `SM_FULL_VOLTAGE`。
- Full 后 `hold_charge_only=1`，`recharge_count > 5` 才退出 Full 并 `recharge=1`；`recharge_threshold_uv = min(cell_target, oem_cv) - drop`，drop 为 100/200/300 mV 按温度带。
- TCA（`0x4000`）直接 `stop_all`，OCA（`0x8000`）直接 hard fault；`SM_FULL_TICK_NS=5s`，`now-last_seen >= 10s` 清 streak。

**mainline/开源做法**
- bq27xxx 的 `STATUS` 由 `FC`（Full Charge）、`CHGS`（Charging）、`DSC`（Discharging）组合；`bq27xxx_battery_get_property()` 的 `STATUS` 分支直接返回 `FULL`/`CHARGING`/`DISCHARGING`/`NOT_CHARGING`，不要求 charger 驱动再数 6 个 tick。
- `qcom_smbx.c` 的 `STATUS` 由 `BATTERY_CHARGER_STATUS_1/2` 的 `CHG_STAT`/`CHARGER_ERROR_STATUS_*` 等位翻译；probe 初始化把 `AUTO_RECHG_BIT`/`VBT_LT_CHG_RECHARGE_THRESH_SEL_BIT` 配成硬件自动 recharge，不依赖软件 5 秒计数器。
- mainline 的 `POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR` 是“auto/inhibit”这一层，不承担 Full/recharge 的具体阈值。

**实质差异**
- 当前实现把 OEM 的“5 秒采样 + 计数器”作为 Full 的软件后备，mainline 完全依赖 gauge/charger 硬件标志；在 suspend 或调度抖动时，当前实现的 streak 会被清掉，导致 Full 进入变慢或永远不进入。
- 当前实现的 `hardware_full` 条件是 `(status & 0x0c) == 0x0c && current_qualifies`；mainline 的 bq27xxx FC 不附加 ±110 mA 条件，且 `CHG_STAT=3` 本身已经是硬件终止。
- 当前实现 Full 后仍保留输入转换器（`sm_apply_charge_hold()`），mainline 通常让 charger 进入 `NOT_CHARGING` 但保持输入路径；这点方向一致，但当前实现会在每次 poll 重新验证并可能 `sm_stop()`，mainline 不会。

**日用工况风险**
- 高：suspend 后 `last_seen` 间隔 >10 s 清 streak，若系统频繁短睡，Full 永远到不了；用户看到“充到 99% 一直不 Full”。
- 中高：`recharge_count > 5` 要求连续 6 个 5 秒 tick 都低于阈值，且中间不能有 `recharge_forbidden`；热降额/屏幕亮起导致电压抖动时会反复清零，表现为“Full 后不再充”。

**建议补丁**
- `oem-full-cycle.h:sm_oem_full_step()`：把 `sm_oem_full_clear_streak()` 的 suspend 间隔从“>=2 tick 清空”改为“保留已确认的 Full 事实，只清未完成的 streak”；已 Full 的状态不应因一次 suspend 被清掉。
- `oem-full-cycle.h`：把 `recharge_count > 5` 改为 `>= 2` 或由 DT 配置，且允许 `FC` 位直接触发 recharge；同时不要用 `recharge_forbidden` 清掉已累计计数，除非是硬 fault。
- `samurai-mp2650.c:sm_battery_status_locked()`：当前 override 只写 `Full`，但 `bq27xxx` 的 `STATUS` 还会读 `CHGS`；应确保 override 同时覆盖 `FULL`/`NOT_CHARGING`，避免 UPower 在 Full hold 时仍显示 Charging。

**可安全移植性**
- 可安全移植：bq27xxx 的 `FC`/`CHGS`/`DSC` 优先级、`STATUS_FULL` 映射；`POWER_SUPPLY_PROP_CHARGE_BEHAVIOUR` 只做 auto/inhibit。
- 不应直接移植：把 `qcom_smbx` 的 recharge 寄存器序列复制到 MP2650；MP2650 的 recharge 是 `REG04` bit0 + CV 阈值，和 SMB2/SMB5 的 `AUTO_RECHG_BIT`/`VBT_LT_CHG_RECHARGE_THRESH_SEL_BIT` 不同。

### 4. 输入预算

**当前实现**
- `samurai-usb-input.c` 从 PM8150B 的 `0x1307/0x1308/0x1310/0x1506/0x1509/0x150b/0x150d` 读 APSD/CC/attached/legacy，`samurai_usb_decode()` 给出 `kind` 和 `current_ua`；`CURRENT_MAX` 返回 `budget.current_ua`，`INPUT_CURRENT_LIMIT` 返回 `udc_current_ua`（DWC3 软件设置的限流）。
- `samurai_usb_get_budget()` 每次读两遍 status，不完全相等就 `-EAGAIN`；`samurai_usb_poll()` 每秒轮询，变化才 `power_supply_changed()`。
- `sm_input_budget()` 优先读 `typec-supply` 的 `ONLINE`/`USB_TYPE`/`CURRENT_NOW`/`CURRENT_MAX`/`VOLTAGE_NOW`，再读一次并要求 `sm_input_allowance_equal()`；没有 typec 时退回 `input->CURRENT_MAX`。
- `sm_policy_with_band_reason()` 的 `out->input_ua = min(budget, input_cap, SM_OEM_INPUT_MAX_UA)` 并对齐 50 mA；`sm_apply()` 会同时写 `0x00` 和 `0x0f` 两个输入限流寄存器。

**mainline/开源做法**
- `tcpm.c` 的 `tcpm_pd_set_state()`/`tcpm_register_port()` 在 PD 合同变化时更新 `CURRENT_MAX`/`VOLTAGE_NOW`，`usb power supply` 的 `CURRENT_MAX` 是合同上限；`INPUT_CURRENT_LIMIT` 是 charger 自己的软件限流，通常由 `power_supply_set_property()` 设置。
- `qcom_smbx.c` 并没有 `INPUT_CURRENT_LIMIT` 属性；它把 `CURRENT_MAX` 映射到 `USBIN` 限流寄存器，`CURRENT_NOW` 是 IIO ADC 的输入电流。`smb_get_current_limit()`/`smb_set_current_limit()` 只处理一个合同上限，不要求两次采样一致。
- mainline 的 `power_supply` 核心在 supplier 变化时通过 `power_supply_changed()` 通知消费者，消费者可以接受 `-EAGAIN` 并延迟重试；不会把“两次读取不一致”当成永久错误。

**实质差异**
- 当前实现把 `CURRENT_NOW` 当作 TCPM 的“operating_ua”，但 `CURRENT_NOW` 在 mainline 的 `tcpm` 里通常是“当前实际电流/合同电流”，不是“允许的最大电流”；把 `CURRENT_NOW` 和 `CURRENT_MAX` 同时读并比较，会把正常的合同更新当成不一致。
- `samurai_usb_input` 的 `CURRENT_MAX` 是 APSD 结果的静态预算，不随 PD 合同更新；如果同时存在 TCPM，`sm_input_budget()` 优先 TCPM，但 `samurai_usb_input` 仍会以 1 秒轮询向 DWC3 提供 `INPUT_CURRENT_LIMIT`，两套预算可能打架。
- `sm_apply()` 同时写 `0x00` 和 `0x0f`；如果这两个寄存器在 MP2650 上分别代表“输入限流”和“输入电流检测阈值/第二限制”，同时写同一个值可能不是 OEM 的行为，需要按原厂寄存器定义确认。

**日用工况风险**
- 高：PD/NCM 重新协商时 `CURRENT_MAX` 变化，`sm_input_budget()` 返回 `-EAGAIN`，`sm_step_locked()` 进入 `source_inhibit`，`sm_collect()` 不产生有效 sample；用户看到“插着 PD 充电器但充电图标闪断”。
- 中高：`samurai_usb_input` 的 1 秒轮询与 `samurai-mp2650` 的 1 秒轮询不同步，`INPUT_CURRENT_LIMIT` 可能在 DWC3 设置后又被旧 APSD 结果覆盖。

**建议补丁**
- `samurai-mp2650.c:sm_read_typec_allowance()`/`sm_input_allowance_equal()`：只比较 `ONLINE`/`USB_TYPE`/`CURRENT_MAX`/`VOLTAGE_NOW`，不要比较 `CURRENT_NOW`；`CURRENT_NOW` 只作为诊断。
- `samurai-usb-input.c:samurai_usb_get_budget()`：把两次 `samurai_usb_read_status()` 的一致性检查改为“单次快照 + 时间戳”，或在 `-EAGAIN` 时保留上一次有效预算并标记 stale，而不是让消费者立刻 inhibit。
- `mp2650-core.h:sm_apply()`：确认 `0x00`/`0x0f` 的 OEM 语义；如果 `0x0f` 是输入电流监测阈值而非第二限流，不应每次写入相同值，应只写 `0x00` 并按 OEM 初始化设置 `0x0f`。

**可安全移植性**
- 可安全移植：`CURRENT_MAX` 与 `INPUT_CURRENT_LIMIT` 分离、`power_supply_changed()` 通知、`-EAGAIN` 只延迟不 latch。
- 不应直接移植：把 `tcpm` 的 PD 合同状态机搬进 MP2650；MP2650 没有 PD 角色，PD 应由 TCPM 负责，charger 只消费预算。

### 5. 温控

**当前实现**
- `thermal-bands.h` 复刻 OEM `oplus_charger.c` 的 `pre_shake`/动态边界：`sm_thermal_gate()` 在温度跨越 band 时调整 `bounds[]`，绝对 `< -2 C` 或 `>= 53 C` 直接 hold。
- `sm_oem_bands` 是 OEM 19781 的 6 段 profile；`sm_policy_with_band_reason()` 用 `sm_oem_bands` 的 `cell_target_uv`/`current_ua`/`cell_ovp_uv`，温度不在任何 band 时 `-ERANGE`。
- `sm_full_bands` 单独用 `sw_uv`/`oem_cv_uv`/`recharge_drop_uv` 做 Full/recharge 阈值。

**mainline/开源做法**
- `qcom_battmgr.c` 通过 `POWER_SUPPLY_PROP_TEMP`/`HEALTH`/`CHARGE_TYPE` 和电池管理固件（ADSP/PMIC）做温控；`qcom_smbx.c` 的 `smb_get_prop_health()` 把 `BAT_TEMP_STATUS_*` 翻译为 `COLD`/`COOL`/`WARM`/`OVERHEAT`，具体阈值由 PMIC 配置/DT 给出。
- bq27xxx 只报告 `TEMP`/`HEALTH`，不负责充电电流降额；mainline 的 `thermal` 框架通过 `thermal_zone`/`cooling_device` 让 charger 降额，而不是在 charger 驱动里硬编码 6 段。
- `tcpm` 的 `TEMP` 只用于端口保护，不参与电池充电 profile。

**实质差异**
- 当前实现把 OEM 的 `pre_shake` 动态边界完整搬进内核，逻辑复杂且依赖“状态变化时更新”的历史；mainline 更倾向 DT 静态阈值 + thermal zone，避免驱动内隐式状态。
- 当前实现同时维护 `sm_oem_bands` 和 `sm_full_bands` 两套温度阈值，可能出现“policy 允许充电但 Full 判定用另一套 band”的不一致。
- 当前实现没有注册 `thermal_zone`/`cooling_device`，用户空间无法通过标准 thermal 接口观察/干预；mainline 的 qcom battmgr 会暴露温度/健康状态。

**日用工况风险**
- 中高：`pre_shake` 历史在 suspend/resume 后未重置（`sm_resume()` 只清 `notified_valid`，不清 `thermal`），恢复后可能沿用 suspend 前的动态边界，导致温度恢复后仍 hold 或过早恢复。
- 中：`sm_oem_bands` 与 `sm_full_bands` 的边界不一致时，可能出现“充电已停但 Full 仍 hold”或反之。

**建议补丁**
- `samurai-mp2650.c:sm_resume()`：明确是否重置 `c->thermal`；如果 OEM 要求在 resume 后重新初始化 band，调用 `sm_thermal_init()` 或至少清 `pre_shake`。
- `thermal-bands.h`：把 `sm_thermal_gate()` 的 `pre_shake` 逻辑改成无历史滞回的静态 band + 2 C hysteresis，降低 suspend/恢复后的状态不确定性。
- `mp2650-core.h`：把 `sm_oem_bands` 与 `sm_full_bands` 合并为一份 DT 可配置的 profile，避免两套阈值漂移。

**可安全移植性**
- 可安全移植：绝对 `< -2 C`/`>= 53 C` 的硬停止、`POWER_SUPPLY_HEALTH_OVERHEAT`/`COLD` 映射。
- 不应直接移植：把 OEM `pre_shake` 动态边界当成 mainline 标准；它是 OEM 私有行为，且缺少完整的状态机文档。

### 6. suspend/resume

**当前实现**
- r8 快照的 `sm_suspend()`：`paused=true` → `cancel_delayed_work_sync()` → `sm_clear_full_status_locked()` → 若 `control` 则 `sm_stop()`；失败时 `latched=true`、`paused=false`、立即重排 work，并返回错误。
- 更新后的 `charging-integration-20261026-01` 已改为 `sm_suspend_needs_stop()`：仅当 `!auto_requested`、`latched`、`last_error`、`stop_error`、`source_inhibit`、sample 无效/离源/保护不良、fault、timeout 或 `!target.enable` 时才 stop；正常 active 充电保持硬件自主。这个方向与 mainline 一致。
- `sm_resume()`：`paused=false`、`notified_valid=false`、立即 `mod_delayed_work(...,0)`；没有重新采样 charger/gauge 的同步步骤。
- `samurai_usb_suspend()`：清 wake → stop → arm wake；`samurai_usb_resume()`：clear wake + restart work。

**mainline/开源做法**
- `qcom_smbx.c` 没有注册 `dev_pm_ops`；它只用 `devm_pm_set_wake_irq()` 把 `usb-plugin` IRQ 设为唤醒源，充电状态由 PMIC/硬件维持。这个结构本身就说明“suspend 不写停充位”是 mainline 的默认取向。
- `bq27xxx_battery.c` 的 `bq27xxx_battery_suspend()` 只取消 delayed work/标记 suspended，resume 时重新调度；不改变 gauge 配置。
- `tcpm` 在 suspend 时可能进入低功耗，但保持合同/端口状态；resume 后重新读取 CC/PD 状态。

**实质差异**
- 当前实现的 `sm_stop()` 在 suspend 中会写 `REG08` 清 CHG_EN 和输入转换器；mainline 的 charger 驱动不会因为系统 suspend 就停充。这是最直接的日用工况差异。
- 当前实现 suspend 失败会 latch 并立即重排 work，可能在 suspend 回调中触发 I2C 访问；mainline 通常返回错误让 PM 核心处理，不在 suspend 回调里重排工作。
- 当前实现 resume 立即排 work，但没有 `pm_runtime_get_sync()`/regmap cache sync/IRQ 重新使能；如果 I2C 控制器在 resume 早期不可用，第一次采样会失败并 latch。

**日用工况风险**
- r8 快照极高：插电睡眠时 `sm_stop()` 停充，早上电量不增；如果用户依赖夜间充电，这是阻断日用的第一问题。
- 最新候选已消除 active 充电的 suspend 停充，但仍需保证 `target.enable` 在 Full hold 时被正确置 0；否则 Full 后睡眠可能继续以 hold 状态保留输入，行为需要实测。
- 高：resume 后第一次 I2C 失败 → `last_error` + `latched`，用户看到“睡醒后不充电”。

**建议补丁**
- r8 快照 `samurai-mp2650.c:sm_suspend()`：按最新候选的 `sm_suspend_needs_stop()` 方式，**不要**在正常 suspend 中调用 `sm_stop()`；只有 `!auto_requested`、`latched`、`thermal hold`、`cycle.timed_out` 或显式 `control` 的“安全停止”策略才停。正常充电应保持 CHG_EN。
- `samurai-mp2650.c:sm_resume()`：先 `pm_runtime_get_sync(c->client->dev.parent)`（或确保 I2C 可用），再重排 work；第一次采样失败只标记 `source_inhibit`，不要 latch。
- `samurai-mp2650.c:sm_suspend()` 失败路径：不要在 suspend 回调中 `mod_delayed_work()`；返回错误，让 PM 核心决定 abort/resume。

**可安全移植性**
- 可安全移植：`bq27xxx` 的“suspend 只停 work、不改 gauge 配置”模式；`tcpm` 的“resume 重新读 CC/PD”模式。
- 不应直接移植：`qcom_smbx` 的 suspend 寄存器序列；MP2650 的 `REG08` 位定义不同，且当前实现已经证明会停充。

### 7. 错误恢复

**当前实现**
- `sm_sample_latch()`：`latched || fault || (error && !source_inhibit)`；即除 source 变化外的任何错误都 latch。
- `sm_set_property(AUTO)` 清 latch；物理 detach 清 latch/thermal/full；`sm_probe()` 初始 `last_error=-ENODATA`。
- `sm_cleanup()`/`sm_shutdown()` 在 `control` 时 `sm_stop()`；失败只打日志。
- `sm_notification_locked()` 把任何 `last_error`/`latched`/`stop_error` 映射为 `HEALTH_UNSPEC_FAILURE`。

**mainline/开源做法**
- `bq27xxx` 的 `bq27xxx_battery_update()` 在 I2C 错误时保留上次 cache 并返回错误，不把整个 gauge 永久 latch；`bq27xxx_battery_get_property()` 可以返回 `-ENODATA` 让上层重试。
- `qcom_smbx.c` 的 `get_property` 失败通常返回 `-EINVAL`/`-ENODATA`，由 `power_supply` 核心/用户空间重试；不会因为一次 I2C 错误停止充电。
- `tcpm` 的错误恢复通过 `tcpm_reset()`/`tcpm_pd_hard_reset()` 和 state machine 重试，不是永久 latched。

**实质差异**
- 当前实现的错误恢复只有“拔插/显式 AUTO/重新 probe”，没有自动重试或退避；mainline 的 charger/gauge 驱动通常有 retry/backoff、IRQ 重新使能、regmap cache 恢复。
- 当前实现把 `-EAGAIN` 也视为 latch（除非 `source_inhibit`），但 `sm_collect()` 在 TCPM 预算变化时正是返回 `-EAGAIN`；这会把正常协商误判为故障。
- 当前实现的 `sm_notification_locked()` 每次 poll 都读 `0x13` 和 battery status，I2C 错误会直接 `state.charger_error`，但不会触发恢复流程。

**日用工况风险**
- 高：一次 I2C 超时 → latch → 必须用户拔插/显式 AUTO；mainline 会自动重试。
- 中高：`-EAGAIN` 在 PD 协商时 latch，用户看到“PD 充电器插着但一直不充”。

**建议补丁**
- `mp2650-core.h:sm_sample_latch()`：区分 `-EAGAIN`/`-ENODATA`（瞬态）与 `-EIO`/`-ERANGE`（硬错误）；瞬态只 inhibit，不 latch。
- `samurai-mp2650.c:sm_step_locked()`：增加指数退避重试（1s→2s→4s，上限 30s），连续 N 次失败才 latch；成功一次清 `last_error`。
- `samurai-mp2650.c:sm_notification_locked()`：不要把 `last_error` 直接映射为 `HEALTH_UNSPEC_FAILURE`；瞬态错误应保持 `HEALTH_GOOD` 或 `HEALTH_UNKNOWN`，避免 UPower 弹“电池故障”。

**可安全移植性**
- 可安全移植：bq27xxx 的“cache + 返回错误 + 上层重试”、tcpm 的 state machine reset。
- 不应直接移植：把 `qcom_battmgr` 的 ADSP 错误恢复整套搬进 MP2650；MP2650 没有 ADSP 通道。

## 按日用工况风险排序

| 优先级 | 风险 | 触发条件 | 用户感知 | 代码位置 | 建议 |
|---|---|---|---|---|---|
| P0 | PD/NCM 预算抖动导致 inhibit/latch | PD 重新协商、NCM 枚举 | 充电图标闪断/不充 | `samurai-mp2650.c:201-216`、`488-505`、`negotiated-input.h:13-18` | 只比较 `CURRENT_MAX`，`CURRENT_NOW` 不参与相等判断 |
| P1 | `CURRENT_NOW` 语义混用 | UPower/用户空间读 `mp2650-input/current_now` | 电量/功率方向错误 | `samurai-mp2650.c:565-576` | charger psy 返回电池净电流或改名 |
| P2 | Full/recharge 计数受 suspend/抖动影响 | 夜间充电、短睡、热降额 | 长期 99% 不 Full / Full 后不再充 | `oem-full-cycle.h:110-245` | suspend 保留已确认 Full；降低 recharge 计数门槛 |
| P3 | 温控 band 历史跨 suspend | 温度变化后睡眠 | 恢复后仍 hold/过早恢复 | `thermal-bands.h:31-71`、`samurai-mp2650.c:942-953` | resume 重置 `pre_shake` 或改静态 band |
| P4 | 错误恢复只靠拔插 | I2C 瞬时错误 | 不充，需拔插/重启 | `mp2650-core.h:38-41` | 瞬态错误不 latch，增加退避重试 |

## 可安全移植 / 不应移植

### 可安全移植
- `bq27xxx` 的 `CURRENT_NOW`/`CURRENT_AVG` 语义、`FC`/`CHGS`/`DSC` 状态映射。
- `tcpm` 的 `CURRENT_MAX`（合同）与 `INPUT_CURRENT_LIMIT`（软件限流）分离。
- `power_supply` 的 `power_supply_changed()` 通知、`-EAGAIN` 延迟重试、suspend 只停 work 不改配置。
- `sm_apply()` 的写后读回、`sm_apply_charge_hold()` 的先清 CHG_EN。
- OEM 绝对温度 `< -2 C`/`>= 53 C` 硬停止。
- `sm_sample_latch()` 的“source inhibit 不等于电气 fault”原则。

### 不应移植
- `qcom_smbx` 的 SMB5 `CHARGE_TYPE`/`RECHARGE_THRESHOLD`/`OTG` 寄存器序列：MP2650 寄存器不同，直接写会破坏输入/OTG/BATFET。
- `qcom_battmgr` 的 ADSP/PMIC 固件充电参数接口：MP2650 没有该通道，且当前 DT 没有对应 firmware 节点。
- `bq27xxx` 的 `BQ27XXX_DT_UPDATES_NVM`/DM 写路径：当前 `sm_probe()` 明确拒绝 `CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM`，不应打开。
- OEM `pre_shake` 动态边界作为 mainline 通用策略：缺少文档，且 suspend 后状态不确定；应改为 DT 静态 profile。
- `samurai_usb_input` 的 1 秒 APSD 轮询作为 PD 预算唯一来源：PD 合同应由 TCPM 提供，APSD 只做 BC1.2 后备。

## 具体建议补丁（按优先级）

### Patch 1（P0）：只比较 `CURRENT_MAX`，不比较 `CURRENT_NOW`
文件：`samurai-mp2650.c`
函数：`sm_read_typec_allowance()` / `sm_input_allowance_equal()`

```c
static int sm_read_typec_allowance(struct power_supply *psy,
				   struct sm_input_allowance *a)
{
	int ret;

	*a = (struct sm_input_allowance){ 0 };
	ret = sm_psy_int(psy, POWER_SUPPLY_PROP_ONLINE, &a->online);
	if (ret) return ret;
	if (!a->online) return -ENODATA;
	ret = sm_psy_int(psy, POWER_SUPPLY_PROP_USB_TYPE, &a->usb_type);
	if (ret) return ret;
	/* CURRENT_NOW is diagnostic only; never gate a contract on it. */
	(void)sm_psy_int(psy, POWER_SUPPLY_PROP_CURRENT_NOW, &a->operating_ua);
	ret = sm_psy_int(psy, POWER_SUPPLY_PROP_CURRENT_MAX, &a->maximum_ua);
	if (ret) return ret;
	return sm_psy_int(psy, POWER_SUPPLY_PROP_VOLTAGE_NOW, &a->voltage_uv);
}
```

并把 `negotiated-input.h:sm_input_allowance_equal()` 改为只比较 `online/usb_type/maximum_ua/voltage_uv`（不比较 `operating_ua`）。

### Patch 2（P2）：已确认 Full 不因 suspend 被清空
文件：`oem-full-cycle.h`
函数：`sm_oem_full_step()`

```c
if (s->have_seen && now - s->last_seen_ns >= 2 * SM_FULL_TICK_NS) {
	if (!s->full)
		sm_oem_full_clear_streak(s);
	/* s->full is a confirmed hardware fact; keep it across suspend. */
}
```

并把 `if (s->recharge_count > 5)` 改为 `if (s->recharge_count >= 2)`（或由 DT 提供 `recharge_samples`）。

### Patch 3（P1）：`CURRENT_NOW` 返回电池净电流
文件：`samurai-mp2650.c`
函数：`sm_get_property()`

```c
case POWER_SUPPLY_PROP_CURRENT_NOW:
	/* Battery net current, not the input ADC. */
	if (!c->sample.valid) { ret = -ENODATA; break; }
	v->intval = c->sample.gauge_current_ua;
	break;
```

如果用户空间依赖输入 ADC，新增 `POWER_SUPPLY_PROP_INPUT_CURRENT_NOW` 或单独 exporter，不要复用 `CURRENT_NOW`。

### Patch 4（P3/P4）：瞬态错误不 latch + resume 重置 thermal
文件：`mp2650-core.h`、`samurai-mp2650.c`

```c
static inline int sm_sample_latch(int latched, int error, int source_inhibit, int fault)
{
	if (error == -EAGAIN || error == -ENODATA)
		return latched || fault;
	return latched || fault || (error && !source_inhibit);
}
```

`sm_resume()` 中增加：

```c
c->thermal = (struct sm_thermal_state){ 0 };
```

## 证据边界

- 本报告只读检查了源码，没有在设备上重新刷入、重启、插拔或改变构建。
- `qcom_smbx.c` 是 WSL 内 7.3.0-rc6 的 QCOM SMB2/SMBx 驱动（PMI8998/PM660），当前手机使用 MP2650 + bq28z610，不能把它的实现当作可直接替换的“主线驱动”；只把它作为 mainline 状态机/属性语义的参照。
- `bq27xxx_status_override` 是本地补丁，不是 mainline ABI；`bq27xxx_battery_set_status_override()` 的调用需要内核 Image 导出符号，模块单独更新不可行。当前 r15 只评估语义，不改变该 ABI。
- 行号基于 2026-10-27 的 `reference/charging-session-20261023/r8-source-integration/kernel-sources` 快照；如果后续源码移动，以函数名为准。
