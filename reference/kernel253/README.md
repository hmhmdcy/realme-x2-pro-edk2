# 253：原厂GPS弱信号、UTC实注与射频/初始化对照

2026-10-17，按用户要求继续在当前位置室内排查。保持原厂realme UI 2.0 / Android11、`RMX1931_11_F.16`，同251/252启动，没有刷写、OS/HAL重启或NV/校准写入。**尚无定位成功，但已取得普通GPS的非零原始C/N₀，不能再将“GPS始终固定为零”作为当前结论。** [摘要](summary-validation.json)

后续[254](../kernel254/README.md)已解出这19份的QMI测量有效位：仅第一份fresh，后18份没有新测量；位同步、毫秒时间和有效锁定点均未建立。因此本页“连续正值”只描述报告字段，不表示连续捕获成功。254另做两次HAL重启与原厂初始化实测，当前HAL身份已变化。

## 新出现的GPS数据

在关闭Wi-Fi连接及后台扫描的第一段，同一颗GPS出现19个连续正值：DIAG原始C/N₀为15.9 dB-Hz，QMI普通SV列表为19.5 dB-Hz。两路卫星编号相同且落在GPS合法范围，普通列表状态均为`SEARCH=2`，没有进入`TRACK=3`，也没有星历或成功定位。它们是约19秒内同一颗卫星的累计字段，**不是19颗卫星**；两个接口的C/N₀分别保留，未假定处于相同测量/补偿点。[交叉核验](gps-positive-validation.json)

SBAS仍能间歇报告约34.2 dB-Hz和TRACK。GPS弱正值只出现在四段重复对照的B1，B2没有复现，所以不能把一次同时变化直接归因于Wi-Fi，也没有证明此时已有可用导航测量。当前现象更具体地表现为：基带能给出普通GPS弱信号候选，却未形成稳定跟踪；接收质量、干扰、天线/RF链路及捕获策略的最终原因仍未确定。

本轮三次采集共8756个实际原始C/N₀字段，其中19个GPS非零；GLONASS、Galileo仍全零。分别取得1896、2429、2897份GNSS/Clock/RF/任务分配日志。缺记录没有算作零值，普通/扩展SV列表的重复格式不混入这些DIAG字段数。

## 时间链路：更正旧标注并实测

此前250—252把`0x7D`误标为UTC注入。官方IDL确认它是Wi-Fi AP数据注入，真正UTC为`0x38`。旧文字和252相应JSON键已更正，原始包及C/N₀统计不变。[协议更正](PROTOCOL-CORRECTION.md)

这次使用三个外部NTP源交叉核对，检查响应源模式、闰秒告警、stratum和originate时间戳，按往返、根延迟/离散度及传输余量给出1000ms不确定度。参考UTC绑定手机BOOTTIME，并在发送时补足经过时间；拒绝过期参考。PC的PHC0仅反映本地时钟关系，没有单独拿它当外部UTC准确度依据。采样时手机实时时钟比外部UTC约慢204ms，没有看到数秒以上的系统时间错位；旧252接收器GPS周/TOW减实际报告的18秒闰差后，与手机trace时间约差−0.46秒。

| 活动会话阶段 | 实际结果 |
| --- | --- |
| UTC注入前 | 35份PQWM1；TimeSource=7，TimeUncNs约6.71457秒；无正SV信号/fix |
| 标准0x38请求 | TLV1=u64 UTC毫秒、TLV2=u32不确定度1000ms；ACK及异步完成均成功，正常关闭独立client |
| 注入后继续60秒 | 60份PQWM1；TimeSource=3，TimeUncNs约6.00000—6.00003秒；仍无正SV信号/fix |

这次接收器报告确实发生变化，不只看shell返回或ACK。原始GPS/GLO/Gal合计2257个C/N₀字段全零，未被UTC注入修复。[时间对照](time-chain-validation.json)、[原始测量](time-measurements-validation.json)。Linux209此前同样成功注入UTC、仍报告约6秒且无正CNR，见[209](../kernel209/README.md)。报告的不确定度不是实测系统时钟偏差；也不能据此判定物理XO失锁。后续新GNSS会话未再次注入，不把其TimeSource=7当作本轮取得过fix。

