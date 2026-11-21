# Realme X2 Pro (RMX1931CN) 真机只读状态审计（2026-10-28）

审计时间：2026-10-28 03:42-03:50（Asia/Shanghai）  
目标：`root@169.254.42.1`，promiscuous-mode USB 网络  
方式：SSH 只读采集。未加载或卸载模块，未写 sysfs，未启动、停止或修改服务，未写设备文件。

设备型号原始值：

```text
/proc/device-tree/model=Realme X2 Pro (RMX1931CN)
/proc/device-tree/compatible=realme,samurai qcom,sm8150
hostname=samurai
```

## 结论

1. 设备当前运行 **Linux 7.3.0-rc6-rmx1931-samurai-k363+ #528**，与 r20 的 kernel 版本一致；但 boot_id 为 `46319ec0-e790-43bc-b4d0-78bf05c0f2b0`，不是 r20 接受证据中的 `67f122ca-d67e-4ca6-b8a7-9de86d702810`。因此这是**新的 #528 启动实例**，不能直接继承旧 boot_id 的接受结论。
2. MP2650 驱动已正确绑定在实际 I2C 设备 `0-005c` 上：驱动目录为 `mp2650`，modalias 为 `of:NchargerT(null)Cmps,mp2650`。`driver_override` 文件不存在；MP2650 不是已加载模块（`/sys/module/mp2650` 与 `/sys/module/samurai_mp2650` 均不存在）。
3. `samurai_usb_input` 模块已加载，refcnt=1，参数 `native_retained=Y`、`register_board=N`；当前 `samurai-usb-input` 的 `current_max=500000`、`input_current_limit=500000`、`online=1`。
4. TCPM source 已在线，电压 5 V、current_now/current_max 均为 500 mA，`usb_type=[C] PD PD_PPS PD_SPR_AVS PD_PPS_SPR_AVS`。
5. 电池当前为 **Not charging / Full，100%，Good**。这表示当前已满且不再充电，不等于充电链路失效；MP2650 的 `mp2650-input` 也报告 `online=1`、`status=Full`。
6. `rc-service samurai-charging status` 退出码为 0，输出 `healthy: true`，driver=`mp2650`。充电服务处于健康状态。
7. 备份目录 `/root/charging-daily-20261028-01-before` 存在，约 586.5 KiB，包含 manifest、SHA256SUMS、两个 `.ko`、service runtime/init 与 trial-lib。两个 `.ko` 与设备实际安装文件哈希一致；但当前 `/usr/sbin/samurai-charging` 的 SHA 与备份中记录的 `83469a88...` 不一致（当前 `45078d63...`），说明备份的 runtime 记录不是当前 runtime 字节级快照。
8. dmesg 中充电相关启动记录正常，未见到 MP2650、TCPM、samurai-usb-input 的错误/超时/崩溃行。主要相关记录是 USB input 原生 DWC3 supply 保留、只读 USB 输入预算注册、APSD handoff 与 `isr: tx_sig`。

## 原始值

### 主机/内核

```text
remote_time=2026-10-28T03:42:05+08:00
boot_id=46319ec0-e790-43bc-b4d0-78bf05c0f2b0
uname=Linux samurai 7.3.0-rc6-rmx1931-samurai-k363+ #528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026 aarch64 Linux
uname_r=7.3.0-rc6-rmx1931-samurai-k363+
uname_v=#528 SMP PREEMPT Tue Oct 27 08:49:26 CST 2026
cmdline=console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused bq27xxx_battery.samurai_instant_current=1
tainted=4096
```

说明：`tainted=4096` 是内核 taint 标志的原始值；本次审计未根据该值单独判断模块签名或许可证状态。

### I2C `0-005c`

```text
/sys/bus/i2c/devices/0-005c -> ../../../devices/platform/soc@0/8c0000.geniqup/884000.i2c/i2c-0/0-005c
name=mp2650
modalias=of:NchargerT(null)Cmps,mp2650
driver=../../../../../../../bus/i2c/drivers/mp2650
driver_override=不存在（no such file or directory）
status=不存在
telemetry=不存在
uevent:
DRIVER=mp2650
OF_NAME=charger
OF_FULLNAME=/soc@0/geniqup@8c0000/i2c@884000/charger@5c
OF_COMPATIBLE_0=mps,mp2650
OF_COMPATIBLE_N=1
MODALIAS=of:NchargerT(null)Cmps,mp2650
```

