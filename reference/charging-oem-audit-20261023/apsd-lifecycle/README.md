# 本机 PM8150B 的 APSD / DPDM 生命周期差异

本目录仅离线源码恢复与定向验证，未 SSH、未访问手机/SDK、未修改共享源码、R7 或 usb500 诊断候选，未写硬件。恢复的是同机原厂旧下游固定提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6`，不是将它冒称当前 AndroidR 或正在运行的原厂固件。完整文件来自既有 bare git 对象；smb5-lib.c SHA 与此前 FLOAT 审计的 `5203488026f12fddc65ca899f16c8eb461e0da08dc151c4c5be18501204342a8` 相同。出处、完整函数行号与 SHA 在 `source-manifest.json`。

## 新发现及当前能下的结论

根会话提供的新实际状态是 boot 时 CDP / 1.5A，实体重接后为 SDP、native100mA、APSD_STATUS `0x11` / RESULT `0x01`。这些硬件状态不同于先前 FLOAT `0x21/0x10`。此处不重做 FLOAT 分类或图标语义审计。

**本机原厂存在每次插入会重新武装的一次 SDP/CDP APSD 复测；当前只读 provider 没有实现这条生命周期。** 这不是从 `uusb` 变量名推断：原厂 Makefile443–446 全局定义 `VENDOR_EDIT`，其 source-change IRQ 的 vendor 条件移除了非 vendor 的 MICRO_USB 限制，因而同样覆盖本机 Type-C。`usb_source_change_irq_handler`5458起：未处于 PD/两芯OTG/fake insertion，APSD DONE 且本轮尚未复测、result 含 SDP 或 CDP 时，先置 `uusb_apsd_rerun_done=true`，再通过完整 `smblib_rerun_apsd` 写 `CMD_APSD(0x1341)` bit0，立即返回；该次不消费 APSD 完成、不发送后续 supply_changed。下一次完成才进入正常处理。DCP/FLOAT 不在该 vendor 一次复测条件内。

这证明“原厂会采取而当前没有的动作”，**不能证明当前 SDP 是错判，不能保证复测会变回 CDP，也不能据此授予500mA**。`0x11/0x01` 本身是已完成的 SDP 结果，可能符合当前实际口/线/中间设备。必须分别保留 BC1.2 结果与 USB 主机 native 授权。

## 19781 实际连接及调用顺序

| 阶段 | 同机原厂完整函数与条件 | 当前 provider |
|---|---|---|
| Type-C 初始化 | `smb5_configure_typec`3285：启用 `0x1362[3]` BC1P2 source detect，关相应 HVDCP 检测，清 `0x1358[7]` start-on-CC；另有 Type-C/VCONN/角色设置，不能整体抄入 | 不读取/设置这些配置，不拥有角色 |
| boot 已接线 | `smb5_determine_initial_status`4256先读 present，依次重放 plugin→Type-C attach→state→source IRQ；后者可走上述 Type-C vendor SDP/CDP 复测 | 仅启动1Hz只读采样，没有等价初始化/IRQ重放 |
| VBUS 上升 | `smblib_usb_plugin_locked`5080：排除原厂 fake insertion；取消 PR detach work；`smblib_request_dpdm(true)` 后才继续后续管理 | 没有 DPDM owner/供电引用/高阻交接 |
| 第一次 SDP/CDP DONE | source-change IRQ 一次 rerun，等待下一完成再发布 | 立即把当前 raw 分类供上层读取 |
| VBUS 下降 | plugin5140起：重置 fastcharge/chargerID相关状态，在5160附近清 `uusb_apsd_rerun_done`，5211 request_dpdm(false) | 清 native valid、报告断线；没有 DPDM release / APSD once 状态 |
| Type-C 真 detach | `typec_attach_detach_irq_handler`6075：按原角色退出；若不在 PR swap，清 session角色状态并 `smblib_apsd_enable(true)` | 没有 PD/PR swap 所有权 |
| PD active | `smblib_set_prop_pd_active`4320将 APSD 设为 !pd_active；source IRQ 对 PD 直接返回 | 七字段没有独立 pd_active/pr_swap/hard_reset |

不能把 `smb5_init_hw` 中 **PMI632-only** 的显式 boot rerun 移植为本机 PM8150B 的证据；本机上述 boot-source IRQ 链才是相应依据。不能把 `smblib_rerun_apsd_if_required` 当作 vendor source IRQ 的实际直接调用：vendor IRQ 在匹配 SDP/CDP 后直接调用 `smblib_rerun_apsd`；该 helper 在其它调用点才按 present/type 使能 DPDM 再 rerun。

[19781 sm8150-pmic-overlay.dtsi157](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-pmic-overlay.dtsi#L157) 的 `pm8150b_charger.dpdm-supply` 明确连接 `usb2_phy0`；[sm8150-usb.dtsi147](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-usb.dtsi#L147) 是 `0x88e2000` 的 `qcom,usb-hsphy-snps-femto`，同文件35行 USB 控制器也引用此 DPDM supply。

DPDM 在这里是 PHY 检测模式接口，不能当作普通电源轨。[完整原函数](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/usb/phy/phy-msm-snps-hs.c#L633) 在 `phy_lock` 内先开 PHY 电源、时钟、reset，再设 `PHY+0x64` mask0x0c/value0x0c、`+0x3c` mask0x18/value0x08、`+0x94` mask1/value1，使 UTMI non-driving / D+/D− high-Z，最后标记 dpdm_enable。disable在无 cable_connected 时才关时钟/电源；有线时只释放 dpdm_enable，不能据此假定它恢复全部 data override。

[dwc3-msm.c3827](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/usb/dwc3/dwc3-msm.c#L3827) 的 extcon 分支明确在 DPDM enabled 时避免控制器/PHY reset，并注册 regulator notifier 等 release 后恢复状态机。故需要 PHY+USB 控制器配套，不只是 SMB5 一个寄存器位。

## legacy、mux、角色与锁前提

原厂 `typec_src_insertion`（对端是 source，本机是 sink）读取 `LEGACY_CABLE_STATUS(0x150d)` bit1，保存在 typec_legacy，再结合 pd_disabled / early_usb_attach / pd_not_supported 决定能否走 PD。`smb5_configure_typec` 的 disable→50ms→dual 来回切角色仅针对 pd_not_supported 且 legacy 的特定初始化问题；不允许把它套到当前连接。vendor `typec_disable_cmd_work` 在插入后500ms/boot已接1s只针对 typec_mode NONE 的异常场景切Type-C，仍不是普通 SDP 的复测前置。

detach 的 `oppo_chargerid_switch_work` 调用 `smbchg_set_chargerid_switch_val(0)`，后者要求实际GPIO/pinctrl存在，并在 adapter-fw-update 或 BTB overtemp 时拒绝，受 pinctrl_mutex 保护。它不是 EUD enable 位；不能仅凭名字把 chargerID、DPDM高阻模式与 EUD hub 归为同一个可替换 mux。此目录保留完整函数，未提出搬动任何 GPIO。

此旧版 `smblib_request_dpdm` 无 dpdm_lock：它只在 pr_swap_in_progress 时直接跳过；`phy_lock` 只保护实际 PHY enable/disable，regmap_update_bits 只序列化单次寄存器更新。原 threaded IRQ 的 IRQF_ONESHOT 只覆盖同一个IRQ，**不是 plugin/source/PD/role 回调之间的完整事务锁**。未来迁移应由单一 session owner 串行化实际 attach/detach、一次复测和 PD/role/PM取消；引用现 provider 的 input->lock 并不能证明与 DWC、PHY、charger 的锁序无环。不得在持 input getter锁时执行 PHY reset、role变更或可反向调用 supply 的动作。

原厂还存在需要改进而非照抄的失败语义：request_dpdm enable失败后 `smblib_rerun_apsd_if_required` 仍继续；source IRQ 先消费 once 标志再调用返回 void 的写函数，写失败只记录；result寄存器读失败没有阻止后续 handle。7组实际原函数测试已展示这些路径。未来候选必须保留错误、禁止以 attempted 当 completed、维持已授权保守预算，不能暗中无限复测。

## 可复用的最小完整恢复边界

`oem-functions.inc` 恢复25个完整函数；`tested-oem-smb.inc` / `tested-oem-phy.inc` 为其中实际参与定向执行的8个完整函数，`oem-registers.inc` 保留31条原始定义，均有原行号/hash。它们是可审的源码恢复包，**没有可部署的硬件写 patch**。原因是当前尚缺以下可证明的所有权接口：

1. 实际 R7 generic PHY 的 DPDM高阻进入/退出接口及平衡电源、时钟、reset生命周期；
2. DWC与EUD真实数据路径的停用/恢复交接，不能在活跃USB数据上强置non-driving；
3. 独立的 Type-C sink/PD/PR-swap/hard-reset 状态与取消接口；
4. 每次实际detach重置的一次复测状态、等待新DONE而非复用旧result、写/检测失败的终态；
5. 只触及 BC1.2 位的作用域，不能移入原厂 Type-C角色、VBUS/QC、内置充电器或电流升级策略。

完整最小软件方向是恢复 PHY 的 DPDM owner + USB协调，然后在单一输入 session owner 内接入 BC1P2 enable / one-shot rerun / detach reset。R7 provider 仍宜保持只读，不将纯 decoder 改成隐含的硬件控制者。保持原有MP2650/两芯保护、CC250/input900帽及native授权上限；复测后的预算也只能来自新的真实判别/授权。根会话正在独立评估 EUD 常态off，此恢复包不将它与R7/USB500单次诊断一起部署。

用于对照的同SoC公开方案是 [2026-08-20 v4 SMB5 提交](https://lists.openwall.net/linux-kernel/2026/08/20/748)，Message-ID `20260820-submit-qcom-smbx-send-v1-v4-2-818dabb2771e@snyders.xyz`，基于 `99b38cda3f4c486cfbc40f3c8ede1703594e9f13`；缓存与SHA见 `primary-comparison-manifest.json`。它说明保留TCPM/PD PHY/VBUS独立所有权、USBIN `0x1358` 与Type-C `0x15xx` 区分。该patch涵盖内置充电器配置，不适合整段用于本机外置MP2650；其中AICL周期不是APSD重测。它也不能证明本机EUD拓扑的行为。

## 因果证据的限度与验证

EUD hub可改变USB数据拓扑，DPDM高阻与APSD也依赖实际D+/D−状态，二者有合理交互可能。但现有证据没有同一物理口/线、受控EUD状态、同一检测初始化下的对照，也没有APSD每轮开始/完成与D+/D−模拟波形。boot CDP→实体重接 SDP不足以区分真实普通下游端口、固件继承状态、检测初始化缺口或EUD交互。此处不将可能性写成根因，不以结果SDP作为强制rerun理由；后续试验必须逐个变量独立验证，普通口可合法继续SDP100。

`test-result.json`：7组小定向测试通过，执行完整原厂 Type-C IRQ/request/rerun/enable及PHY enable/disable/is_enabled，fake仅限寄存器、regulator、PHY OS边界。ASan/UBSan与-Werror通过；另逐字核25个恢复函数的原文件行号/hash。覆盖首轮0x11/result1、CDP、第二完成、PD/两芯OTG/fake拒绝、读写错误、缺DPDM、enable失败、PHY三步顺序与mutex、连接/断开release及失败状态。没有重跑12768+14旧套件，也没有扩大枚举矩阵；这些软件测试不代替未来物理验收。

当前source354只读挂载在本次审计中途消失，未为此重挂或调用SDK。较早读取和历史缓存显示 generic femto-v2 没有原厂DPDM regulator接口，但本目录 `current/cached-femto-v2.c` 明确只是历史缓存，**不是已重新固定的R7当前PHY字节**。未来写候选前必须由根会话从受控源码再核实。固定v6.17官方raw比较取回遇429，已记录失败，未冒用缓存作官方版本。当前provider C/header只从本地既有文件复制并逐hash记录。
