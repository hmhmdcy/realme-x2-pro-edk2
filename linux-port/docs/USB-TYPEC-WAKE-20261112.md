# PM8150B Type-C / USB 唤醒检查点（2026-11-12）

## 结论

标准 PM8150B Type-C/TCPM、`usb-c-connector`、PM8150B VBUS
regulator 和 DWC3/NCM 已作为**持久 DTB + Image** 冷启动部署并通过
短时 `s2idle` 稳定性验证。当前状态：

- 已通过：Type-C sink/device 枚举、`wakeup-source` 使能、
  3 轮 15 秒 + 1 轮 60 秒 + 8 轮 15 秒 + 16 轮 30 秒
  `s2idle`、每次
  UDC/NCM 自动恢复、Windows PnP Problem Code 0、Wi‑Fi 与 NCM SSH
  同时可用；`samurai-platform 5-r30` 的 `link_lost` 注入恢复和
  `reattach` fake-sysfs 状态机测试通过；awake 模式寄存器周期能产生
  Type-C IRQ；诊断模块在 suspend 边界生成真实 PM8150B CC 事件后，
  系统在 RTC 安全闹钟前恢复，Type-C IRQ 与 TCPM wake 事件均增长，
  证明 Type-C IRQ → SPMI → PDC 的睡眠唤醒路径可用。
- 一次受控的 awake PM8150B 模式周期把 TCPM 重新接到当前线缆：
  `/sys/class/typec/port0-partner` 从不存在变为存在，partner 为
  non-PD，`orientation` 从 `unknown` 变为 `normal`，UDC/carrier
  保持不变。TCPM log 显示
  `TOGGLING -> SNK_ATTACHED -> SNK_READY`。这是软件触发的
  detach/attach，不是物理插线；反插方向仍待用户翻接 Type-C 插头。
- 未通过/未执行：**物理拔线后插线唤醒**、**物理拔线唤醒**、反插
  方向、长时间反复插拔/枚举、同线 U3 host-resume。用内核
  `msleep()` 在 s2idle 中合成 Type-C 事件的尝试失败：定时器随
  s2idle 冻结，不能替代真实线缆事件。
- 本轮 `/proc/sys/kernel/tainted` 为 `4608`（`0x1200`，启动 warning
  加诊断模块的 out-of-tree 标记）。这不影响上面的功能证据；最终生产
  基线应在不加载诊断模块的冷启动上重新记录 taint，至少清掉 OOT
  位 `0x1000`，不要机械地假设它一定为 0。

因此不能把本检查点写成“USB 插拔唤醒已完成”；它证明的是生产
Type-C 路径、唤醒源已布防、suspend/resume 和 DWC3 恢复路径可用。

## 部署内容

### 板级 DTB

源码 wrapper：

```text
linux-port/dts/experiments/sm8150-samurai-usb-typec-sink-compact.dts
```

它在完整 `sm8150-samurai.dts` 上只做两件事：

1. 删除 `&ethernet` 节点。SM8150 以太网控制器在 RMX1931 上不存在，
   生产 DTB 中本来就是 `status = "disabled"`；删除它是为了把 DTB
   压进现有 boot FFS 的 114716 字节 DTB section。
2. 启用标准 PM8150B Type-C：
   - `&pm8150b_typec`：`status = "okay"`、`vdd-pdphy-supply`、
     `wakeup-source`；
   - `connector`：`usb-c-connector`、`power-role = "sink"`、
     `data-role = "device"`、`vbus-supply = <&pm8150b_vbus>`、
     `sink-pdos`、`op-sink-microwatt`；
   - `&pm8150b_vbus`：500 mA 限流，`status = "okay"`。

`model`、`chassis-type`、DWC3、USB2 HS PHY、NCM 和其余板级节点保持
生产值。没有 GPIO10 extcon、FSA4480、keep-connect 或
`usb-role-switch`。

部署 DTB：

```text
SHA-256 3d3b5a25dc3c6f2f9936b9c3aef102769d5b0a656ec3c93f817ec2a9c4515977
bytes   114595
```

### 内核唤醒补丁

```text
linux-port/patches/experiments/0010-usb-typec-pmic-attach-wake.patch
SHA-256 6ccc145022173048491c6f1d24c196907c71edd72443a4b44af5b75aa1f37b13
```

