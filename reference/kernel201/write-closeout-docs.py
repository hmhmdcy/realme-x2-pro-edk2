from pathlib import Path
import json
ref=Path(__file__).resolve().parent;root=ref.parent.parent
readme='''# 阶段201：GPS辅助数据有效期、自动UTC补时与GeoClue接入

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
'''
(ref/'README.md').write_text(readme)
checkpoint='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段201，完整外设goal active。GPS辅助窗口/UTC自动补时服务已部署，同boot真实UID10000 GeoClue启停与自动触发通过；仍无fix/正CNR。4705.66秒同200启动，taint0/所列fault全0。见[边界](WORKING-BOUNDARIES.md)、[201报告](reference/kernel201/README.md)。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 基础组合 | boot200/静态DT2e2f8e64…/CAMSS82cbc052…；仍Image183/logdump183、modules132覆盖hci_uart185/fastrpc189、Mesa149/UCM173/MM191 |
| GPS辅助服务 | /usr/sbin/samurai-gnss-assist cf3d92a4…，init54b81745…/OpenRC default已启用；GPS active才工作，当前空闲；没有改电源或Setup/Start |
| GPS数据 | 旧窗口10-02 08至10-09 08 UTC已过期；新51331字节30370293…标准注入后为10-15 05至10-22 05 UTC，独立查询核对。UTC后GGA时间不再为0 |
| 实际定位 | GNSS-only GeoClue UID10000五轮183/92/92/182/32秒，NMEA4/91/97/260/37，校验错0；GGA有效/RMC active/raw fix/正CNR/GeoClue位置事件全部0 |
| 电源与清理 | 一次标准Power1→3：DMS shutting-down→online；当前MM−1/原因2、bearer0，GPS0/Signals0/刷新30；桌面定位原false已恢复，测试policy/DesktopId/程序已移除 |
| 整机 | ADSP/SLPI/modem running，SensorProxy三Has true；4705.66秒taint0，WARNING/Oops/GPU/SLPI fatal/BT重组0。NV源保持，201未重启/刷写 |
| 相机200证据 | 新boot四轮12帧IMX471 RAW10、原频率/自身MMCX384→0，无外部helper；最后GPIO12/15/29 CTL1/1/1、P0/Q1与七Q LDO恢复。临时相机资源仍全部撤销 |

依据：[辅助](reference/kernel201/assist-native-validation.json)、[GeoClue](reference/kernel201/geoclue-native-validation.json)、[健康](reference/kernel201/native-health-validation.json)。[200逐字快照](archive/NEXT-SESSION-through200-2026-10-15.md)保留完整相机源码/回退/引脚索引，相对链接按根解释。

## 源码、产物与回退依据

- WSL /home/cy122/pmos-samurai-kernel136/kernel；200所有源保持，25 tracked改动/11 untracked未暂存。Image183 bfa72dd9…、canonicalDTB22c1f2ad…/config55f1f0a3…、符号16793行/顺序770保持。[收据](reference/kernel201/source-final-validation.json)
- 新产品源reference/kernel201/samurai-gnss-assist.py/initd，安装cf3d92a4…/54b81745…，watch-state记录启动源hash；依赖Python/dbus/GI Qmi/Qrtr/chrony，APK/新rootfs未整合。[部署收据](reference/kernel201/assist-deployment-validation.json)
- 服务active触发串行worker、活动每小时复查/失败十分钟后再试；chrony同步后自身LOC补UTC/查绝对有效期，过期走TLS全球URL/MM注入/读回。当前有效便跳过，已知无效窗口私人缓存。37检查及UTC/QMI清理原生通过，详见201报告。
- 同boot一次自动启用/完成见k201-product-snapshot/watch-state.json；受控试验前重启后当前计数0且idle，新快照k201-product-snapshot-r3。区分历史验收与重置计数。
- 受控旧e905a729…注入一次返回Core.Aborted，有效期仍当前，未建立过期现场、未继续桌面试验/未强制清缓存。备好的新文件无需回注。完整自动过期刷新分支仍未原生证明，不能将模型或手工更新当成该分支通过。
- QMI窗口秒/小时、UTC注入毫秒；GeoClue支持无SIM GPS，refresh0是不节流，详见201。
- 首次AccessDenied/父清理失败与独立清理保留；最终Signals1/rate0正常化0/30，阶段初未记、归因未证。桌面设置前后false已核。
- MM191运行文件b350c55b…保持，APK更新会覆盖原MM补丁；当前Power3由201一次标准on对照留下，仍无真实SIM业务。不盲目reset/online，也不把SIM-missing/no-atr当物理无SIM证明。
- boot200在主机kernel200/boot-partition-k200-mmcx.img，5109097b…/100663296字节；DT2e2f8e64…，驱动82cbc052…四域/build-id已核，频率表保持。详情见200。
- 回退boot172 77e1a272…在主机kernel200/boot-rollback-k172-private.img；旧CAMSS e9b73f4c…手机k200-baseline/k200-deploy及归档。须fresh身份后旧boot/旧模块配套，保留logdump183 e73754c7…/NV/persist；201只加辅助程序/服务，无启动分区变更。
- 相机仍开发overlay/正常启动空sensor图。200 sensor-only overlay5109da88…/MCLK sleep pull-down，固定FW samurai/k196-front.dtbo；VIO helper允许RPMH初始unknown。原模块/源码hash与GPIO/PMIC完整细节见200快照，全部临时资源已撤销。
- GPIO12/15/29新boot CTL全1，地址0x0390c000/0x0390f000/0x0351d000（旧boot15为0）；200首6帧后单次恢复，后6帧改sleep后完整恢复。临时VIO301已撤销，下次phandle重读。P0/Q1、Q4/5、8无响应仅warm；PLDO四输入未知，仅S8C已证，勿套hotdog布线。
- 当前boot身份k200-runtime/boot-id-private.txt及k201-baseline；host201沿host200新USB peer/原公钥，Wi-Fi端点私人kernel190文件/实现kernel200/host-before-newboot.py。新boot重新发现身份、端点与Phosh bus，不用旧guard。
- 122份最终原生文件及首版105份均核对；NMEA/配置/会话端点/身份/归档指纹只在E:/edk2-samurai-out/kernel201。200四张RAW及更早归档仍私人保存。[收据](reference/kernel201/evidence-export-validation.json)

