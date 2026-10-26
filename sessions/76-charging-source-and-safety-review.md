# Session76：X2 Pro 充电设备树、相关内核与安全边界

用途：为电池/充电适配确定本机硬件、可参考实现和下一步边界。
核对日期：2026-10-10（Asia/Shanghai）。来源：固定提交的原厂/主线源码、
2026-10-05 本机 Android 设备树存档、芯片官方文档，以及当前 Linux 只读状态。
关联：session75 的显示/GPU基线；reference/kernel76 的来源清单和原厂事实。

## 当前结论与设备状态

原厂配置指向 BQ28Z610 电量计和 MP2650 充电芯片。电量计已有主线支持；
在本轮检查的主线树中，MP2650 和本机 PM8150b/SMB5 组合尚不能直接接入。
原厂实现依赖 OPPO 充电策略、USB/SMB5、快充 MCU 等协作，不能仅移植一份
MP2650 驱动就认为充电安全可用。下阶段优先验证电量计的标准只读数据。

本轮没有构建/刷入镜像、改变内核或设备树、重启手机，也没有扫描充电总线、
写入充电/电量计寄存器或修改登录配置。当前仍是 #76：

- uname：7.3.0-rc6-rmx1931-samurai+；taint：0。
- boot_id：af922f36-bacd-481d-a5c5-21c8e3fada65，与 session75 末状态一致。
- /sys/class/power_supply 为空；已枚举 I2C 仅 i2c-0 / 0-0020（触摸）。
- 未测得本轮实时电池电压、温度、电量或充电电流，不能据此宣称充电已经适配。

命令与输出见 reference/kernel76/README.md、current-linux-state.txt。
显示、GPU、EUD、触摸及 USB SSH 的验收和回退证据继续以 session75 为准。

## 1. 相关机型与源码范围

这里的设备树是内核 .dts/.dtsi；Android ROM 的 android_device_* 仓库不能
单独证明主线驱动可用。提交号固定，避免后续分支更新改变本轮结论。