语义：

- Type-C 节点支持标准 boolean `wakeup-source`；
- probe 时 `devm_device_init_wakeup()`；
- system suspend 时对 `cc-state-change`、`vbus-change`、
  `attach-detach` 三个 IRQ 调 `enable_irq_wake()`；
- resume 时 `disable_irq_wake()`；
- SPMI child wake 请求经 PMIC arbiter 父 IRQ 进入已路由到 PDC
  pin 1 的路径。
- 当前候选在部分 arm/disarm 失败时，对已经处理的 IRQ 做相反方向的
  回滚；部署 `#6` 是较早版本，正常成功路径相同。

部署 Image：

```text
7.3.1-rmx1931-samurai-v731-usbwake #6
SHA-256 d73641bfb888d713fe0fe32df0d28c1f7e64e70e3d0b548240d3febea3fd1ec8
```

注意：部署的 `#6` 来自较早的补丁版本（`0f2069f...`）；当前
`0010` 的 `6ccc...` 只增加了格式收敛和 wake-IRQ unwind 错误路径的
对称恢复，正常成功路径未变。`0010` 当前版本对应下面的新 Image
候选 `e1e6...`，不能用 `6ccc` 冒充已部署 `#6` 的逐字节来源。

对两个构建目录做了对象代码审计：在
`dpu_rm.o`、`dsi_host.o`、`panel-samsung-sofef03f.o` 和
`qcom_pmic_typec.o` 中，运行 `#6` 与候选的 `.text` 段逐字节相同；
只有 `qcom_pmic_typec_port.o` 因错误回滚路径而不同。因此先前
“WSL 树含显示改动、候选不能刷”的阻塞已经核对清楚，不需要为了
这些显示文件重刷；当前仍不部署候选，因为它对正常唤醒路径没有
功能增量。审计记录在
`usb-typec-wake-probe-20261112/SOURCE-AUDIT-20261112.md`。

### boot / logdump

| 产物 | SHA-256 |
| --- | --- |
| boot（r3，DTB-only in-place） | `69cf8066b8851c01cd546a98e3f115e3896be932197db9cd44d131e7d037e4ea` |
| logdump FAT（Image + `samurai.dtb`） | `767b79853f1f0d12ab12c514f8bcdf26fae27cf6bcd13b511c6437711a021a5e` |

boot 候选由生产 boot
`4f62605fc11a3b9b3594e745c5667572c3224ef85eb048c894d5c9c521ee9835`
生成；`review-boot-metadata.py` 确认 `BdsDxe`、`UiApp`、
`PlatformSmbiosDxe` 逐字节不变，只有 DTB FFS 改变。logdump 中的
`/Image` 和 `/samurai.dtb` 分别与上述 Image/DTB 哈希一致。

## 真机状态

冷启动后：

```text
boot_id                         0225f227-30f8-4541-b200-cdf53cb7f311
model                           Realme X2 Pro (RMX1931CN)
chassis-type                    handset
typec port0                      sink / device / normal / rev 1.2
typec platform wakeup            enabled
usb_vbus regulator               disabled, 0 users, 500000 uA
UDC                              configured
usb0 carrier                     1
mp2650-input/online              1
Windows USB\VID_0525&PID_A4A1     Problem Code 0, Code 43 absent
```

Type-C IRQ 已注册在 `pmic_arb` 下：

```text
cc-state-change, vbus-change, attach-detach,
sig-tx, sig-rx, msg-tx, msg-rx, msg-tx-failed,
msg-tx-discarded, msg-rx-discarded
```

boot 时 PD PHY 出现过两次：

```text
Initiating hard-reset, which might result in machine-power-loss.
isr: tx_sig
```

两次都发生在开机阶段，之后未再复现；`port0` 保持 sink/device，
充电、NCM 和 SSH 正常。该日志目前按“非致命 PD PHY 初始化/充电器
协议事件”记录，不能据此宣称 PD 协议已验收。

