# 241：本机 GNSS HAL 初始化与 Linux QMI 差异

2026-10-16，用户要求继续定位零 CNR。使用238只读导出的本机vendor ELF，逐文件复核原manifest；不执行厂商二进制。通过原严格SSH密钥核对仍是236启动，当前MM程序和源码分别匹配固定部署摘要。接收环境由用户再次确认为室内窗边。

**已找到 Linux 缺少的调用和客户端字段，并进行原生对照；尚未证明零 CNR 的根因。** 所有接收结论按实际返回的有效字段记录；缺失数组不计为零信号。

## 实际库的初始化链

入口服务rc运行`android.hardware.gnss@2.1-service-qti`，身份gps、附加system/gps/radio/diag组。后续关注GNSS适配层至modem的链路：

1. `GnssAdapter`构造、`ContextBase::readConfig()`读取35项GPS和15项SAP表。本机实际库固定vendor配置路径；239取得的ODM文件存在，仍不等于证明Android运行时映射和采用。
2. `LocApiV02::open()`打开LOC client。`isMaster()`成立时注册master、配置/探测原始测量能力，经LBS proxy注入辅助服务配置；之后查询消息/功能能力并注册事件。
3. `handleEngineUpEvent()`将消息排入队列；实际消息处理体依次执行能力广播、`setConfig()`、SV blacklist/type配置、非UNKNOWN平台电源通知、secondary-band、CDFW和恢复会话。
4. `setConfig()`另排队执行配置更新、NMEA、CTU/PACE、robust-location及传感器参数。多数步骤有配置/能力条件，静态分支存在不等于本机Android实际发送过。
5. 开始时间定位时注册事件、设置操作模式，发送Start；停止后Stop并释放client。

定位依据是动态符号、AArch64指令、虚表重定位和`.eh_frame`函数范围，包含Android APS2 RELA。4字节导出函数可能是CFI跳板：例如`LocContext::injectFeatureConfig`从`0x77ba0`跳到`0x3e928`，不能按符号长度称其no-op。私有反汇编和原始二进制不公开。[ELF核验](hal-elf-validation.json)、[Linux当前源码/程序核验](linux-source-validation.json)

## 逐项差异与适用边界

| 项目 | 实际厂商库 | 当前Linux | 本轮判断 |
| --- | --- | --- | --- |
| LOC传输、CID和生命周期 | 同一LOC client持有会话，Stop后释放 | MM和226诊断已具备 | 当前测试沿用同CID，不再把CLI短生命周期当零CNR解释 |
| master注册`0xBA` | `registerMasterClient()`，公开SDK同款key | MM没有此调用 | 本机ACK/完成status均0；需在Start前比较，运行中加入会改变报告表现 |
| 注册事件`0x21`的clientType | 实际`locClientRegisterEventMask`发送AFW=1，并带字符串及notification=false；静态标签HAL/MHAL | libqmi/MM当前请求只有事件mask | 实测AFW单变量与组合条件，不能由字段缺失直接推定接收被禁 |
| 测量星座报告`0x88` | 测量能力探测/报告掩码变化时配置 | MM没有此调用 | Start前配置成功并订阅bit24后收到原始`0x86`事件；报告内容另验 |
| 平台电源通知`0xD0` | 仅非UNKNOWN状态下发送；构造时平台状态初始为0 | MM没有此调用 | 本固件返回ACK result1/error57，无完成指示；没有生效，不称RESUME已注入 |
| 能力`0xA9`及AON查询`0x9D` | open中查询功能/批处理能力 | MM路径不同 | `0xA9`只读查询成功；能力查询本身不是RF供电动作 |
| GPS锁`0x3A` | setConfig中的条件分支 | MM已有设置MT；221读回MT | 不重复写锁或NV。MT不等于禁止本机发起定位 |
| SUPL/LPP/LPPe/A-GLONASS`0x54` | 实际库`gnssUpdateConfig`有LPP/LPPe虚调用 | MM只有部分SUPL服务器配置，没有完整厂商配置链 | `0x55`读回SUPL=2.0，LPP/LPPe字段未返回；未返回不当0。standalone零CNR因果尚未建立 |
| NMEA`0x3E` | 依据provider/feature设置掩码 | MM已有GET/SET | 当前掩码63；原始SV结果不依赖HAL的NMEA合成 |
| CTU/PACE`0xCA/0xCB` | setConfig的时间/功耗条件分支 | MM没有对应调用 | 用于时间不确定度/时钟估计策略，没有本机LNA漏开的证据 |
| SAP/sensor`0x84/0x58/0x5A` | LBS proxy及sensor配置路径 | MM不复用厂商融合栈 | 238已解码GTP_CELL/GTP_WIFI/SAP；不是新增RF开关发现 |
| 操作模式`0x4A`、Start`0x22` | 按定位请求发送模式、周期/精度等参数 | MM具备；226及本轮原始诊断显式HIGH | 本轮读回standalone=4、HIGH=3；没有强行改变蜂窝DMS电源 |
| raw测量与上层fix | 厂商按事件和可用测量上报 | MM主要消费NMEA | 已新增诊断订阅；测量事件存在不等于有SV测量或真实定位 |

