# 当前：postmarketOS USB 栈已部署；物理插拔/同线 resume 待验收

## 2026-11-12 postmarketOS USB 当前状态

- 普通 USB 运行时已从板级 `samurai-usb` 迁移到标准
  `usb-signaller 0.4.3-r3` + `postmarketos-usb-moded` +
  NetworkManager + `unudhcpd` + `umtprd`；`samurai-platform 6-r2`
  已安装；6-r1 完成普通重启后在同一 boot 升级到 r2。当前 boot ID
  `fc04a2e7-894b-4814-878e-6fdf5d44cc43`。
- Developer 默认模式为 `0525:a4a1`、class `ef/02/01`、MaxPower 500、
  NCM `qmult=20`、`usb0=172.16.42.1/16`；Windows UsbNcm Problem 0，
  DHCP `172.16.42.2/24`，严格 host-key NCM SSH 通过。Tethering
  `10.42.0.1/24`、MTP `0525:a4a2`/WPD、charging-only 均已实测。
- `samurai-usb-recover` 已改为通过标准 DWC3 unbind/bind 和
  usb-moded D-Bus 恢复当前模式；`ip link down` 注入在 boot ID 不变
  下恢复到 UDC `configured`/carrier 1，标准模式服务自动重绑。
  `6-r2` 在末尾用公开 UDC `soft_connect` 强制干净重枚举；实测
  Windows 在同一恢复窗口重新取得 `172.16.42.2/24` DHCP 租约，
  `USB\VID_0525&PID_A4A1` 和 UsbNcm 均 Problem 0。
- 一次 `rtcwake -m mem -s 15` 烟测后 NCM 先消失、约 20 秒内自动
  重连；suspend 期间不保持同一条活动链路，不能写成 USB host-resume。
  `dmesg` entry/exit 时差约 0.7 秒，睡眠时长仍需单独验收。
- 早期一次重连曾停在 APIPA；设备侧 `unudhcpd`/UDC/carrier 正常。
  `6-r2` 的 UDC `soft_connect` 已在该 `ip link down` 恢复路径解决，
  但更长 suspend/resume soak 的主机 DHCP 行为仍待验收。
- 未验收仍是物理插线/拔线、反插方向、长期插拔/suspend soak、
  Windows 物理 replug 后 Code 43、同线 U3 host-resume；当前内核
  仍无 `DWC3_DUAL_ROLE`/xHCI，不能声明 OTG host。
- 详细证据、包哈希和板级分层见
  [PMOS-USB-20261112](linux-port/docs/PMOS-USB-20261112.md)。

## 历史：2026-11-12 Type-C 唤醒与验证

- 标准 PM8150B Type-C/TCPM、`usb-c-connector`、500 mA PM8150B
  VBUS regulator、DWC3/NCM 已作为持久 DTB + Image 部署并冷启动运行。
  `port0` 为 sink/device；awake 模式周期后的当前链路为 non-PD
  partner、`orientation=normal`；反插仍需物理翻接。
  `mp2650-input/online=1`，Windows `0525:a4a1` PnP Problem 0；当前 boot ID
  `0225f227-30f8-4541-b200-cdf53cb7f311`。
- Type-C 平台设备
  `c440000.spmi:pmic@2:typec@1500/power/wakeup=enabled`。唤醒补丁为
  `linux-port/patches/experiments/0010-usb-typec-pmic-attach-wake.patch`
  （当前 SHA-256 `6ccc...a1f37b13`；已部署 `#6` 使用较早的
  `0f2069...`，仅差格式和错误路径 unwind，成功路径相同）；
  3×15 s + 1×60 s s2idle 均以 RTC
  秒数确认实际睡满，UDC/NCM 自动恢复，boot ID 不变。之后 8 轮
  15 s soak 全部睡满 17 s，`suspend.success` 18→26，boot ID 不变，
  Windows PnP 仍为 Problem 0；主机自行重枚举，未触发强制 DWC3
  重绑。soak 后 30 分钟心跳 216 样本，NCM/Wi‑Fi/PnP 失败均 0，
  `LastArrivalDate` 变化 0。
