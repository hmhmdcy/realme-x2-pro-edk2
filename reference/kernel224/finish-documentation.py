from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel224')
assert json.loads((here/'package-integration-validation.json').read_text())['canonical_r11_r6_recipes_and_framework_deployment_locks_promoted']
readme='''# 224：RAW自动统计、曝光元数据与停止清理已部署

2026-10-16，手机当前为boot219/Image183、IMX471 e49、CAMSS fae1、完整libcamera 99990.7.2-r11/config 0.1.0-r6。本轮没有刷写或重启；全外设goal继续active。[安装](r11-package-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。

前摄IMX471的约2MP、4MP RAW和CPU RGB已取流。r11安装后普通/隔离IPA共128帧通过；实验4608×3456 RAW和CPU RGB各36帧通过，曝光元数据换算误差均小于1µs。默认cam/GStreamer各6帧通过，实验模块参数与用户态开关已关闭，WP恢复。[128帧](r11-installed-native-validation.json)、[完整RAW](raw-exposure-metadata-system-r11-4608x3456-validation.json)、[完整RGB](exposure-metadata-system-r11-4608x3456-validation.json)、[GStreamer](standard-gstreamer-validation.json)。这些是取流与控制链证据，未验收真实色彩、几何、实时帧率或GUI日用。

原r8的RAW-only绕过软件ISP配置和统计，16帧基线的曝光/增益元数据均缺失；−1只是探针缺失标记。0015让CPU路径只读原RAW缓冲，执行DMA读同步、统计和原软件IPA配置/启动/请求/元数据流程，不分配RGB输出、不修改RAW数据；非CPU旧RAW路径保留。223按真实SOF取得的捕获控制快照继续使用。[基线](baseline-raw-gap-validation.json)、[0015](libcamera-raw-only-statistics.patch)。

有限帧取流之外，同一相机停止/重配测试找出两处错误。r9在重复取消请求时触发断言/SIGABRT；0016改用仍由live frame map持有的请求，先清除所有权、再各取消一次。r10修好RAW退出，但未处理的RGB输出未继承取消状态；0017在completeBuffer前传播捕获状态。r9、r10各128帧普通取流通过仍未获部署，失败日志与产物均保留。[r9失败](lifecycle-r9-cancellation-failure-validation.json)、[0016](libcamera-stop-live-requests.patch)、[r10失败](lifecycle-r10-cancellation-failure-validation.json)、[0017](libcamera-capture-cancel-status.patch)。

r11候选普通/隔离IPA及安装后系统各做一次相同生命周期测试，每次同一Camera对象RAW2M→RGB2M→RAW4M→RGB4M→RAW2M，20请求完成且有曝光/增益、20请求正确取消，无停止卡死或挂起请求。测试二进制与断言未因失败修改。[探针源码](raw-lifecycle-probe.cpp)、[候选普通](lifecycle-r11-candidate-threaded-validation.json)、[候选隔离](lifecycle-r11-candidate-isolated-validation.json)、[安装后](lifecycle-r11-system-threaded-validation.json)。首次包装器晚采样/proc失败单独保留，不当作驱动结论。

三版均用官方abuild完整构建13包；r11保留原14补丁、17补丁完整链、全部管线、子包和tuning。34个ARM64 ELF、5IPA匹配保留核心公钥及Qt/Python入口通过；原214构建树2254文件/链接/模式均已恢复，r9/r10/r11对象树独立保留。外部原IPA214/APK203签名私钥复用，未公开；二次逐字重建未验证。[r11构建](r11-package-build-validation.json)、[产物](r11-forward-package-artifact-validation.json)、[主机QA](r11-host-runtime-qa-validation.json)。

原生签名七包升级已完成，944包中的937无关记录及49相机payload/权限复核通过。仅重载空闲WP，桌面与PipeWire身份保持；完整模式实验结束后当前WP仍映射r11。[重载](wireplumber-reload-validation.json)。r11→r8/r3回退使用实际223七包及224事务前world/repo，保持fae1/e49模块；降级模拟通过，完整回退往返未执行。更早r7/82c是历史配套回退，不能混用。

室内关灯条件保持，没有闪光或外部照明，没有保存场景图像。223暗光4MP RAW/RGB各6帧有非零值和帧间变化，未复现固定全零黑帧；本轮验证元数据与生命周期，没有重新保存或检查场景像素。CPU ISP内部确实读取RAW统计，不能称为“整个CPU未访问像素”。普通客户端报告已更正歧义字段，原输出私人保留。[暗光历史证据](../kernel223/dark-frame-classification-validation.json)、[字段修正](client-reporting-correction-validation.json)。

最终相机/CCI/CAMSS休眠、两前摄电源关闭/用户0、图案0/参数N；三DSP running、BT关闭无连接、GPS引擎关闭/watch空闲、chrony Normal、taint与五类fault均0、NV源保持。Modem仍State−1/原因2/Power1；两槽absent/no-atr是221历史结果，并非本轮查询。[最终健康](final-health-validation.json)。

标准手动曝光/增益独立Auto/Manual、物理2/1帧延迟、真实CFA/几何/颜色/方向/标定、GUI/性能、后置四摄与GPU ISP故障仍开放。16MP为双开关实验，内部TPG普通Bayer不能证明真实Quad颜色。上游CAMSS RFC仍用软件ISP，RAW统计待办可作设计参照，不能据其宣称SM8150硬件ISP已支持。[上游核对](UPSTREAM-NOTES.md)。GNSS真实fix、蜂窝业务、BT phase5、传感器SSR及全部外设继续按[清单](../../linux-port/docs/HARDWARE-STATUS.md)推进。
'''
(here/'README.md').write_text(readme)

