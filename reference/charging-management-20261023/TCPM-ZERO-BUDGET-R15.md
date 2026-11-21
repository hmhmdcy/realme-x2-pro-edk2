# R15 TCPM current_limit=0 根因与最小修复建议

范围：只读核对 R15 实际状态、`charging-integration-20261026-01` 的 `tcpm.c`、`qcom_pmic_typec.c`、`qcom_pmic_typec_5v.c`、`qcom_pmic_typec_port.c`、`qcom_pmic_typec_apsd.c`，以及 `samurai-usb-input` / DWC3 的预算发布链。未改源码、未刷机、未访问设备。

## 先给结论

`current_limit=0` **不是 Type-C/PD 合同消失，也不是 PM8150B 寄存器解码失败**。证据链正好落在 SDP 的“UDC 预算尚未发布”分支：

1. `tcpm.c:tcpm_psy_get_current_max()` 与 `tcpm_psy_get_current_now()` 都返回 `port->current_limit * 1000`；所以 `0/0` 只说明同一个 `port->current_limit` 是 0。
2. `tcpm_get_current_limit()` 在 `CC == TYPEC_CC_RP_DEF` 时调用 `tcpc->get_current_limit`，也就是 `qcom_pmic_typec_port_get_current_limit()`。
3. 后者读 `samurai-usb-input` 的 `POWER_SUPPLY_PROP_CURRENT_MAX`；只有当该值为正时才返回 `value / 1000`，否则直接返回 0。
4. `samurai-usb-input` 对 `1307=0x11, 1308=0x01, 1310=0x10, 1506=0x08, 1509=0x23, 150b=0x29, 150d=0x06` 解码为 **SDP**（`result=0x01`、`apsd bit0=1`、`cc=0x08`、`legacy=0x06`）。SDP 分支只设 `kind`，**不设 `current_ua`**，继续依赖 `samurai_usb_apply_udc()` 把 DWC3 的 `INPUT_CURRENT_LIMIT` 填进去。
5. DWC3 在系统 suspend 前 `dwc3_vbus_budget_close()` 把 `udc_valid=false` 并写 0；resume 时 `dwc3_vbus_budget_open()` 只清 `vbus_draw_blocked`，明确不重发旧许可。若 resume 后没有新的 `SET_CONFIGURATION`/gadget resume/角色事件，`udc_valid` 保持 false。
6. 因此 `samurai_usb_get_property(CURRENT_MAX)` 返回 `budget.current_ua = -ENODATA`，`qcom_pmic_typec_port_get_current_limit()` 返回 0，TCPM 两个属性就是 0/0。

这与 R15 验收时 `1500000` 并不矛盾：当时 Type-C 解码走了 `cc==4/2` 的 Type-C 配件分支并直接给 1.5 A；现在这组稳定寄存器是 `cc=0x08`，走 SDP，**Type-C 在线但预算由 DWC3 决定**。SDP 是 USB2 设备，不能从 `cc=0x08` 推出 1.5 A。

补充：`tcpm_psy_get_online()` 当前代码把 `TCPM_PSY_FIXED_ONLINE`（数值 1）、`TCPM_PSY_PPS_ONLINE`（2）、`TCPM_PSY_SPR_AVS_ONLINE`（3）都作为非 0 online 返回。你给出的 `online=1` 与 5V/Type-C 固定合同一致，不能据此证明 PPS/AVS；但 `qcom_pmic_typec_samurai_fixed_5v()` 仍要求 DT 中 `sink-pdos=<PDO_FIXED(5000,500,...)>`、`op-sink-microwatt=2500000`、无 `source-pdos`。这条 DT 约束是防止把 1.5 A 写进 5V/500 mA PDO 的关键，不能为了修 0 预算而放宽。

## 寄存器解码核对

`samurai-usb-input-decode.h:samurai_usb_decode()` 的判定：

- `plugin = !!(0x1509 & 0x10) = 1`
- `vbus = !!(0x150b & 0x20) = 1`
- `attached = !!(0x150b & 0x01) = 1`
- `state_attached = !!(0x1506 & 0x20) = 1`
- `cc = 0x150d & 0x7f = 8`
- `legacy = 0x150b = 0x29`，`legacy & 2 = 0`，但 `legacy & 1 = 1`，不满足 Type-C 配件分支
- `apsd = 0x11`，`apsd & 1 = 1`；`result = 0x10 & 0x7f = 0x10`？注意这里实际 `1308=0x01`，所以 `result = 0x01`，不是 FLOAT 的 `0x10`
- 最终进入 `switch (result)` 的 `case 1: SAMURAI_USB_SDP`

结论：`online=1/usb_type=SDP/current_ua` 未赋值，必须依赖 UDC。`samurai_usb_apply_udc()` 只接受 `kind == SDP || FLOAT`，并在 `valid=false` 时把 `current_ua` 设为 `-ENODATA`。