- 无人值守阶段又完成 16×30 s soak：16/16 轮睡满 32 s，
  `suspend.success` 28→44，boot ID 不变；每轮 UDC 自动回到
  `configured`、carrier=1，没有 `RECOVER_BEGIN`，也没有人工 DWC3
  重绑。随后 30/30 次 UDC soft reconnect 全部恢复；高频率 Windows
  PnP 采样只看到预期的消失/重建，没有 Code 43。
- suspend 边界诊断 `typec-irq-probe/typec_wake_near.c` 已证明：
  Type-C 驱动布防后生成真实 PM8150B CC 事件，系统在 15 s RTC 前
  4–5 s 恢复，Type-C IRQ +4、TCPM wake events 76→85；unarmed
  对照睡满且 IRQ 增量为 0。该模块仅是诊断，已卸载，不得进入生产。
  当前 boot 的 `/proc/sys/kernel/tainted=4608`（`0x1200`：启动 warning
  + 诊断模块 OOT）；最终生产验收需在不加载诊断模块的冷启动上重新
  记录 taint，至少清掉 OOT 位，不要假设一定为 0。
- `samurai-platform 5-r30` 已签名构建并安装。恢复服务对已建立链路的
  `reason=link_lost` 已在真机自动恢复；`reason=reattach` 已通过
  fake-sysfs 状态机测试。当前服务 `armed=1`、`seen_configured=1`。
  APK SHA-256 `e96f0c085605c5d657e5f3a34f7788f21e1339b0156c8e75222e27aed3e174a0`。
- 主机侧自动 VBUS 断电仍不可用：当前 NCM 在 AMD PTXH root hub
  端口 5；NVIDIA PPC 不在该路径，ANX7411 UCM 驱动没有普通用户
  接口。MUTT 3.0.2 的 `UsbCApiCmd.exe` 未提权返回 `0x80070005`。
  物理插拔仍需人工，不能把 synthetic CC 事件当成插拔验收。
- 已用 `LOCALVERSION=-usbwake` 重建匹配 release 的 Image 候选：
  `e1e607de3cc574791182931b28f99c2ecfab4afc451fdfc19a87ddcb8ae0e31a`，
  UTS 为 `7.3.1-rmx1931-samurai-v731-usbwake`。它**未部署**；WSL
  源码还含有既存显示改动，刷入前必须先做来源/差异审查和回滚验证；
  同树 `modules` 构建通过（3095 个 `.ko`），`checkpatch` 0 errors /
  0 checks，`dt_binding_check` 通过。
- 仍未验收：物理拔线后插线唤醒、物理拔线唤醒、反插方向、长期反复
  插拔/枚举，以及同线 U3 host-resume。当前 DWC3 仍是 gadget-only，
  suspend 会 soft-disconnect；不能用 Windows NCM 的 U0 存活冒充
  host resume。
- 诊断结论：awake 下直接切换 PM8150B Type-C 模式能产生
  `cc-state-change`/`attach-detach`/`sig-tx` IRQ；suspend 边界
  diagnostic 已证明 IRQ → SPMI → PDC 路径。物理线缆事件仍是
  唯一可接受的 Type-C 插拔唤醒验收。

2026-11-12 远程会话复查：当前 `suspend.success=47`、`fail=0`，
UDC `configured`、`usb0 carrier=1`、VBUS online、Type-C
`sink/device`、partner present（non-PD）且 `orientation=normal`，
平台唤醒源仍为 `enabled`。但用户当前只远程控制 PC、不在手机旁，
因此不能执行翻插头、拔线或插线；物理验收暂停在这个门禁，不能把
16×30 s soak、soft reconnect 或 synthetic CC 事件写成“插拔唤醒已通过”。

用户在场时可直接在已插线状态执行拔线测试：

```sh
# 只读预检（不会 suspend）
DRY_RUN=1 /root/samurai-tests/test-usb-typec-wake.sh remove 120

/root/samurai-tests/test-usb-typec-wake.sh remove 120
```

拔线后若要测插入唤醒，先确认 `mp2650-input/online=0`，再执行：

```sh
/root/samurai-tests/test-usb-typec-wake.sh insert 120
```

脚本现在用 RTC 秒数判断提前恢复，并在启动时检查 Type-C 平台
`power/wakeup=enabled`；屏幕是否点亮不是判据。

