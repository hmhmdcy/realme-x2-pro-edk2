# 246：真实RF/时钟日志与modem原始零C/No

2026-10-17。上一轮245分类为进展，本轮继续完整“直到Linux手机定位可用”的goal。仍为室内开窗窗边；未刷Android、未换boot/内核或写原始NV源。本轮完成一次普通Linux重启，**当前246启动/boot235/Image183，244及更早guard失效**。

**取得1245份真实GNSS/RF/时钟诊断报文，原始卫星记录中的2607个C/No字段全部0；定位仍未恢复，goal保持active。** 这把“零值仅由上层QMI解码产生”的解释排除为单独原因，但尚未确定天线、LNA、RF配置或时钟的根因。

## 首次启动持续采集的结果

临时OpenRC项在samurai-radio前发布端点。本次新boot完成新feature和两个DIAG_ID分配，两次VERSION均返回55字节。沿244已成功顺序发送实时模式和十项日志mask，保持同一组socket跨两个90秒会话；本次首次启动路径没有新增control17。

第一次普通观察在MM PowerState1下；第二次通过标准MM SetPowerState(3)进行online对照。两次Start前都确认**本次watch已运行、时间准备完成且完成计数大于0**。没有把启动初期持久watch文件里旧的time_prepared=true当成新boot已准备；当时running=false，随后新daemon重置为false并实际完成准备。[就绪](inspect-readiness-validation.json)、[首轮触发](request-baseline-validation.json)、[online触发](request-online-validation.json)

| 日志 | 代码 | 首轮 | online | body字节数 / 前导字节 |
| --- | --- | ---: | ---: | --- |
| GNSS Clock | 0x1478 | 93 | 93 | 174 / 3 |
| PRX RF HW状态 | 0x147e | 91 | 91 | 722 / 5 |
| Spectrum Analyzer Jammer | 0x1635 | 77 | 77 | 331 / 2 |
| GPS测量 | 0x1477 | 90 | 90 | v0固定头28，加70字节卫星记录 |
| GLONASS测量 | 0x1480 | 90 | 90 | v0固定头29，加70字节卫星记录 |
| Galileo测量 | 0x1886 | 90 | 90 | v0固定头30，加71字节卫星记录 |
| Configuration State | 0x1516 | 3 | 0 | 72 / 6和295 / 3 |
| WWAN/WLAN IMD Jammer | 0x1596 | 90 | 90 | 60 / 4 |

DRX147f与BDS1756没有日志，不能补零或据此判不受支持。所有日志outer/inner length一致，等于实际payload长度减4；非HDLC解帧和包长度错误0。前导字节在未有该版格式定义时不自动当作已验证的版本。615个QRTR接收datagram含1245份日志，两个计数不能混用。[首轮形状](baseline-off-preview-validation.json)、[online增量形状](comparison-online-preview-validation.json)、[最终采集结果](poll-firstboot-validation.json)

online原始快照含首轮完整前缀。分析时先逐字验证前缀相同再剔除385850字节，仅解析新增621份；首轮为624份。不能将1245份累计快照又算作online新增1245份。

## 原始C/No与QMI一致

按已锁定[MobileInsight GPS](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_gps_measurement_report.h)、[GLONASS](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_glonass_measurement_report.h)、[Galileo](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_gal_measurement_report.h)布局：只接受version0，先核完整header及`header + count × stride`精确等于实际长度，再从已核offset读u16 CNo并除100。不是在未知长包上猜偏移。

| 指标 | MM PowerState1首轮 | MM PowerState3 online |
| --- | ---: | ---: |
| QMI有效SNR字段 | 766，全部0/SEARCH | 3872，全部0/SEARCH |
| QMI缺SV列表事件 | 60 | 2 |
| GPS原始CNo字段 | 377，全部0 | 1408，全部0 |
| GLONASS原始CNo字段 | 6，全部0 | 528，全部0 |
| Galileo原始CNo字段 | 无记录，不能计零 | 288，全部0 |
| GPS周数 | 2440，全90份 | 2440，全90份 |
| 正CNo、TRACK、成功fix | 0 | 0 |

GPS首轮61份无记录/29份各13记录；online2份无记录/88份各16记录。GLONASS首轮仅1份6记录、online88份6记录；Galileo online18份各16记录。GPS/GLO的ObsState原值均1、MeasStat原始字节11062000；Galileo为0/00002000。未依据记录数或未验证的bit称已经捕获卫星。空测量包不是零CNo样本，普通/扩展QMI的重复字段也不是唯一卫星数量。[首轮严格解码](baseline-off-satellite-validation.json)、[online严格解码](comparison-online-satellite-validation.json)

这次直接读到modem内部CNo为0，不能再只怀疑MM/NMEA字符串转换；仍未证明具体哪段模拟RF链路失效。

## 时钟与RF状态的具体变化

测量header中的`ClkFreqUnc`原始浮点值首轮恒1500，online恒94；FreqBias范围−1.171至0.878、1.757至28.691。采用源码字段名，不给未验证的固件值补Hz等物理单位。变化说明软件时钟估计状态不同，不是物理XO锁定测量。这是顺序A/B，未做A/B/A，时间经过和先前状态也可能参与，不能把全部变化唯一归因SetPowerState。

独立按固定SM8150 SystemStatus解码的两轮PQWM1各90份，time_valid1/time_source7、XO原值11、PGA原值−10、error_recovery0。clock_bias_unc原值5123→321；ADC I146—149→138—148、Q139—142→131—140；GPS AGC−3.50至−3.19→−3.37至−2.65；GPS jammer70—71均保持。没有标定阈值，不凭jammer、AGC或XO枚举认定强干扰/失锁。