(repo/'linux-port/packages/libcamera/README.md').write_text('''# libcamera 99990.7.2-r11：Realme X2 Pro补丁集

当前完整配方为r11，与config/stack r6部署。保留auto,virtual全部管线、全部11个框架子包、tuning/desktop输入及原14补丁；224新增0015 RAW-only CPU统计、0016停止时按live请求清理、0017捕获取消状态传播。[源锁](source-lock.json)、[224记录](../../../reference/kernel224/README.md)。

0013逐配置刷新sensorInfo、0014在真实采集序号处快照曝光历史保持。0015只读RAW，不分配RGB输出，接通自动曝光/增益与结果元数据；标准手动API尚未加入。0016/17分别修复实机复现的重复取消断言与未处理RGB输出取消状态。相同探针与断言在r11通过，不把有限帧取流通过当作退出正确。

官方abuild构建13个框架/配置包，34个ARM64 ELF、5IPA与保留核心公钥以及Qt/Python入口通过，原214树2254文件/链接/权限恢复。安装后128帧普通/隔离IPA、实验16MP RAW/RGB各36帧、cam/GStreamer各6帧，以及同相机五轮重配通过。真实像素算法历史证据在219/223；完整色彩、几何、曝光光学校准、后置四摄、GPU ISP和完整rootfs仍开放。

LIBCAMERA_IPA_PRIVATE_KEY使用保留的外部私有输入；APK另用原项目受信任密钥，strip后重签IPA。私钥不进入包或仓库；二次逐字重建未验证。当前r11→r8回退使用实际223七个r8/config-r3包及224事务前world/repo，保持fae1/e49模块，原生降级模拟通过，未完整往返。更早配套r7/82c回退见223历史记录。
''')
(repo/'linux-port/packages/samurai-camera-config/README.md').write_text('''# Realme X2 Pro 相机配置包

当前samurai-camera-config与stack为0.1.0-r6，固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r11。配置payload与原版相同：CPU ISP/system heap、heap模块自动加载和权限，目录0755/文件0644。通用堆video/uaccess，FastRPC专用池root0600。[224记录](../../../reference/kernel224/README.md)。

完整16MP默认关闭，须模块参数与用户态Quad配置双开关；隔离IPA配置只用于验证，产品YAML保持。r11补RAW自动统计/元数据及停止清理，普通UID10000的cam/GStreamer默认入口均已回归。

回退使用223保留的实际七个r8/r3包及224事务前world/repo/配置，保持CAMSS fae1与IMX471 e49；降级模拟通过，未完整往返。更早r7/82c回退属于历史配套操作。本包不含内核、设备树或私钥。
''')
(repo/'linux-port/camera/libcamera/README.md').write_text('''# IMX471与CPU ISP补丁

当前完整产品为libcamera r11/config-r6、CAMSS fae1、IMX471 e49。0007/8/9的helper、1000nm属性与首帧LUT修复，219原生尺寸Quad CPU实验和dma_heap选择，220逐配置sensorInfo，223捕获控制快照均保留。224加入RAW自动统计/元数据与两处停止取消修复。[完整配方锁](../../packages/libcamera/source-lock.json)、[224证据](../../../reference/kernel224/README.md)。

本目录[source-lock](source-lock.json)将213三补丁源码快照明确标为历史，当前完整17补丁输入锁在产品配方。安装后128帧RAW/RGB普通与隔离IPA、72帧实验16MP元数据、同相机五轮切换及普通客户端通过。CPU RAW-only只读原缓冲，不分配RGB输出。

219真实4MP/实验16MP和223暗场噪声仍是像素路径证据。完整模式TPG普通Bayer不证明真实Quad颜色；标准手动API、CFA/几何/颜色/光学延迟/标定、后置四摄和GPU路径仍开放。
''')
(repo/'linux-port/camera/README.md').write_text('''# Realme X2 Pro 相机接入

前摄IMX471已支持约2MP、4MP的RAW与CPU RGB取流，实验4608×3456 RAW/RGB也能取流。当前boot219/Image183、IMX471 e49、CAMSS fae1、完整libcamera r11/config-r6。224补齐RAW独立取流自动统计与曝光/增益元数据，并修复停止时重复取消及RGB取消状态。[224记录](../../reference/kernel224/README.md)、[部署锁](deployment-lock.json)。

安装后普通/隔离IPA共128帧，实验16MP RAW/RGB各36帧、默认cam/GStreamer各6帧，以及同相机五轮格式重配通过。相机已恢复休眠，16MP双实验开关默认关闭。RAW和RGB的统计读取由CPU ISP完成，RAW-only无RGB DMA输出。

配置包管理CPU ISP、system heap、heap模块自动加载和权限。通用堆video/0660及活动会话权限保持，FastRPC专用池root/0600。相机分配修复保持原始尺寸和四缓冲，不放宽DSP专用池。

用户房间关灯：223 RAW有效像素62–133、标准差约2.66，有帧间噪声变化，RAW/RGB各6帧未见全零帧；本轮只检查元数据和请求流程。没有保存场景、闪光或外部照明。亮光画质、真实CFA/几何/FOV/方向/标定、标准手动曝光、光学延迟、GUI日用与RGB实时性能仍未验收。[暗光证据](../../reference/kernel223/dark-frame-classification-validation.json)。

后置主摄/长焦/超广角/人像四路尚未完成实拍验收；GPU ISP黑帧/IOMMU退出告警继续开放。完整模式内部TPG为普通Bayer，不证明Quad真实颜色。[内核补丁链](kernel/source-lock.json)与[17补丁完整配方](../packages/libcamera/README.md)已保存，宿主canonical内核仍216/旧CAMSS源码，不能把旧输出刷成当前设备树；完整kernel/rootfs整合仍待办。

当前r11→r8只回退224事务前七包/world/repo、重载WP，保持fae1/e49；更早r7/82c是配套历史回退。二次逐字构建与完整回退往返均未验证。历史模式/像素证据见[219](../../reference/kernel219/README.md)、[220](../../reference/kernel220/README.md)、[223](../../reference/kernel223/README.md)。
''')

