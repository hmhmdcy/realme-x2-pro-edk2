# 254：GPS SEARCH 的新鲜度与原厂初始化实测

2026-10-17，继续在用户指定的当前位置室内测试，保持原厂 realme UI 2.0 / Android 11 / F.16，同251—253系统启动。**尚未定位成功。253的19个GPS弱正值中，只有首条带有“最近一秒获得新测量”标志；其余18条属于保留/外推报告，不能当成连续19次捕获成功。** 本轮新采集2808个DIAG原始C/N₀字段全零，PGA仍−6；没有把原厂/Linux的PGA差异认定为根因。

## 为什么有弱信号却仍 SEARCH

按锁定的高通IDL重新解码253原始QMI `0x86/TLV0x1B`，957份事件中19份有真实卫星数组，其余938份缺数组，未计作零测量。19份均对应同一颗GPS，QMI C/N₀=19.5 dB-Hz，DIAG=15.9；仍是19个累计字段，不是19颗卫星。

| QMI测量状态；均先检查有效掩码 | 19份中的真值次数 |
| --- | ---: |
| 最近一秒有新GNSS测量 | 1，仅第一份 |
| 码相位已知、粗Doppler已知 | 各19 |
| 子比特时间、毫秒时间已知 | 各0 |
| 已确认位边沿、有效锁定点 | 各0 |
| 精Doppler已知 | 0 |
| 普通状态进入TRACK、星历标志 | 各0 |

粗Doppler连续19份固定323.5087585 m/s，其不确定度从10.4485增至37.4485 m/s，每份约增加1.5；SV时间已按接口定义传播到公共参考时刻。因此“同一次候选被延续/外推，未建立持续同步”比“已经稳定接收19秒”更符合证据。这解释SEARCH的直接测量状态，尚未区分最终由RF信噪、频率搜索还是其它初始化条件造成。

DIAG与QMI的卫星编号、SV毫秒/小数时间、Doppler/不确定度及状态低32位全部19/19一致，支持这两路确实对应同一组测量；**延迟和时间不确定度却不一致**：QMI latency均0，DIAG `Latency`原值6139→24139；QMI时间不确定度固定约0.00009295 ms，DIAG相应浮点变化。没有把DIAG Latency原值直接换算成秒，也不利用它推断候选早于Wi-Fi关断。接口的`lossOfLock=0`同样不能覆盖有效锁定点为假的证据。

[严格QMI解码与掩码](qmi-measurements-validation.json)、[原始GPS字段/时钟对照](search-measurements-validation.json)。定义来自锁定的[Qualcomm LOC IDL](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/location_service_v02.h)，没有把DIAG未知高位解释成硬件故障位。

## 原厂服务重启与初始化采集

保持SELinux Enforcing，使用libc `sendto`入口/返回uprobes，只读采样最多256字节。先与同一HAL的成功strace发送交叉验证：5个请求均唯一匹配，包含4个完整包及1个大包前缀；第二次验证同时核对成功返回值。[探针验证](uprobe-validation.json)、[返回验证](uprobe-return-validation.json)。静态原生辅助工具没有调用bionic，不能用它验证该探针，初次辅助工具尝试未作为通过证据。

两次均先确认当前boot、服务身份及TracerPid，再各发送一次普通SIGTERM，由原init服务自动按原gps用户/SELinux域重新启动；不是手工root执行HAL。未请求系统/modem重启，也未刷写分区。

第一轮采集包含20秒基线、服务重启及90秒搜星。取得74个可归属新HAL线程的完整成功发送，另一个Wi-Fi大包只有前缀。由于同时开启的电源事件导致部分CPU缓冲覆盖，**这份不是完整初始化证明**。随后缩小为短时纯uprobes采集，再次重启定位服务，8个CPU overrun/drop均0，取得39个完整成功初始化发送。只覆盖已核实线程的sendto路径，不声称覆盖所有瞬时退出线程、其它IPC、厂商文件打开或modem内部RF总线。[初始化结果](initialization-validation.json)

| 本轮实际看到的原厂动作 | 与Linux适配的关系 |
| --- | --- |
| master `0xBA`、测量配置`0x88`、AFW相关事件注册`0x21` | 不是仅在ELF发现；Linux241已有相应补入试验而未恢复信号 |
| 9次协议配置`0x54`，SUPL枚举1→2，LPP配置2→3 | 实际存在初始化/框架覆盖；只读运行内存也确认LPP_PROFILE由253的2变成3，不能只按gps.conf文件字面比较 |
| lock `0x3A`依次4/3/4/3/3，NMEA`0x3E`、blacklist`0xB6`等 | 与已知原厂路径吻合；不能将lock或NMEA选择当成RF增益 |
| CTU `0xCA`、PACE `0xCB`请求值均0 | 原厂并未请求打开它们；发送成功不等于异步完成，不能称它们是Linux漏开的已生效RF开关 |
| 未识别出直接PGA/LNA增益设置命令 | 不等于证明modem内部没有RF初始化；当前无经验证可安全重放的增益寄存器设置 |