PRX722字节包的offset116和120按小端int32读取，与独立PQWM1 ADC I/Q分别在**两轮各90/90**匹配（PRX序列相对NMEA偏移一条）；每个字段只有这一处候选offset满足双轮条件。这是可复核的经验对应，不是完整公开wire schema，也不是天线/LNA电压或RF输入功率测量。PRX包含SDR8150、L1-E/L5-E等字符串，静态标识不能证明路径实际使能。

Clock174、PRX722及Config各版尚未获得完整权威字段定义。Spectrum331可分为6字节前缀及13个25字节候选槽位；每包所有槽的“第二整数−第一有符号整数”相同，三种基准整数分别1575420000、1602281250、1561098000，两轮各48/21/8包。初版只假定一个GPS基准的断言失败，已按实际三基准修正；**这只是算术结构推断，功率单位、flag语义、干扰强弱均未确认**。不能据此选GPIO、改RF校准或认定某个干扰源。[比较与经验映射](rf-comparison-validation.json)

## 先前重连的control17对照

在旧244启动先依据固定[linux-msm/diag](https://github.com/linux-msm/diag/tree/23c12c167e93215853af4e59c021551767f6fec8)和[Android打包实现](https://android.googlesource.com/kernel/msm/+/bf51f920fdef2acb189f5c2e282148279a1f12c9/drivers/char/diag/diagfwd_cntl.c)补发control17 v1/stream1/streaming0（14字节）。原端口与两份VERSION匹配后，90秒仍日志0包、746个有效SNR全0，未恢复重连日志。退出发送mask清零/实时模式释放并关闭；原buffering模式没有getter，不声称精确恢复其原值。[报文及回归](streaming-library-validation.json)、[实测](poll-streaming-validation.json)

随后使用首次启动采集才收到上述八类报文，因此本轮没有宣称control17修复了日志通道或GNSS。实时模式包含上游sleep vote，结束释放；没有NV/射频配置命令API，没有原位图读回或撤销ACK，不声称逐字节恢复原mask。

## 普通Linux重启和当前设备身份

重启前核244 guard、Image183、F2FS根sda16、34个modem部署哈希、文件服务实际PID/执行文件与NV源哈希。先停定位/桌面/音频/传感器消费者、解绑ath10k，再停三DSP；保留camera MFD/providers。供电空闲、显示inactive、fault/taint0后，按当前EUD驱动退场顺序仅进行普通RESTART，不进bootloader、不刷写。请求在主机预记一次；USB在最终receipt前断开，后续只观察，没有重复提交。[前置核对](pre-reboot-health-validation.json)、[停流](poll-quiesce-validation.json)、[单次请求代码](submit-normal-reboot.py)

刷新唯一USB NCM邻居、保留原严格SSH密钥，核不同boot ID、相同model/release，确认新246启动；三DSP先后就绪，MM及时间watch完成准备后才Start。[新boot](observe-nextboot-validation.json)

当前guard：`/var/lib/samurai/k246-runtime/boot-id-private.txt`。运输：[host.py](host.py)、[run-postboot.py](run-postboot.py)，私有USB端点在`E:/edk2-samurai-out/kernel246`。244及更早guard无效，预重启脚本只适用于旧244，不能重放或覆写旧guard。

采集worker及LOC子进程均退出，两个阶段Stop/release/close通过；临时hook和stale started项已移除，本地DIAG/52服务0。锁MT、操作模式standalone、MM PowerState1、DMS读回offline、location0/Signalsfalse/rate30、watch running/activefalse/timepreparedtrue/dataworker0。**只证明MM电源枚举回到1，未证明DMS与新boot首轮未查询的原始值逐字相同。** 三DSP和Wi-Fi正常，新boot WARN/Oops/GPU/DSP fatal0、taint0，原NV源哈希保持。[最终健康](final-health-validation.json)

59项完整原生归档逐成员大小/SHA验证，另有两份各11成员的活动期快照；原始DIAG/NMEA/坐标/标识及完整状态仅私有保存。[完整归档](evidence-export-validation.json)、[首轮快照](baseline-off-snapshot-validation.json)、[online快照](comparison-online-snapshot-validation.json)

## 继续定位

本轮Exa四次针对RF/Clock版式查询请求20项结果；一次大页面读取连接失败，随后搜索恢复。未找到与前导3/174、5/722匹配的可验证完整decoder，未套用Android HAL的GnssClock结构或其它SoC枚举。已缓存19781板源里的rfa/rf_clk3命中属于WLAN节点，GNSS UART是通用CDP/MTP注释；这些命中不提供本机LNA接线证据。

最明确的软件待证项还包括**modem首次启动前的MEMSHARE真实请求**：245只在运行期公布服务，246仅提前建立DIAG。下一次可在modem启动前提供同号、不给物理地址的观察服务，核是否出现GPS client0及实际申请大小，再决定真实分配/SCM实现；当前不搬用MSM8916的2MiB地址或大小。

同时继续解读实际PRX/Clock/Config字段，核对真实天线与LNA板级链路，或用保持端点的多轮采集验证RF干扰候选。不能从未标定谱值直接动RF寄存器。已异步询问完整装机状态及最后一次Android正常定位时间，尚待用户反馈；未再要求户外或刷Android，也未把未知装机状态解释为硬件故障。

仍未达到定位可用。245锁NONE负结果、MEMSHARE113秒0请求和active ID匹配原机MBN SHA1证据保留；其它外设沿用240验收，本次不是整机新验收。