诊断周期后 TCPM 一度留在 `orientation=unknown`、没有 partner。
2026-11-12 05:52 再次执行一次 awake `typec_irq_probe` 模式周期，
TCPM log 捕获到完整的 `TOGGLING -> SNK_ATTACHED -> SNK_READY`；
随后 `port0-partner` 存在（non-PD）、`orientation=normal`、
`UDC=configured`、carrier=1。该周期只是恢复软件 attach 状态，
不是新的物理插线。证据为
`typec-awake-cycle-tcpm-20261112.txt`；物理反插仍需翻动 Type-C
插头确认 `orientation=reverse`。

随后在 partner/normal 状态下又执行 3 轮 15 秒 s2idle：每轮实际
17 秒，`suspend.success` 44→47，boot ID 不变，UDC/NCM 每轮恢复；
resume 后 partner 仍存在且为 non-PD、orientation 仍为 normal，
Windows PnP 保持 Problem 0。证据 summary SHA-256 为
`bcc8f0836694c8392cbbe30bf15f7dc8434e1162db6d38c492bd602e9b23b0ed`。
之后 5 分钟心跳 32 个样本，NCM/Wi‑Fi/PnP 失败均为 0，
`LastArrivalDate` 变化 0。
随后又做 10 轮 soft reconnect：10/10 恢复，100 ms 主机 PnP 采样
1087 个样本，恰好 10 次消失/重建，非零 problem 为 0。

### suspend 边界唤醒诊断

`linux-port/diagnostics/typec-irq-probe/typec_wake_near.c` 是仅用于
取证的诊断模块，不进入 boot、DTB 或生产包。它通过 device link 把
一个 dummy supplier 排到 PM8150B Type-C 驱动之后，在 `suspend_late`
写入 `TYPEC_DISABLE_CMD`，在 resume 恢复原 mode。这样可以在 Type-C
驱动已 `enable_irq_wake()`、系统尚未完成 `machine_suspend()` 时产生
真实 PMIC CC 状态变化。

15 秒 RTC 安全窗口内的结果：

| 场景 | RTC 实耗 | suspend success | Type-C IRQ 增量 | TCPM wake events |
| --- | ---: | --- | ---: | --- |
| armed | 5 s | +1 | +4 | 未采样 |
| armed repeat | 5 s | +1 | +4 | 未采样 |
| armed + TCPM 采样 | 4 s | +1 | +4 | 76 → 85 |
| unarmed control | 20 s | +1 | 0 | 76 → 76 |

armed 轮次均在 RTC 到期前恢复，`boot_id` 不变，UDC 仍为
`configured`，carrier 仍为 1；unarmed 控制睡满 RTC 窗口且 Type-C
IRQ 无增量。另有一个 `power/wakeup=disabled` 控制同样睡满窗口。
因此可以确认睡眠中的 Type-C wake IRQ 确实被布防，且
PMIC/SPMI/PDC 路径能把唤醒送到系统。

这不是物理线缆事件，不能据此宣称插拔唤醒或同线 U3 host-resume
已完成。诊断模块测试后已 `rmmod`，Type-C `power/wakeup` 仍为
`enabled`，UDC/`carrier` 正常。

## suspend/resume 结果

使用 `rtcwake -m mem`：

| 测试 | 实际墙钟 | suspend.success | boot ID | UDC/NCM |
| --- | ---: | ---: | --- | --- |
| 20 秒单轮 | 22 秒 | 0 -> 1 | 不变 | 恢复 |
| 15 秒 × 3 轮 | 17 秒/轮 | 1 -> 2 -> 3 -> 4 | 不变 | 每轮恢复 |
| 60 秒单轮 | 62 秒 | 4 -> 5 | 不变 | 恢复 |

这里不能把 `suspend exit` 与 `suspend entry` 的 printk 时间差当作
睡眠时长：本板的 s2idle 会冻结局部 printk 时钟，即使实际睡满，两个
时间戳也可能只相差约 0.6–0.7 秒。上表使用 `rtcwake` 的墙钟时间，并
用 RTC `since_epoch` 复核；因此表中的 15/60 秒是实际经过时间。
每次 resume 后 Windows 会重新枚举，`samurai-usb` NCM 服务或
`samurai-usb-recover` 能在 12–20 秒内恢复 UDC `configured` 和
`usb0 carrier=1`。