**对上一轮公开源码结论的更正：** AOSP固定`57ced1d`把LPP/LPPe下发注释为由MBN配置；本机实际`libgnss.so`在`0x33908/0x33968/0x339c8`仍分别通过虚表调用LPP、LPPe CP/UP。这两个版本不能互相替代。该差异确认了版本核对的必要性，尚未证明LPP是零CNR原因。[公开版本](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/gnss/GnssAdapter.cpp#1138)

## 已执行的接收对照

先进行同client的四个连续90秒阶段：baseline→master→尝试RESUME→测量配置/订阅；再使用全新client把master和测量配置放在Start前，补AFW单变量及AFW+master组合，共630秒观察。它们是有界诊断，不是持久服务改动。[构建](probe-build-validation.json)、[四阶段结果](differential-validation.json)、[Start前结果](ordered-validation.json)、[AFW结果](afw-validation.json)、[组合结果](combined-validation.json)

四阶段基线有854个有效SNR字段，全0/SEARCH。加入master后的三个阶段均缺少卫星数组，不将这些阶段称为“测得零CNR”；期间出现一次位置status3/TIMEOUT。这里有时间、角色及顺序混杂，不能用来证明master破坏接收。

新client的Start前master+测量配置：89次SV事件中29次同时有普通/扩展列表，890个有效SNR字段全0/SEARCH；另外60次缺列表。取得534条原始测量事件，但全部缺少TLV0x1B卫星测量数组，不能据此统计测量CNo为0。AFW单变量90秒亦有890个有效SNR字段全0/SEARCH，无TRACK/fix。[测量解码及缺字段](measurement-validation.json)

AFW+master+测量配置的Start前组合90秒：916个有效SNR字段仍全0/SEARCH，另61次SV事件缺列表；540条原始测量事件仍全部缺少SV数组，无TRACK/fix。注册附带测试标识`LAPI`及notification=false；它不是实际库的HAL/MHAL标签，也没有声称完整重放Android初始化。单变量AFW请求不含标识字段，分别保留报文。

普通/扩展列表同时报告时累计字段含重复，不是唯一卫星数量。所有阶段继承当时辅助状态，本轮没有重新下载/注入XTRA，不能把226的168小时收据当成本轮有效期。此前226的辅助前后零CNR证据仍单独成立。

本轮直接读回的SUPL enum2表示2.0，与ODM文件SUPL_VER=0x10000的1.0不同。这证明不能用文件内容代替当前modem状态，但当前请求是standalone，尚无证据说明该网络辅助协议差异造成原始信号为零。

## 剩余定位边界

本轮找到的是客户端身份、master、测量报告及配置链的差异；还没有找到已验证的RF/LNA上电缺口。正CNR、TRACK和真实fix保持未完成。

最有区分力的下一份证据仍是同机匹配Android在相同接收条件下的实际GNSS启动报文及射频表现，或在无遮挡天空下复用本轮有界探针。Android若有正CNR而Linux持续为0，再比对其真正执行的配置、modem固件/MCFG、RF/时钟状态；若两边都无信号，则先区分环境与硬件。当前室内负结果不足以单独判定天线或LNA故障。

后续可继续分析GNSS DIAG/RF状态，但须有该固件对应的字段语义；不把XO状态数字、变化的ADC/AGC或名含clock的API直接解释为失锁或供电故障。

本轮没有刷写、重启、修改厂商分区、GPS锁、NV/校准或生产MM/辅助服务。各程序完成Stop、释放CID和close；程序正常完成不代表定位验收通过。原始NMEA/卫星标识/坐标及归档摘要只保存在工作区外私有目录。

[最后健康检查](final-health-validation.json)核四个worker及探针均退出、定位Enabled0/Signalsfalse/rate30、辅助服务空闲、MM二进制保持、三DSP运行、taint0，整个本轮无新增WARN/Oops/GPU/DSP fatal。旧240 GPU故障历史不因本轮增量0而消除。四份私人归档各6成员已逐一验证：[基线/增量](differential-export-validation.json)、[顺序](ordered-export-validation.json)、[AFW](afw-export-validation.json)、[组合](combined-export-validation.json)。
