# 453：长焦个体 AF 的实际消费与条件步表

后续补证：[460](../kernel460/README.md)已用匹配ODM默认库／配置执行原解析及HAL边界覆盖分支，确认当前长焦全部条件表项数值不变。以下保留初始条件与原收据；checksum、实际运行时文件／姿态和光学安全仍缺，不改写候选或升级部署。

2026-10-23。已从326本机长焦EEPROM、当前原HAL和固定源码核对完整AF尾部，执行实际formatter、margin／clip／步表数学及runtime sag数值核心。**生成了“原厂外部配置未选择边界override”条件下的私有个体步表，`conditional_only=true`、`deployable=false`。**当前外部配置选择、工厂checksum接受规则、物理供应商和真实姿态输入仍未一起验收；没有形成正式个体AF配置。

本项接续[AF来源报告](AF-PROFILE-NEXT.md)，仅适用于当前声明Qtech S5K3M5SX、sensor mode3的Preview／Video。三份已通过nominal文件SHA保持；未访问手机／SDK、未编译、未改驱动／DT、正式调校或生产源码。每次WSL访问前经449 `mounted_build()`。检查器为[inspect-af-individual.py](inspect-af-individual.py)，结果见[脱敏收据](af-individual-validation.json)；所有端点、系数、原始读回指纹和完整指令证据仍私存。

## 已确认的原件与数据成员指针

当前326描述 SHA `823404fc…c77`，281原HAL SHA `e2b1b9b6…a70dde`；326两份长焦读取逐字节一致，未重采EEPROM。沿用已通过的AF模式绑定：AFAlgoTuning UID96，payload SHA `963df4c8…f9400`；ContrastAF UID68，SHA `929e31e5…ef59`，该模组Preview／Video分别一致。

直接执行 `EEPROMDriverDataClass::Parse`（`0x179268`），完整消费描述root，得到1080字节原生对象。`ImageSensorModuleData::CreateAndReadEEPROMData` 的原指令 `0x4f9728` 明确给模式模块地址加88，再传给EEPROM构造函数；这是ParameterModule头与EEPROMDriverData成员的区别。首轮formatter试跑误用模块首地址，已拒绝计入证据，最终按该原调用点及全部字段对等重验。

AF实际尾部各scalar／MemoryInfo与有界序列化原件逐项相等；当前空的calibrationInfo数组也核对引用和大小。原厂还插入 `dacOf50cm`／`dacOf100cm` 两组字段，旧通用XSD没有这两组，正是不能直接复用旧完整EEPROM XML的原因之一。字段名另由本机HAL实际formatter日志字串确认；当前描述未启用这两个扩展点，没有据此生成距离映射。

## 实际formatter、margin与姿态分支

| 消费项 | 本轮证据 | 仍保留的边界 |
| --- | --- | --- |
| AF可用性 | `0x4fb9d0` 起的实际formatter复制描述中的available标志；把该描述标志置false的内存反例得到零原始读取、零输出 | 该标志不是本机EEPROM checksum／有效性位的验收 |
| macro／infinity | 原 `FormatDataTypeInteger`（`0x506328`）与formatter完整执行，和独立读取原始字节的模型相等 | 双读一致证明读取完整性，未认证供应商或工厂接受状态 |
| margin | 实际parser读取、formatter复制和后续浮点消费均已核，实值只私存 | 需区分校正后范围与nominal范围 |
| EEPROM校准姿态 | 当前 `lensSagCalMac`／`lensSagCalInf` 都走DEFAULT；当前描述不声明水平／垂直端点替代 | 没有凭其它模组的姿态偏置补值 |
| runtime lens sag | 已选AF v9原生parser完整消费，其enable和fDAC数组与此前完整类型／XML证据相等；当前已选调校启用这项 | 实际运行还受静态feature gate及实时gravity输入约束 |

formatter审查覆盖 `0x4fb9d0…0x4fd14c`，所有实际EEPROM访问和整数getter调用留有私有trace。零mask的getter也可能访问一个原始字节，这种访问没有独立的接受判断，不能凭“读了开头某字节”推成有效性验证。hall、扩展点可用标志、空距离数组及margin输出也完成独立模型核对。