另有一个非持久 observer 正在记录 VBUS/UDC/carrier、Type-C 方向和
suspend 计数变化，日志为
`/var/log/samurai/typec-transitions-20261112-observer.log`；它只用于
事后关联，不能单独判定唤醒成功。observer 运行时又做了一次 15 s
`s2idle`，26→27、boot ID 不变，observer 存活并记录了
UDC/carrier 掉线后约 1 秒恢复。设备上当前脚本哈希：
`test-usb-typec-wake.sh` `9d777a4c17d1ce4d397c93812ff37bc9c60f3e8b3db308c7a98d40ec93d42aa9`，
`typec-transition-observer.sh` `3e35f278...8c6063e`。随后 5 分钟
心跳 33 样本，NCM/Wi‑Fi/PnP 失败均 0。
另做了 `test-usb-typec-wake.sh remove 10` 不拔线负对照：RTC 12 秒
唤醒、success 27→28、online 1→1、IRQ/TCPM 增量为 0，脚本正确
返回 `RESULT: FAIL`，证明不会把 RTC-only wake 误报为 USB wake。

当前回滚：boot `4f62605f...ee9835`，logdump
`898e7608...33979`。详细证据见
[USB-TYPEC-WAKE-20261112](linux-port/docs/USB-TYPEC-WAKE-20261112.md)。

## 历史：2026-11-11 USB 唤醒撤回

- PM8150 GPIO10 `extcon-usb-gpio` 被真机证据否定：厂商
  `refs/19781/sm8150-mtp.dtsi` 里 `vbus-gpio` 和 `&usb1` 消费者都被
  注释掉；实测 GPIO10 不跟随 VBUS，IRQ 120 始终为 0。overlay、udev
  规则和包条目已删除。
- keep-connect RFC 在拔线但链路仍显示 U3 时布防 `dp_hs_phy_irq`，
  观测到该 IRQ 增长；printk 局部时钟显示的 0.6 秒差不能单独证明
  实际未睡，但它不是可信唤醒源且插线 resume 曾出现 Windows Code 43。
  板级 opt-in 已关闭，保留内核 cable-event fallback 供将来标准
  Type-C 源使用。
- 标准路径已验证：插着线 `rtcwake -m mem -s 20` 返回 0；拔线
  `rtcwake -m mem -s 30` 实测睡 32 秒，`suspend.success` +1，
  boot ID 不变，`dp_hs_phy_irq` 不变。
- 当时 USB wake **未支持**；主线 PM8150B Type-C/TCPM +
  `usb-c-connector` 已于 2026-11-12 部署，下一步只剩真实电缆插拔
  验收。`usb-role-switch`/host 模式仍未接入；不要恢复 GPIO10 extcon。
- 证据、产物和回滚见
  [USB-REMOTE-WAKE-20261111](linux-port/docs/USB-REMOTE-WAKE-20261111.md)。

最新产物：

```text
E:\edk2-samurai-out\standard-arm64-v731\usb-resume-fallback-20261111\
Image 1e9b4ca98548a1a5dc3576799845df03b125b0e5843e343c718d729d42e3fbd3
DTB   5c957d06cae9a5ad6541f8e5707057337f8c100b33e9447837e8daa0274d8472
boot  4f62605fc11a3b9b3594e745c5667572c3224ef85eb048c894d5c9c521ee9835
FAT   898e76086b4beaf654927b2084e8ecb09fab9541df06541c20e07e252a133979
```

目标（2026-11-09）：Wi‑Fi、CDC NCM、SSH 仅作强制回归门禁；相机
Selection API、PM8150L 闪光灯/V4L2、蓝牙主机模块、NFC 控制器和
MAX98937/AW8697 私有 `status` 删除已关闭。
继续用 Linux 主线模型/API 适配其余硬件，私有层只保留不可标准化的
板级接线。`boot`/`logdump` 在 Linux 侧成对写入；不擦写
NV/persist/校准/userdata。

目标更新（2026-11-10）：活动块切换到 USB 标准平台适配。先只上
DTB-only `usb2-typec-sink`；它启用 PM8150B TCPM，但保持
`dr_mode=peripheral`，不加 role-switch/HS graph。当前 Image 是
`DWC3_GADGET`，没有 xHCI；OTG/host 必须另建
`DWC3_DUAL_ROLE+xHCI` Image，USB3/DP 继续分层。