## 为什么会停在这个状态

### 1. suspend/resume 的预算撤销

`drivers/usb/dwc3/core.c`：

- `dwc3_vbus_budget_close()`：`vbus_draw_blocked=true`、`current_limit=DWC3_CURRENT_UNSPECIFIED`，取消 `vbus_draw_work`，然后向 `samurai-usb-input` 写 `INPUT_CURRENT_LIMIT=0`。
- `dwc3_vbus_budget_open()`：只把 `current_limit` 设为 `UNSPECIFIED`，`vbus_draw_blocked=false`，**不重新发布旧值**。
- `dwc3_gadget_vbus_draw()`：只有 gadget 驱动主动调用 `usb_gadget_vbus_draw()` 时才会更新；`composite_resume()` 在 `cdev->config` 存在时会给 `maxpower`（通常 500 mA），但 R15 状态显示这个回调没有在这个连接/恢复周期完成，或者 `vbus_draw_blocked` 期间被 `-EBUSY` 吃掉。
- 若 resume 后 USB 栈没有重新 `SET_CONFIGURATION`，`udc_valid` 保持 false，`CURRENT_MAX` 永久 `ENODATA`。

### 2. `samurai-usb-input` 的保守设计

这是有意设计，不是漏写：

```c
/* A detection result is an advertised allowance, never a current measurement.
 * SDP requires the UDC's configured/suspended budget, so leave it unavailable.
 */
```

问题在于：**“未配置”与“已配置但 suspend 后未重发”被视为同一种状态**。前者应当 100 mA/ENODATA，后者应当恢复 500 mA（或至少不把整个充电预算降为 0）。这是 R15 日用工况失败的关键语义漏洞。

### 3. TCPM 的 0 不是独立的“无合同”

`tcpm_psy_get_online()` 依据 `vbus_charge`，当前 `online=1`；`tcpm_psy_get_voltage_now()` 返回 `supply_voltage=5000000`，说明 TCPM 已经处在 5V sink 状态。`current_limit=0` 只是 `get_current_limit()` 返回 0，不是 Type-C attach 失败。

### 4. `qcom_pmic_typec_5v.c` 不是主因

该文件负责 5V-only/PD5V 的离线和 lease 路径；R15 的 TCPM checklist 仍是完整 `qcom_pmic_typec` + APSD handoff，不是 `pd5v-only` 分支。`5v` 代码不会直接写 `port->current_limit`；它只在 profile 选择/APSD handoff 时参与。当前 `online=1/5V` 已经证明 Type-C port 侧工作，问题在预算 provider，不在 5V profile。

### 5. APSD handoff 不是主因

`qcom_pmic_typec_apsd.c` 的 `apsd_read_sink()` 只在 TCPM probe 前检查 `0x1307/0x1308/.../0x1362`，确认 SDP/5V 后清 `APSD_ENABLE` 和 `APSD_START_ON_CC`。它不设置 `current_limit`，也不会在每次 resume 重新运行（`apsd_verify()` 只读隔离位）。所以 APSD handoff 成功/失败不会直接造成 `current_limit=0`；但它会决定 `samurai-usb-input` 是否能稳定读到 SDP 寄存器。

## 最小修复方案

### 方案 A（推荐，供应商驱动最小改动）

在 `samurai-usb-input-decode.h:samurai_usb_decode()` 中，给 SDP 一个**保守的固定 500 mA 上限**，但仍让 DWC3 的 `INPUT_CURRENT_LIMIT` 细化：

```c
case 1:
	b->kind = SAMURAI_USB_SDP;
	/*
	 * A fixed 5V SDP may draw 500mA only after configuration. Use 500mA
	 * as the board-safe ceiling; DWC3 may lower it to 100mA before
	 * SET_CONFIGURATION and raise it after enumeration.
	 */
	b->current_ua = 500000;
	break;
```

并修改 `samurai_usb_apply_udc()`，让 DWC3 的 valid=false 不再把 SDP 清成 `ENODATA`：

```c
static inline int samurai_usb_apply_udc(struct samurai_usb_budget *b,
				       int valid, int current_ua)
{
	if ((b->kind != SAMURAI_USB_SDP && b->kind != SAMURAI_USB_FLOAT) ||
	    !b->online) return 0;
	if (!valid || current_ua < 0 || current_ua > 500000) {
		/*
		 * Keep the board-safe SDP ceiling while the UDC budget is
		 * unavailable. Never turn a confirmed SDP into zero budget.
		 */
		if (b->kind == SAMURAI_USB_SDP && current_ua < 0)
			b->current_ua = 500000;
		else
			b->current_ua = -ENODATA;
		return 0;
	}
	if (b->kind == SAMURAI_USB_FLOAT)
		b->kind = SAMURAI_USB_SDP;
	b->current_ua = current_ua;
	return 0;
}
```

