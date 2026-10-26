# R8 只读 PD/USBIN 配置快照与原厂 Type-C 初始化对照

新的可确认差异是 **当前 0x1358 bit7 仍为 1，与同机原厂 Type-C 初始化要求清零的后置条件不符**。这已经从此前“没有执行初始化的源码差异”，推进到两个相邻实测快照的状态差异；它仍不是 SDP 分类错误的因果证明。

`result.json` 绑定根会话已完成的 `pd-controls-r8-result.json` 原件哈希 `b31b31b10caa02477fb7be79b9c825e9aefc01b584a9424ec710e612ca13a65d`、固定 OEM commit `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的三个完整源文件以及两个原厂完整函数。此目录仅解析本地缓存；没有连接手机、重跑旧函数套件或写寄存器。

| 项目 | 原厂源码 | 新快照及可得结论 |
|---|---|---|
| 0x1358 bit7 | `smb5-reg.h:282` 的 `TYPE_C_CFG_REG = USBIN_BASE + 0x58`，bit7 是 `BC1P2_START_ON_CC_BIT`；vendor 的 349/350 行又以 `APSD_START_ON_CC_BIT` 命名同一位 | 两次都是 `0xc0`，bit7=1；这是 USBIN 外设的检测触发配置，不是 0x15xx 的 Type-C 角色寄存器。 |
| Type-C 初始化 | `qpnp-smb5.c:3285` 完整 `smb5_configure_typec`，读取 legacy 状态、处理有条件的非 PD legacy 角色恢复后，在 3324→3328 依次启用 BC1.2 source detection、关闭适用的 HVDCP detection、masked clear bit7；这个 clear 不在 micro-USB 分支 | 当前不满足成功执行此 Type-C 配置后的 bit7=0。只读 provider 没有 0x1358 访问或 PMIC 写入，不能自行补齐该状态。 |
| vendor fake-TypeC fallback | `smb5-lib.c:7172` 的 `typec_disable_cmd_work` 仅在 Type-C mode 为 NONE、关/开 Type-C 并等待后仍为 NONE 时，于 7197 清同一位，然后等待 600ms、记录 fake insertion | 这是另一条有条件的原厂调用，不能因为当前 bit7=1 就照搬角色切换或伪造 fake insertion。该分支日志用“enable”字样，但实际 masked-write 数值是 0，应以代码为准。 |
| 0x1362 bit3 | `BC1P2_SRC_DETECT_BIT` 是 `BIT(3)`；`smblib_apsd_enable(true)` 设置它 | 两次 `0x18` 的 bit3 已为 1。不能再把当前状态描述为“BC1.2 source-detection enable 缺失”。bit7 是另一个配置条件。 |
| APSD 状态/结果 | 已有同机解码为 SDP | 两次 0x1307=0x11、0x1308=1。结果与控制配置的同时出现不证明因果，实际普通 SDP 口仍是可能解释。 |

调用该 Type-C 配置的是 `smb5_init_hw` 中实际 connector-type 选择（`qpnp-smb5.c:3780` 起）；非 PMI632 同样走 `TYPEC_U_USB_CFG_REG` 决定 Type-C/micro-USB，并不是将 micro-USB APSD rerun 套用本机。上游已缓存 v4 SMB5 提案也将清 bit7 与“charger USBIN 如何启动 BC1.2”对应，并单列 TCPM 对 Type-C 外设的所有权，但它不是本机运行实现，不能替代同机证据。

可准确写入差异清单的是：“当前配置未达到原厂的 start-on-CC 清零状态；现只读 provider 缺少负责达成该状态的生命周期动作。”不能据此声称历史上从未执行过 OEM 初始化，也不能仅凭位名推断所有硬件触发时序、断言软件 rerun 必然被该位阻止，或预测清位后主机一定从 SDP 变成 CDP。

根会话同时观测到 0x1746/0x1744/0x174c/0x174e 为 0，可成为未来 owner 的独立新鲜前置数据；它们不证明 bootloader 合同 inactive。DWC HALT 和 EUD 软件 quiet 也各自只证明本组件状态。未来要实施 masked clear 或 APSD rerun，仍需同一事务中复核 PD/角色/route、持有 DWC/EUD token、建立 PHY 高阻及恢复顺序，保存被改位的实际旧值并处理退出失败。此相关审计没有产生硬件写候选，也没有扩大 DWC 窗口补丁。

后续更正：上一段把单 bit 初始化与主动检测混为同一前置，范围过宽。新完整调用链复核见 [start-on-CC 最小作用范围](../start-on-cc-scope-r8/README.md)：物理 offline 稳定期的 `0x1358[7]` 单独 masked 初始化按该新范围处理，不必等待完整检测链；主动 APSD rerun、PHY 或 route 操作仍需完整 owner。带 VBUS 在线清位无间接自动触发尚未证实。此更正不改变本轮观测事实或 `result.json` 绑定哈希。

复核入口：`python3 audit-observation.py`。脚本校验原厂文件/完整函数哈希、两份快照及只读 provider，不执行新的设备操作。`passed=true` 仅表示这些本地来源和断言一致，不是 APSD 或充电实机验收。