USB 唤醒也已拆成独立层：Android 真机运行 DT 的 `extcon_usb1` 绑定
PM8150 GPIO10 VBUS，标准 `linux,extcon-usb-gpio` 可通过 udev
`power/wakeup` 策略启用。SPMI periph IRQ 已在 `sm8150.dtsi` 接到
PDC pin 1（GIC SPI 481），属于 SoC 基线而不是板级 overlay；否则
PMIC GPIO 的 `enable_irq_wake()` 只是对裸 GIC 的无效请求。该层只
验证“插拔线唤醒”，不保证同一根线的 NCM 跨 suspend 保持在线；
DWC3 仍会 soft-disconnect。

## 2026-11-11 USB 分层清理（已刷入，运行时门禁通过）

- `0011-usb-phy-remove-dead-hsphy-window.patch`：删除通用 SNPS Femto
  PHY 驱动里的 577 行私有 window API 和私有头文件。该接口在
  `CONFIG_USB_DWC3_SAMURAI_APSD_OWNER` 关闭后已无消费者。
- `0012-arm64-dts-qcom-sm8150-spmi-pdc-wake.patch`：把 SPMI
  `periph_irq` 的 PDC 父中断从板级 overlay 提升到 `sm8150.dtsi`，
  与 SM8250 主线一致。
- `usb2-vbus-wake.dtso` 只保留 `extcon_usb1` 和 GPIO10 pinctrl；
  删除无效的 `wakeup-source`（extcon binding 不允许该属性，驱动也
  不读取它），唤醒启用继续由 udev `power/wakeup` 规则负责。
- `0006/0007/0008` 已按工作区真实差异重建为可 apply 的补丁；
  `0024/0025` 旧提取稿归档到 `linux-port/patches/superseded/`。
- USB 系列的验证基线是内核头 `604f840`；`0001`/`0002` 是历史快照，
  不能按 `0001`→`0002` 顺序重放。

验证：`phy-qcom-snps-femto-v2.o`、`core.o`、`gadget.o`、
`dwc3-qcom.o` 编译通过；wake DTB 构建通过，语义差分只剩
`/extcon-usb1` 和 GPIO10 pinctrl 两个板级节点；SPMI 为
`interrupts-extended = <&pdc 1 ...>`，extcon 无 `wakeup-source`。
已刷入并启动，boot ID
`1c8e8db5-9f2a-4c2f-b46b-05dbeaa05737`；只读门禁通过，U0 链路下
`rtcwake` 被 `dwc3-qcom` 以 `-EBUSY` 正确拒绝。物理插拔 VBUS 和
U3 host-resume 仍未验收。

## 2026-11-11 提交与有效性台账（手机离线）

手机已恢复连接；本轮先提交源码、补丁、包配方和文档，再刷入 USB
清理并做运行时门禁。有效性分类见
[修复与适配有效性台账](linux-port/docs/FIX-VALIDITY-20261111.md)。

- **有效修复**：SOFEF03F 1023/1024 HBM 边界；部署 `0009`，新树用
  收敛后的 `0010`。10 轮 DPMS 1024、真实触摸、实体电源键和拔电冷启动
  已通过。
- **有效收敛**：`samurai-desktop` 4-r16 删除 `samurai-powerkey` 桥；
  包已构建/签名但未安装。KWin `0103` 只保留为独立 EBUSY 重试。
- **有效清理**：USB PHY 死代码、SPMI PDC 路由和 extcon 无效属性；
  已刷入并启动，只读门禁通过，U0 suspend 正确返回 `-EBUSY`；
  物理插拔 VBUS 和 U3 host-resume 仍未验收。
- **无效/作废**：`wakeup-source`、APSD 私有 Kconfig、U0 active-link
  唤醒实验、first-frame 重发候选、MDSS reset 冷启动候选，以及把
  `samurai-powerkey` 当生产修复。它们只保留为历史或实验记录。
- **仍未验收**：USB sink/dual、真机插拔线唤醒、同线 host resume、
  4-r16 安装、1080p60 相机和长期 suspend/功耗。

设备恢复后先按 [PANEL-HBM-20261110](linux-port/docs/PANEL-HBM-20261110.md)
复核 HBM/电源键，再按
[USB-WAKE-20261110](linux-port/docs/USB-WAKE-20261110.md) 和
[USB-HOST-RESUME-20261110](linux-port/docs/USB-HOST-RESUME-20261110.md)
分别测试插拔线唤醒与同线 host resume；不要合并成一个“USB 唤醒通过”。