另有 15 分钟主机侧心跳：108 个样本，NCM 失败 0、Wi‑Fi 失败 0、
Windows PnP 失败 0、`LastArrivalDate` 变化 0。证据在
`evidence/host-usb-heartbeat.txt`。
安装 5-r30 后又做了 5 分钟/34 样本心跳：NCM、Wi‑Fi、PnP 失败均为
0，Windows `LastArrivalDate` 无变化；证据在
`usb-typec-wake-probe-20261112/host-usb-heartbeat-r30.txt`。
完成 8 轮 soak 后又做了 30 分钟心跳：216 个样本，NCM、Wi‑Fi、PnP
失败均为 0，Windows `LastArrivalDate` 变化 0；证据为
`host-heartbeat-after-soak-20261112.txt`，SHA-256
`f389f7551eded0cd7757736d67f4c7c2c2f34bf1a1be7d60026388767d88931a`。
随后做了一次 32 MiB NCM 往返：上传 1.17 秒、下载 1.10 秒，
两端 SHA-256 均为
`83ee47245398adee79bd9c0a8bc57b821e92aba10f5f9ade8a5d1fae4d8c4302`。
在边界唤醒实验后又执行了 8 轮 15 秒 `s2idle` soak：8/8 轮均睡满
17 秒，`suspend.success` 18 → 26，boot ID 不变；每轮 resume 后
UDC 先短暂 `not attached`，随后由主机重新枚举恢复为 `configured`、
carrier=1，Windows PnP 仍为 Problem Code 0。恢复服务记录了 8 次
`LINK_LOST`，但没有触发 `RECOVER_BEGIN`，即没有执行强制 DWC3
unbind/bind。之后 32 MiB NCM 往返哈希仍一致。证据 summary 的
SHA-256 为
`bf1346621b4e241e5ba060b401a4b70917b095d1c21d72b1f84eec6810d62c4e`。
随后在后台 observer 运行时又做了一次 15 秒 `s2idle`：RTC 实耗
17 秒，`suspend.success` 26 → 27，boot ID 不变；observer 进程在
resume 后仍存活，并记录 UDC `configured -> not attached -> configured`
和 carrier `1 -> 0 -> 1`，约 1 秒内恢复。observer 只是诊断日志，
不能单独判定唤醒源。随后 5 分钟心跳 33 个样本，NCM/Wi‑Fi/PnP
失败均为 0，`LastArrivalDate` 变化 0；心跳 SHA-256 为
`249c6c9eedaf626cd2cc975a050a3a94cdcdcc77963018333a41c09cfba2f621`。
此后又执行了测试脚本的负对照：`remove 10`，但不拔线。脚本正确
等待 10 秒 RTC 闹钟（实耗 12 秒）后返回 `RESULT: FAIL`，
`suspend.success` 27→28，boot ID 不变，`online` 1→1，Type-C IRQ
和 TCPM events 增量均为 0。默认 `/var/log/samurai/typec-wake-*.log`
日志路径生效，Windows PnP 仍为 Problem 0。该负对照证明脚本不会把
RTC-only wake 误报为插拔唤醒。

无人值守阶段又完成了一轮 16 × 30 秒 `s2idle` soak：
16/16 轮均睡满 32 秒，`suspend.success` 28 → 44，boot ID
`0225f227-30f8-4541-b200-cdf53cb7f311` 不变；每轮 resume 后
UDC 自动回到 `configured`、carrier=1，没有触发
`RECOVER_BEGIN`，没有人工 DWC3 重绑。Windows USB/NCM 仍为
Problem Code 0。summary SHA-256 为
`143f5692e3c961450969233636189dfe3bfc7e2cbb049f0346f99f8157936c24`，
第一轮和末轮日志分别为
`9c2f325eca84875392bc43ec00cfc80dcb01e4e7787b24dbb4eb3ee67c634754`
和 `b5855cc541a37bd8e45ed98827ddac909350b4175544fc736f787504bf313e71`。
soak 后 10 分钟心跳 34 个样本，NCM/Wi‑Fi/PnP 失败均为 0，
`LastArrivalDate` 变化 0；32 MiB NCM 往返下载 1.072 秒、上传
1.155 秒，两端 SHA-256 均为
`6753c8cd9c49affaaf4d566e66de26010c6c97e3325d5c8e467980fe445c157d`。
传输后又做 5 分钟心跳：19 个样本，NCM/Wi‑Fi/PnP 失败均为 0，
`LastArrivalDate` 变化 0。
每轮 suspend 仍会记录一次
`dwc3-qcom ... port-1 HS-PHY not in L2`；这不阻止进入 s2idle，
UDC/NCM 也正常恢复，但说明系统睡眠时主机链路并未保持 U3，
不能据此宣称同线 host-resume。

