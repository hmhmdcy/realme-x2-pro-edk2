# 258：Linux室外无线GNSS持续定位，完成原厂对照

2026-10-17，用户确认已把恢复后的Linux手机放到刚才原厂测试的室外位置，并拔掉USB。通过原主机密钥的无线SSH核对257同一Linux启动、USB输入0、taint0和定位辅助就绪，完成一轮300秒原生QMI LOC采集。**Linux成功持续定位：287份有效坐标回包全部仅报告SATELLITE，连续输出286.003秒，最大间隔1.012秒。** [结果摘要](summary-validation.json)

| 项目 | 256原厂F.16室外 | 258 Linux室外 |
| --- | --- | --- |
| 有效坐标回包 | 302份，覆盖300.998秒 | 287份，覆盖286.003秒 |
| 最大成功回包间隔 | 1.563秒 | 1.012秒 |
| GPS最多TRACK卫星，按同一报文内卫星编号去重 | 10颗 | 12颗 |
| GPS最高C/N₀ | 45.5 dB-Hz | 44.4 dB-Hz |
| PGA | 302份全部+2 | 300份全部+2 |
| 频率估计来源 | 1 | 1 |
| 定位后的漂移不确定度 | 2.661—5.873 m/s | 2.929—5.449 m/s |

两端系统启动、辅助数据与开始时状态不同。原厂捕获开始前已经定位；Linux首份有效位置距客户端初始化12.919秒，之后约每秒一份，结束Stop时另有一份USER_END=4。因此287对302不是丢失15次定位或性能退步的证据，也不能据此比较冷启动TTFF、接收灵敏度或绝对精度。[对照汇总](comparison-validation.json)

## 卫星数量更正

本轮复核发现普通SV列表也会重复出现同一星座、同一卫星编号。此前256所说的“最多15颗”和本轮进度中的“最多17颗”实际是TRACK条目数，不能直接当作不同卫星数量。逐报文按星座和卫星编号去重后，GPS峰值分别为原厂10颗、Linux12颗，最后分别9颗和10颗。普通与扩展列表仍分开处理；这次另补了普通列表内部去重。保留历史条目计数，修正其解释和当前入口。[去重审计](sv-uniqueness-validation.json)、[审计代码](audit-unique-satellites.py)

## 持续新测量、射频与时钟

GPS原始测量4110条，其中4099条TRACK、10条SEARCH、1条IDLE；584份含GPS数组的测量报文中559份含fresh记录，共2567条fresh，首末fresh报文跨度296.761秒。4099条位边沿、4097条毫秒同步状态为真，均先核对有效位。这已经与旧室内“仅首次fresh、之后停在SEARCH”的行为不同。584是跨信号的测量报文数，不等同于584个独立GNSS历元。Galileo、GLONASS、BeiDou、QZSS也有持续新测量与TRACK。[原始测量汇总](measurements-validation.json)

PGA由历史Linux室内的−10变为本轮全+2，和原厂室外一致；本轮没有设置PGA、射频寄存器、时钟、NV或校准，也没有补齐此前记录的client1完整5 MiB连续内存/SCM provider。这证明现有Linux组合可以完成持续卫星测量和定位，不能继续将−10或该provider差异当作本机必然无法fix的充分解释。完整provider支持及两端初始化差异仍是未完成项。

频率估计来源仍为1；重置计数2376份全部为7，没有反复重置。漂移不确定度在启动早期为94 m/s，定位后为2.929—5.449 m/s。它是运行估计，不能代替物理XO、PLL或天线输入功率测量。GPS的lock_point状态仍全部为假，同时实际TRACK与有效定位成立，与原厂对照一致；该位不能单独作为失锁判据。[PGA与时钟](pga-clock-validation.json)

这次和旧室内测试同时改变了位置、USB连接、启动及辅助状态；本轮还将正常modem电源策略临时切为在线。247已有室内在线仍失败的记录，但这里没有做全部单变量往返，室内失败与PGA变化的具体原因尚未识别。两次室外峰值C/N₀相差1.1 dB-Hz，也不能证明哪一端灵敏度更好。

## 采集方法与收尾

从226已审查的同CID原生客户端构建新工具，固定300秒、session226、高精度请求；增加raw测量事件和0x88客户端测量报告配置0x3f，停止后清零该配置。没有改OEM增益/时钟初始化，不重启modem，不清辅助数据。[客户端源码](loc-session.c)、[构建验证](build-validation.json)

无SIM下ModemManager原PowerState1；260复核本轮原始 `dms-before` 日志，实际DMS为SHUTTING_DOWN，修正此前误写的offline。通过正常接口临时切PowerState3，并GET确认DMS online后采集。worker独立于SSH存活，退出时恢复PowerState1，实际DMS变为OFFLINE；两种固件状态不能因MM均映射为1而视为相同。原engine lock=mt和standalone均保持，未修改锁。START/STOP ACK、报告清除、CID释放和设备关闭均成功，客户端返回0。最后USB0、taint0，ADSP/SLPI/modem运行，watch idle、time prepared、无线SSH可达。[生命周期](lifecycle-validation.json)、[最终状态](final-validation.json)、[本轮worker](outdoor-worker.py)、[后续电源转换](../kernel260/README.md)

此次验收的是原生QMI LOC卫星定位链；ModemManager/GeoClue到桌面应用的自动定位、冷启动、休眠恢复、长稳和实测精度仍未验收。水平圆形不确定度报告5.80—30.04米，不能当作实地绝对误差；报告的39%置信度也不直接附会到圆形半径。

8份私有导出逐件与手机快照SHA一致，布局解码错误0。坐标、卫星编号、原始NMEA、启动身份与无线端点仅保存在工作区外`E:/edk2-samurai-out/kernel258`；公开只有聚合统计及分析源码。[解析核验](analysis-validation.json)、[源码锁](source-lock.json)
