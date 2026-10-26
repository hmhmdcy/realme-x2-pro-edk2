# 244：Linux 首次启动 DIAG 握手与真实 GNSS 测量

2026-10-16。上一轮为进展：开窗/WLAN对照及UFS归因改变了后续动作。本轮继续“修复直至手机定位可用”的完整目标，**仍未取得正CNR或fix，goal保持active**。保持Linux，未刷镜像、改分区或发NV/RF配置命令；完成一次普通Linux重启。当前是244启动、同boot235/Image183，旧236 guard已失效；新guard和运输见文末。

## 新取得的接收机证据

提前在modem第一次启动前建立DIAG端点，完成feature及DIAG_ID v1协商后，采到90秒真实GNSS诊断日志：

| 日志 | 代码 | 完整报文数 | 每份有效测量卫星数 |
| --- | --- | --- | --- |
| GPS Measurement | 0x1477 | 90 | 0 |
| GLONASS Measurement | 0x1480 | 90 | 0 |
| Galileo Measurement | 0x1886 | 90 | 0 |
| BeiDou Measurement | 0x1756 | 0 | 没有报文，不能补零 |

270份均version0，包外/内长度相等且匹配实际大小，固定body分别28/29/30字节，严格非HDLC解帧错误0。NumValidReports=0，**没有任何C/No字段，不能说“270个零CNR样本”**。同期QMI89次SV事件全部缺列表；没有可计入本轮的有效SNR字段或TRACK/fix。原始包及位置/NMEA仅私有保存。[QMI及报文统计](packet-preview-validation.json)、[测量解码](measurement-decode-validation.json)

GPS周数前41份为65535，后49份变为2440。开始搜星时辅助watch的time_prepared=false，随后准备成功，观测到GPS时间更新；因此不是90秒全程都已有时间准备。后49份仍无测量。时钟浮点字段TimeUnc、FreqUnc等保留原值和范围；后者恒1500，尚无同固件单位/标定证明，不能直接称1500Hz、判断XO锁定或推导LNA状态。