## 2026-11-10 触摸后黑屏

最终根因是 SOFEF03F 面板的 HBM 边界，不是 KWin EBUSY。原厂亮度路径
在 `brightness > 1023` 时先写 `MIPI_DCS_WRITE_CONTROL_DISPLAY (0x53)
= 0xe0` 进入 HBM，再写亮度；离开 HBM 时先写亮度，再写
`0x53 = 0x20`。KWin 唤醒时把亮度设为 1024（50%），旧驱动没有 HBM
切换，面板物理黑屏；降到 308（30% 调光）后回到普通区间又恢复，因此
表现为“触摸/唤醒后黑屏、过一会又亮”。

`linux-port/patches/v7.3.1/0009-arm64-panel-sofef03f-serialize-brightness.patch`
补上原厂 HBM 序列，并用 mutex 串行化 first-frame post-on 与亮度更新。
部署时使用该补丁；新建源码树改用等价的
`0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch`，它已收敛
0003/0005/0009 并与部署源码逐字节一致。
收敛后又重跑 10 轮 DPMS 1024（`hbm-10cycle-r2.log`）全部通过；
当前运行态检查（`post-hbm-runtime-check.log`）显示 `On/1024/0`、
HBM 错误 0、KWin EBUSY 0、NCM/Wi‑Fi/UDC 在线。
新 Image `2a2da4cfaf217be8533801e17578087146df86ae012a69fd6669361da9a2d018`，
kernel FAT `2fe43ec3997ccc4372d2fd12e8878216598e0624c125070c39b57642069e18aa`，
boot ID `12a652a5-ac2f-434f-8dc1-4dec0bfd4b53`。只写 logdump，boot
和 DTB 未动。

真机验收：10 轮 DPMS off/on（每轮 brightness 1024）全部为
`On/enabled/1024/bl_power=0`，HBM/亮度写入错误 0，KWin EBUSY 0；
用户真实上滑多次确认不再黑屏。产物与校验和：
`E:/edk2-samurai-out/standard-arm64-v731/panel-hbm-20261110/`。

实体电源键门禁脚本已固化到
`linux-port/scripts/wait-powerkey.py` 和
`linux-port/scripts/capture-powerkey-wake.sh`。2026-11-10 23:56 的抓取
收到 `POWER_DOWN/POWER_UP`，trace 为
`phase=0 -> first_frame ret=0 -> phase=1`，最终
`On/enabled/324/bl_power=0`；用户确认实体电源键已能正常开关屏幕。
2026-11-11 00:03 拔电冷启动通过：boot ID 变为
`f70fcefd-310b-4130-bcf3-c28f47ef5624`，NCM/Wi‑Fi/UDC 恢复，用户目视
确认屏幕亮起；冷启动后电源键唤醒也通过。

2026-11-11 00:29 长按电源键复核：KWin 6.8.2 在 `Key_PowerOff` 按住
1000 ms 后合成 `Key_PowerDown`；PowerDevil 6.8.2 的 `PowerDown`
默认动作是 `PromptLogoutDialog`。本机 `kglobalshortcutsrc` 原为
`PowerDown=none,Power Down,Power Down`，action 已注册但没有 active
shortcut。已通过 KGlobalAccel `setForeignShortcutKeys` 恢复为
`Power Down`，配置写入
`PowerDown=Power Down,Power Down,Power Down`；未锁屏时 D-Bus 触发
`PowerDown`，截图确认出现 Restart / Shut Down / Log Out 菜单。实体
长按另用 `/dev/input/event0` 注入 1.2 秒 `KEY_POWER`，同样走通 KWin
长按合成路径并出现菜单；实体按键最终手感由用户确认。截图
`E:/edk2-samurai-out/standard-arm64-v731/panel-hbm-20261110/powerdown-menu-20261111.png`
SHA-256 `3eee694439ea04d70bb4474f2cdff098dfd3f67f3622ae583760cc1dddb4ca2f`。

KWin `0103-retry-transient-ebusy-commits.patch` 仍保留，但只作为独立的
瞬时 EBUSY 重试，不是本次黑屏的根因。

