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

## 未完成

- 真机 suspend 后插拔线唤醒、U3 host-resume 仍未验收。
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