这会让：

- 正常未配置时：DWC3 写 100 mA（`composite_reset()`/`set_config()` 的 `power=100`），`current_ua=100000`。
- 已配置时：DWC3 写 500 mA，`current_ua=500000`。
- suspend 后 resume 未重发：`valid=false` 但 SDP 已确认，保留 500 mA 上限，不再 `ENODATA`。
- DCP/QC 等非 SDP 不享受该兜底，保持原来的拒绝/0，避免误升到 1.5 A。

注意：不要在 `composite_reset()` 的 100 mA“未配置”阶段把 SDP 直接当作可配置 500 mA。`composite_reset()` 的本意就是未配置 SDP 只允许 100 mA；因此上面的 500 mA 只作为 `CURRENT_MAX` 的**板级安全上限**，真正的 `INPUT_CURRENT_LIMIT` 仍由 DWC3 的 100/500 mA 状态覆盖。若要让 TCPM 在“未配置”时也显示 100 mA，应让 DWC3 明确发布 100000，而不是 provider 猜。

### 方案 B（更小，仅 provider）

如果不想动 decode header，只改 `samurai_usb_get_property(CURRENT_MAX)`：

```c
case POWER_SUPPLY_PROP_CURRENT_MAX:
	if (budget.current_ua < 0 &&
	    budget.online && budget.kind == SAMURAI_USB_SDP)
		value->intval = 500000;
	else if (budget.current_ua < 0)
		return budget.current_ua;
	else
		value->intval = budget.current_ua;
	return 0;
```

优点：改动一行分支；缺点：`CURRENT_MAX` 和 `INPUT_CURRENT_LIMIT` 的语义会短暂不一致（DWC3 尚未配置时 `CURRENT_MAX` 已 500 mA），但 TCPM 只需要一个安全上限，且不会写 MP2650 的 900 mA。

### 方案 C（仅当 A/B 因符号/模块生命周期不可行时）

在 `qcom_pmic_typec_port_get_current_limit()` 中，当 provider 返回 `ENODATA` 且 `usb_type == SDP` 时返回 500：

```c
ret = power_supply_get_property(psy, POWER_SUPPLY_PROP_USB_TYPE, &type);
if ((!ret && type.intval == POWER_SUPPLY_USB_TYPE_SDP))
	return 500;
```

这是最接近“立即恢复”的补丁，但把板级 SDP 默认值放进了通用 QCOM Type-C 驱动，其他板子/其他供应商可能被误套；只应作为 A/B 失败后的保守回退。该方案还必须同时要求 `usb_type == POWER_SUPPLY_USB_TYPE_SDP` 和 `online==1`，不能只按 `ENODATA` 兜底。

## 为什么优先不重启

`current_limit` 是 TCPM 的软件状态；硬件 5V 已在线，`voltage_now=5000000`。只要让 `samurai-usb-input` 的 `CURRENT_MAX` 从 `ENODATA` 变为 500000，TCPM 的 `tcpm_psy_external_power_changed()` 会在 `SNK_READY`、`RP_DEF`、`!pd_capable`、`!explicit_contract` 条件下重新调用 `tcpm_set_current_limit()`，把 `current_limit` 从 0 改成 500。无需重启，也无需重新插拔。

但要注意：`tcpm_psy_external_power_changed()` 只接受 `CC == TYPEC_CC_RP_DEF`。若当前 CC 被读成 `RP_1_5`/`RP_3_0`，这条自动刷新不会生效；此时应先确认 `qcom_pmic_typec_port_get_cc()` 的 `SNK_RP_STD/1P5/3P0` 解码，而不是直接改 `tcpm.c`。R15 的 `cc=0x08` 是 PM8150B 的 `DETECTED_SNK_TYPE_MASK` 原始值，不等于 `TYPEC_CC_RP_DEF`；两者不能混为一谈。

还有一个必要条件：`tcpm_psy_external_power_changed()` 只有在 provider 的 `power-supply` 关系被 core 识别时才会被调用。`samurai-usb-input` 不是 TCPM psy 的 supplier，`samurai-measured-vbus.dtsi` 的 `power-supplies = <&samurai_usb_input>` 只挂在 Type-C controller 节点上，不是挂在 TCPM psy 的 fwnode 上。因此不能只依赖 provider 的 `power_supply_changed()` 自动回调 TCPM；必须在 `qcom_pmic_typec_port` 的 `get_current_limit` 调用路径之外，增加一个明确的“预算已变化”通知点，或在 `tcpm.c` 的 `tcpm_psy_get_current_max()` 里按 `cc==RP_DEF` 主动重读。更稳妥的最小做法是方案 A/B 让 `CURRENT_MAX` 永不为 `ENODATA`，然后由 TCPM 下一次 `get_current_limit()`（例如 `SNK_READY` 状态或 `tcpm_psy_get_*` 读取）拿到 500 mA；但如果现场 TCPM 不会自动重读，就需要一次受控的 `tcpm` 端口重绑定，而不是依赖不存在的 supplier 关系。