`samurai-platform 5-r30` 的恢复服务保留“本次启动至少成功枚举过
一次”这一门槛，并增加 VBUS 重新上电后的重连 watchdog：如果之前
枚举过，VBUS 0 -> 1 后 20 秒仍未 `configured`，允许一次 DWC3
unbind/bind；已建立链路丢失 12 秒的旧路径仍保留。每会话最多两次，
成功或连续失败后都会停止，链路稳定 300 秒后刷新预算；只插墙充、
从未枚举的会话不会重绑。3 轮 suspend 中实际由主机重新枚举自行恢复，
没有触发强制重绑。另做了一次主动故障注入：在 `UDC=configured` 时
手写 `echo a600000.usb > /sys/bus/platform/drivers/dwc3-qcom/unbind`，
约 12 秒后服务记录 `RECOVER_BEGIN attempt=1 reason=link_lost`/
`RECOVER_OK attempt=1 reason=link_lost`，UDC 回到 `configured`、
`usb0 carrier=1`、NCM SSH 10.42.0.1 恢复，boot ID 不变，Windows
PnP 仍为 Problem Code 0。另一个 fake-sysfs 状态机测试验证了
`VBUS_ON seen=1` -> `RECOVER_BEGIN reason=reattach` ->
`RECOVER_OK reason=reattach` 的离线路径。它们都不是物理插拔测试。

另外新增并执行了 20 轮 **soft reconnect**：保持线缆和 VBUS 不变，
直接对 UDC `soft_connect` 写 `disconnect`，保持 2 秒后写
`connect`。20/20 轮均恢复为 `configured`/carrier=1，耗时 3 秒
（19 轮）或 4 秒（1 轮）；boot ID 和 `suspend.success=44` 不变。
恢复服务记录 20 次短暂的 `LINK_LOST`，但没有
`RECOVER_BEGIN`/`RECOVER_OK`，即主机每次都自行重枚举，不需要
人工或服务强制 DWC3 重绑。

主机侧用 `CM_Get_DevNode_Status` 每 100 ms 采样，3 分钟内 1629
个样本：设备节点出现恰好 20 次消失/重建，和手机侧 20 轮一致；
断开窗口内设备节点暂时不存在，但所有 present 样本均为
`problem=0`，没有 Code 43。测试后 32 MiB NCM 上传 1.146 秒，
SHA-256
`6753c8cd9c49affaaf4d566e66de26010c6c97e3325d5c8e467980fe445c157d`。
这不是物理 VBUS 事件，不能替代待做的插拔唤醒。

## 物理唤醒验收（待用户执行）

当前唯一阻塞基本验收的是需要真实拔插电缆的动作。建议在手机
Wi‑Fi SSH 可用时执行：

2026-11-12 远程会话状态：用户只远程控制 PC，不在手机旁，无法
完成 Type-C 翻面、睡眠中拔线或睡眠中插线。当前真机为
`suspend.success=47`、`fail=0`、UDC `configured`、`usb0 carrier=1`、
VBUS online、partner present（non-PD）、`orientation=normal`，
Type-C 平台 `power/wakeup=enabled`。这些只证明运行时和休眠恢复
稳定；物理插拔验收仍未执行。

已尝试用 Windows 根集线器的 `IOCTL_USB_HUB_CYCLE_PORT` 自动切断
手机端口 VBUS，但 AMD XHCI root hub 对该 IOCTL 返回
`ERROR_GEN_FAILURE (31)`；同一 hub 的查询 IOCTL 正常，端口 5
确认为 `0525:a4a1`。因此这台主机无法在不提升管理员权限、不重启
PC 的情况下自动做 VBUS 断电，物理插拔仍需人工完成。
相关脚本和失败回执：
`linux-port/scripts/cycle-windows-usb-port.ps1`、
`linux-port/scripts/capture-typec-transition.sh`、
`evidence/port-cycle-*.txt`。

