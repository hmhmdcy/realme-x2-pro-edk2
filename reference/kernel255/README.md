# 255：PGA来源、外部频率估计与XO初始化核对

2026-10-17，按用户要求继续在当前位置室内排查。保持原厂F.16、同254系统启动和同一HAL进程，本轮没有重启服务或系统。**不能将已测PGA −6/−10直接视为两套系统各自固定写入的初始化常量：它已存在于modem返回的状态句中，历史Linux也报过−2/0；同一次第三方Android启动中还曾从多数−10变到多数+2。** 目前仍无GNSS fix。[摘要](summary-validation.json)

后续[256室外无线对照](../kernel256/README.md)已取得原厂成功定位：302份有效位置回包覆盖约301秒，GPS最多15颗TRACK，PGA全+2；仍是同一系统启动/HAL。以下无fix结论限于255室内窗口，不再代表原厂整体定位不可用。位置和USB同时改变，尚未唯一确定改善原因。

## PGA追到了哪一层

从收到的QMI LOC `0x26`提取并验证PQWM1校验和，第9字段就是当前使用的PGA值。固定SM8150 SystemStatus参考源码按`ePgaGain=9`，以`atoi`解析，再复制到`SystemStatusRfAndParams::mPgaGain`。本机匹配ELF中的`LocApiV02::reportNmea`也将收到的普通/扩展NMEA字符串转交`LocApiBase::reportNmea`。没有发现Linux侧额外减4或把Android值换算成−10的处理。

因此已追到的是**modem报告 → QMI/NMEA → 接收软件状态对象**；尚未取得MPSS内部AGC算法、实际PGA寄存器或每个RF级的增益读回，不能据此指定一个可直接修改的初始化参数。

重新解码已保存的原始接收数据，而非只复述旧摘要：

| 同机窗口 | 实际PGA报告 |
| --- | --- |
| Linux241，90份 | 0共54份；−2共36份 |
| Linux242，90份 | 0共27份；−2共63份 |
| Linux243开窗/关闭WLAN、Linux247两轮 | 都是−10 |
| 第三方Android250窗边，188份 | −10共156份，其余−8/−6/−4/−2 |
| 同一次Android250启动的首轮室外，184份 | +2共181份，0共2份，1份PGA缺失未补0 |
| 同一次启动的后续室外301份 | −8共189份、−6共65份，另有−4/−2/0 |
| 原厂253、254及本轮255 | 已采窗口均−6 |

250三份私人boot ID逐字相同。这里没有用历史室外结果要求用户移动，也没有将第三方系统当成原厂；它是反驳“PGA由操作系统固定设置”的同启动证据。位置、时间和其它运行状态有混杂，不能把数值变化唯一归因环境或自动AGC某一算法，更不能由此建立PGA与灵敏度的线性关系。更早[208 Linux收据](../kernel208/README.md)还曾记录−6至−4。

[重新解析和分布](pga-clock-validation.json)、[AOSP固定源码](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/core/SystemStatus.cpp)。254的“原厂−6/Linux−10”仍是对应窗口的真实值，但应限定范围，不能扩写为平台固定差异。

## 固件中的PGA配置名与实际EFS查询

以只读`mtype`扫描原modem备份的31个`modem.*`成员，共77,609,277字节，逐件大小及SHA均与此前部署清单一致。在`modem.b19`中找到三个GNSS相关ASCII名称：`me/gnss_apq_pga_cal`、`me/gnss_dynamic_pga_config`、`me/gnss_pga_backoff_config`。这是配置名线索，没有函数调用或读取成功的执行证据，也没有解出其结构、单位、默认值或适用硬件条件。

