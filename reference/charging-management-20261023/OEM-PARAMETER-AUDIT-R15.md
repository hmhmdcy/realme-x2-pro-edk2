# RMX1931 / Realme X2 Pro 原厂充电参数审计（R15）

日期：2026-10-28  
范围：只读取证；未修改源码、未构建、未刷机、未访问手机。  
结论级别：

- **A / 已证实**：原厂分区提取物、官方源码、器件数据手册或现场寄存器直接证明。
- **B / 高可信**：固定官方源码加上板级 DT/现场读数一致，但缺少完整出厂写入轨迹。
- **C / 约定**：由芯片寄存器定义或 Linux power_supply 语义得出，不能替代整机实测。
- **D / 推断**：仅用于收敛方向；不得当作出厂常量。

## 1. 来源与完整性

| 证据 | 路径 / 版本 | SHA-256 | 级别 |
|---|---|---|---|
| 原厂 DTBO entry0 | `E:\RMX1931_decrypted\dtbo_entry0.dtb` | `c3a4895ff04015f9810ce1413b3079bbd8ff742dd2499c87232ac17d2e7a5d04` | A |
| 原厂 DTBO entry1 | `E:\RMX1931_decrypted\dtbo_entry1.dtb` | `880d90066799c099a0bb3070a6461506860d12394891339bc9f9c6632489bd0a` | A |
| 原厂 boot DT | `E:\RMX1931_decrypted\boot_dtb.dtb` | `64dce2aa88e3dcda6c7c1eb9bbd324d979f60702434ae2651c60bdbe928f2b26` | A |
| 官方 Android R 电源 DT | `E:\edk2-samurai-out\kernel83\realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--arch--arm64--boot--dts--19781--pm8150b.dtsi` | `43d554879e68bb9b7795d7fb37530dfe6a5ce6cc6aae42514057e757079140c8` | A/B |
| 官方 MP2650 驱动 | `E:\edk2-samurai-out\kernel83\realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--charger_ic--oplus_mp2650.c` | `b6313a6592732597eee41c7171ca210a45f0ce05685447c3cb354a8df79d123e` | A/B |
| 官方电量计驱动 | `E:\edk2-samurai-out\kernel83\realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--gauge_ic--oplus_bq27541.c` | `0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87` | A/B |
| 官方电量计头文件 | `E:\edk2-samurai-out\kernel85\official-oplus_bq27541.h` | `58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e` | A/B |
| MPS MP2650 数据手册证据 | `datasheet-evidence.json`，官方 66 页，2026-10-23 获取 | 文件 `d7627ca8a415f988e77f1154cb6da47059be36e848eb512c93c724e3c1b8562b` | A |
| TI SLUUA65E 文本 | `E:\edk2-samurai-out\charging-management-20261023\ti-manual-private.txt` | `c5cfb494ed5dad0311a13f134702be09cd137ed2c4478b10143eab0c760327fc` | A |
| R15 驱动快照 | `.../charging-integration-trial-20261027-r9-status-precharge-15/source-snapshot/drivers/power/supply/` | 见第 6 节 | A |

固定官方源码仓库：`realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source`，提交
`23172a1571bd91156032cc9fef16284a82b63d2c`。

注意：旧缓存
`reference/charging-oem-audit-20261023/apsd-lifecycle/oem/arch--arm64--boot--dts--19781--pm8150b.dtsi`
的 `warm_bat_decidegc=450` 与官方 `kernel83` 源码及两份原厂 DTBO 的 440 不一致，**不可用来证明 45 C 温门限**；本报告采用官方源码和原厂 DTBO 的 44 C。该旧目录中的 `smb5-reg.h` 仍可用于 SMB5 寄存器名，SHA-256 为
`d8b7ac8b704f8c7be4399249296f0c7acc156e5b44db20c71f406142a179e508`。

## 2. 原厂板级常量

两份原厂 DTBO 在上述充电相关字段上一致。