触发方式：

1. 若使用方案 A/B 的新模块，加载/重绑 `samurai-usb-input` 后，下一次 `power_supply_changed()` 或 1 秒 poll 会更新 `CURRENT_MAX`；
2. 由于当前 DT 没有把 `samurai-usb-input` 声明为 TCPM psy 的 `power-supplies` supplier，`tcpm_psy_external_power_changed()` 不会被 provider 通知自动触发；不要把这当作已保证的刷新路径；
3. 如果 TCPM 已错过通知，只能在只读确认 `SNK_READY` 后，通过一次受控的 `tcpm` 端口重绑定/模块 reload 重新执行 `SNK_DISCOVERY` 的 `tcpm_set_current_limit()`；不需要关机，但这不是纯 sysfs 读操作，必须由操作者显式执行。

## 建议的验证顺序（不改硬件）

1. 先读 `samurai-usb-input/current_max`、`tcpm-source-*` 的 `online/usb_type/current_max/current_now`，确认 SDP/5V。
2. 加载新 `samurai-usb-input` 模块后，观察 1 秒轮询是否把 `current_max` 从 `ENODATA` 变为 `500000`。
3. 观察 `tcpm-source-*` 的 `current_max/current_now` 是否从 0 变为 500000，`online` 仍为 1，`voltage_now` 仍为 5000000。
4. 读 MP2650 `INPUT_CURRENT_LIMIT` 与 `samurai-charging` 的 `desired_enable/auto`，确认 500 mA 已进入策略，但没有写 900 mA/1.5 A。
5. 物理测试一次短 suspend/resume，确认不再是 0/0；再测一次拔插，确认 DWC3 `SET_CONFIGURATION` 后仍能回到 500 mA。

## 代码位置与最小补丁边界

- `drivers/power/supply/samurai-usb-input-decode.h`：`samurai_usb_decode()` 的 SDP 分支、`samurai_usb_apply_udc()`。
- `drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c`：`qcom_pmic_typec_port_get_current_limit()`（方案 C）；若要让 provider 变化自动回调 TCPM，还需为 TCPM psy 建立真实的 `power-supplies` 关系，或增加明确的 `tcpm_vbus_change`/重读预算路径。
- `drivers/usb/typec/tcpm/tcpm.c`：`tcpm_psy_get_current_max()`/`tcpm_psy_get_current_now()` 只读 `current_limit`，不应在这里加板级兜底。
- `drivers/usb/dwc3/core.c`：`dwc3_vbus_budget_close()`/`dwc3_vbus_budget_open()` 是预算撤销/重开语义；若要彻底修，应在 resume 后让 composite 重新 `usb_gadget_vbus_draw()`，但这不是 R15 最小修复。`dwc3_gadget_vbus_draw()` 在 `vbus_draw_blocked` 时会返回 `-EBUSY`，所以 resume 顺序必须保证 `dwc3_vbus_budget_open()` 先于 composite 的重新发布。

## 明确不该做的

- 不要在 `tcpm.c` 里把 `current_limit==0` 无条件改成 500；那会把“真正未配置/错误 detach”也伪装成可充电。
- 不要把 `tcpm_psy_get_online()==1` 当作“PD 固定合同”或“1.5 A 已协商”；它只说明 TCPM 的 `vbus_charge` 非 0。
- 不要根据 `CURRENT_NOW=0` 推断没有电流；R15 的两个 0 是同一个 `current_limit`，不是硬件 ADC。
- 不要把 `cc=0x08` 当 Type-C 1.5 A；它是 SDP，1.5 A 只属于 CDP/DCP 或 Type-C 配件分支。
- 不要恢复到旧的 900 mA/1.5 A 上限；R15 的板级上限是 500 mA，且 MP2650 的 `input-current-limit-microamp=<900000>` 只是上限，不是当前许可。

## 结论

R15 的 `current_limit=0` 是 **SDP 的 UDC 预算在 suspend/resume 后未重新发布**，不是 Type-C/APSD 解码错误，也不是 5V 合同丢失。最小且安全的修复是在 `samurai-usb-input` 对已确认的 SDP 保留 500 mA 上限（方案 A/B），让 TCPM 通过现有 `power_supply_changed()` 路径自动从 0 恢复到 500 mA；优先无需重启，也无需修改通用 TCPM。