pmaports 侧已确认：`device-realme-samurai` 使用
`device-realme-samurai-kernel-none`，EDK2/kernel 链外置维护，本机没有
可挂载 0010 的 kernel APKBUILD。因此 0010 目前作为外置 kernel patch
set 的 canonical 补丁，source-lock 记录 provenance；要声称 official
pmaports 携带，必须先新增 kernel APKBUILD 或先完成 upstream panel 提交。

## 已完成（离线）：USB 插拔唤醒

- `usb2-vbus-wake` DTB：
  `ea4ba7bc55eae8d63c8b7c7277634b1d016c278d23753fb04d98040692ebf887`；
- 产物：
  `E:/edk2-samurai-out/standard-arm64-v731/usb-wake-20261110-r4/`；
- 语义差分只有 `/extcon-usb1`、GPIO10 pinctrl 和 SPMI
  `interrupts`→`interrupts-extended`；DWC3 仍为 `peripheral`；
- rootfs 候选 `samurai-platform 5-r25` 增加
  `99-realme-rmx1931-usb-wake.rules`，只设置标准
  `/sys/.../power/wakeup=enabled`，不增加常驻服务；APK 已实际打包、
  验签，SHA-256
  `f2f9a285d7a4677173f2c8bfba8ac1fa21b0cb211f0937a18a30143c94d3c931`；
- 只读门禁：
  `linux-port/scripts/check-usb-wake-baseline.sh --require-enabled`；
- 详细边界、PDC 依据、真机 `rtcwake`/插线测试和回滚：
  [USB-WAKE-20261110](linux-port/docs/USB-WAKE-20261110.md)。

## 设备状态

2026-11-10 已刷入并完成真机验收：

- release：`7.3.1-rmx1931-samurai-v731-usbwake`
- boot ID：`12a652a5-ac2f-434f-8dc1-4dec0bfd4b53`
- boot：`b9e9e53129d7d82401385a6f096af8a260a3b3d9e63d5940f7516424f4e6a438`
- logdump：`2fe43ec3997ccc4372d2fd12e8878216598e0624c125070c39b57642069e18aa`
- Image：`2a2da4cfaf217be8533801e17578087146df86ae012a69fd6669361da9a2d018`
- DTB：`9648ca7f8dbba077c7474b2687ccdbf54b6f9c26fd196e50acf007f7d7e9cb52`
- NCM：UDC `configured`，high-speed，`usb0` carrier 1，
  `10.42.0.1/24` SSH 可用；
- Wi‑Fi：`wlan0` `192.168.0.114/24`，独立 SSH 可用；
- modules：773，`nbd` 加载/卸载探针通过；
- `usbwake-debug`：`default` runlevel，started，恰好 1 个 USBwake
  elogind sleep inhibitor；
- 官方 `/etc/sleep-inhibitor.conf` 未改：
  `9c6ca8ecb04ca042abab57d0f1b44ac2dbcfbc5d9f1962185a1bcfe3b51cab99`；
- 产物与 manifest：
  `E:/edk2-samurai-out/standard-arm64-v731/usbwake-final-20261110/`。

`host_resume_verified=false`、`u0_usb_wake_verified=false`。成功的是
“插电/NCM 活跃时用官方 sleep-inhibitor 保持手机在线”，不是 U0 主机
唤醒。要重做 U3/PDC host-resume 验收，必须先停止 `usbwake-debug`。
`taint=512` 在刷入前后相同，来自既有的启动期 clk WARN，不是本轮回归。

## 历史：USB2 Type-C 离线候选

- sink DTB：`b18da56255f82ecf9fa2095f7eddd4d0041fbb1a8162162007f1b55c657bd792`；
- dual DTB：`ef8e40ba6dca4f344918b7be9a6d1c6145c0b4d2670d58336cd3ee4086c4d164`；
- dual ARM64 config 解析：`524cc7e476b2c7ad1e35dd1fb339d95f60f0cb29f4e1f3b44d105180d30ec3e6`；
- 产物和语义差分：
  `E:/edk2-samurai-out/standard-arm64-v731/usb-typec-20261110/`；
- sink 与 production base 的 diff 只有 PM8150B Type-C/VBUS 节点新增、
  两个状态 enable；DWC3 `dr_mode` 保持 peripheral；
