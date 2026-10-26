# 保护查询剩余项：现有证据与不能恢复的语义

本轮结论是**没有证实生产 TCA 分类错误，没有生成生产 patch，也没有扩展查询白名单**。现有普通充电遇到 TCA 会停充，保留 raw bit 和既有 fault/timeout；不把它当作正常 Full。本目录只有已有六份实际报文回放、两个原厂安全查询函数的直接执行、21 项受影响边界与来源记录。未查手机、0050/0056、PF_EN、FET、NVM/OTP 或解封；未运行旧 2027/154/910 套件。

[result.json](result.json) 固定本轮输入和测试摘要；[audit.py](audit.py) 可离线重现。[test-query-evidence.c](test-query-evidence.c) 直接包含生产 `gauge-protocol.h`、R7 `mp2650-core.h/oem-full-cycle.h/charge-cycle.h`，两个原厂函数从固定源码按函数范围提取到 `oem-query-extracted.inc`。总线、等待与日志仅替换为内存桩，不调用设备；没有生成新的 MAC 包。异常位输入明确是软件状态向量，不是实物故障记录。

## 先确定本机和实际调用

原厂来源固定为 `realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source` 提交 `23172a1571bd91156032cc9fef16284a82b63d2c`：

- `drivers/power/oppo/gauge_ic/oplus_bq27541.c`，SHA `0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87`。
- 同路径头文件，SHA `58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e`。
- 本机原厂 DT 的 `qcom,batt_bq28z610` 及 legacy `0xFFA5` 是家族/接口匹配依据，扩展 DeviceType 实际为 `0x2719`；**不能据此确定精确型号、固件版本或自动接受标准 TI 2610 的所有状态位**。已有 `reference/kernel80/source-references.json` 与 `reference/kernel85/source-audit.json` 记录这一边界。实际 FirmwareVersion 的 11 字节 payload 没有可靠格式映射，继续保留原件，不按猜测字节序解成型号。

当前保护 provider `samurai-gauge-protection.c::sm_protection_read()` 只以一个 I2C segment lock 串行读 `0001/0051/0053/0054/0057`；每帧经 `sm_gauge_mac_locked()` 检查完整 36 字节、echo、精确有效长度、固定偏移 checksum。读取失败不返回 cached Good。charger 的 `sm_gauge_sample()` 在同一段锁下读 `0x06/0x08/0x0a/0x0c` 和 `0071`。它的 `sm_collect()` 先取得真实 source/ACOK/预算及 protection 健康，单一拥有 REG14 清故障读并缓存，再进行完整策略；本审计没有额外读取 REG14。

R7 和冻结 R8 均在策略中先检查 fault/OCA、已有超时、来源/全局电芯一致性，再处理 `0x0a` TCA bit14。TCA 输出 `-EAGAIN + SM_POLICY_REASON_GAUGE_CHARGE_STOP`，停止 CHG/输入转换器，可后续重评；`sm_sample_latch()` 保留旧 latch。Full helper 遇 TCA 即 `stop_all`，即便同次 hardware_full 也不能建立新 Full/再充；已建立 Full 事实可保留，但不会以它越过 TCA。这些路径分别直接执行，不只是重新实现一个“参考分类器”。

原厂头文件的 `BQ27541_FLAG_FC=BIT(9)` **不能移植**为本机 `0x0a` 的 FC：它服务多种 gauge，`gauge_set_cmd_addr()` 是通用兼容路径；`bq27541_get_battery_fc()` 在 BQ27541/ZY0602 分支直接返回 -1，后续还排除 `batt_bq28z610` 的正常读值返回（447–475 行）。它不是本机可靠的 Fully Charged 位解码证明。当前生产没有把该 bit9 用作 Full；普通 Full 使用真实 MP2650 REG13 和已移植 OEM 软件证据。

## 六份实际报文能可靠恢复的内容

原件 `window2/fixed-query-private.json` SHA `8858bfa3fa9914a6f92262f549257c2dc22c037c1e1b9d95c9aaf06292a40d96`；六份原始帧 fixture SHA `662254550a4f08ed8d0b1f9b1b58139e10cec0ceace5d2b222c438730d7d5ca2`。本轮只读原件，不重写 fixture。

| 命令 | 实际值/长度 | 可以确认的范围 |
| --- | --- | --- |
| 0001 | `0x2719`，payload2/length6 | 本机扩展协议身份；不能映射精确硅片/固件 |
| 0051 | `0`，payload4/length8 | 当前 SafetyStatus 原始值为0；并不排除预触发 SafetyAlert |
| 0053 | `0`，payload4/length8 | 当前 PFStatus 原始值为0；不代表 PF 功能已启用或所有阈值合格 |
| 0054 | `0x00000386`，payload4/length8 | OEM `bq8z610_sealed()`（2184–2202）从 echo 后第2 payload字节低2位确认 sealed；直接喂本包返回1 |
| 0057 | `0x0018`，payload2/length6 | OEM `bq8z610_check_gauge_enable()`（2406–2426）取 payload低字节 bit3，直接喂本包返回1 |
| 0071 | payload32/length36 | OEM `bq28z610_get_2cell_voltage()`（2468–2498）读最前4 payload字节的两个 LE16 电芯电压；剩余 payload 不自行赋义 |

