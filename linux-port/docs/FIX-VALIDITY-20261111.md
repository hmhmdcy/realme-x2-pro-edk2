# 修复与适配有效性台账（2026-11-11）

用途：在手机暂时不可达时，先把已经完成、可以复核的适配提交入库，并把
“已验证的修复”“离线候选”“无效修复/误判”分开。本文不是运行验收；
设备恢复后仍按各专题文档的门禁重测。

## 结论

- 可以称为“修复”的只有 SOFEF03F HBM 边界及其验证链。
- 可以称为“适配/清理”的有电源键桥删除、KWin 独立 EBUSY 重试、USB
  分层清理，以及相机取景/高像素路径；它们各自的验收范围不同。
- 不能称为修复的包括：extcon 的 `wakeup-source`、未编译的 APSD 私有
  Kconfig、U0 active-link 唤醒实验、只做 first-frame 重发的面板候选、
  MDSS reset 冷启动候选，以及用 `samurai-powerkey` 桥掩盖面板问题。
- 手机 2026-11-11 起 SSH/NCM 暂时不可达；本轮只提交源码、补丁、文档
  和离线验证结果，不声称新的真机结果。

## 已验证并提交

| 项目 | 结论 | 证据 / 边界 |
| --- | --- | --- |
| SOFEF03F HBM 黑屏 | **有效修复**。`brightness > 1023` 必须先写 `0x53=0xe0`，离开 HBM 写 `0x53=0x20`；旧驱动只写 `0x51=1024`，物理面板黑屏 | 部署用 `0009`，新树用 `0010`；10 轮 1024 亮度 DPMS、真实上滑、实体电源键、拔电冷启动通过。见 [PANEL-HBM-20261110](PANEL-HBM-20261110.md) |
| `samurai-desktop` 4-r16 | **有效的架构收敛**：删除 `samurai-powerkey` Python 桥和 OpenRC 服务，电源键/DMPS 回到官方 KWin/PowerDevil 路径 | 包已离线构建、签名；尚未在设备安装。见 [DESKTOP-R16-20261109](DESKTOP-R16-20261109.md) |
| KWin `0103-retry-transient-ebusy-commits.patch` | **独立的瞬时 EBUSY workaround**，不是 HBM 根因 | `kwin 6.8.2-r3` 已安装；10 轮锁屏/DPMS/触摸无新增 EBUSY。Plasma 6.8.3 后优先删除或换上游修复。见 [kwin README](../packages/kwin/README.md) |
| USB 控制器分层清理 | **有效清理**：删除无消费者的 577 行 Femto PHY 私有 window API；SPMI periph IRQ 移入 `sm8150.dtsi` | `0005/0011/0012` 在 `604f840` 基线可 apply，PHY/core/gadget/dwc3-qcom 对象编译通过；已刷机验证。见 [USB-LAYER-CLEANUP-20261111](USB-LAYER-CLEANUP-20261111.md) |
| U3-only keep-connect | **已禁用（不是有效修复）**：拔线但链路残留 U3 时布防 `dp_hs_phy_irq`，每次 suspend 0.6 秒内被伪唤醒；插线 resume 后曾出现 Windows Code 43 | 板级 `snps,gadget-keep-connect-sys-sleep` 已关闭；内核 cable-event fallback 保留但未启用。标准 suspend/resume 已验收。见 [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md) |
| 相机预览 854x480 快路径 | **有效适配**：`viewfinderbin` 先在 NV12 域缩放，再转 BGRx，避免 Cairo 逐帧 1080p YUV→RGB | 实机 30 fps、单核约 17%、SDP 900 mA 下净充 `+21..+39 mA`。见 [PERFORMANCE](../camera/PERFORMANCE.md) |
| 1440x1080 取景 / 4608x3456 双流 / 9280x6944 高像素 | **在 k363 基线上有效的相机路径**：原厂取景参数、RAW 双流和高像素 mode 0 均已实拍 | 高像素约 10 fps，只作静态拍摄；当前 v7.3.1 生产树是否携带这些补丁要以 source-lock 为准，不能把 k363 结果写成 v7.3.1 已验收。见 [camera kernel README](../camera/kernel/README.md) |

## 无效或被取代