- dual 与 sink 的 diff 只有 power/data role、PDO 和 role-switch graph。

已删除未启用且源码不存在的 `USB_DWC3_SAMURAI_APSD_*` 私有
Kconfig/Makefile 钩子，补丁为
`linux-port/patches/v7.3.1/0005-usb-dwc3-qcom-remove-unused-samurai-apsd-kconfig.patch`。

恢复设备后的 USB 顺序：

1. 先用 WiFi SSH 建立临时 sleep inhibitor，保存当前 boot/Image/DTB；
2. 只把 `/samurai.dtb` 换成 sink 候选，Image/boot 不动；
3. 普通重启后确认 `taint=0`、UDC/NCM/SSH、`/sys/class/typec/port0`
   和正反插 orientation；
4. 跑 NCM 大传输/心跳和完整硬件门禁；
5. sink 通过后才构建 `usb2-typec-dual` 的独立 Image/modules。

详见 [USB-TYPEC-20261110](linux-port/docs/USB-TYPEC-20261110.md)。

## 已完成：Linux 侧成对刷写

`linux-port/scripts/flash-pair-linux.sh` 按 GPT label 找到 `boot`
(`/dev/sde11`) 和 `logdump` (`/dev/sde32`)，校验镜像大小、SHA-256、
挂载状态和只读性，先写 logdump、整块回读，再写 boot、整块回读。
实际写入日志见
`E:/edk2-samurai-out/standard-arm64-v731/thin-private-final-20261109/flash.log`。

thin-private 两次普通重启用时：NCM SSH 31.905/38.284 秒，Wi‑Fi SSH
47.984/59.074 秒。两次都在同一 boot 内通过 777 模块完整门禁。这个
结果证明常温普通重启，不证明拔电冷启动或 suspend/resume。

## 已完成：闪光灯/V4L2

- 标准 `leds-qcom-flash`、LED flash class、V4L2 flash subdevice；
  S5KGW1 通过 `flash-leds` 加入 CAMSS 媒体图；
- `white:flash` 存在，亮度 26/255、torch 200 mA、`faults=0`；
- 开灯 RAW 均值 `177.04 -> 407.147`（+130%），0% 饱和；
- 774/777 模块普通重启前后，四路 RAW、thermal、网络和 `taint=0`
  门禁均通过。

## 已完成：蓝牙主线模块

签名 `samurai-bluetooth-host-0.1.0-r0` 已安装；`bnep`、`uhid`、
`uinput` 自动加载，`/dev/uhid`、`/dev/uinput`、BNEP socket、BlueZ
`hci0` 和 777 模块 gate 通过；外部 PAN/HID 对端未验。详见
[BLUETOOTH-HOST-MODULES](linux-port/docs/BLUETOOTH-HOST-MODULES.md)。

## 已完成：NFC/nfc0/neard

Alpine `neard-openrc`/`neard 0.20` 和签名 `samurai-platform 5-r22`
已安装；普通重启后 `nfc0`、`neard`、D-Bus 属性及电源/轮询启停通过。
无实体标签，不声称读卡；一次 NCM 探针 `Connection reset` 仍保留为
未闭环的 USB 瞬态。详见 [NFC-NEARD](linux-port/docs/NFC-NEARD.md)。

## 已完成：private status sysfs 删除

- 最终 FAT 以当前 flash/V4L2 FAT `c99c690e…` 为底，只替换 `/Image`；
  boot `5b4dd487…` 和 DTB `b244b3f1…` 逐字节不变；
- 刷后三处节点均消失：两个 `samurai-max98937` 的 `status` 和一个
  `samurai-aw8697` 的 `status`；
- 标准 ALSA playback/capture、AW8697 input/FF、四路相机 RAW、
  flash/V4L2、蓝牙三模块、NFC `nfc0`、thermal 和 Wi‑Fi/NCM/SSH
  全部通过；两次普通重启 `taint=0`，CAMSS `suspended`，MMCX 128。

## 恢复后先做：面板候选刷入

唤醒后先只读保存日志，不再次 suspend。设备重新出现在 NCM/Wi‑Fi 后，
按[PANEL-FIX-20261109](linux-port/docs/PANEL-FIX-20261109.md)只写
kernel FAT `logdump`，boot 和 DTB 不动；写入脚本会校验大小、SHA-256、
挂载状态并整块回读。回滚 FAT 为
`1f4bbb302a62d1f8a950994ac93b00ca194a41c768d4d11b1b97c69f5702574b`。

