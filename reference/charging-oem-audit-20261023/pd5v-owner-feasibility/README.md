# 普通 5V 子流程：明确拥有的 PD-disabled 候选

本叶交付了**真实、默认关闭的 PM8150B PD 收发器控制/租约代码**，不用先移植完整 TCPM。它不是返回固定 `false` 的 permission stub，也不把既有 PHY enable=0 当作合同 inactive。当前无消费者接入、未安装、未编译/链接新 Image，保留现行 Image363 启动实验。

封存前发现并修正了一个实际边界：probe 不能直接 `regulator_enable()`，因为共享 L2 若原先真的关闭，这会在 VBUS 在线时给遗留 PD 配置上电。最终代码 probe 仅取 regulator 句柄；真正的 enable 与四个禁用写均受首次真实物理 off/vSafe0V 窗口约束。上电后再取 fresh off 样本，attach 竞争或 enable errno 立即终态拒绝，零 PD 写、不自动重试。

最终源码和 7 组/22 个真实函数测试已通过。最终两对象重编因**原 `/mnt/samurai-full282` mount 缺失**，在前置只读检查处停止；未调用可能 remount 的 helper、未建 anchor、未挂卷、未绕守卫。见 [build-result.json](build-result.json)。[build-before-power-gate-result.json](build-before-power-gate-result.json) 是上电修正之前的 W=1 两对象成功收据，**不能证明最终源码已编译**。后续只需在根会话按原 guard/原 helper 恢复原卷后补这两个对象；当前不进行恢复操作。

## 精确原厂与当前源码依据