## Wi-Fi连接、后台扫描和重复性

USB保持调试，蓝牙全程关闭。首轮30秒ON→40秒OFF→45秒ON时，GPS/GLO/Gal原始2965个C/N₀字段全零；SBAS在前两段有正值，重新开启后没有正值。这一轮只关连接，原后台扫描策略仍为1，电源ftrace在两个CPU出现796/3025条覆盖；**不能把它当作完整的射频静默或完整电源时序证据**。QMI/DIAG帧本身无截断或CRC错误。[首轮](radio-aba-validation.json)

随后将`wifi_scan_always_enabled`固定为0，再做重复对照。B1/B2均以设置读回和Wi-Fi服务状态确认连接关闭；不是仅相信关闭命令返回。

| 阶段 | 时长 | GPS | SBAS | 定位 |
| --- | ---: | --- | --- | --- |
| A1，Wi-Fi开启 | 30秒 | 无正值/TRACK | 最高34.2，有TRACK | 无 |
| B1，连接和后台扫描关闭 | 40秒 | 同一颗19次正值；QMI19.5/原始15.9，仍SEARCH | 最高34.2，有TRACK | 无 |
| A2，Wi-Fi开启 | 40秒 | 无正值/TRACK | 无正值 | 无 |
| B2，连接和后台扫描关闭 | 40秒 | 无正值/TRACK | 无正值 | 无 |

因此观察到了弱GPS候选，但未建立“关Wi-Fi就稳定恢复”的可重复关系。四段同一活动会话，PGA报告均−6；原始3534字段中19个GPS非零。不能排除其它本机/外部干扰，也不能将负结果解释为硬件完全正常。[四段对照](radio-abab-validation.json)、[原始测量](abab-measurements-validation.json)。结束恢复连接和原后台扫描策略，Wi-Fi已重新连接。

## 射频、载波和电源证据