又检查了 Windows 的 Type-C/UCM 路径：当前 NCM 位于
`PCI\VEN_1022&DEV_43D5`（AMD PTXH）root hub 的端口 5，并非 NVIDIA
`VEN_10DE&DEV_1ADB` PPC 所控制的端口。主机另有
`ACPI\ANX7411` / `ANXUcmCxCD` 厂商 UCM 控制器，但没有暴露可供普通
用户调用的端口电源接口。Microsoft MUTT 3.0.2 的
`UsbCApiCmd.exe` 在未提升权限运行时返回 `0x80070005`
（Access denied）；`UsbCApi.dll` 虽然导出
`UsbCApi_SetConnectorPowerRole`，同样需要受保护的主机接口。
因此当前不能把无人值守的 host-side VBUS 断电作为验收步骤。

设备上已放好一键脚本：

```sh
# 先验证正反插；当前为 normal，脚本会等待用户翻动 Type-C 插头
DRY_RUN=1 /root/samurai-tests/test-usb-typec-orientation.sh 2 90
/root/samurai-tests/test-usb-typec-orientation.sh 2 90
```

方向测试不会 suspend，且只在一轮看到 `normal`、另一轮看到
`reverse`，同时 UDC/carrier 恢复后才打印 `RESULT: PASS`。应通过
Wi‑Fi SSH 运行，因为翻动插头会让 NCM 短暂断开。

```sh
# 先拔线，再运行插入测试；脚本会显示 8 秒倒计时，然后开始 suspend
/root/samurai-tests/test-usb-typec-wake.sh insert 120

# 或先插线并枚举，再运行拔线测试
/root/samurai-tests/test-usb-typec-wake.sh remove 120
```

脚本会记录 IRQ 增量、online 变化、boot ID、RTC 闹钟和 Type-C 状态，
只有同时满足下述判据才打印 `RESULT: PASS`。也可手工执行：

脚本会先检查
`/sys/bus/platform/devices/c440000.spmi:pmic@2:typec@1500/power/wakeup`
必须为 `enabled`，并用 RTC 秒数而不是 dmesg 时间差判断是否提前恢复。

```sh
# 1. 先拔线，确认没有 VBUS
cat /sys/class/power_supply/mp2650-input/online        # 期望 0
# A-to-C/non-PD 链路可能没有 port0-partner；不能只凭 partner 判断
cat /sys/class/udc/a600000.usb/state                  # 期望 not attached

# 2. 记录基线并启动 120 秒 RTC 安全闹钟
cat /proc/sys/kernel/random/boot_id
cat /sys/power/suspend_stats/success
rtcwake -m mem -s 120

# 3. 系统睡下后 10 秒内插回电缆
```

成功判据必须同时满足：

- 在 120 秒 RTC 到期前恢复；
- `suspend_stats/success` 增加；
- `boot_id` 不变；
- 睡眠期间 `attach-detach`/`cc-state-change`/`vbus-change` IRQ
  至少一个增加；
- `pm_wakeup_irq` 不是 RTC alarm；
- 恢复后 `/sys/class/typec/port0` 存在，`mp2650-input/online=1`；
- UDC 回到 `configured` 或由 `samurai-usb-recover` 自动恢复；
- Windows PnP 保持 Problem Code 0。

屏幕是否点亮**不是**判据。`s2idle` 被 PMIC/PDC 唤醒后，充电事件
不保证 compositor 立即打开面板；应以 `suspend_stats`、IRQ 增量、
boot ID、Type-C sysfs 和 SSH/NCM 恢复为准。
`pm_wakeup_irq` 在部分 `s2idle` 路径上可能为空，因此它是辅助证据，
不能单独作为失败判据。

拔线唤醒需反向重复一次：先插线并枚举，启动 RTC 安全闹钟，
睡下后拔线，要求同样的非 RTC 唤醒证据。当前 DTB 的
`vbus-change`/`attach-detach` 是 `IRQ_TYPE_EDGE_RISING`；如果拔线
不能唤醒，应先检查 PM8150B 中断实际边沿，再评估改成
`IRQ_TYPE_EDGE_BOTH`，不要直接改生产 DTB。
脚本的 remove 模式只要求开始时 `online=1` 且 UDC `configured`，
不要求 `port0-partner` 存在；当前链路在重新 attach 后已有 non-PD
partner；旧状态或不上报 partner 的源仍可能出现该对象缺失。