格式依据[MobileInsight GPS原实现](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_gps_measurement_report.h)、[GLONASS](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_glonass_measurement_report.h)、[Galileo](https://github.com/mobile-insight/mobileinsight-core/blob/master/dm_collector_c/gnss_gal_measurement_report.h)。已下载完整源码并锁SHA256；不根据链接master名称假定未来内容一致。[源码锁](source-lock.json)

## DIAG 接入具体改变了什么

243从已经退出的被动探针借用旧control peer发送feature，随后观测到该peer删除；不能将“send成功”当作仍活着的握手。本轮客户端删除这个fallback，收到DEL_CLIENT时清除peer，只协商实际新收到的feature。[修订客户端](diag_transport.py)

236旧boot当前DMS实查为shutting-down/MM PowerState1。通过标准MM SetPowerState(ON)变为online/3后，持续观察仍无新feature，单独VERSION也无回应。这是在测试DIAG生命周期，没有重复宣称“普通online能修GPS”。该次没有启动GNSS或发送日志mask，三DSP/taint及fault保持。[电源对照](poll-power-diag-validation.json)、[online VERSION](query-online-version-validation.json)

官方Android DIAG源码的[传输选择](https://android.googlesource.com/kernel/msm/+/bf51f920fdef2acb189f5c2e282148279a1f12c9/drivers/char/diag/diagfwd_cntl.c)会按feature关闭RPMSG或socket另一后端；[feature/mask发送](https://android.googlesource.com/kernel/msm/+/bf51f920fdef2acb189f5c2e282148279a1f12c9/drivers/char/diag/diag_masks.c)也有自己的顺序。这说明完整初始化有状态，尚未证明旧peer退出的唯一原因。本轮用Exa按传输和RF/时钟日志两个方向检索26项结果（含重复），没有把普通博客字段猜测当修复依据。

参照[linux-msm/diag固定实现](https://github.com/linux-msm/diag/tree/23c12c167e93215853af4e59c021551767f6fec8)，启动客户端协商master mask ownership、DIAG_ID与传输位，实际选值为remote支持的交集；支持control33的v1 ID分配。只为GNSS四个日志设置mask，采集期按原实现临时启用诊断实时模式，结束发送zero mask和实时模式释放请求。不含NV、内存读写、RF校准或任意DIAG命令API。[生成器](prepare-boot-diag.py)、[启动客户端](diag_transport_boot.py)

第一次VERSION超时、第二次返回55字节；控制数据持续收到，分配2个DIAG ID，90秒测量报文真正到达。结束后mask reset及实时模式释放请求均已发出，3个AP服务/4个socket关闭。没有原mask读回，**不声称逐字节恢复了原mask或取得撤销ACK**。随后普通fresh-only重连仍没有新feature，说明当前只验证了首次启动采集，通用重连问题未修好。[重连负结果](probe-reconnect-validation.json)

## 受控普通 Linux 重启

先按当前设备验证guard、Image183、F2FS根与34个modem文件的部署哈希。初版按原始进程名搜索文件服务返回0，继续读取实际pid文件，确认程序是samurai-tqftpserv和samurai-rmtfs-cow且存活；**0次旧名字匹配不是服务停止**。[启动核对](inspect-boot-order-validation.json)、[pid核对](inspect-file-pids-validation.json)

安装唯一临时OpenRC项，依赖localmount、在samurai-radio前等待端点发布；它只接受新boot并核同机model/release，不在236运行。最长12分钟，源文件有hash，没有覆盖既有服务。[安装](nextboot-install-validation.json)

停止应用/定位watch与相关服务，确认摄像头无FD、供电空闲，保留相机MFD/providers；先卸下ath10k消费者，再停止modem/ADSP/SLPI，音频关闭静音、显示从实际DRM资源查询后置空、传感器供电关闭。NV源哈希保持、无新fault/taint。[停流](poll-quiesce-validation.json)

按当前183 EUD驱动的退场顺序，冻结F2FS、解绑console并只写已核CSR_EUD_EN，读回后调用普通RESTART，**不是RESTART2 bootloader，不发flash**。主机先记录单次请求；USB在EUD退场时断开，最后一条console收据未达。随后只观察该切换，刷新唯一USB NCM邻居并保持原严格SSH密钥，确认boot ID确已改变且同机model/release一致；未重复请求。[请求代码](submit-normal-reboot.py)、[新boot观察](observe-nextboot-validation.json)

## 当前接收配置与下一步

新boot实查：DMS shutting-down、engine lock=mt、operation mode=standalone，标准六种NMEA类型均已设置；不能把没有普通GGA/RMC输出直接解释为未设置NMEA掩码。[查询](inspect-receiver-afterboot-validation.json)

现已从modem内部证实“没有形成有效测量”，排查下一层应加入专门RF硬件与时钟日志，而非只看AP clk_summary或反复同一零CNR会话。查得原厂共享[log_codes.h](https://github.com/bcyj/android_tools_leeco_msm8996/blob/master/diag/include/log_codes.h)：0x1478 GNSS Clock、0x147e PRX RF HW、0x147f DRX RF HW、0x1516 Configuration State、0x1596 WWAN/WLAN IMD Jammer等。它们是诊断日志代码，**不是RF写命令，也不是当前固件支持/字段语义已验证**；下一轮须按收到的版本/长度验证，不能按名称猜bit或电压。

下一次采集应保持首次打开的DIAG端点以支持多轮会话，先确认UTC已准备，再观察RF/时钟与normal online/standalone配置变化。现有辅助数据采用证据仍可复用，必要时在新测量通道下复核；保持当前Linux，不以刷Android为前提。

## 收尾与有效上下文

44项原生归档成员逐一验证大小/SHA256，额外源码和网页收据保持私人。[归档](evidence-export-validation.json)

临时OpenRC项、runlevel链接、pid文件及本项stale started状态已移除；启动采集进程已退出，GNSS Stop/CID释放/close成功，AP DIAG服务0。当前三DSP running，Wi-Fi重新连接，watch running但active=false、time_prepared=true、data worker0；新boot WARN/Oops/GPU/DSP fatal均0、taint0。这不抹去240的历史GPU故障。[最终健康](final-health-validation.json)

当前guard：`/var/lib/samurai/k244-runtime/boot-id-private.txt`。运输：[host.py](host.py)，私有USB端点在`E:/edk2-samurai-out/kernel244`；原SSH密钥保留。236及更早guard不可用于新动作，旧244 preboot脚本也只适用于236；不覆盖旧guard假装匹配。boot235/Image183未换，其他功能验收沿用240，244没有重做全机验收。