- 251的61条正SBAS应用记录载波为1575420032Hz，恰好等于1575420000Hz转换为float32后的数值。32Hz差值不能拿来判定失谐。SBAS L1与GPS L1同为标称1575.42MHz；这是标称频率/接口表示，不是频谱仪实测，也不证明天线完整健康。[数值核验](sbas-carrier-validation.json)、[官方WAAS标准](https://www.gps.gov/sites/default/files/2025-07/2008-WAAS-performance-standard.pdf)
- 原厂PRX body722的offset76—79为有符号−6，Linux247为−10，分别对应这些窗口的PQWM1 PGA报告。它是**经验字段对应候选**，尚无完整PRX v5公开布局；不是已识别的LNA使能bit。原厂同一个−6下既有SBAS/GPS候选又有全零时段，不能用该常量单独解释接收成败。[候选比较](prx76-candidate-validation.json)
- 实际设备树中`pm8150_l10`被UFS控制器的`vcc-supply`引用。其2.504V/用户1不构成GNSS LNA供电证据；`rf_clk3_clk`同样位于wil6210/WiGig节点。没有把这些资源误作内部GNSS接线或对它们写寄存器。
- 在独立ftrace实例中采集regulator、GPIO、RPMH和SPMI写事件。时间对照无覆盖；首轮Wi-Fi有覆盖，重复轮缓冲增至4MiB/CPU后八CPU的overrun/drop均0。观察到的电源活动主要涉及UFS/GPU/MMCX等，仍不能由“未看到GNSS专属事件”推出LNA断电；基带自身管理的动作未必经过AP这些tracepoint。
- 请求了SBAS demod/report日志，但三轮未产生相应包，不能将缺包当作未接收的证明。尚无SBAS导航数据CRC或独立原始测量验证。新取得4714份搜索策略任务分配0x148A日志，其私有格式未解，不据日志名称猜每个搜索通道的成功状态。[帧完整性与实际日志种类](diag-integrity-validation.json)

## 初始化链路：读取真实运行配置

确认当前服务路径为`/vendor/bin/hw/android.hardware.gnss@2.1-service-qti`，init配置以gps用户和system/gps/radio/vendor_qti_diag组运行，实际SELinux域为vendor_hal_gnss_qti。本轮没有另启厂商HAL，也没有为追踪关闭SELinux或重启现有服务。

根据匹配的实际ELF配置表和重定位，只读复制当前进程的1232字节`ContextBase::mGps_conf`，解析35项；另取得10项RF_LOSS的40字节运行数组。补充Android RELR地址遍历后，libloc_core/libloc_api各564/785个RELR目标纳入分析；此前按已知地址读取指针的方法不因此失效。[离线复核](runtime-config-reproduced.json)、[配置比较](live-config-validation.json)、[RELR解析](elfview_relr.py)

| 当前真实值 | 解释范围 |
| --- | --- |
| AGPS_CONFIG_INJECT=1、LPP_PROFILE=2、CAPABILITIES=23、NMEA_PROVIDER=0 | 这些值已在运行对象中，不是仅发现文件；仍不是完整exec/open/初始化时序 |
| SUPL_VER=0x20000；vendor/ODM文件为0x10000 | 不能只凭文件字面断言最终配置，也未证明哪一环覆盖/保留了该值；本轮未修改或据此宣布RF修复 |
| 十项RF_LOSS均0 | 已验证当前软件配置；不能等同LNA断电。官方参考实现用RF_LOSS计算上报的baseband C/N₀补偿，不能用它解释在AP处理前已经出现的modem零测量 |

服务器等字符串值不公开。相同的默认值和共同文件键不能独立证明具体打开过vendor还是ODM路径；当前没有补得原厂完整初始化trace。[高通参考实现](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/LocApiV02.cpp)

## Linux对照与剩余缺口

原厂当前已报告弱GPS候选，Linux247当时2586个原始C/N₀仍全零；两者不是同一时间严格同天空条件A/B，不能直接把强弱差归因于某个初始化参数。MPSS34文件、活动平台/软件MCFG及已返回星座/黑名单相同的证据仍按251/252；PGA差别没有物理增益或灵敏度标定。

Linux MEMSHARE client1依旧缺真正5MiB连续内存和SCM所有权转交；原厂该分配已成功。它是独立的适配缺口，本轮没有实现/部署，也未证明它造成当前共同无fix。时间辅助在两种系统上均可完成但未修复接收；原厂HAL运行配置已进一步实读，物理RF/时钟与完整厂商初始化时序仍待核。后续应围绕稳定捕获、真实RF状态和完整provider验证继续，而非调整RF_LOSS来抬显示数值或猜GPIO。保持当前位置排查，不设室外或另一台手机前提。

## 完整性和收尾

三轮诊断结束均以GET逐字节确认equipment1原日志掩码恢复。51个手机源文件逐项SHA256核验，所有DIAG解帧CRC错误/截断/尾部残帧0。首轮get-sbas请求ACK成功但完成status6/TIMEOUT，未取得有效配置，不能当作查询成功。编译格式警告、旧日志非UTF8注释、补充RELR遍历前未找到RF表等分析失败均先拒绝后修正，没有拿失败调用当手机功能结果。[导出](exports-validation.json)、[源码锁](source-lock.json)

最终同启动/原HAL进程、服务running、TracerPid0；Wi-Fi和后台扫描原策略1恢复并重新连接、蓝牙仍0，所有本轮采集器和GPSTest退出；GPSTest自动更新的两项能力缓存已恢复原字节，vendor/ODM配置保持，独立trace实例删除、全局tracing仍原off/nop/local、SELinux Enforcing。没有系统时钟修改、缓存清空、NV/校准/分区写入。[最终状态](final-validation.json)

原始QMI、坐标、卫星标识、进程内存和Wi-Fi资料只保存在`E:/edk2-samurai-out/kernel253`。公开[阶段解析器](analyze-trace-phases.py)和[配置解析器](analyze-runtime-config.py)只读已保存证据并输出脱敏结果；[UTC辅助工具](loc-time-probe.c)会发送普通时间辅助，原始stdout须保持私人。当前仍保留原厂，最后Linux全机验收240、返回备份248均未改变。