| 参数 | 原厂值 | 解释 / 级别 |
|---|---:|---|
| `qcom,thermal-mitigation` | 3000000 / 1500000 / 1000000 / 500000 uA | 四档热限流；A |
| `qcom,usb-icl-ua` | 2000000 uA | 板级输入上限 2 A；A |
| `qcom,fcc-max-ua` | 2000000 uA | 板级快速充电上限 2 A；A |
| `input_current_charger_ma` | 2000 mA | 普通适配器策略上限；A |
| `pd_input_current_charger_ma` | 2000 mA | PD 策略上限；仅 5 V 日常范围采用；A |
| `qc_input_current_charger_ma` | 2000 mA | QC 策略上限；高电压不纳入日常范围；A |
| `input_current_usb_ma` | 500 mA | SDP，USB2 板不允许推断 900 mA；A |
| `input_current_cdp_ma` | 1500 mA | CDP；A |
| 相机 / 通话 / LED 预算 | 1200 mA | 场景限流；A |
| LED 暖 / 正常预算 | 1500 / 2000 mA | 场景策略；A |
| `iterm_ma` / `default_iterm_ma` | 110 mA | 终止电流请求；A |
| `recharge-mv` | 100 mV | 重充电压差；A |
| `max_chg_time_sec` | 36000 s | 软件充电上限 10 h；A |
| `warm_bat_decidegc` | 440 (44 C) | 暖温门限；A |
| `hot_bat_decidegc` | 530 (53 C) | 高温门限；A |
| `auto-recharge-soc` | 98% | SMB5 策略；A |
| `vbatt_full_thr` / `vbatt_hv_thr` | 4400 / 4600 mV | Full/过压判定；A |
| `batt_capacity_mah` | 4000 mAh | 典型容量；A |
| `vbatt_num` | 2 | 两串电芯；A |
| PD sink PDO | 5 V/3 A、9 V/3 A、12 V/2.25 A | 板级能力；日常适配只取 5 V；A |
| 电量计节点 | `bq27541-battery@55`，I2C `0x55`，`qcom,batt_bq28z610` | 系列/地址已证实，精确 2719 型号未证实；A/B |
| 控制标志 | `recharge_after_full`、`check_batt_full_by_sw`、`external_gauge`、`step-charging-enable`、`sw-jeita-enable`、`sw_vfloat_over_protect_enable` | 原厂策略使能；A |
| 其他 | `wd-bark-time-secs=16`，`suspend-input-on-debug-batt`，`qc3-disable`，`hvdcp-disable`，`float-option=1` | A；WDT 实际归属见后文 |

## 3. 原厂温度 / 充电曲线

官方 `pm8150b.dtsi` 的普通充电值如下。官方注释对最冷边界有歧义（`cold_bat_decidegc=20` 而注释写 `-2C~0C`），因此最冷边界单独标记为需补证；0 C 以上和 44/53 C 门限为 A。

| 温度区间 | 快速充电电流 | CV | 软件/过压限 | 级别 |
|---|---:|---:|---:|---|
| 约 -2..0 C | 250 mA | 3980 mV | 3990 mV | A 值、B 边界映射 |
| 0..5 C | 900 mA | 4400 mV | 4410 mV | A |
| 5..12 C | 普通 1100 mA | 4400 mV | 4410 mV | A |
| 12..16 C | 1100 mA | 4400 mV | 4410 mV | A |
| 16..44 C | 1100 mA | 4400 mV | 4410 mV | A |
| 44..53 C | 550 mA | 4130 mV | 4140 mV | A |

补充原厂策略：

- 普通充电的软件限压为 4350 mV；暖温为 4080 mV；冷区为 3930 mV。
- PD/QC 快速档在正常温度为 2000 mA，暖温为 550 mA。
- `temp_warm_fastchg_current_ma_led_on=250 mA`，说明亮屏/LED 场景有独立降流。
- FFC/FFC2 常量存在，但不属于当前普通 5 V 日常路径；不得把 FFC 的 4495/4465 mV 与普通 CV 混用。

结论：原厂普通曲线是“温度分档 + 电流降额 + CV 降额”，不是仅靠 MP2650 的 JEITA 自动完成；SMB5/OPLUS 充电框架也参与策略。R15 已把核心普通档表下沉到充电策略，但相机/通话/LED 场景预算尚未完整接管。

## 4. MP2650 寄存器与确认程度

MP2650 的位定义以 MPS 官方数据手册为主；社区头文件
`kernel85/cyborg-oplus_mp2650.h`（SHA
`05102b4c6b863b2fe4030839051355325a52aba406b4f38d961bb36b808f03cc`）
仅用于核对同名位，不作为独立原厂证据。