结论：MP2650 通过设备树 modalias 与内建 `mp2650` 驱动绑定，不依赖 `driver_override`。

### 模块

```text
samurai_usb_input 16384 1 - Live 0xffffffc07bb98000 (O)
samurai_usb_input/refcnt=1
samurai_usb_input/holders=空
samurai_usb_input/parameters/native_retained=Y
samurai_usb_input/parameters/register_board=N
samurai_usb_input/sections/.text=0xffffffc07bb98000
/sys/module/mp2650=不存在
/sys/module/samurai_mp2650=不存在
```

说明：MP2650 当前不是可卸载模块；不能把它描述成“`samurai_mp2650` 模块已加载”。

### Power Supply

实际条目：

```text
bq28z610-0
mp2650-input
samurai-usb-input
tcpm-source-psy-c440000.spmi:pmic@2:typec@1500
```

`samurai-usb-input`：

```text
type=USB
online=1
current_max=500000
input_current_limit=500000
usb_type=Unknown [SDP] DCP CDP C
```

`mp2650-input`：

```text
type=USB
online=1
status=Full
of_compatible_0=mps,mp2650
```

`tcpm-source-psy-c440000.spmi:pmic@2:typec@1500`：

```text
type=USB
online=1
voltage_max=5000000
voltage_min=5000000
voltage_now=5000000
current_max=500000
current_now=500000
usb_type=[C] PD PD_PPS PD_SPR_AVS PD_PPS_SPR_AVS
of_compatible_0=qcom,pm8150b-typec
```

`bq28z610-0`：

```text
type=Battery
status=Not charging
capacity=100
health=Good
present=1
technology=Li-ion
cycle_count=950
voltage_now=8591000
current_now=0
current_avg=0
power_avg=0
charge_full_design=1965000
charge_full=1388000
charge_now=1388000
capacity_level=Normal
temp=256
manufacturer=Texas Instruments
```

### 服务

```text
rc-service samurai-charging status
{"battery_capacity": 100, "battery_current_now": 0, "battery_health": "Good", "battery_status": "Not charging", "battery_voltage_now": 8591000, "charger_status": "Full", "driver": "mp2650", "healthy": true, "typec_current_max": 500000, "typec_current_now": 500000, "typec_voltage_now": 5000000, "usb_current_max": 500000, "usb_online": 1}
rc-service_exit=0
```

`/etc/init.d/samurai-charging` 是 OpenRC 包装器，`status()` 调用 `/usr/sbin/samurai-charging status`；`stop()` 明确说明“Charging remains owned by the kernel”。

当前文件哈希：

```text
45078d63b94cab0464448e6fdc49b3b6e8bce3d768713fefedd1c86182648405  /usr/sbin/samurai-charging
b5f55ab12f868f6a0f673f44e9d70640889b57ac3665900ac0887a9817499bd7  /etc/init.d/samurai-charging
```

### dmesg 充电关键行

完整筛选后保留的关键行：

```text
[Wed Oct 28 03:24:40 2026] samurai-usb-input c440000.spmi:pmic@2:usb-input@1300: native DWC3 supply retained until next boot
[Wed Oct 28 03:24:40 2026] samurai-usb-input c440000.spmi:pmic@2:usb-input@1300: read-only PM8150B USB input budget registered
[Wed Oct 28 03:24:40 2026] qcom,pmic-typec c440000.spmi:pmic@2:typec@1500: APSD handoff prepared: connected-5V vbus=4906912uV sink=10,08,23,29,06,19,18
[Wed Oct 28 03:24:42 2026] qcom,pmic-typec c440000.spmi:pmic@2:typec@1500: isr: tx_sig
[Wed Oct 28 03:24:43 2026] qcom,pmic-typec c440000.spmi:pmic@2:typec@1500: isr: tx_sig
```

