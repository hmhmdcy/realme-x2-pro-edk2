# 0x1358 bit7 初始化的最小作用范围

结论：**源码支持把这一位作为独立 USBIN 初始化修正审查；此前把任何 bit7 改动一律绑到完整 DWC/EUD/PHY 检测窗口，超出了已知证据。** 这澄清并替代 `../pd-controls-r8-correlation/README.md` 末段对所有 masked clear 的笼统前置要求。它不等于已经证实当前带 VBUS 在线清位无副作用。

唯一原厂操作是 `regmap_update_bits(map, 0x1358, 0x80, 0)`。同机 `smblib_masked_write` 144–147 行只是这个 regmap 操作的薄封装，没有命令、延时、role、PHY、DPDM、PD 或预算调用。给定已观测的 `0xc0`，此 mask 的数值结果是 `0x40`，保留其余位；这不是把整字节写成固定默认值的授权。

## 同机原厂调用顺序

固定 [OEM commit 9668fcdc](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/tree/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6)，完整函数及各自哈希在 `oem-scope-functions.inc` / `result.json`：

| 顺序 | 位置 | 实际动作 |
|---|---|---|
| 1 | `qpnp-smb5.c:6061` | probe 调用 `smb5_init_hw`。此前 `smblib_init` 初始化 work/锁/notifier；其完整函数不调用 `smblib_request_dpdm`。 |
| 2 | `qpnp-smb5.c:3816` | 实际 Type-C 分支调用 `smb5_configure_typec`，不是 micro-USB 分支。 |
| 3 | `qpnp-smb5.c:3324–3328` | 先 `apsd_enable(true)`，再适用的 `hvdcp_detect_enable(false)`，然后单独 masked clear start-on-CC bit7。clear 本身不取得 DPDM，也没有 DWC/EUD/PHY token。 |
| 4 | `qpnp-smb5.c:6182` / `4273` | 初始化后才执行 `smb5_determine_initial_status`，其中显式调用初始 `usb_plugin_irq_handler`。 |
| 5 | `smb5-lib.c:5270` / `5113` | 正常插件路径调用 `smblib_usb_plugin_locked`，VBUS rising 分支才 `smblib_request_dpdm(true)`。hard-reset / 双电芯 DFP 假插等分支可跳过，不能无条件宣称每次都取得 DPDM。 |

`init_hw:3832` 的早期 APSD rerun 是明确的 PMI632 专用块；PM8150B 不走它。上述顺序证明这份显式 probe/initial-plugin 路径将 bit7 clear 放在后续 DPDM 请求之前，不能推导固件此前从未开启过模拟通路，亦不保证其它异步固件状态不存在。

## 缓存的同 SoC 上游提案

已固定的 [2026-08-20 SMB5 v4 提案](https://lists.openwall.net/linux-kernel/2026/08/20/748)，Message-ID `20260820-submit-qcom-smbx-send-v1-v4-2-818dabb2771e@snyders.xyz`，base `99b38cda3f4c486cfbc40f3c8ede1703594e9f13`，HTML SHA `695d810663f59a1ffe31ed86ac78e07b3a9b013f890f8243c684300d9a1da6e4`：

SMB5 `smb5_init_seq` 第一项就是 `USBIN_TYPE_C_CFG` / start-on-CC masked clear，第二项才配置 source detection。`smb_init_hw` 按数组顺序逐项 `regmap_update_bits`，没有 DPDM、DWC 或 EUD 窗口调用。提案明确把 USBIN 的 BC1.2 启动配置与 TCPM 所有的 0x15xx、PD PHY 0x17xx 分开。这支持它的初始化作用范围，不支持把完整 Type-C 角色函数搬过来。

必须保留上下文：v4 probe 在执行这整个 init 数组前先保存并 suspend USB input、关闭其**内置** charging。它不是在本机外置 MP2650 的当前运行状态下做单 bit 在线实验的证据。这些其它写入也不属于当前最小修正范围。相应原始片段在 `v4-scope-excerpts.txt`。

## 可以证实和仍未知的边界

可以证实的是：此操作是 USBIN start-on-CC 配置，既不是 `CMD_APSD`，也不直接写 Type-C role、PD、PHY、DPDM regulator 或输入/充电限值。独立、精确 masked clear 有原厂和上游初始化依据，完整检测 session 不是这些源码为这次配置写规定的必要接口。

**不能证实它“只关闭触发且在线绝不会自动开始检测”。** 位名与提案注释描述的是 BC1.2 如何开始；缺少对应硅片的完整触发语义说明。同机 vendor fake-TypeC fallback 在仍无 Type-C mode 时清同一位，再等 600ms 并报告 fake insertion，也不能排除清位改变自动启动条件。没有显式 CMD 不代表硬件没有间接自动行为，更不能保证 SDP 会变成 CDP。

因此可将闭环缩到单独的有界初始化事务，而不等待整套模拟检测窗口：保持所有其它动作不变，在独立确认的物理 offline 稳定期只改这一位、核对 readback 与原值并记录结果；确需恢复时也只恢复保存的该位，不能把整字节旧快照覆盖其它状态。实际事务的 identity、物理 off 新鲜证据、唯一 writer、执行窗口和失败处置由主会话/独立候选实现，此审计没有执行它。带 VBUS 在线清位的安全性仍未经验证，完整 session 仍留给明确的主动 rerun / PHY / route 操作。

`python3 audit-scope.py` 只校验本地固定源字节、完整函数与实际调用顺序，不运行旧测试矩阵，不连接或写设备。`passed=true` 表示源码作用范围断言一致，不是实机初始化验收。