| 寄存器 | 约定 | 原厂 / 现场值 | 级别 |
|---|---|---|---|
| `REG00`、`REG0F` | 输入限流，7 位，50 mA/步 | 板级上限 2 A；R15 以 50 mA 量化 | A |
| `REG01` | VINDPM，100 mV/步 | 原厂初始化 4440 mV，软件 AICL 4500 mV；电池 >4140 mV 时硬件 4520/软件 4535 mV | B |
| `REG02` | 快速充电电流，50 mA/步；bit7 保留 | 正常档 1100 mA，暖温 550 mA；R15 另受 2 A 板级上限约束 | A/B |
| `REG03` 高半字节 | 预充电流表：code 0-4=180 mA，5=240，6=300，7=360，8=420，9=480 | R15 快照写 `0x91`，即 480 mA；旧验证路径/工作区头文件为 `0x31`，即 180 mA | A 位定义；具体出厂值缺证 |
| `REG03` 低半字节 | 终止电流，100 mA/步 | 原厂请求 110 mA，硬件只能取 100 mA（code 1） | A 位定义；B 映射 |
| `REG04` bit6:1 | CV = 3712.5 mV + code×12.5 mV（每串） | 现场继承 `0x68` => 4362.5 mV/串；两串 8725 mV，和 R15 现场 `constant_charge_voltage=8725000` 一致 | A |
| `REG04` bit0 | 重充阈值：0=-100 mV，1=-200 mV/串 | 原厂 `recharge-mv=100`；R15 取 bit0=0 | A/B |
| `REG07` bit5:4 | 预充转快充阈值：0=6600、1=6800（默认）、2=7400、3=7200 mV | 官方初始化显式写 6600 mV；现场 `0x14` 读回为 6800 mV/两串、1 A OTG | A 位定义；B 有效值 |
| `REG08` | bit1 BATT FET、bit3 LEARN、bit4 CHG_EN、bit5 OTG、bit6 WDT_RST、bit7 REG_RST | 现场 `0x16`：CHG_EN=1、BATT FET=1；R15 不写 raw reset/OTG | A |
| `REG09` | 安全定时 5/8/12/20 h，WDT 关/40/80/160 s，终止使能 | 原厂初始化启用 40 s WDT；现场快照 `0x4c` 为 12 h 定时 + 终止使能 + WDT 关 | A 位定义；B 原厂写入轨迹 |
| `REG13` bit1 | `VIN_POWER_GOOD`：**0=good，1=no-good，反相** | R15 现场 `0x16`、`0x1b` 的 bit1 均为 0，表示 power good | A |
| `REG13` bit3:2 | CHG_STAT：0=off，1=precharge，2=fast，3=termination/full | 预充现场 `0x16`；快充现场 `0x1b`；Full 需结合 gauge 电流 | A |
| `REG14` | NTC/电池 OVP/充电/OTG/WDT 故障 | 现场保护路径读取 | A 位定义 |

### MP2650 关键差异

1. **R15 的最高优先级寄存器缺陷**：`samurai-mp2650.c:235` 与 `:270` 把 `REG13.bit1` 当作 `ONLINE`，且前者比较极性相反。按头文件和数据手册，bit1=1 表示 power **not good**。正确用法是：输入 `POWER_SUPPLY_PROP_ONLINE` 作为 online 来源；`!(reg13 & 0x02)` 只作为 power-good 条件，不能反推 online。
2. R15 快照采用 `REG03=0x91`（480 mA 预充、100 mA 终止）；旧工作区采用 `0x31`（180 mA 预充、100 mA 终止）。原厂源码没有给出 WPC 数值常量，实际预充验证又在 180 mA 版本上通过，因此 480 mA 仍是未经 OEM 证明的改动。
3. R15 保留继承的 4362.5 mV/串上限，没有因 DT 的 4400 mV 直接抬高到 4400；这是更保守且与现场 `0x68` 一致的选择。不能把“DT 目标 4400”误写成当前实际 CV。
4. 原厂初始化启用 40 s WDT，但现场快照 WDT 关；R15 明确拒绝接管活动 WDT。启用 WDT 之前必须先证明谁负责 kick、suspend 时是否继续、超时后寄存器是否回到安全默认值。

## 5. BQ28Z610 / “2719” 电量计