刷入后按以下顺序验收：

1. 普通重启，确认 `/proc/sys/kernel/random/boot_id` 变化、`taint=0`、
   panel driver probe、CAMSS `suspended`、MMCX 128；
2. 用实体电源键关屏/唤醒，确认 `drm_panel_backlight` 的 100 ms/500 ms
   重发后物理屏亮起；
3. 命令唤醒后单次触摸，确认 KWin 不再把触摸序列卡住或再次关屏；
4. 安装 `samurai-desktop 4-r16` 候选，确认 `samurai-powerkey` 服务已
   停止、禁用并删除，电源键仍由 KWin/PowerDevil 正常处理；
5. 再跑设置来源、NCM/Wi‑Fi/SSH 首连时延和完整硬件门禁。

设置分层、`5-r24` 和清理步骤见
[SETTINGS-PROVENANCE](linux-port/docs/SETTINGS-PROVENANCE.md)；
PowerDevil 覆盖先 dry-run 再 `--apply`，`sshd` 的 `boot` runlevel
另案恢复官方 `default`。

## 剩余候选与未验项

- suspend：本次 `loginctl` + 直接 sysfs RTC alarm 测试未恢复，不能
  声称通过。上次干净 s2idle 用的是 `rtcwake`；物理唤醒后必须用
  `rtcwake -m mem -s 30` 复测，并保留串口/人工恢复路径。
- NFC：真实标签读写、eSE 和长时间轮询功耗未验。
- 蓝牙 PAN/HID：外部对端、配对/路由、冷启动和带业务 suspend 未验。

私有层审计覆盖 14 个 C/H、11 个 DTS/表文件，无私有 ioctl、用户态
拷贝或 Android/Binder 入口；唯一保留的旧只读面是
`sensor-power/state`。

## 已确认的网络/相机基线

- `samurai-platform` 5-r22 / `samurai-desktop` 4-r10 已安装；普通重启
  后 UDC `configured`、`usb0` carrier 1，configfs `qmult=20` 自动恢复。
- NCM 24/24、1798.828 秒心跳；Wi‑Fi 1810 样本/1820.51 秒。旧 Genesys
  Hub 的 Code 43 仍归主机/物理路径；主板直连口已通过。
- 相机四路自动 probe，flash/V4L2 boot 的 RAW 各两张 100% 非零、
  0% 饱和、帧间变化 26.012–48.634%；IMX471/S5K3M5 Selection API
  已无 EINVAL，libcamera 0.7.2 四路 640×480 RGB888 单帧成功。
- 内置麦克风 PulseAudio 连续采集 61.98 秒，RMS 15.053、0% 削顶、
  stderr 空；原始音频未保留。
- 时钟只读审计：358 个时钟中 55 个“硬件使能但无逻辑 consumer”，
  含 `gcc_cpuss_rbcpr_clk`；这不是逐项 critical 证明。

## 其余未完成

- 闪光灯拔电冷启动、重复冷启动和长时间热升；当前控制/光学/普通重启
  已通过。
- thin-private 的联合 suspend/resume、拔电冷启动和回滚演练；
- 蓝牙外部对端、音频耳机/watchdog、传感器 SSR、相机画质/录像/热功耗。
- NFC 标签、指纹认证、真实 SIM、高压充电、实体电源键、deep sleep、
  真正断电冷启动和长期功耗。
- `clk_ignore_unused` 仍是实测必要约束；无 flag 的 kexec 预检曾使
  设备离线超过 255 秒，禁止无人值守重试。UEFI/GRUB 和 RBCPR 候选
  仍未刷入。
- 真正拔除外部供电的物理按键冷启动、多次冷启动、长期 suspend/sleep
  与功耗测量仍需现场条件。

## 约束

- 不重刷/擦除 NV、persist、校准、userdata；不做 boot-only 半套部署。
- 不热反复 unbind PM8008/CAMSS；不以 OOT 模块冒充最终验收。
- 不把私密 RAW、音频或场景哈希写入公开文档。
- 根仓库有大量既有脏改动；不要 `git add -A`，不要提交无关文件。