## 未完成

- 物理插线/拔线唤醒、反插方向；
- 长时间反复插拔、重复 cold boot 和 Windows Code 43 soak；
- 同线 U3 host-resume：当前 DWC3 节点的 `wakeup-source` 未启用，
  Windows UsbNcm 也长期保持 U0；不能用 Windows NCM 做该验收，
  需要 Linux 主机 autosuspend；
- PD/APSD 合同、PPS、SuperVOOC 等充电协议行为；
- `usb-role-switch`/dual-role/host 模式。当前 Image 仍是
  `DWC3_GADGET`，没有 xHCI。

## 回滚

生产基线：

| 产物 | SHA-256 |
| --- | --- |
| boot | `4f62605fc11a3b9b3594e745c5667572c3224ef85eb048c894d5c9c521ee9835` |
| logdump | `898e76086b4beaf654927b2084e8ecb09fab9541df06541c20e07e252a133979` |

上一版无 VBUS regulator 的实验：

| 产物 | SHA-256 |
| --- | --- |
| boot（r10） | `f72ff3330cdea930db24718d784fbbacacda5ba3234a844cc6eb1d8135c5744d` |
| logdump（r10） | `f568e07f3391cacc201ed6881778889eaa656dd3f4163274861e47193fed23c5` |

回滚只写 boot/logdump；不写 NV、persist、calibration 或 userdata。

## 本地产物

```text
E:\edk2-samurai-out\standard-arm64-v731\usb-typec-final-20261112-r3\
E:\edk2-samurai-out\standard-arm64-v731\usb-typec-wake-20261112-r12\
E:\edk2-samurai-out\standard-arm64-v731\usb-typec-recover-20261112-r3\
E:\edk2-samurai-out\standard-arm64-v731\usb-typec-wake-probe-20261112\
```

`samurai-platform 5-r30` 的签名安装包在 `usb-typec-recover-20261112-r3/`，
SHA-256 为
`e96f0c085605c5d657e5f3a34f7788f21e1339b0156c8e75222e27aed3e174a0`；
该包已安装到当前设备。`typec-irq-probe` 只是诊断模块，已卸载，不是
生产载荷，也没有被加入 boot/DTB。

另用 `LOCALVERSION=-usbwake` 重建了匹配 release 的 Image 候选
`e1e607de3cc574791182931b28f99c2ecfab4afc451fdfc19a87ddcb8ae0e31a`
（UTS `7.3.1-rmx1931-samurai-v731-usbwake`），产物在
`usb-typec-image-repro-20261112/`；同一构建树的 `modules` 也完成
（3095 个 `.ko`）。`checkpatch.pl --strict` 为 0 errors / 0 checks，
仅 1 个“binding 文档应拆分为单独 patch”的 warning；`vmlinux` 中
suspend/resume/set_wake 符号存在；`dt_binding_check` 对
`qcom,pmic-typec.yaml` 通过（`yamllint` 未安装，跳过该子项）。
该候选**尚未刷入**；源码树含既存显示改动，刷写前需做来源/差异审查。

`evidence/` 中包含运行时快照、3 轮 suspend 日志、60 秒 suspend
日志、8 轮 soak、suspend 边界唤醒/对照日志、Windows PnP 状态、
flash 回执和恢复服务日志。host-side VBUS 自动化探测另见
`linux-port/diagnostics/typec-irq-probe/HOST-VBUS-AUTOMATION-20261112.md`。
本轮 resume 后的运行时快照 SHA-256 为
`034449ee9d9bad87ae9f5fdb700a9e5eb14be715784a749d33e8b4347127ef33`。
最终状态快照 `runtime-snapshot-final-20261112.txt` 的 SHA-256 为
`1823f1fcea0b39ee9900d2210391817b539e8cce4e7c0a18fd4ee57419ed46ae`。
负对照后的状态快照
`runtime-snapshot-after-negative-control-20261112.txt` 的 SHA-256 为
`794da49b8de00beed24f0ccfb5725adc326410200919cfa4e87ca035be52ab25`。
