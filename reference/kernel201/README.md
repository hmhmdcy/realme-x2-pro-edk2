# 阶段201：GPS辅助数据有效期、自动UTC补时与GeoClue接入

已安装按GPS启用触发的辅助服务：同步UTC、查询绝对有效期、有效时跳过下载/重注入、过期时通过标准MM接口刷新并核对结果。同一200启动完成真实UID10000的GNSS-only GeoClue启用/停止与服务自动触发。**仍没有真实fix或正C/N₀，GPS整项尚未完成。**

## 旧辅助数据并非当前有效

新启动保存的XTRA窗口为2026-10-02 08:00至10-09 08:00 UTC，已经过期；不能只看duration168小时就称为当前有效。QCOM公开IDL定义起点为Unix UTC秒、持续时间为小时，而UTC注入字段用毫秒。[字段定义](https://android.googlesource.com/platform/hardware/qcom/gps/+/android-4.2.2_r1/loc_api/loc_api_v02/location_service_v02.h)、[绝对有效期核对](orbit-current-validity-validation.json)

从三个基带公布的全球服务器通过TLS及no-cache请求取得一致的新文件51331字节，30370293…，Last-Modified为当日05:15 UTC。标准MM InjectAssistanceData成功，独立LOC查询确认窗口更新为10-15 05:00至10-22 05:00 UTC。未启动GPS引擎来进行这次注入；NTP正常，MM owner保持。[下载](assistance-refresh-download-validation.json)、[新窗口](validity-after-validation.json)

190/191的能力发现和协议顺序修复仍有效，本次没有改动MM191二进制b350c55b…。191“注入后duration0→168h”的旧结果仅证明当时装载了数据，不能扩大为10月15日仍新鲜；本轮补上绝对时间检查。

## 标准桌面链路与时间对照

GeoClue2.8.2已允许非enabled/SIM缺失modem的GPS能力；无需把失败状态伪装成正常。测试使用独立安装的DesktopId、UID10000及当前Phosh的真实会话环境。临时仅启用modem-gps，关闭IP/Wi-Fi/蜂窝/网络NMEA/静态位置等来源，避免把其它来源当作GPS结果。配置、测试身份、临时可执行文件均已撤销，原GeoClue配置逐字保持。

首次客户端AccessDenied时GPS未启用，桌面定位总开关实际为false；后续临时打开该正常设置后，客户端启动、Active、停止和删除均通过，结束恢复false。首次父脚本的清理PID检查也退出，随后独立完成清理。目录核对为0755，未把未证实的目录权限猜测当作原因。

| 会话 | 时间 | 本轮去重NMEA | 关键观察 |
| --- | --- | --- | --- |
| 新XTRA、未手工UTC | 183.14秒 | 4 | GGA时间字段始终为0 |
| 补UTC、DMS shutting-down | 92.21秒 | 91 | 88个不同GGA时间，开始正常推进 |
| 补UTC、DMS online | 92.27秒 | 97 | 出现7条不同GSV |
| 首版辅助服务自动触发 | 182.17秒 | 260 | 一次worker完成UTC与有效期检查 |
| 最终辅助服务自动触发 | 31.93秒 | 37 | 最终源cf3d92a4…，一次worker完成 |

五轮均校验和错误0，GGA有效质量/RMC active/GPS raw位置/正C/N₀/GeoClue位置事件均0。每轮去重计数不能相加称为跨会话全局唯一。[GeoClue证据](geoclue-native-validation.json)、[时间字段独立检查](nmea-clock-validation.json)

当前模式查询为standalone、engine lock为mt。本轮只针对实测的DMS shutting-down/PowerState1执行一次标准SetPowerState(3)作对照，未重启modem；online后有GSV仍无正C/N₀，不能据此宣称RF跟踪已经工作。当前保留PowerState3，MM仍State−1/原因2、bearer0。物理SIM情况未被这些状态证明。

## 已部署辅助服务

[Python源](samurai-gnss-assist.py)安装于/usr/sbin/samurai-gnss-assist，SHA256 cf3d92a4…；[OpenRC源](samurai-gnss-assist.initd)为54b81745…，已加入default并运行。未重启设备，本次验证范围是同boot的服务启动/空闲停机/重启和真实GPS启用触发，跨boot仍待测。[部署](assist-deployment-validation.json)、[原生验证](assist-native-validation.json)

- 只响应MM实际启用GPS_NMEA/GPS_RAW；GPS关闭时空闲。工作进程用文件锁串行，活动时每小时复查，失败十分钟后再试。
- 先要求chrony同步；通过自己的LOC client注册完成信号后发送UTC请求，等待ACK及独立indication，释放CID/关闭设备后再处理有效期。
- 以起点和持续时间判断当前有效性，保留协议uint16小时范围。现有数据有效便跳过下载和数据注入。
- 过期时只用基带公布的全球URL，升级HTTPS并拒绝降级/凭据/query/fragment重定向，限制大小、拒绝HTML，检查modem owner和GPS是否仍活跃，再调用标准MM注入及独立有效期读回。
- 已知不在有效窗口内的文件指纹/窗口只在私人缓存中保存；同文件仍无效时拒绝，未来窗口到达起点后可重新考虑。服务本身不设置modem电源、不发GPS Setup/Start，也不处理或上传位置。

10个时间窗口、6个URL、8个payload、3个重定向拒绝和10个实际刷新流程模型通过，包括到期边界、将来起点、停止客户端、ACK后仍旧过期、失败不得报告成功/重复注入。原生最终版UTC ACK/完成、有效期查询及全部临时QMI客户端释放/关闭通过；对真实旧191文件的缓存拒绝也通过。[离线检查](assist-core-validation.json)

自动触发时数据已有效，确实未下载或重注入。为了验证真实过期刷新，另做一次受控旧文件注入并备好已验证新文件；旧文件调用返回Core.Aborted，独立查询仍是当前窗口，未建立过期现场，未继续启动该桌面试验，也未重复注入或强制清除。该错误名不足以证明具体固件拒绝原因。**完整“自动下载→注入→有效期更新”分支尚未在自然过期现场实测**；标准MM手工更新和自动有效跳过是各自已证明的范围。[受控结果](controlled-expired-flow-validation.json)

首次最终检查读取到SignalsLocation1/GpsRefreshRate0，随后在GPS关闭、GeoClue退出下正常化为0/30。未记录本阶段第一次测试前这两个字段，不将产生环节的早期推断当成事实；原始记录及更正一并归档。桌面总开关false恢复已有独立前后证据。

## 最终现场、回退与后续

4705.66秒仍是200启动/kernel183，taint0、WARNING/Oops/GPU/SLPI fatal/BT重组均0；ADSP/SLPI/modem running、SensorProxy三Has true。GPS0/SignalsLocation0/刷新30、桌面定位false，原GeoClue配置保持，所有测试身份及可执行文件移除。辅助服务在受控测试前空闲重启后当前worker0；此前最终版的一次真实启用/完成已保留独立快照。CAMSS200四域/模块82cbc052…保持，201没有相机资源或启动分区操作。[最终健康](native-health-validation.json)

内核200全部源码、Image/config/canonical DTB/符号/模块顺序保持，25 tracked修改/11 untracked，未暂存。原MM191及NV源校验保持。[源码](source-final-validation.json)

辅助服务目前为本机安装，设备APK和新rootfs打包尚未完成。回退时在当前身份及GPS空闲核对后停止服务、移除default项与本次新增的辅助程序/init脚本即可；私人缓存/现场记录保留。旧启动/模块回退继续用200的配套记录，不应为回退服务重注入已过期XTRA。MM电源策略应按当前承载、SIM及用户WWAN偏好处理。

122份最终原生文件完整逐成员核对；首版105份也保留。NMEA、配置、会话端点、身份及所有归档指纹均只存E:/edk2-samurai-out/kernel201。[归档](evidence-export-validation.json)

下一步先验证重启后的辅助服务与冷时间恢复，再核对GNSS电源策略、RF/LNA/时钟/板级资源及真实天空接收条件。同平台[Hotdog记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/status.md)目前也仅GNSS partial，不能拿其QMI启停当作实定位方案。相机正常启动资源/用户态、真实蜂窝业务、BT后段重组、传感器完整精度及冷启/长稳继续属于完整goal。见[检查点](../../NEXT-SESSION.md)与[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
