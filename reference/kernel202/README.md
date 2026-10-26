# 阶段202：GPS首会话UTC准备与真实自动辅助数据恢复

修复重启后首次GPS会话的NMEA时间停在0：在时钟同步、GPS未启用时自动准备一次UTC，再由正常桌面请求启动GPS。第二次普通重启后的首次182.36秒会话取得185条去重NMEA、176个推进的GGA时间，基带电源保持OFF。**仍无有效fix、正C/N₀或GeoClue位置事件，整机适配goal继续。**

## 冷时间问题与实际对照

201的自动补时验收发生在已经手工补过UTC的同一次启动，不能替代新启动后的首次会话。202先保留cf3d92a4…服务执行普通重启，不提前手工补时或注入数据；服务随OpenRC正常启动。

| 同一标准GeoClue应用路径 | 时长 | 去重NMEA | 不同非零GGA时间 | 实际结果 |
| --- | --- | --- | --- | --- |
| 首次重启，旧服务，首次会话 | 182.26秒 | 4 | 0 | UTC ACK/完成和自动数据刷新均成功，时间仍为0 |
| 同一启动，第二次会话 | 92.27秒 | 91 | 88 | 无手动补时、无电源变化；自动worker跳过已有效数据 |
| 修订服务，第二次重启后首次会话 | 182.36秒 | 185 | 176 | 空闲UTC准备后首次会话时间推进，6条GSV |

三轮均为真实Phosh会话环境中的UID10000独立测试应用，只启用modem-gps，关闭其它定位来源；校验错、有效GGA、RMC active、raw fix、正C/N₀和位置事件均为0。前两轮原始汇总保存在第一轮私有归档；末轮见[首次会话收据](geoclue-first-session-validation.json)。这个对照支持提前准备UTC解决已复现的首会话时间问题，没有证明接收链路、首次真实定位或所有启动时序均已修复。

## 部署的服务改动

[产品源](samurai-gnss-assist.py)为42168f33…，安装到`/usr/sbin/samurai-gnss-assist`；[init](samurai-gnss-assist.initd)保持54b81745…，OpenRC default已启用。

- 在一个ModemManager实例下，GPS空闲且chrony为Normal时只准备UTC，不下载数据、不调用GPS Setup/Start、不改变基带电源。成功后不再重复空闲QMI操作。
- GPS active时继续串行执行UTC、绝对有效期查询、必要时TLS下载/标准MM注入/独立读回。有效数据仍跳过下载与重注入，并记录刷新前窗口。
- 时钟未同步改为10秒后重试；其它普通错误保留600秒退避。新MM owner重新准备；旧owner的晚到结果不能把新实例标记为已准备。
- 定位请求抢在空闲准备完成前到达时记录竞态，不重启应用会话；该时序及同owner内部SSR仍需原生验收。

新启动确实遇到`clock-not-synchronized`：早期观察在第2次尝试后超时，服务自行第3次完成UTC，未重启服务或手工补时。[启动重试收据](clock-startup-retry-validation.json)、[第二次启动](reboot-r2/runtime-validation.json)。首次观察服务尚未启动的记录同样保留；当前服务启动是正常完成依赖后的自动行为。

原37项窗口、URL、载荷、重定向及实际刷新函数检查保持通过；新增6组生产watcher调度场景和6项退避检查，覆盖时钟恢复、owner更换/晚完成、定位竞态及停止时等待worker清理。[原核心检查](assist-core-validation.json)、[调度检查](watch-preparation-tests.json)。模拟清理与owner竞态不是硬件SSR/活跃停机验收。

## 完整自动刷新分支的实机证据

第二次启动首次GPS请求时，QMI读出的原窗口为Unix起点315964800、时长0小时；服务自动执行3次下载尝试、1次标准MM数据注入，再读回1792047600/168小时，即2026-10-15 07:00至10-22 07:00 UTC。UTC收到ACK与独立完成，所有QMI客户端释放/关闭，MM owner保持，未发送引擎启动或电源操作。最终又独立只读查询确认当前有效。[首次会话](geoclue-first-session-validation.json)、[最终健康](native-health-validation.json)。

这次证明“空窗口→下载→注入→有效期读回”的真实自动链路。201手工旧文件注入返回Core.Aborted、未建立非零过期窗口的历史结论仍保留；不能把本次时长0的窗口写成已实际复现非零过期窗口，也不为制造场景清除未知校准数据。成功收据记录下载次数，没有记录前两次失败的具体原因，未把它们归因于网络或服务器缓存。

## 重启、清理与整机状态

两轮均重新采集当前boot身份、分区及模块清单，先停止空闲GNSS服务、NetworkManager、MM、GUI、音频和DSP，再确认CRTC关闭、传感器供电关闭并冻结根文件系统。EUD退场后SSH断开，提交脚本分别出现确认断言/传输异常；均没有重复Linux重启请求，而是fresh fastboot身份及product核对后各发送一次普通reboot。首轮旧私有路径解析失败发生在任何fastboot reboot发送前，修正路径后重新核对身份。**202没有刷写分区。**

首轮桌面测试退出后，后续观察发现SignalsLocation/刷新率又为true/0，与测试结束瞬时恢复报告分开记录；原因未确定，保持GPS关闭后恢复false/30。末轮初次收尾检查也未立即通过空闲条件，随后保留日志并重新核对；最终不需要额外终止GeoClue进程。原配置逐字保持、桌面定位恢复false、临时policy/DesktopId/程序均已移除。

最终第二次启动504.96秒：taint0，WARNING/Oops/GPU/SLPI fatal/蓝牙重组均0；ADSP/SLPI/modem running，SensorProxy三项Has true。MM Power1、State−1/原因2、bearer0，GPS0/Signalsfalse/刷新30；没有202电源切换或modem reset。实际NM WWAN软/硬允许均true；源码映射LOW到DMS low-power、OFF可对应offline或shutting-down，202未测试LOW且未直接查询本轮DMS模式，不能仅凭Power1断言具体模式。[电源偏好观察](inspect-active-policy.py)、[健康收据](native-health-validation.json)。

boot200、logdump183、persist、NV源及784模块均再次校验一致；CAMSS四域两轮均自动加载/绑定，无临时相机资源。内核200源码、Image/config/canonical DTB/符号表/模块顺序保持，25 tracked改动和11 untracked未暂存；MM191未改变。[源码收据](source-final-validation.json)。本轮没有新增相机帧或蓝牙扫描，200的12帧与扫描证据保留原归属。

第一轮110文件、最终轮108文件及归档均逐成员校验，NMEA、会话、身份和归档指纹只在私有`E:/edk2-samurai-out/kernel202`及`reboot-r2`，未发布。[首轮归档](first-cycle-archive-validation.json)、[最终归档](final-cycle-archive-validation.json)。

## 后续完整目标

真实GNSS接收/精度和长稳、电源策略、首次请求抢先/SSR仍开放。OEM 19781 DTS仅找到通用CDP/MTP GNSS UART注释，没有据此推导本机LNA供电或修改GPIO。下一步应整合helper/MM补丁的APK与新rootfs，并继续相机板级资源持久化/PLDO输入与其它镜头、蜂窝真实SIM业务、BT phase5错误、Wi-Fi/USB PM及FastRPC/传感器物理精度。当前用户态服务仍是本地安装，旧rootfs132不含此改动。