| 范围 | 固定来源和结论 |
| --- | --- |
| 原厂真正 close | [同机官方 Android R `qpnp-pdphy.c`](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/usb/pd/qpnp-pdphy.c#L575)：`pd_phy_close:575–610` 先关软件 opened/IRQ，BIST=0，再 TX=0、EN=0，最后放供电引用。它是 void，BIST 返回值未检查，TX/EN 失败提前返回且没有 readback，不能直接当已验证完成。Android R 与旧官方 9668 该文件逐字节相同，SHA `aee34f05…01e0eeb`；原件保留私有目录。 |
| Image363 关联 qcom 代码 | 既有 `current-r7/image-source-linkage.json` 已将三个 qcom 文件与原 ba61 输入比较相等。`qcom_pmic_typec_pdphy_stop:538–551` 只停 IRQ/reset_work、TX/filter=0 后放 regulator 引用，**不清 EN/BIST**。`disable:484–494` 虽写 EN=0，却吞掉 void reset_on 的前段失败。`reset:496–508` 最后 enable，因此本候选绝不调用它。 |
| 自动 PD 生产者 | 原正常 `probe` 会注册 TCPM，`port_start` 写 TRY_SNK，`pdphy_start` 使能并开 PD IRQ。新分支位于这些调用之前并直接返回，实际同一 platform 设备已独占绑定，所以这些 TCPM/IRQ/reset_work/PD transmit 回调均未建立。不是靠另一个 shadow 设备检查“似乎没 owner”。 |
| CC / USB2 分离 | PD 写仅落在 `0x174e/1744/174c/1746`；不写 CC/角色 `0x1544`、USB2 PHY、VBUS/VCONN、DPDM 或 source budget。原厂 `pd_phy_update_roles` 的 MSG_CONFIG 供 GoodCRC 角色使用；本候选不改角色或协议头，只停整个收发块。 |
| 共享供电 | 同机 19781 `pm8150b.dtsi:608–611` 给 PDPHY 使用 `pm8150_l2`；当前源 MTP 的 `vdd_pdphy/vdda_usb_hs_3p1` 同指 L2。精确 native DTB `c559…c4503` 的 USB2 `vdda33-supply` phandle `0xc0` 指向 `/soc@0/rsc@18200000/regulators-0/ldo2`，固定 3.072V。故不能把 drop 引用当作实际断电，更不能为证明 PD off 直接切共享 rail。 |
| 真实 0V 前提 | 当前 qcom port `0x150a` bit6 是 `VSAFE0V`，bit5 是 `VSAFE5V`，其 VBUS toggle 使用该实际状态轮询。本候选要求七字段真实 detach 加 bit6=1/bit5=0，拒绝 ACOK=0 或 `get_vbus()` 读错返回0的替代。现有 003 记录没有这个 off 窗口的 vSafe0V 原件，本轮没有制造实物确认。 |
| 已有但不能当未来许可的本机值 | [R8 两次选定控制字节](../../charging-management-20261023/pd-controls-r8-result.json) 均 `0x1544=0x02`，对应 EN_SNK_ONLY、没有 SRC/TRY/DISABLE；`0x1362=0x18` 的 HVDCP AUTH bit6、AUTO bit5、ENABLE bit2 都为0，BCdetect bit3为1。所以最短路径可以**读后要求继承策略**，无需角色/QC写；每次 acquire/validate 仍必须重新实读，历史值不给许可。 |

精确来源路径、字节数、哈希、函数/行号见 [evidence.json](evidence.json)。恢复的原厂全源码保留 `E:/edk2-samurai-out/charging-management-20261023/pd5v-oem-private/`；没有将其他型号或老版本的状态当当前硬件状态。

## 代码边界与生命周期

[pd5v-owner.patch](pd5v-owner.patch) 只改 qcom 内部实现/头/Makefile；新控制代码在 [qcom_pmic_typec_5v.c](qcom_pmic_typec_5v.c)，接口在 [qcom_pmic_typec_5v.h](qcom_pmic_typec_5v.h)。完整可编程条件见 [contract.json](contract.json)。

1. 默认参数 `samurai_5v_only=false`。只有显式参数和 DT `realme,pd5v-only` **都存在**，且实际 native `realme,samurai`、`qcom,pm8150b-typec`、1500/1700 基址、无 connector 子节点和实际 USB2 同一 L2 supply phandle 都匹配，才建立特殊实例；部分 opt-in 失败直接拒绝，不落回正常 TCPM 开启路径。实际 native DT 仍 disabled，示意 [board-opt-in-design.dtsi](board-opt-in-design.dtsi) 也保持 disabled，没有生成 DTB。
2. probe 无 PD I/O、无 regulator enable、无自动 work/poll。唯一显式 acquire 先在未接触 PD 模块时取得两个稳定相同的 13xx/15xx 状态，再取得 L2 enable 引用。500ms 稳定和250ms fresh 是本候选保守工程值，不是原厂时限。上电后每步都重读 fresh off/policy，按 **BIST→TX→filter→EN** 写0，检查每步 write errno、直接 readback 和完整 post off 状态。未知保留真实错误；不会继续写完、自动重试或恢复为旧启用状态。
3. 成功后 `qcom_pmic_typec_5v_acquire(actual_typec_device, client, lease)` 才提供单 owner lease。实际设备必须在本驱动的真实绑定 registry 中；短 registry 锁只保护 lookup/kref，不跨 I/O 或 join。`try_module_get()` 在任何 I/O 前取得，lease 持 kref/module 引用，直到 release。
4. `validate()` 必须使用唯一实际 lease 对象和当前控制 generation，重新读 disabled/sink-only/QC-off。它证明的是 **PD-disabled 控制代**，不是物理 attach epoch。会话仍必须在唯一真实 bus 写前核自己的同代物理源、sink、DWC/PHY/EUD 和 route。负值必须 unwind。
5. system PM prepare、shutdown/remove 先 block 新 acquire、递增 generation，再在本组件锁外调用实际 client `cancel_join`。join 必须结束并释放 lease；失败保留 EBUSY/blocked，不假报结束。实现不用 runtime `device_lock` lookup，因此不会与 generic PM.prepare 持 device_lock 的 cancel+join互等。恢复只读验证，掉电/控制失配保留错误，不自动 enable/reset/重写。第一次 off 尚未发生时的正常待机只暂停等待，不永久放弃。
6. 本特殊分支不启动 runtime PM 或 runtime 断电路径。未来新增该路径必须先撤租约/join，再恢复验证，不能偷偷继承 TCPM 的供电语义。remove 撤销实际 binding，取消使用者并按真实引用计数收尾；不会重新启动 PD。普通 qcom 分支原 probe/remove 尾逐字保留，新增 PM/shutdown 对普通实例都是空操作。

所有控制写都是禁用零值。它没有 `CMD_APSD`、HVDCP/QC 命令、PD TX、VBUS/角色切换、GPIO、预算升级或充电器写接口；不改 R8、provider、保护阈值、现 Image、EUD/DWC/PHY 冻结组件或任何共享源码/配置。

## 证据与剩余边界

[test-result.json](test-result.json) 的 7 组直接编译/执行最终真实函数（22 个），只 fake Linux/OF/regmap/regulator 边界：真实 probe opt-in 及默认尾、四写顺序/读回、vSafe0/CC/QC拒绝、module GOING 零 I/O、逐步写错/读回错及未知位、首次上电错误/上电后 attach 竞争零 PD 写、fresh 超时、post attach 竞争、PM撤销/失败join/恢复失配、真实设备匹配和引用收尾。ASan/UBSan、`-Werror` 通过；它不是并发全证明或实物电气验收，旧 126/PD/充电/保护大套没有重跑。

供电改变与物理拔插不可能由这些 regmap 操作原子化；fresh gate 后仍可发生电气竞争。代码将 post 失配记为终态失败，不能把它说成“已保证拔线中写”。同样，当前没有任何活设备 vSafe0V、四次禁用读回、PMIC latch/中断或新 attach PD TX 测量；源码也不证明任意外设提供的电压一定是5V。VOOC MCU 的 rail/firmware/自主行为没有在本叶取得控制，不能用“PD关闭”冒称全部快充协议已禁止。

当前 `CONFIG_TYPEC_QCOM_PMIC=m`，新接口没有 EXPORT，也没有自动消费者。现 provider/DWC 不能跨模块直接调用这些私有函数；未来若采用，需一致的内建或明确同组件链接方案、新板级绑定及独立复核，**不能只塞一个新 ko 到当前环境**。完整 PD/VOOC、DPDM 路由、APSD rerun/session、USB500合法授权、实际充电图标和低功耗验收仍未完成。

下一最小动作是补最终两个私有对象编译收据与独立代码复核；之后才可能在另一协调窗口取得真实 physical-off/vSafe0V→禁用→新 sink attach 的原件。当前没有运行候选、申请设备窗口、刷写、重启或调用 USB/SSH/SDK/Git。