接着执行原HAL `0x4f8474…0x4f89cc` 的margin、截断、端点clip、重新计算codePerStep和全部个体表项；与独立float32模型逐项相等。位宽和VCM类型来自原生解析的本模组执行器对象；协议上下界在此只作为**条件clip输入**，没有被当作搜索端点。个体表由读取端点与各自margin计算，和已保留nominal表不同，沿用macro／infinity反向逻辑索引。

该数值核心前面还有真实 `GetKeyCount`／`GetValuesCount`／`GetLocaleIntegerListConfiguration` 分支，查询外部 `libhwconfigurationutil.so` 的 `OemCamActuatorSettingMap` 后可改写边界。当前缓存尚未证明这一路实际选了什么，因此没有把本次数值核心输入标为“原厂已选的完整分支”。条件候选明确保留这一缺口。

runtime `CalLensSagComp`（`0x41d508`）消费的是已选AF调校的fDAC和实时重力，与EEPROM的两个额外距离点分开。其两段实际数值核心在5个显式重力输入上均与独立float32模型相等，包括DAC差值到逻辑index差值的换算；这些输入是离线检查用例，未采集手机姿态，也未代替真实static feature gate。不能把“个体margin表已算出”解释成“全部运行时姿态补偿已接入”。

## checksum：已有名字不足以证明工厂接受

固定CamX提交 `9f17f1b568626b393e785b369c5dc94543774d7a` 的 [FormatAFData](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/camx/src/core/camxeepromdata.cpp) 没有AF checksum验证；本机实际formatter路径也没有恢复出与工厂保存校验字节比较的逻辑。当前AF描述不提供已核的checksum offset、覆盖区间或算法，不能从原始字节自行选一种求和规则。

原厂GPL提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的 [cam_eeprom_core.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/media/platform/msm/camera/cam_sensor_module/cam_eeprom/cam_eeprom_core.c) 确有 `CAM_CHECK_CALIBRATION_DATA`。但它根据调用方传入的startAddr，以固定跨距抽样求和并回传；该函数自身没有与工厂保存值比较，也没有给出长焦AF区域的接受规则。普通EEPROM读取路径仍读取并回传原始段。没有移植该私有ioctl或用其名字宣告AF checksum通过；调用方工厂验收语义仍未知。

## 当前私有候选与最小补项

私有目录 `E:/edk2-samurai-out/kernel453/af-individual/` 包含实际AF尾字段、原生formatter结果、raw读取trace、条件个体步表、runtime sag对等用例及来源清单。`s5k3m5-conditional-individual-step-candidate-private.json` 绑定当前描述、两个已选AF payload和原HAL核心指纹，明确外部override／checksum／物理搜索安全未验证、未应用、不可部署。它不是正式加载器的YAML；原AF来源三文件保持原SHA。

为补外部配置权威，已只读debugfs检查现存242／248 vendor镜像中的HAL；两者均为另一SHA `660eef76…c90ef`，与281当前原件不同，已拒绝套用其库或配置。无需重采现有EEPROM；下一最小原件是**与281 HAL同一当前vendor的 `/lib64/libhwconfigurationutil.so`，以及从该匹配库实际定位的 `OemCamActuatorSettingMap` 配置来源**，不能先猜XML路径。未来由主线串行安排只读窗口，或先复用能证明匹配的现存缓存。

工厂AF checksum若需认证，还需要匹配此供应商EEPROM的原始布局／工厂工具接受函数；当前没有证据可指定某个校验字节。未知checksum保持为明确的认证缺口，不撤销已授权的受限、可回退诊断。底层接续可使用本报告的真实逻辑步表和姿态单位，单独确定消费者采样／稳定及FoM策略；硬件窗口仍按453只接一颗lens、核model和资源、在确认约束内触发AF，并覆盖长焦720p／1080p的实际曝光／帧时序、返峰和停流释放。未经这些验收，不把个体候选升级为正式配置。