| 项目 | 判定 | 原因 / 替代 |
| --- | --- | --- |
| PM8150 GPIO10 `extcon-usb-gpio` | **总体撤回**：厂商 DTS 注释掉了 `vbus-gpio` 和 `&usb1` 消费者；实测 GPIO10 不跟随 VBUS、IRQ 120 始终为 0 | overlay、udev 规则和包条目已删除；`wakeup-source` 本身也从来不是有效属性。详见 [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md) |
| `USB_DWC3_SAMURAI_APSD_*` Kconfig/Makefile 钩子 | **无效适配** | 引用不存在的源文件，从未可编译；已由 `0005-usb-dwc3-qcom-remove-unused-samurai-apsd-kconfig.patch` 删除 |
| U0 active-link keep-connect 实验 | **无效唤醒路径** | 系统能睡，但 USB/NCM 流量不能唤醒，因为 DWC3 IRQ 是 GIC IRQ、不是 PDC wake 源；未部署，保留在 `patches/experiments/`。生产仍是 U3-only + PDC 策略 |
| `0003`/`0005` 面板 first-frame 重发 | **误判，不是根因修复** | 只覆盖普通亮度区间；当时把 KScreen 降到 308 后的恢复误认为时序修复生效。300/400 重发不能处理 1024 HBM 黑屏 |
| [PANEL-FIX-20261109](PANEL-FIX-20261109.md) | **候选作废** | 构建过但从未刷入；基于 first-frame 假设，已被 HBM 修复取代 |
| [PANEL-COLD-BOOT-20261110](PANEL-COLD-BOOT-20261110.md) | **候选作废** | MDSS reset / null insertion 候选从未刷入；2026-11-11 同一 HBM Image 的拔电冷启动已通过，观察到的症状不需要该候选 |
| `samurai-powerkey` 桥 | **不应回到生产** | 用独占 evdev、KScreen modeset 和背光重写掩盖面板问题，导致反复 60/90Hz 初始化；4-r16 删除，r15 APK 仅作诊断回滚 |
| KWin `0103` 作为黑屏根因 | **错误归因** | EBUSY 是独立的瞬时原子提交问题；它仍保留为有界重试，但 HBM 边界才是 1024 黑屏根因 |
| 内核 release 与 `/lib/modules/...+` 后缀错配 | **环境/打包错误，不是 USB 回归** | 运行 Image 是 `7.3.1-rmx1931-samurai-v731`，模块目录却是 `...v731+`，导致 `socinfo`、RTC、Bluetooth、zram 不可用。不能用该 boot 判断 USB wake 失败 |

## 尚未验收

| 项目 | 当前状态 | 恢复设备后的下一步 |
| --- | --- | --- |
| USB2 Type-C sink/dual | 仅 DTB/config 离线构建；dual 缺 `DWC3_DUAL_ROLE`/xHCI | 先只换 sink DTB，确认 TCPM、正反插、UDC/NCM 不回归 |
| USB 插拔线唤醒 | **未支持**：GPIO10 extcon 被否定，已删除；没有可信的 VBUS/attach 源 | 先启用主线 PM8150B Type-C/TCPM + `usb-role-switch`，再用 `vbus-change`/`attach-detach` 验证 PDC 唤醒；不要恢复 GPIO10 |
| 同线 host resume | **未支持**：keep-connect 已禁用；标准路径不保留 U3 链路 | 在标准 Type-C 层落地后重新评估；不能把 Windows 常驻 U0 当失败或成功 |
| `samurai-desktop` 4-r16 | 已构建/签名，未安装 | 安装后确认旧服务/二进制删除、KWin/PowerDevil 电源键和长按菜单正常 |
| Snapshot 4608x2592@60 | sensor 60fps，但 A5 IPE 只有约 4fps 并出现 `IMAGE_PAIR_TIMEOUT` | **不能作为默认 1080p60 取景**；需 libcamera 按 stream 角色在 mode 3/4 间选择 |
| NFC 标签、蓝牙外部 PAN/HID、长期 suspend/功耗 | 仍缺外部条件 | 保持未验收，不用控制器注册或服务在线代替业务验收 |

## 提交边界

- 本轮不改 `boot`/`logdump`，不写 NV、persist、校准或 userdata。
- 只提交源码、补丁、包配方、脚本和文档；不提交 `build-tmp/`、设备
  临时日志、预编译 `.so` 或无关的旧实验目录。
- `reference/charging-*` 的既有未提交改动不在本轮范围内；不要用
  `git add -A` 混入。
- 所有“已通过”只对应文中写明的 boot/Image 和场景；手机恢复后必须
  按各专题门禁复测，不能把离线构建或历史 boot 结果当作当前运行状态。

## 本轮提交

提交范围从 `2380c0e463`（面板 HBM）开始，依次为桌面、USB、相机和本文档：

```sh
git log --oneline 2380c0e463~1..HEAD
```

各提交只包含对应主题的源码、补丁、包配方、脚本和文档；未提交
`reference/charging-*` 的既有工作区改动，也未提交设备临时日志或预编译
`.so`。