未发现以下关键词对应的错误：`mp2650` error、TCPM timeout、typec error、charging failure、battery error。dmesg 其余大量内容是 `qcom_q6v5_pas: samurai Q6 ready item=424 running=1` 的重复行，以及 03:31 之后的 `ath10k_snoc` 频率告警，和充电状态无直接关系。

## `/root/charging-daily-20261028-01-before` 清单

目录：`drwxr-xr-x root:root`，总大小 `586.5K`。

```text
/root/charging-daily-20261028-01-before/SHA256SUMS
/root/charging-daily-20261028-01-before/manifest.json
/root/charging-daily-20261028-01-before/modules/samurai-mp2650.ko
/root/charging-daily-20261028-01-before/modules/samurai-usb-input.ko
/root/charging-daily-20261028-01-before/service/init
/root/charging-daily-20261028-01-before/service/runtime
/root/charging-daily-20261028-01-before/trial-lib/control-trial.py
/root/charging-daily-20261028-01-before/trial-lib/live-session.py
/root/charging-daily-20261028-01-before/trial-lib/postboot_audit.py
/root/charging-daily-20261028-01-before/trial-lib/trial_autoaudit.py
/root/charging-daily-20261028-01-before/trial-lib/trial_common.py
/root/charging-daily-20261028-01-before/trial-lib/trial_guard.py
/root/charging-daily-20261028-01-before/trial-lib/__pycache__/control-trial.cpython-314.pyc
/root/charging-daily-20261028-01-before/trial-lib/__pycache__/live-session.cpython-314.pyc
/root/charging-daily-20261028-01-before/trial-lib/__pycache__/postboot_audit.cpython-314.pyc
/root/charging-daily-20261028-01-before/trial-lib/__pycache__/trial_common.cpython-314.pyc
/root/charging-daily-20261028-01-before/trial-lib/__pycache__/trial_guard.cpython-314.pyc
```

备份 manifest 摘要：

```json
{
  "adapter_revision": "apsd-eud-route-image505-01",
  "default_charge_cap_ua": 250000,
  "default_input_cap_ua": 900000,
  "release": "7.3.0-rc6-rmx1931-samurai-k363+",
  "source_budget_enforced": true
}
```

备份关键哈希：

```text
45c90153ea978b96b83d1638292ddaafc7269178446c739255efe50c4b2ec8f4  manifest.json
1668d92a3c391b314749fa0158b3980692a6963bc8e831c8a53fae37e9b361bb  SHA256SUMS
dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1  modules/samurai-mp2650.ko
22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529  modules/samurai-usb-input.ko
```

设备安装模块哈希与备份一致：

```text
dbe445cfef6e095f8d028034f0fbba9231484b6510ab6f60354c6ff55e9c23d1  /lib/modules/.../samurai-mp2650.ko
22604106772b89758ea745531e99dd70a6ab696b7740705107a767599e9a6529  /lib/modules/.../samurai-usb-input.ko
f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e  /lib/modules/.../samurai-gauge-protection.ko
```

注意：`service/runtime` 的备份哈希为 `83469a88...`，但当前 `/usr/sbin/samurai-charging` 为 `45078d63...`。如果后续需要完整回滚 runtime，应先归档当前文件并确认差异来源；本次仅记录，没有替换或重启服务。

## 风险与状态判断

- **驱动绑定正常**：`0-005c` 已绑定 `mp2650`，无 `driver_override` 依赖。
- **输入预算正常**：samurai-usb-input 500 mA，TCPM 500 mA / 5 V，符合当前记录。
- **当前不充电是满电状态**：`Not charging`、100%、`Full`、0 A，属于满电后的正常停止。
- **服务健康**：`rc-service` 返回 0，健康 JSON 为 true。
- **版本一致性**：内核版本与 r20 相同，但 boot_id 不同；需新的 boot 接受/ soak 证据才能声称该启动实例已完整验收。
- **备份完整性**：模块备份与设备实际 `.ko` 完全一致；runtime 备份与当前文件不一致，是唯一明显的字节级差异。
