# 453：两路 BU64253 的原厂 AF 数据与下一消费者边界

2026-10-23。IMX319／S5K3M5SX 已恢复匹配原件的 AF v9 搜索边界、分区步距、帧跳过和执行器阻尼数据，并复现原 HAL 的 nominal 逻辑位置→DAC 步表。**两份私有来源候选仍为 `deployable=false`；没有修改正式440调校、驱动／DT、libcamera或部署。**本轮未访问手机、SDK，未编译；每次 WSL 源码／ext4 访问先经449 `mounted_build()`。

适用身份与底层前置见[450模组核对](../kernel450/LENS-SCOPE-NEXT.md)、[453镜头候选](README.md)及[热接入边界](../kernel450/LIVE-LENS-ATTACHMENT.md)。本报告不重新认证实物供应商，也不把原厂默认范围当作本机个体安全端点。

## 精确原件、模式绑定与独立核对

| 当前声明模组 | 描述原件 SHA256 | 已核普通上下文 | AFAlgoTuning payload SHA256 | ContrastAF payload SHA256 |
| --- | --- | --- | --- | --- |
| Sunny IMX319 | `e2d68359…21704`，115保留本机BIN | sensor mode2，Preview／Video | `e6db0d1d…af439` | `22162f7e…86c7` |
| Qtech S5K3M5SX | `823404fc…c77`，优先326当前本机BIN | sensor mode3，Preview／Video | `963df4c8…f9400` | `929e31e5…ef59` |

四个上下文各查两类root，8次查询均与343保留的原厂模式管理器一致；两模组分别落在 AFAlgoTuning UID96／ContrastAF UID68，同模组的 Preview／Video 对应payload相同。**相同 UID 不代表跨模组数据相同**，上表两列payload均已区分。上下文无附加Feature／Scene／Effect；不能据此接受其它sensor mode、供应商或特殊场景。

先核343／426记录，再从已有 `/home/cy122/x2pro-linux/refs/CamxChi-k117` Git对象取回 AF／common 的18个XSD和7个相关原代码文件，固定提交 `9f17f1b568626b393e785b369c5dc94543774d7a`；未重新下载仓库。主要语义来源是 [AFAlgoTuning v9](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/api/chromatix/XSD/stats/af/afalgotuningelements.xsd)、[ContrastAF v9](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/api/chromatix/XSD/stats/af/afcontrastafelements.xsd)和 [ActuatorData](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/camx/src/core/camxactuatordata.cpp)。文件指纹及完整提交见[脱敏收据](af-profile-validation.json)。

保留的 ParameterParser 在受限宿主进程中分别输出两类root的XML；分析副本仅关闭其它root标志，所有payload和模式树保持。独立reader按XSD读取带界限的类型、数组引用、字符串及枚举；IMX319的25份、长焦14份，共**39份root全部字段与原厂XML相等**，且完整消费各自payload。没有按猜测offset摘取若干同名数值。执行器的初始码、region、forward／backward damping也与450独立XML逐项相等；IMX319另一个文件名供应商变体的这些语义一致，仍不能靠文件名认证供应商。

## 原 HAL 的实际位置换算

281保留的本机 `camera.qcom.so` SHA `e2b1b9b6…a70dde`，debug符号把初始化定位到 `ImageSensorModuleData::CreateSensorSubModules`。本轮以原字节执行其内联步表核心 `0x4f8718…0x4f89b4`，核心 SHA `6f5c2583…1769d`：两模组全部 nominal 表项与独立float32逐步累加、向零截断模型相等；没有以数学provider替代原指令，也未调用框架或设备。

该核心将逻辑首index放在macro端、末index放在infinity端，使用 `codePerStep` 逐项生成反向表，循环不包含 `macroStepBoundary` 本身；此处不再除 `qValue`。因此不能把连续边界公式直接当作实际已用的最大DAC，也不能把原厂逻辑步距直接填进当前IPA的DAC步距。完整表和根据已选 `commonElements` 生成的nominal边界私存；两模组已选逻辑边界均落在本模组步表内。这只复现nominal换算，没有执行EEPROM校正、整个原厂AF搜索、厂商算法的optics index选择或真实镜头动作。

## 当前 IPA 能消费什么