path=repo/'linux-port/docs/HARDWARE-STATUS.md';s=path.read_text();a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段224。相机完整r11/config-r6已安装，RAW自动统计/元数据及停止取消修复通过；boot219/e49/fae1保持，全外设goal active。[224报告](../../reference/kernel224/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
a=s.index('| 摄像头 |');b=s.index('\n',a)
s=s[:a]+'| 摄像头 | boot219/e49/fae1保持，完整r11/r6已安装。RAW-only CPU统计/自动曝光增益与元数据接通，两处停止取消修复；安装后128帧普通/隔离RAW/RGB、16MP RAW/RGB各36帧、同相机五次重配40请求、cam/GStreamer通过。223暗4MP RAW/RGB非全零且变化，最终taint/fault0、49payload保持 | 标准手动曝光/增益/Auto-Manual；物理曝光/延迟/颜色/几何/CFA/方向/GUI/实时性能、后置四路、GPU ISP、未知PLDO输入、冷启/长稳及完整kernel/rootfs开放；16MP实验已关、TPG普通Bayer不验真实Quad颜色 |'+s[b:];path.write_text(s)

(repo/'sessions/224-camera-raw-statistics-and-stop-cancellation.md').write_text('''# 224：相机RAW统计与停止取消修复

2026-10-16。完整libcamera r11/config-r6安装通过，保留boot219/Image183/e49/fae1。0015补CPU RAW-only自动统计和曝光/增益元数据；0016/17修复相同实机生命周期探针依次找到的重复取消断言、未处理RGB取消状态。r9/r10失败及产物保留，未部署。

安装后128帧普通/隔离IPA、RAW/RGB实验16MP各36帧、cam/GStreamer各6帧、同相机五次重配40请求通过。最终相机电源关闭、DSP正常、taint/fault0、NV源保持；16MP实验开关已关。没有刷写/重启、外部照明或保存场景。后置四摄、手动API、真实画质与整机其它外设继续开放。

[完整记录](../reference/kernel224/README.md)、[补丁配方](../linux-port/packages/libcamera/README.md)、[当前检查点](../NEXT-SESSION.md)。
''')

handoff='''# Realme X2 Pro 当前检查点

2026-10-16，224：完整libcamera r11/config-r6已安装，RAW自动统计/元数据和停止取消修复通过；boot219/e49/fae1保持，全外设goal active。[224记录](reference/kernel224/README.md)、[边界](WORKING-BOUNDARIES.md)、[历史through223](archive/NEXT-SESSION-through223-2026-10-16.md)。

## 当前部署与已验证状态

- 运输reference/kernel224/host.py，严格USB邻居/原公钥；guard /var/lib/samurai/k224-baseline/boot-id-private.txt，与219-runtime/220/221/222/223-baseline同boot。218及219-baseline/before-reboot旧身份不可用。224事务verified、实机任务终态；BT只扫描、不新增振动。
- boot219 156f0370…/DTB a214fd6b…，Image183 bfa72dd9…/logdump183 e73754c7…；本轮未刷/重启。IMX471 e49dab26…/29536B，CAMSS fae1ed40…/777360B文件及loaded-note核对。772ko保持；CCI f9c9272a…/PM8008 d1ff82c0…及其它外设指纹见219。
- libcamera/IPA/tools/gstreamer/v4l2=99990.7.2-r11，config/stack=0.1.0-r6；944包/937无关记录保持、49payload核对。world只更新stack版本，CPU/system heap YAML不变。通用堆root/video0660+uaccess，FastRPC池root0600。WP为手动UID10000；重载须现取argv/env，桌面/PipeWire保持。
- 前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP；默认1928×1088/2304×1728。4608×3456须模块+用户态双实验开关，当前N。真实CROP/FOV/CFA开放；TPG普通Bayer不证明真实Quad颜色。
- 219三模式真实RAW/CPU RGB证据、2MP RAW约57.82fps保持，未验RGB30fps；220逐配置sensorInfo修复行时长。223 CAMSS仅SM8150/VFE170发布FRAME_SYNC，缓冲保存真实SOF号，重排清标签，缺标签buffer error，时间戳仍EOF；libcamera捕获时按采集号快照DelayedControls，统计用副本，IPA仍请求号。
- 224的0015 CPU RAW-only只读/DMA同步原缓冲，无RGB输出，接通软件IPA配置/启动/请求/统计/元数据；非CPU直通RAW旧路径保持。0016 live frame map按所有权各取消一次；0017给未处理用户输出传播捕获取消/错误。r9重复cancel断言、r10 RGB取消状态失败及产物保留，均未部署。
- r11候选128帧、安装后128帧（各64RAW/64RGB，2M/4M×普通/隔离IPA）通过，捕获历史/曝光增益换算<1µs/自动调节验证。候选两IPA和安装后各同Camera五次重配，20完成+20取消，无挂起/断言；测试二进制与断言相同。安装后16MP RAW/RGB各36帧，cam/GStreamer各6帧通过。实验N/WP恢复。
- 关灯暗光证据仍223：4MP RAW/RGB各6帧只RAM统计，RAW62–133/std约2.66/相邻约56.2%变化，两者无全零帧；未验真实颜色/曝光。224元数据测试未保存场景/闪光/外部照明。CPU ISP确实读RAW，客户端不检查像素，两个报告歧义字段已更正、原输出私人保留。
- 224最终：相机/CCI/CAMSS休眠，两前摄电源关/用户0、图案0/参数N；GPS0/Signalsfalse/rate30，watch空闲0workers，chrony Normal；三DSP running、BT关无连接、taint/五fault0、NV源保持。Modem State−1/原因2/Power1；UIM两槽absent/no-atr是221历史结果，不证明未插卡。

## 源码、产物与回退依据

- canonical kernel /home/cy122/pmos-samurai-kernel136/kernel仍216 IMX源cc756279…/对象1388a070…/旧DTB22c1…、CAMSS原82c对应源；25 tracked/11 untracked、16798符号保持。当前IMX源61931497…/e49/a214与223 CAMSS另存，不能刷旧canonical输出。
- 223 CAMSS四源/模块在私人kernel223/sof-candidate-source、qcom-camss-sof223.ko；公共camera/kernel/0005及source-lock.camss锁定。原180源/对象/模式通过JSON清单恢复，不用NTFS仿真模式。224未改内核源锁、模块、Image或DTB。
- 完整r11官方abuild13包/34ARM64 ELF/5IPA匹配保留核心公钥、Qt/Python通过，17补丁/tuning/完整子包保留。SDK /home/cy122/x2pro-linux/libcamera214-root原/work/libcamera2254文件/链接/模式恢复，无before224/r10/r11快照；r9/r10/r11分别保留224-built、224-r10-built、224-r11-built，r8缓存223-built。原IPA214/APK203私钥外置复用，不生成/公开；二次逐字重建未验。
- 当前配方/配置/源锁/部署锁已提升r11/r6，保留fae1。设备224事务k224-r11-package-transaction保存前world/repo/配置；实际r8/r3七包在k223-r8-package-candidates/forward及私人223/camera-forward-repo。签名/payload/降级模拟通过，未完整往返。
- 当前r11→r8仅降级七包、恢复224事务前world/repo并重载WP，保持fae1/e49。更早r7/82c配套回退见through223，不混用。IMX回退k219-timing-baseline/imx471-original.ko d82c941d…；boot回退私人211/boot-partition-k211-sensor-domain.img c3bf043f…，须现取身份并核对。
- 私人kernel224/current-work-private.json，原生归档见224/final-evidence-validation.json；223为281、22271、22137、220146、219512成员。USB严格邻居/64KiB只是截断绕过，根因开放。

## 续作与已知风险

下一步标准曝光/增益独立Auto/Manual、AeEnable优先级、Auto期间忽略手动值、切换冻结、Camera::start控制和真实生效模式元数据；不能只回显请求。RAW自动链已修，物理控制2/1帧延迟未标定。

真实CFA/几何/颜色/方向/曝光/标定/GUI/性能、后置GW1/3M5/IMX319/人像及未知PLDO输入继续，不猜供电。GPU ISP211 CMA/黑帧/unmap349 WARN/taint512开放，149 CCU修复保持。

GNSS仍无fix/正CNR、室内窗边；221GPS强制/GLO-BDS-QZSS-GAL启用及四黑名单0不证明RF，多频GET error57不证明无L5。209缩小UTC误差未改善约6秒报告，勿重复。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp仍0B；SIM/注册/数据/通话/SMS开放，外发需明确目标。

BT phase5、传感器FastRPC/SSR/首启、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护、指纹/NFC实卡及rootfs132整合按[清单](linux-port/docs/HARDWARE-STATUS.md)继续，全goal active。
'''
planned=len(handoff.encode());assert planned<=6500,planned
(repo/'NEXT-SESSION.md').write_text(handoff)
d=json.loads((private/'current-work-private.json').read_text())
d.update(state='224 r11/r6 installed regressions and final health passed; canonical recipes and source locks promoted; archive/source audit/mirror finishing',
 active_native_session=None,active_build_session=None,transition_pending=False,
 next='Complete phase224 evidence/source/mirror checks, then implement standard exposure/gain modes and continue GNSS/rear cameras/all peripherals',
 next_session_bytes=planned)
(private/'current-work-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(stage=224,documentation_updated=True,next_session_bytes=planned,full_goal_active=True)))