按[QCSuper的STAT实现](https://github.com/P1sec/QCSuper/blob/master/src/qcsuper/modules/efs_shell_commands/stat.py)及协议常量核对，使用DIAG子系统19的HELLO/STAT，只查元数据；没有OPEN、READ、WRITE、创建、解锁或NV设置。最初推测的`/nv/item_files/gps/me/...`三个路径均ENOENT；随后核对常见的`cgps`层级，并取得成功的父目录对照：

| 实际查询路径 | STAT结果 |
| --- | --- |
| `/nv/item_files/gps/cgps/me` | 成功，目录，报告6项 |
| `…/gnss_apq_pga_cal` | errno2，ENOENT |
| `…/gnss_dynamic_pga_config` | errno2，ENOENT |
| `…/gnss_pga_backoff_config` | errno2，ENOENT |

全部8次查询都有完整HELLO/STAT回包，源文件导出SHA一致，HDLC CRC无错误；每次LOG_CONFIG GET都与原413字节全零掩码相同。父目录成功避免了把单纯的错误前缀或DIAG不可达当成三个配置项缺失。

结论只限于**这次原厂运行中，所查目录下未暴露这三个同名文件**。不能由此判定必需校准丢失，不能推算未返回文件的数值，也不能断言MPSS采用何种默认值；可能存在编译默认值、其它配置层或不同的实际读取路径。本轮没有Linux现场EFS对照，先前MPSS二进制相同也不证明全部运行配置相同。[只读查询校验](efs-pga-validation.json)、[可复核解析器](analyze-pga-efs.py)、[来源锁](source-lock.json)

## 一次新测量之后，时钟和RF指标发生了什么

沿用254已证实的19份GPS弱报告：只有第一份fresh，位边沿、毫秒时间对应状态位未成立，lock_point上报位未置位。256成功定位时该lock_point位也未置位，因此不能将它单独解释成无法跟踪。本轮重新解码同一窗口全部QMI `0x86`的时钟与分频段RF字段：

| 时段 | PGA | 频率信息来源 | 漂移不确定度 | 累计时钟重置计数 | GPS L1 C/A AGC指标 |
| --- | --- | --- | --- | --- | --- |
| 弱报告前20秒 | −6 | 1，外部注入的频率信息 | 94 m/s | 34 | 0.11—1.12 dB |
| 19份弱报告覆盖区间 | −6 | 1 | 94 m/s | 34 | 0.45—0.99 dB |
| 弱报告后20秒 | −6 | 1 | 94 m/s | 34 | 0.60—0.97 dB |

这里的source1是**频率估计来源枚举**，不是“硬件选择了某个外部晶振引脚”，也不是UTC来源枚举。`qmiLocRcvrClockFrequencyInfoStructT`明确将clockDrift及其不确定度定义为m/s；94 m/s相当于GPS L1约494 Hz的不确定度等效量，**不是测得载波偏了494 Hz，更不是94 Hz**。Linux241与原厂均报source1；第三方Android室外有正测量时同样为source1/94，因此这些值不能单独解释当前失败。

没有看到那次fresh之后发生PGA切换、频率来源失效或上报的时钟重置计数递增。频率漂移估计仍在更新，粗Doppler却沿用候选并增加不确定度，与未持续取得新观测相符；尚不能由两者的数值变化推出相关器失锁原因。

AGC/BP来自QMI `jammerIndicator`，按IDL的0.01 dB比例解码并按**星座＋信号类型**区分。不能把未测L5等频段的INT32_MAX/−100原值与GPS L1混合，然后声称极端功率或饱和。L1 BP指标在弱报告区间及随后均65 dB；这是接口报告的指标，没有经本机干扰阈值标定。较新IDL的AGC饱和状态TLV未返回，未补成“无饱和”。这些指标都不是天线输入功率或LNA电压实测。

[时间窗口比较](pga-clock-validation.json)、[Qualcomm固定IDL](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.h)

## 尝试直接取得频段PGA

固定IDL的`0xCE` BandMeasurementMetrics定义了Band1 PGA dB及分频段RF指标。本轮独立只读客户端先查询`0x1E`，再注册对应事件位、原始测量及SV事件，借用GPSTest的正常活动会话，自己不发GNSS Start/Stop或RF设置。

75秒内注册ACK成功，取得505份原始测量事件的时钟信息及75份SV事件，但`0xCE`没有返回；原HAL同时有77份PQWM1，PGA全部−6。能力位图也没有宣告0xCE，但这些结果仍不足以唯一判定“不支持”，也可能涉及该事件的产生条件；更不能把缺包解释为PGA=0。当前仍未获得这条接口对−6数值的独立单位确认。

独立客户端没有收到NMEA，不能据此说modem未生成NMEA，因为同一时段原HAL已收到PQWM1；各客户端的注册/输出配置不同。结束仅撤销自己的事件掩码，ACK成功后关闭socket。HAL的517份原始事件也未提供可用的新增GPS测量；普通列表GPS正值/TRACK均0，SBAS55个正字段但TRACK0，整体无fix。[订阅及质量](observer-validation.json)、[固定观测程序](rf-clock-observer.c)

## 普通无线电运行模式对照

先核实两SIM槽均缺卡、两份通话状态均空闲、DMS实际online=0，使用已核对libqmi定义的GET `0x2D`和SET `0x2E`，仅允许临时模式1及恢复0；没有使用offline=3、reset=4、factory-test或持久低功耗模式。

| 阶段 | 实际DMS读回 | GNSS结果 |
| --- | --- | --- |
| A1在线20秒 | 20次均0 | PGA−6，时钟source1/94 m/s |
| B临时低功耗30秒 | 过渡1次0，随后29次1 | PGA−6，source1/94不变 |
| A2恢复在线35秒 | 过渡1次1，随后34次0 | PGA−6，source1/94不变 |

两个SET的ACK均成功，最后独立GET再次确认0。87份PQWM1全部−6，GPS普通有效SNR字段1044个全0，TRACK/fix0。分段使用结束后的realtime/monotonic桥接并剔除边沿3秒；未独立排除期间系统时钟微调，但整个窗口PGA与频率不确定度恒定，因此这些主要负结果不依赖精确边界。

它只验证**这次临时低功耗切换**未改变GNSS PGA/频率报告，不能替代Linux247 offline状态或整套MPSS冷启动A/B，也不能证明外部频率信息在低功耗时仍持续更新。[模式读回与接收对照](dms-cycle-validation.json)、[限定模式程序](dms-power-cycle.c)

## XO与AP启动资源是否有明显错配

复用同启动且本轮逐字确认未变的原厂实际DTB：MSS节点使用RPMH provider的selector0，clock/proxy-clock均`xo`，proxy regulator为`vdd_cx/vdd_mss`，PAS ID4，proxy timeout10000ms。

固定realme Android R公开源码中，selector0就是RPMH_CXO_CLK，SM8150 `bi_tcxo`标称19.2 MHz；Linux SM8150驱动将同一selector绑定`bi_tcxo_div2`，38.4 MHz父时钟除2，同样为19.2 MHz。Linux242实际五个快照也均报xo_board38.4 MHz、bi_tcxo/ao19.2 MHz；本轮核实该clk-rpmh源码SHA仍与242审计一致。

Linux PAS启动源码有XO prepare/enable、CX/MSS proxy域及PAS4，handover后撤销AP代理投票；OEM通用peripheral-loader也有proxy-unvote中断/延时撤票路径。因此**没有找到这里的二倍频错误或Linux完全缺少XO启动投票的证据**。但公开OEM源码并未宣称与F.16内核逐字一致，源代码/clk_summary不是物理XO锁定或频率测量；这也未覆盖modem自行管理的RFFE、GNSS PLL、LNA和MEMSHARE。

[实际DT、源码与历史运行快照核对](clock-bootstrap-validation.json)。`rf_clk3`和UFS LDO10的既有归因保持，不拿这些无关资源冒充GNSS初始化动作。

## 结论范围与收尾

本轮推进的是PGA上报来源、非固定平台值、三个固件配置名的只读EFS核查、fresh丢失前后的频率/计数连续性，以及一次真实无线电状态对照。**当前更符合“候选未被持续接收/同步刷新”，没有发现可直接归责的PGA常量或AP XO初始化错误。** 最终原因仍可能涉及真实RF信噪、频率/相位动态、基带相关器或其它初始化条件；本轮没有把它判成已知硬件损坏。Linux完整client1 5 MiB连续内存/SCM provider仍缺，因果也未验证，不能据上述AP bootstrap匹配宣称两端完整初始化相同。

同stock boot/同HAL、服务及xtra运行、TracerPid0；原应用偏好2128字节恢复，Wi-Fi/后台扫描1、BT0，vendor/ODM哈希及实际DTB保持。独立DMS GET确认online，自己的LOC订阅已撤销；本轮未改DIAG日志掩码，未新增uprobes或ftrace实例，全局原off/nop/local、SELinux Enforcing保持，任务进程均退出。[最终状态](final-validation.json)

原始QMI、位置、设备身份、NMEA和电话状态只在工作区外私人`E:/edk2-samurai-out/kernel255`。公开解析器只读已保存数据，两个原生程序的原始stdout也须私人保存。没有请求HAL/OS/modem重启或刷写，没有直接操作NV、校准、RF寄存器或GPIO。当前仍保留原厂系统，Linux全机验收240和返回备份248保持。
