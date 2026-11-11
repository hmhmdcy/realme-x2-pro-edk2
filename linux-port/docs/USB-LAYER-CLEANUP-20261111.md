# USB 控制器分层清理（2026-11-11）

本轮只做分层和可重放性清理，不改 USB 数据路径，不刷机。

## 结论

USB 控制器主干的分层是正确的：`dwc3` core 管通用 keep-connect 语义，
`dwc3-qcom` 管 Qcom glue 和 PDC wake IRQ，板级 DTS 只放
`dr_mode`、`maximum-speed`、PHY 选择和 extcon 接线。清理前的三个
问题已经移除：

| 问题 | 处理 | 产物 |
| --- | --- | --- |
| 通用 SNPS Femto PHY 驱动里的 577 行私有 window API，无消费者 | 删除私有头和全部 window 代码，恢复 v7.3.1 PHY 基线 | `v7.3.1/0011-usb-phy-remove-dead-hsphy-window.patch` |
| SM8150 SPMI `periph_irq` 的 PDC 路由放在板级 overlay | 移入 `sm8150.dtsi`，与 SM8250 主线一致 | `v7.3.1/0012-arm64-dts-qcom-sm8150-spmi-pdc-wake.patch` |
| extcon overlay 携带无效的 `wakeup-source` | 删除；唤醒启用仍由 udev `power/wakeup` 负责 | `usb2-vbus-wake.dtso` |

## 补丁系列

USB 系列的可重放基线是内核头
`604f840ec52b24142aff59b5d1a77b6cecb58397`，不是历史
`0001`/`0002` 快照：

```text
0005-usb-dwc3-qcom-remove-unused-samurai-apsd-kconfig.patch
0006-usb-dwc3-gadget-keep-connect-sys-sleep.patch
0007-usb-dwc3-qcom-peripheral-wake.patch
0008-arm64-dts-samurai-usb-host-resume.patch
0011-usb-phy-remove-dead-hsphy-window.patch
0012-arm64-dts-qcom-sm8150-spmi-pdc-wake.patch
```

`0006`/`0007`/`0008` 已按工作区真实差异重建；旧的手工版本存在
hunk 缺行或上下文不匹配，不能 `git apply`。`0024`/`0025` 旧提取稿
已移到 `linux-port/patches/superseded/`，避免与 `0001` 重复。

## 验证

- 干净 worktree `604f840` + 上述六个补丁全部 `git apply` 成功，
  `git diff --check` 通过。
- `phy-qcom-snps-femto-v2.o`、`dwc3/core.o`、`dwc3/gadget.o`、
  `dwc3/dwc3-qcom.o` 编译通过；PHY 对象无 window 符号。
- wake DTB 构建通过：`sm8150-samurai-base-clean.dtb` +
  `usb2-vbus-wake.dtbo` → `sm8150-samurai-usb2-vbus-wake.dtb`。
- 语义差分只剩 `/extcon-usb1` 和
  `/soc@0/spmi@c440000/pmic@0/gpio@c000/usb2-vbus-det-default-state`；
  SPMI 为 `interrupts-extended = <&pdc 1 ...>`，extcon 无
  `wakeup-source`。
- 产物：`E:/edk2-samurai-out/standard-arm64-v731/usb-wake-20261111-r5/`。
  DTB SHA-256
  `53217926a2d8725895401d12ff8a11689b1ae0b984ee42d2ce3ecc31ab366702`。

## 真机运行结果（2026-11-11）

- 已刷入新 boot/Image 并启动，release
  `7.3.1-rmx1931-samurai-v731-usbwake`，boot ID
  `1c8e8db5-9f2a-4c2f-b46b-05dbeaa05737`。
- `check-usb-wake-baseline.sh --require-enabled` 通过：extcon
  compatible/vbus-gpios 正确，`power/wakeup=enabled`，extcon IRQ 120
  存在，SPMI 为 `interrupts-extended = <&pdc 1 ...>` 且无裸 GIC
  `interrupts`，extcon 无 `wakeup-source`。
- `/proc/kallsyms` 中 `qcom_snps_hsphy_window` 符号数为 0；UDC/NCM/
  Wi‑Fi/SSH 正常，`taint=512` 与刷入前相同。
- U0 链路下 `rtcwake -m mem -s 30` 被 `dwc3-qcom` 以 `-EBUSY` 正确
  拒绝：`last_failed_dev=a600000.usb`、`last_failed_errno=-16`，
  boot ID 不变。这说明 keep-connect 的 U3 门禁仍然有效。
- 物理拔插 VBUS 未在 120 秒窗口内完成，因此
  `VBUS insertion/removal wake` 和 `U3 host-resume` 仍未验收。
- boot carrier 由 EDK2 重新构建；4 个同尺寸模块差异已确认是构建
  日期字符串和 BdsDxe 构建路径，DTB 与 r5 逐字节一致。若要求严格
  “仅 DTB 字节变化”，需要在设备恢复后另做 carrier 重建。

## 未完成

- 真机 suspend 后插拔线唤醒、U3 host-resume 仍未验收；需要一次
  可协调的 USB 拔插，或主机侧可用的 U3 autosuspend。
- `dwc3_gadget_keep_connect()` 只看属性、role 和 connected，
  `dwc3-qcom` 的 keep-connect 还看 `device_may_wakeup()`；运行时把
  `power/wakeup` 设为 disabled 会让 core 和 glue 的判定不一致。
  修法是把 `device_may_wakeup(dwc->dev)` 并入 core 的统一谓词，需要在
  有设备可回退时单独验证。
- `0001` 仍是 96 文件的历史平台快照，包含 `0005`/`0011` 要删除的
  历史内容；本轮的构建基线是 `604f840`，不是重放 `0001`→`0002`。
- `linux-port/dts/v731/source-lock.json` 的 `usb_wake_candidate`
  段仍是 2026-11-10 的候选快照，未随本轮重建；以本文和
  `USB-WAKE-20261110.md` 的新哈希为准。