另有原厂 `bq28z610_get_balancing_config()`（912–955）直接将 0054 的 payload 按 LE32 解释并读取 bit28 Cell Balancing。这是可以复用的准确 OEM 语义；不是需要新增查询的缺口，当前无需为了“补齐”再增加控制行为。原厂 current 名称同样不能照字面移植：`bq27541_get_average_current()`（1207–1233）在 legacy FFA5 映射处（1590–1592）实际读取 `0x0c`，且 API 对有符号净电流取负；现生产采集已按原始正=充入保留，未用 `0x14` 平均电流代替。

实际同批 BatteryStatus=`0x00c0`，TCA/OCA/FC 均0，DSG=1。**这些包没有一次 TCA=1 的自然终止/保护事件**，因此不能用它们来“确认”正常 TCA 因果。

## PF_EN=0 的准确范围

0057 原始 `0x0018` 的 bit6 为0；标准 TI SLUUA65E §12.2.33（PDF89–90页，当前 text4092–4094）将其命名为 PF_EN、0=Disabled。OEM源码直接验证的是 GAUGE_EN bit3，不提供 PF_EN 的本机更详细例外说明。当前 `pf_enabled=0` 是该继承位的只读报告，生产没有启用它，也未把它作为“已启用 PF”的通过条件。

据此可以说“PF_EN 继承0，尚无永久故障功能开启的证明”；不能说“PFStatus0 已验收永久保护”，也不能反向扩展成“所有硬件/一级安全保护都关闭”。SafetyStatus、自动 FET、MP2650 NTC/终止/安全计时有各自语义，PF_EN 位本身不能证明这些功能被改变。当前无资料允许安全地推导本机每个永久故障条件的使能例外和具体阈值，不读取 DataFlash 来凑资料、不写 bit6。

## 0050/0056 为什么仍不能离线结案

唯一完整 TRM 是 TI 官方 BQ28Z610 SLUUA65E（June2023），PDF SHA `f62ec12bb5aa23631759e59a378f36d254f9b0e2b5b6b8523a0dd081a13e4139`。它说明标准接口：

| 标准命令 | payload/length | 可恢复的标准定义；本机适用门槛 |
| --- | --- | --- |
| 0050 SafetyAlert | 4/8 | 保护延时 trip 前可告警；TCA 可由 OCC/COV/OTC 引起。没有本机报文 |
| 0056 GaugingStatus | **4/8** | 第4字节保留，不能误缩为3/7；TC bit3、FC bit1、DSG bit6，QEN bit12。没有本机报文 |
| 0052 PFAlert | 4/8 | 当前未采集；若未来要排除正常终止外的预警，不能只看 PFStatus0 |
| 0055 ChargingStatus（可选） | 2/6 | VCT bit15；同样未采集，不能冒充当前已有独立终止证据 |

TI §4.8（PDF27页；当前 text1233–1248）将 TCA 来源列为 SafetyAlert 的 OCC/COV/OTC，或 GaugingStatus.TC 且处于 CHARGE 模式。0054.CHG bit2 是 FET 状态，**不是**此充电模式；§4.6还允许正常 TC 后按配置关闭 CHG FET。因此 SafetyStatus=PFStatus=0、Operation.CHG=0/1、SOC100 或电流0都不足以解释 TCA。

当前固定 OEM gauge/header 中未找到 0050/0052/0055/0056、SafetyAlert、GaugingStatus、TCA 或 PF_EN 的分类实现；不是用相近 TI 型号填补原厂缺失。已有 `../tca-classifier/tca-reference.h` 的纯解码候选和分类规范可复用，但它的 `compatibility_verified` 仍须外部真实证据，不能因为完整36字节/checksum通过而自动设真。标准 Operation.EMSHUT、INIT 或其它未映射高位也不能直接按另一型号当本机已验证故障来扩展 mask；同样不能据现有 mask 的接受结果宣称这些高位都安全。

未来若根会话另行取得设备窗口，最小补证仍是已有 MAC 段锁所有者的一次只读批次：同身份和前后稳定 BatteryStatus；0050/0056（必要时0052）完整36字节原包；既有 Safety/PF/Operation/Manufacturing、温度/电芯/净电流/来源许可与缓存故障年龄。首个全0帧只能确认帧兼容，仍不能证明 TCA 正常终止；还需自然 TCA/TC 的关联和独立真实 Full/VCT 证据。旧用户态 `query-fixed-telemetry.py` 运行时还没有当前两个内核 MAC 工作队列，**不能直接拿来新增裸 I2C 查询**；每次 transfer 串行不等于 selector→读回的整个 MAC 事务有段锁。任何长度、echo、checksum、模式或兼容性异常都应保存原件并停止，不循环重试凑预期。

本轮不修改 timer：TCA hold 不表示已完成周期，也不允许调用正常 Full reset。当前易失周期的累计/暂停选择属于独立状态机范围，不能通过把 TCA 冒认 Full 来解决长期停充挂线问题。未来即便证明正常 TC，仍必须保留已成立 fault/timeout，且 TCA 未自然清除时不得授权再充。

离线复现：

```text
wsl -d Ubuntu -u root -- python3 "/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/protection-query-candidate/audit.py"
```

实际6包、21项定向检查及两个原厂查询函数执行通过 ASan/UBSan。结论的范围是恢复来源与确认当前保守行为，没有新的保护物理验收，也没有供部署的新查询模块。