| 来源 | 固定提交 / 内核 | 本轮可用的参考 |
|---|---|---|
| [realme X2 Pro 官方源码](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/tree/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6) | 9668fcdc6ec15be7a10d66f7b93c347829e0fdb6；4.14.83 | 19781 DTS、oppo_bq27541.c、oppo_mp2650.c、OPPO 策略和 SMB5；本机首要参考 |
| [OPPO Reno10X/RenoAce 官方源码](https://github.com/oppo-source/Reno10X-RenoAce-10.0-kernel-source/tree/289d6118ef783a281a8ecf0378e3c560ff6976c4) | 289d6118ef783a281a8ecf0378e3c560ff6976c4；msm-4.14 子目录，4.14.117 | 19081 配置也声明 BQ28Z610、MP2650、双串电池及相关控制器，适合对照结构和实现 |
| [OnePlus SM8150 官方源码](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8150/tree/1dd473abda05a72f6978c47b2a7d80828db6b426) | 1dd473abda05a72f6978c47b2a7d80828db6b426；oneplus/SM8150_P_9.0，4.14.83 | guacamole/7 Pro 的 PM8150b/SMB5 与电池配置；没有从已检查文件得到本机 MP2650 的替代驱动 |
| [Linux 主线](https://github.com/torvalds/linux/tree/3857c2fe5449541e24afc5efdb0f81a8a8f9a3a0) | 3857c2fe5449541e24afc5efdb0f81a8a8f9a3a0；7.3-rc6 | BQ28Z610、qcom_smbx 的实际匹配范围、power/supply 目录及 Kconfig/Makefile |

OPPO 组合仓库里存在 19081 配置，不意味着 Reno10X 的每个版本都采用这组器件。
OnePlus 只检查上述默认 Android 9 分支，未穷尽其他分支。网页没有找到可直接使用的
MP2650 主线实现，结论限定为已检查的树和检索范围，不排除其他人的未合入工作。

## 2. 本机原厂设备树与主线映射

下表来自本机存档的 Android live DT，并与 [19781 DTS](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-mtp.dtsi)
和主线 SM8150 总线定义交叉核对。节点声明不能代替实物识别和成功绑定证据。

| 功能 | 原厂地址和配置 | 主线接入判断 |
|---|---|---|
| 电量计 | I2C c94000、地址 0x55、100kHz；节点名 bq27541，但带 qcom,batt_bq28z610 标志 | 对应 &i2c15；应选 ti,bq28z610，而不是依据节点名选 bq27541 或通用 SBS |
| 电量计总线引脚 | GPIO27/28、qup15、2mA、bias-disable | 需核对实际主线 pinctrl；不为此引入其他充电器节点 |
| 充电芯片 | I2C 884000、MP2650 0x5c、400kHz | 对应 &i2c1；当前主线没有 MP2650 驱动，mp2629_charger.c 是不同器件 |
| MP2650 OTG | PM8150 GPIO4；原厂 active 为高、sleep/default 为低 | 涉及 VBUS 输出方向，不在电量读取阶段激活或切换 |
| 协作器件 | 电量计同总线还声明 DA9313 0x68、short IC 0x58、STM8S 快充 MCU 0x26 | 本轮未探测/写入；不能把节点声明当作主线适配完成 |
| PMIC 电量计 | 原厂 fg-gen4 节点 status 为 disable | 本机优先外部 BQ28Z610，不能直接启用 PMIC gauge 替代 |

原厂 SMB1390 等节点也有声明，但本轮未核实实物和驱动绑定，不应顺手启用。

## 3. 主线电量计可先行，充电控制仍缺适配

[bq27xxx binding](https://github.com/torvalds/linux/blob/3857c2fe5449541e24afc5efdb0f81a8a8f9a3a0/Documentation/devicetree/bindings/power/supply/bq27xxx.yaml)
及驱动已有 ti,bq28z610。当前内核 CONFIG_BATTERY_BQ27XXX 和 I2C 前端已内建，
CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM 关闭；BQ28Z610 的 dm_regs 为 NULL。
已审查 setup/settings/probe：这条配置的电池信息更新路径在写入数据存储前返回。
首阶段不添加 monitored-battery 配置、不解封、不修改 NVM、保护参数或标定。

当前代码已包含 BQ28Z610 AverageEnergy 无效地址的修正（该型号 AE 映射为
INVALID_REG_ADDR）。不要为无效属性自行猜测寄存器或换用 BQ28Z620 配置。

[TI BQ28Z610 TRM Rev.E，第 12 章](https://www.ti.com/lit/ug/sluua65e/sluua65e.pdf)
说明标准读接口可在 sealed 状态使用：Temperature 0x06 的单位为 0.1K；
Voltage 0x08 是电芯电压之和，单位 mV。应保留电池包电压含义，核对有符号电流、
SOC 和容量单位；不能把双串包电压直接当单节电压，或用宣传容量覆盖实测值。

[qcom_smbx.c](https://github.com/torvalds/linux/blob/3857c2fe5449541e24afc5efdb0f81a8a8f9a3a0/drivers/power/supply/qcom_smbx.c)
当前仅匹配 qcom,pmi8998-charger 和 qcom,pm660-charger，没有本机 PM8150b/SMB5。
不能把 compatible 改成其他 PMIC 来强行绑定，也不能让 MP2629 驱动控制 MP2650。

## 4. 原厂策略差异与移植风险

本机 Android live DT 的 qcom,vbatt_num=2，指向双串配置。以下仅为存档策略值，
不是本轮测量值，也不是可以直接写入的新充电限额：

| 项目 | 本机存档值 | 解读和对照 |
|---|---|---|
| 普通温区浮充 | 4400mV | 原厂每节策略值；电池包/芯片寄存器编码要另行核对 |
| 普通温区充电电流 | 1100mA | 属于完整 OPPO 策略，不能独立作为安全默认值 |
| USB / 普通充电器输入策略 | 500 / 2000mA | input_current_usb_ma / input_current_charger_ma；还需电源识别、USB 预算和温控约束 |
| 常规 warm 阈值 | 440，即 44°C | warm_bat_decidegc；Realme 19781 和 OPPO 19081 公开源码为 450，即 45°C，本机 live DT 与源码不完全一致 |
| 常规 hot / cold | 530 / 20 | hot_bat_decidegc 为 53°C；原厂解析对 cold_bat_decidegc 取负，因此 cold 是 -2°C，不能误读为 +2°C |

本机差异保存在 charging-stock-runtime-facts.json。FFC 等特殊模式另有更高策略值，
本轮不将其用作常规充电参数。OnePlus 的温区参数也不能套给本机。

原厂 charger_ic/Makefile 将 MP2650、DA9313、msm8150_pro 适配层一起构建；
vbatt_num==2 的路径取得 MP2650 ops，同时等待 gauge/VOOC/charger 就绪并依赖
OPPO 温度、电压和充电状态机。只复制驱动文件会遗漏这些协作和保护条件。

特别是 [原厂 oppo_mp2650.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/oppo/charger_ic/oppo_mp2650.c)
的 probe 会调用 vbus_avoid_electric_config、hardware_init 和 GPIO 初始化。
hardware_init 会复位芯片、设电流/浮充/终止/OTG、解除 suspend、启用充电和看门狗，
并用 OVERTIME_DISABLED 关闭充电安全计时器。因此它不是只读识别程序，不能为了
“看看能不能 probe”直接绑定到设备。

[MPS MP2650 数据手册 Rev.1.0](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/)
第 27、35–36 页说明：看门狗超时恢复默认模式，默认值可以由 OTP 定制，不能
视为必然关闭充电。REG08 涉及 reset、watchdog、OTG、CHG_EN、NTC 引脚功能和
BATTFET；REG09 涉及看门狗及安全计时器。未来必须审查读事务、副作用和失联后的
实际状态，保护既有电源路径、NTC/终止/超时机制，不能照抄通用复位值或盲目切换
BATTFET/OTG。芯片结温保护不能代替电池温度策略。

## 5. 下一步顺序与验收条件

1. 仅接入 &i2c15 上的 ti,bq28z610 电量计，保持 NVM 更新关闭和充电器节点不绑定。
   先审查驱动所有访问，再构建设备树候选；变更必须进入实际 UEFI DTB。
   上机验收以标准寄存器读值、单位、连续采样和日志为准，不以节点出现为准。
2. 在电量/温度可读且合理之后，审查 MP2650 文档中的已知寄存器读事务、读副作用、
   实际引脚和 OTP/当前配置；不做全地址扫描、不解封 gauge、不刷快充 MCU。
3. 再准备主线 power_supply 充电驱动：使用本机确认的限制，明确 USB 输入预算、
   温度区间、终止和安全计时器，以及总线故障、进程/内核失联时的电源状态。
   测试应从受限普通供电开始；高压/大电流和 VOOC/SuperVOOC 另行验证。

本轮研究不构成“已具备安全充电”的验收。全硬件目标仍 active；其他硬件优先级
和显示/GPU回归边界继续看 living handover 与 HARDWARE-STATUS.md。

## 6. 检索与证据边界

已核验 43 项公开源码/目录来源（15 项 Realme、28 项相关/主线），保留固定提交、
URL、字节数和 SHA256；存档 DT 的 9 个相关节点、238 个策略属性及引脚也有记录。
芯片文档只记录链接、版本和相关章节，不重新发布完整 PDF。私有镜像、密钥和
完整手机日志留在本地输出目录，不纳入本轮文档提交。

网页搜索和 Firecrawl 初次连接失败，重试后恢复；直接 GitHub HTML/raw 获取也成功。
Windows 和 WSL gh 均报告已有 token 无效，匿名 API 曾限流；没有修改认证配置。
MPS 的 Python 直连返回验证页面，之后通过网页 PDF 阅读器成功读取官方数据手册。
完整来源及限制见 reference/kernel76/charging-source-provenance.json。