## 续作与已知风险

1. 先验证普通重启后OpenRC辅助服务与冷时间GPS恢复；不先手工UTC以免掩盖自动路径。新boot重取UID10000实际Phosh环境并只测GNSS来源；helper不能当GPS fix完成，自动过期全链路/活跃中停止/SSR还待验。
2. 继续GNSS电源策略（含用户WWAN/rfkill偏好、低功耗模式）、RF/LNA/时钟/本机OEM资源与真实接收条件；online已有GSV但无CNR不等于RF正常。真实fix/精度/冷启长稳仍开放。不要为强造过期状态删除未知校准数据。
3. 补辅助服务与MM正式APK/新rootfs；推进相机持久化板级/用户态、PLDO输入/双PMICcold、其它镜头模式/曝光色彩方向/持续帧率。相机已有12帧不是完整日用完成。
4. 蜂窝真实注册/数据/通话/SMS、BT phase5历史重组、Wi-Fi/USB PM、FastRPC普通信号/freezer/共享池−22/SSR、传感器物理精度/长稳继续。BT只扫描，振动不新增脉冲。旧193/199告警属于旧boot，本boot0；其余见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(checkpoint.encode())<=6500,len(checkpoint.encode())
(root/'NEXT-SESSION.md').write_text(checkpoint)
(root/'sessions/201-gnss-utc-validity-and-geoclue-assistance.md').write_text('''# 201：GPS绝对有效期、自动UTC补时与标准GeoClue接入

旧XTRA窗口已经过期，标准新文件注入后窗口覆盖当前时间。部署按GPS启用触发的UTC/辅助检查服务，真实UID10000 GNSS-only GeoClue启停及自动worker通过；仍无fix/正CNR。受控旧文件注入Core.Aborted且窗口未变，没有将未建立的过期场景记成自动刷新通过。最终taint0、内核fault0，桌面设置/测试授权已恢复。

详见[201报告](../reference/kernel201/README.md)、[当前检查点](../NEXT-SESSION.md)、[完整硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
''')
status=root/'linux-port/docs/HARDWARE-STATUS.md';s=status.read_text();a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对：2026-10-15，阶段201。已部署GPS按需UTC/辅助有效期服务，同boot UID10000 GNSS-only GeoClue启停/自动触发通过，仍无fix/正CNR；4705.66秒同200 boot，taint0、所列内核/蓝牙fault0，MM Power3/GPS0。200静态MMCX/前摄12帧证据保持。完整goal active。[201报告](../../reference/kernel201/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
lines=s.splitlines()
for i,l in enumerate(lines):
 if l.startswith('| GNSS定位 |'):lines[i]='| GNSS定位 | 201绝对窗口识别旧XTRA已过期，新51331字节标准注入/独立查询当前有效；UTC后GGA时间推进，按GPS active触发的UTC/检查服务已装OpenRC，真实UID10000 GNSS-only GeoClue启停及自动worker通过 | 仍无有效fix/正CNR/GeoClue位置事件；冷时间/跨boot、真实自动过期下载更新分支、电源策略/RF/LNA/时钟/接收条件/精度长稳待验。旧文件受控注入Core.Aborted且窗口未变，没有强制清除或声称该自动分支通过；APK/rootfs整合待做 |'
 if l.startswith('| 蜂窝通话与数据 |'):lines[i]=l.replace('200新boot modem running、MM仍failed','201一次标准电源on后modem running、MM仍failed/原因2').replace('200重启PowerState回1；','200重启PowerState回1，201对照后当前3；')
status.write_text('\n'.join(lines)+'\n')
index=root/'DOCS-INDEX.md';s=index.read_text();needle='| Camera实体前摄、静态启动与内部TPG |';position=s.index(needle)
if '| GNSS标准链路与辅助服务 |' not in s:s=s[:position]+'| GNSS标准链路与辅助服务 | [201 UTC/有效期/GeoClue](reference/kernel201/README.md)、[191协议修复](reference/kernel191/README.md) |\n'+s[position:]
index.write_text(s)
print(json.dumps(dict(stage=201,next_session_bytes=len(checkpoint.encode()),readme_status_session_and_navigation_written=True)))