已核450源 `camss.cpp` SHA `d963f91d…7520c`。根 `autofocus` 与各mode覆盖均可读取，`lens` 必须精确等于实际 `CameraLens::model()`，并要求标准 `FocusAbsolute` 控制；453草稿名字为 `bu64253`，实际枚举仍须集成时核对。

| 当前字段／保护 | 已有原厂依据与本轮状态 | 尚不能直接接受的语义 |
| --- | --- | --- |
| `lens` | 453标准driver名字已匹配 | 实机model／绑定尚未验收 |
| `minimumCode`／`maximumCode` | 已选AFAlgoTuning边界经原HAL nominal表换算，私有候选已记录 | 非个体校正端点，不能用10bit协议范围补齐 |
| `coarseStep`／`fineStep` | ContrastAF的TAF／CAF、正常光／低光、各region逻辑步距完整恢复；对应nominal DAC差值集合也已私存 | 当前消费者只有两个均匀DAC步距；未证明可替代分区策略，未猜optics索引选择 |
| `settleMs` | 起步、粗搜、细搜、fullSweep、返峰和首帧跳过字段已恢复 | 原件单位为各阶段跳帧；不能固定换成毫秒，也不是damping delay或上电等待 |
| `samples` | 原件相关统计／拟合参数可定位 | 不等于当前每位置中位数采样次数 |
| `timeoutMs` | 当前搜索总时限字段已核 | 尚未选择有依据的消费者策略 |
| `minimumPeak`／`peakRatio`／`verifyRatio` | 原件软件／硬件FV阈值完整保留 | 当前FoM及峰值验收域不同，不能按名字或比例直接抄入 |
| 帧保护 | 当前消费者按不可变的实际 `frameLength + exposureLines` 和 `lineUs` 计算时间保护，并结合lens ACK完成时钟 | 不替代尚未核验的机械／光学稳定时间 |
| 执行器阻尼 | 双方向scenario、step、delay、hwParams均已按原件及XML恢复 | 当前IPA没有对应消费者；未证明单次DAC写等价于原厂轨迹 |

现有IPA的缺省采样、稳定时间和FoM阈值没有被当作这两颗镜头的原厂值补齐。也没有复制主摄稳定时间或构造屈光度／距离映射。

299／326已有EEPROM重复读取逐字节相等；描述中AF前缀的可用标志、大小端、macro／infinity offset和mask已核，原始个体候选仍私存。**校验和／有效性、供应商身份、完整AF格式尾部、margin、重力／姿态修正尚未一起验收，未应用这些个体值。**公开源的 `CalibrateActuatorDriverData` 会先修正端点、再重算步表，不能在略过这些条件时声称已经复现个体AF范围。

## 私有产物与最小接续

完整系数、端点、EEPROM值、XML、反汇编和候选只在 `E:/edk2-samurai-out/kernel453/af-profile/`。`imx319-af-source-candidate-private.json`／`s5k3m5-af-source-candidate-private.json`包含原件及已选root指纹、nominal边界、原厂逻辑步距／帧策略、逐字段映射状态；`*-native-step-table-private.json`保存真实核心结果，`*-typed-af-private.json`保存39份类型解码及XML匹配路径。这些不是可被正式调校加载器读取的YAML，均明确未应用／不可部署。

下一离线增量优先长焦单路：补齐实际EEPROM AF格式的校验／margin／姿态消费，再在底层消费者明确接受逻辑步表、分区步距及分阶段帧保护，或给出经过验证的均匀DAC策略。FoM采样／验收阈值需要在现有统计域选取和验证；缺失字段不能由主摄缺省值掩盖。两份候选已提供原厂数据，不需要重新提取整份固件。

硬件窗口交回后，先按453的供电与标准lens绑定门槛只接一颗，确认实际供应商资料、model及控制范围；在已确认的约束内跑一次标准触发AF，记录Scanning、成功DAC写入／ACK、曝光帧保护、有效FoM、最终Focused／Failed和停流释放。长焦720p／1080p各覆盖实际时序，验证返峰与稳定性；个体端点未验收前不扫协议全行程。最小实机验证不等于完整AF、距离映射或其它模式通过。

复现入口：[inspect-af-profile.py](inspect-af-profile.py) 的 `--recover-schemas`、`--recover-native-source`、`--parse-af`、`--crosscheck-af`、`--disassemble-step`、`--replay-step`、`--recover`；解析器及原件已保留，复查不需要手机、SDK或编译。