原厂 DT 证明的是家族/兼容性，不是精确型号：

- 节点：`bq27541-battery@55`
- `compatible = "oplus,bq27541-battery"`
- `qcom,batt_bq28z610`
- I2C 地址：`0x55`
- 原厂头文件家族常量：`DEVICE_TYPE_BQ28Z610 = 0xffa5`

固定原厂输入中未找到 BQ27Z561 的器件/封装证明；在 2719 身份未解出前，不能把
“BQ27Z561”与 `qcom,batt_bq28z610` 或当前电量计互换。

固定源码寄存器映射：

| 命令 | 含义 / 单位 | 级别 |
|---|---|---|
| `0x06/07` | Temperature，0.1 K | A（TI） |
| `0x08/09` | Voltage，mV | A（TI） |
| `0x0a/0b` | BatteryStatus | A（TI） |
| `0x0c/0d` | Current，有符号 mA，充电为正 | A（TI） |
| `0x10/11` | RemainingCapacity | A（TI） |
| `0x12/13` | FullChargeCapacity | A（TI） |
| `0x14/15` | AverageCurrent | A（TI） |
| `0x0071` MAC | 两串 cell voltage，36-byte block；原厂只取前 4 个 payload 字节，cell1=bytes0/1，cell2=bytes2/3 | B（原厂实现 / 标准 MAC） |

**重要语义纠正**：原厂 `get_average_current()` 名字有误导性。对 `DEVICE_TYPE_BQ28Z610`，源码在
`oplus_bq27541.c:1590-1591` 把 `cmd_addr.reg_ai` 覆盖为 `Bq28Z610_REG_TI=0x0c`，所以实际读的是瞬时 Current，不是 `0x14` 的 AverageCurrent。R15 在
`samurai-mp2650.c:145-159` 使用 `0x0c`，方向正确；mainline 的 `current_now` 若暴露 `0x14`，不能拿来复刻原厂 Full/重充门控。

已保存历史帧给出：

- DeviceType 字节：`19 27`，LE 解释为 `0x2719`；旧兼容字为 `0xffa5`。
- 11-byte firmware payload：`27 19 00 04 00 06 00 03 85 02 00`，两份历史帧一致。
- 精确 catalog model、firmware 字段字节序、TCA 映射和完整 MAC 位布局仍未证实；该“2719”只能作为当前电池包身份指纹，不能当作 BQ27Z561 或某个公开型号直接替代。

## 6. PM8150B / SMB5 / Type-C

来自原厂 `smb5-reg.h`（B/A）：

| 项目 | 约定 |
|---|---|
| 基址 | CHGR `0x1000`，BATIF `0x1200`，USBIN `0x1300`，TYPEC `0x1500` |
| APSD 状态 | `APSD_STATUS_REG=0x1307`，`APSD_DTC_STATUS_DONE_BIT=BIT(0)` |
| APSD 结果 | `APSD_RESULT_STATUS_REG=0x1308`；SDP bit0、OCP bit1、CDP bit2、DCP bit3、float bit4、QC2 bit5、QC3 bit6 |
| APSD 命令 | `CMD_APSD_REG=0x1341` |
| Type-C 配置 | `TYPE_C_CFG_REG=0x1358`，`BC1P2_START_ON_CC_BIT=BIT(7)` |
| USBIN 配置 | `USBIN_OPTIONS_1_CFG_REG=0x1362`，`BC1P2_SRC_DETECT_BIT=BIT(3)` |
| 输入限流 | `USBIN_CURRENT_LIMIT_CFG_REG=0x1370` |
| legacy cable | `0x150d`：bit1 legacy，bit0 noncompliant |

原厂板级输入预算（A）：

- SDP：500 mA。
- CDP：1500 mA。
- 普通适配器/PD/QC 策略：2000 mA。
- 相机/通话：1200 mA。
- PD sink：5 V/3 A、9 V/3 A、12 V/2.25 A。

R15 的 `samurai-usb-input-decode.h` 已解码 CC 1.5 A/3 A、SDP/CDP/DCP，并将 SDP/FLOAT 限制在 UDC 的 500 mA；CDP/DCP 被识别为 1500 mA。实际 DWC3 路径只可靠合入 SMB5/Type-C 的 SDP 预算；CDP/DCP 的完整 APSD/ownership 尚未完成。