短采只用于初始化，晚附加strace没有接收测量包，也没有GNSS Start，未把该空窗口计作搜星失败。之后唤醒/解锁并重新开启GPSTest完成约33秒有效测量，确认当前服务仍可接受正常定位请求。

后续[255来源追踪](../kernel255/README.md)确认PGA已存在于modem返回的PQWM1中；Linux241/242也曾报−2/0，第三方Android同一启动内可从−10变到+2。因此以下−6/−10仅描述对应窗口，不是平台各自固定的初始化常量。255另核对了该次fresh前后的频率来源、时钟重置计数及普通无线电模式对照。

## 实际接收与PGA比较

第一轮重启后的90秒，89份SV事件中的4338个有效SNR字段（普通/扩展重复格式）全0/SEARCH；没有GPS/GLO/Gal TRACK、星历或fix。连续DIAG覆盖基线及重启后，GPS1296、GLO972、Gal540，共2808个实际原始C/N₀字段全0；110份PRX v5、body722的offset76候选均为−6。[原始测量](init-measurements-validation.json)、[完整性](init-export-validation.json)

最后约33秒复测，普通列表GPS396、GLO297、Gal240字段仍全0；SBAS出现30个正字段，最高约33.6 dB-Hz，其中18个TRACK，最多同时1颗；无fix。228份QMI原始事件全部缺卫星数组，不能称为228个零C/N₀。33份PQWM1的PGA全部−6。[最终复测](final-readback-validation.json)

| 已核实的比较 | 能得出的结论 |
| --- | --- |
| 原厂HAL、原厂环境的原生standalone客户端、两次服务重启后PGA均−6；Linux247为−10 | 差异真实存在，但不是“是否经过Android定位API”单独决定；原生客户端仍共享先前初始化过的modem环境 |
| 原厂−6同时出现GPS弱候选、SBAS TRACK及全零窗口 | −6并不充分保证成功，也不能由它单独判断天线/LNA健康 |
| 原厂时钟频率不确定度原值94；Linux247 online同为94，仍无fix | 不支持把Linux这项数值单独作为缺时钟初始化的证明；不是物理XO频差/锁定测量 |
| 当前十项RF_LOSS仍0；其余运行数值除LPP_PROFILE外与253一致 | 软件补偿数组不等于物理PGA/LNA设置；没有用抬高显示C/N₀的办法冒充接收改善 |
| 原厂client1实际5 MiB MEMSHARE成功；Linux完整provider/SCM转交仍缺 | 具体适配缺口保持，但本轮未实现，未证明它引起原厂当前共同无fix |

原厂与Linux不是同一时刻的严格接收条件A/B，−6/−10没有物理增益标定，不能当作相差4 dB的灵敏度证据。现阶段最明确的问题仍是**捕获候选未形成持续同步/锁定**；PGA、板级RF电源/RFFE初始化与Linux provider差异的因果尚未闭环。

另做固定只读GET `0x55`，mask0x60c，ACK及完成status均0，实际只返回SUPL版本枚举2；请求的LPP/LPPe字段未返回，不能补成0或当作modem已采用LPP=3的证明。运行内存和发送报文证明的是HAL值/请求，范围不同。[运行配置](runtime-config-after-validation.json)、[只读GET源码](protocol-readonly.c)

## 收尾与续作

当前仍原厂、同系统启动，**HAL已重启两次，旧PID943失效**；续作必须重新读取root属性中的当前服务PID。原始QMI/DIAG、线程身份、进程内存和位置等只在工作区外私人`E:/edk2-samurai-out/kernel254`。Linux最后全机验收240、返回备份248保持。

equipment1原诊断掩码3304位/413字节经GET逐字恢复，18份主采集及8份短采文件均核手机源SHA；DIAG CRC错误/残帧/尾部截断均0。全部本轮uprobes、ftrace实例和strace移除；全局原off/nop/local、SELinux Enforcing保持，服务/xtra正常、TracerPid0。Wi-Fi/后台扫描策略始终1，蓝牙0；GPSTest偏好恢复原2128字节，vendor/ODM文件哈希未变，无任务残留进程。[最终状态](final-validation.json)

没有修改系统时钟、直接写RF/GPIO、NV、校准或分区。后续应验证Linux完整MEMSHARE provider及取得有字段定义/板级依据的真实RF状态；不能仅凭PGA常量、SBAS标称载波、AP缺少电源事件或谱包未知字段宣布LNA损坏/关闭。保持当前位置排查，不设室外或另一台手机前提。