## 7. R15 实际采用值

R15 固定快照：

| 文件 | SHA-256 |
|---|---|
| `samurai-mp2650.c` | `b55b77d751fa472dff1589fc94fc584f91c8463d37c7f334a7ed557261119208` |
| `mp2650-core.h` | `abe6932491c6f518c81abf7d79306f98928396b7f71aeefd4c99044821d81dc6` |
| `negotiated-input.h` | `c8077eef52fca269798d747330aeb42d413a65d471c9a39899705409340836c8` |
| `oem-profile.h` | `14a425065aadcca1cc38efcc75cb112c0c25ac05567195b04feaa2bec21b0729` |
| `oem-full-cycle.h` | `c292836c964831d9582d24d2b74c03059bfb99e11eb7a8d6e1f17e26e001fed1` |
| `thermal-bands.h` | `a06962f52e570b2b418c9e03354f634a1b356ed86c234cf598489a9f02f09112` |
| `samurai-usb-input.c` | `83a412a6093867ad3698e4d0cace95f422565d3d6c54711123831a8df95d3884` |
| `samurai-usb-input-decode.h` | `a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd` |

实际策略：

- 温度档表：`-2.0..0.0 C / 250 mA / 3980 mV`；`0.0..5.0 C / 900 mA / 4400 mV`；`5.0..12.0 C / 1100 mA / 4400 mV`；`12.0..16.0 C / 1100 mA / 4400 mV`；`16.0..44.0 C / 1100 mA / 4400 mV`；`44.0..53.0 C / 550 mA / 4130 mV`（内部实现为 deciselsius / uA / uV）。
- 板级输入和 FCC 上限：2 A；普通默认电流上限：1100 mA；软件充电上限：36000 s。
- 预充转快充：2-cell，6600 mV。
- CV：优先采用继承的 REG04 上限，当前约 4362.5 mV/串；不自动抬到 4400 mV。
- 终止：硬件定时器/终止保持使能；110 mA 的 OEM 请求按 100 mA 步进取 code 1。
- Full：REG13 CHG_STAT=3 且 gauge 电流 ±110 mA；另有 5 s 软件计数和电压 Full/重充状态机。
- 重充：按约 100 mV/串的电压下降；`auto-recharge-soc=98%` 尚未按 SOC 完整实现。
- suspend：不因普通 Full 主动停充；只有未知/不安全/latched/timeout/无效等状态停止。
- Type-C：只接受固定 5 V 合同；输入预算受物理 `CURRENT_MAX` 封顶。

### R15 现场证据

目录：
`E:\edk2-samurai-out\charging-management-20261023\r15-evidence-20261027\trial-517-r15-fixed5v1500\`

- boot id：`a55ef9ba-0837-4ed8-95d3-1847a115fa42`
- kernel：`#528`
- `auto-audit-report.json` SHA-256：`da4b174d409509180771dc8ed37f6a70fe4f778110957158bd06b3682acc2667`
- 固定 5 V，TC/PD `CURRENT_MAX=1500000 uA`，`CURRENT_NOW=1500000 uA`
- MP2650 `managed_source_budget_ua=1500000`，`hardware_input_limit_ua=900000`
- 该次电池状态下 managed FCC/constant current 为 `250000 uA`，不能外推为正常快充电流上限
- battery `Charging`，power role `sink`，`high_voltage_accessed=false`

预充到快充现场（`precharge-live506-r3-recovered-result.json`，sha256
`9a136ae9b1dd75b5bf14fe8615c836af98021c634c012ea9a213e29a6072c257`）：

- phase 1：REG13=`0x16`，CHG_STAT=1（precharge），gauge 约 `+82 mA`
- phase 2：REG13=`0x1b`，CHG_STAT=2（fast），gauge 约 `+93..98 mA`
- 证明相位切换，不证明充电电流计量的绝对精度。

完整低电到 100% 以及多次 Full→recharge 尚未闭环验证。R15 的 screen-off 重充尝试虽然发生了 Full→Charging，记录却因 `positive_current_majority=false` 判为失败，只能作为单次方向性证据。

## 8. 可直接落地的优先修改

1. **[P0] 修正 REG13 bit1 极性。** `ONLINE` 只取输入 power_supply；power-good 使用 `!(REG13 & 0x02)`。删除把 bit1 直接当 online 的两次判断。
2. **[P0] 恢复保守预充参数，除非补到 OEM WPC 证据。** 用 `REG03=0x31`（180 mA 预充、100 mA 终止）替代 `0x91`；实际预充验证是在 180 mA 路径完成的。若以后得到原厂 WPC 数值或出厂写寄存器轨迹，再决定是否提升。
3. **[P1] 输入授权使用合同/上限，不使用测量值。** TCPM 侧以 `CURRENT_MAX` 或协商合同作为授权，`CURRENT_NOW` 仅作监测；物理 `CURRENT_MAX` 作为最终封顶。否则动态负载会把预算误当成合同能力。
4. **[P1] 保持普通 5 V 曲线。** 16–44 C 采用 1100 mA / 4400 mV 目标，44–53 C 采用 550 mA / 4130 mV，SDP 500 mA，CDP 1500 mA，板级 2000 mA。不要因 DT 的 PDO 3 A 或 9/12 V 能力把普通路径抬到非 5 V。
5. **[P1] Full/重充保持双条件。** 硬件终止与 gauge 电流同时满足；继续使用约 100 mV/串重充，并保留 10 h 软件上限和 12 h 硬件安全定时。98% SOC 行为要么实现，要么在文档中明确为保守偏离。
6. **[P2] 保留继承 CV。** 当前约 4362.5 mV/串低于 OEM 目标值，不因 DT 字符串或 PDO 抬高；待完整温度/电芯计量后再评估。
7. **[P2] 场景限流最后接管。** 相机/通话/LED 的原厂值已证实，但在 SMB5/APSD/场景 owner 未收敛前不要同时写入多个限流器，否则会覆盖或抖动。
8. **[P2] WDT 暂不启用。** OEM 40 s WDT 与现场 WDT-off 并存；先证明 kick owner，再谈启用。当前拒绝活动 WDT 是安全选择。

## 9. 主线 DT / 驱动收敛建议

DT 只编码板级事实，策略留在驱动：

- DT：I2C `0x55`、`qcom,batt_bq28z610`、2-cell、4000 mAh、5 V/9 V/12 V sink 能力、SMB5/Type-C/PD 节点、原厂温度阈值、场景预算上限。
- 充电驱动：温度档→电流/CV/OVP、100 mV 重充、10 h 软件上限、Full 状态机、停止/恢复；不把原厂 OPLUS 框架的私有状态机原样搬入 mainline。
- MP2650：仅做寄存器量化、read-back、故障/相位解析；`REG13` 极性、`REG03` 编码、`REG04` CV/重充和 `REG09` 定时器必须有单元约束。
- 电量计：`0x0c` Current 用于 Full/重充门控，`0x14` 仅诊断；MAC `0x0071` 只声明经过原厂代码证明的两串 cell 字节；2719 未匹配前不启用新 MAC/TCA 位。
- USB/Type-C：TCPM 负责 PD 合同和 PDO，SMB5/BC1.2 负责 DCP/CDP 检测；单一口径把合同、物理上限、板级 2 A 和场景上限取最小值。

## 10. 仍缺证据

- 原厂 WPC 的 `WPC_PRECHARGE_CURRENT`、`WPC_CHARGE_CURRENT_DEFAULT`、`WPC_TERMINATION_CURRENT` 数值及最终 REG03 写入轨迹。
- 出厂 OTP/初始化对 REG03、REG04、REG07、REG09、WDT 的实际最终值，尤其是充电器复位后的继承行为。
- 110 mA 终止请求的模拟有效电流、CV 精度和温漂计量。
- 完整低电到 100%、重复 Full→recharge，以及 98% SOC 与原厂 SMB5 策略的关系。
- BQ28Z610 家族下 `0x2719` 的精确 catalog model、11-byte firmware 字段语义、完整 MAC/TCA 位映射。
- CDP/DCP/QC/PD/APSD 的完整 ownership 和切换序列；日常 5 V 已可收敛，但高电压/QC/PPS/VOOC 不属于本报告范围。
- 原厂相机/通话/LED 场景在 suspend、亮屏、热插拔和 PD 重新协商时的实际限流行为。
- 从插线到 precharge、fast、termination、recharge 的完整原始寄存器 trace。
