from pathlib import Path
import json

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel225')
assert json.loads((here / 'package-integration-validation.json').read_text())['canonical_r13_r8_recipes_and_framework_deployment_locks_promoted']
assert json.loads((here / 'final-evidence-validation.json').read_text())['verified_members'] == 191

(here / 'README.md').write_text('''# 225：标准曝光与增益控制已部署

2026-10-16，手机为完整libcamera 99990.7.2-r13/config 0.1.0-r8；boot219/Image183、IMX471 e49、CAMSS fae1保持。本轮没有刷写或重启，全外设goal继续active。[安装](r13-package-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。

0018为CPU软件ISP路径加入曝光/增益独立Auto/Manual、AeEnable兼容优先级、自动期间忽略且不保留手动值、切换冻结/恢复、Camera::start初始控制，以及按捕获SOF延迟历史取得的实际模式/数值元数据。启动控制在stream-on前写入；模式来源cookie与控制值一起经过DelayedControls，元数据不回显当前请求。[0018](libcamera-manual-exposure-controls.patch)、[探针](manual-control-probe.cpp)。固定0.7.2已有Camera核心AeEnable预处理，本轮保持该源码。

首个完整构建发现生成的线程代理非void start遗漏输出参数，41314失败并恢复原树；0019只补生成器输出转发，随后10686完成r12/r7全部13包。独立算法测试又复现无效统计把较老捕获控制重新排回的问题，r12未部署；0020改为保持最新准备目标，同一测试源码在r13通过48项断言。[构建失败](first-build-generator-failure-validation.json)、[0019](libcamera-threaded-start-outputs.patch)、[r12行为失败](agc-preflight-validation.json)、[0020](libcamera-invalid-statistics-hold.patch)、[r13算法回归](r13-agc-control-regression-validation.json)。独立测试首两次编译缺私有include目录，原诊断私人保留，按实际构建包含目录补齐后才取得行为结果。

r13/r8完整官方abuild构建成功，保留原17补丁、全部管线/11框架子包/tuning，现共20补丁。13包、34个ARM64 ELF、5IPA签名及Qt/Python入口通过；原214树2254文件/链接/模式恢复，r12和r13对象树独立保留。[构建](r13-package-build-validation.json)、[产物](r13-forward-package-artifact-validation.json)、[主机QA](r13-host-runtime-qa-validation.json)、[源码顺序重放](candidate-final-source-validation.json)。IPA214/APK203原外部私钥复用，未公开；二次逐字重建未验证。

候选RAW/RGB 2M/4M×普通/隔离IPA八例共1024帧通过九阶段控制测试；覆盖启动前控制、独立模式、优先级、忽略、冻结、恢复、停止再启动默认自动。147帧的捕获来源与当前请求阶段不同，元数据仍与捕获历史一致；来源标签经SOF间隙和环形历史回绕后正确。[1024帧矩阵](r13-candidate-manual-matrix-validation.json)。这是控制关联验证，不是光学2/1帧延迟标定。

签名七包原生升级后，944包中937无关记录及49相机payload/模式/链接核对通过，空闲WP重载且桌面/PipeWire身份保持。实际系统默认环境再测RAW2M/RGB4M共256帧，九阶段控制与来源元数据通过；其中35帧模式来源不同于新请求，仍正确。[RAW128](r13-system-raw-1928x1088-threaded-manual-validation.json)、[RGB128](r13-system-rgb-2296x1728-threaded-manual-validation.json)、[重载](wireplumber-reload-validation.json)。安装记录中的pending字段是安装瞬间历史，由这些后续验收解决。

相同生命周期探针在候选普通、候选隔离和安装后各40请求通过，每次同一Camera对象五次RAW/RGB重配、20完成且有元数据/20取消，没有挂起或重复取消。[安装后生命周期](lifecycle-r13-system-threaded-validation.json)。安装后实验4608×3456 RAW/RGB各36帧、cam/GStreamer各6帧通过。完整模式控制器已终态，参数N/WP恢复；16MP不是九阶段手动矩阵的覆盖范围。[完整RAW](raw-exposure-metadata-system-r13-4608x3456-validation.json)、[完整RGB](exposure-metadata-system-r13-4608x3456-validation.json)、[普通客户端](standard-gstreamer-validation.json)、[关闭实验](full-finish-validation.json)。

当前r13→r11/config-r6回退使用设备k224-r11-package-candidates/forward的实际七包及225事务保存的world/repo/配置，保留fae1/e49模块。原生降级模拟通过，完整往返未执行；r11→r8/r3属于224历史回退，不能混用。canonical配方、配置和部署锁已提升r13/r8，内核源锁仍223。

房间关灯条件保持，没有闪光、外部照明或保存场景。223暗光RAM数值统计仍是最近像素证据：RAW有效值62–133/std约2.66，有帧间变化；RAW/RGB各6帧均非全零。225客户端只检查控制/元数据/流程，CPU ISP内部仍读取RAW统计，不能由此宣称新亮光画质已验收。[历史暗光](../kernel223/dark-frame-classification-validation.json)。

最终相机/CCI/CAMSS休眠、两前摄电源关/用户0、图案0/参数N；GPS关闭/watch空闲、chrony Normal、三DSP running、BT关且无连接、taint与五类fault0、NV源保持。Modem仍State−1/原因2/Power1，UIM absent/no-atr是221历史查询。[191成员私人归档核对](final-evidence-validation.json)。r12主机构建和算法失败日志另在私人225目录，不声称位于手机归档。

前摄本阶段控制链已收尾，后续优先后置四摄、GNSS与蜂窝主要阻塞，并验证宿主musl交叉构建加速。真实CFA/几何/颜色/方向/光学延迟/标定、GUI/实时性能及GPU ISP仍开放；实验TPG普通Bayer不能证明真实Quad颜色。[上游依据](UPSTREAM-NOTES.md)、[加速安排](ACCELERATION-PLAN.md)、[全外设清单](../../linux-port/docs/HARDWARE-STATUS.md)。
''')

(repo / 'linux-port/packages/libcamera/README.md').write_text('''# libcamera 99990.7.2-r13：Realme X2 Pro补丁集

当前完整配方为r13/config-r8，保留auto,virtual全部管线、11框架子包、tuning/desktop及原17补丁；225新增0018标准曝光/增益控制、0019线程start输出转发、0020无效统计保持最新目标。[20补丁源锁](source-lock.json)、[225记录](../../../reference/kernel225/README.md)。

CPU RAW/RGB支持独立Auto/Manual、AeEnable优先级、自动期间忽略手动值、切换冻结/恢复、启动前控制和捕获来源元数据。0015 RAW-only统计无RGB输出、0016/17停止取消修复保持。模式与数值按真实SOF延迟历史关联，物理光学延迟尚未标定。

13包/34ARM64 ELF/5IPA签名、Qt/Python及48算法断言通过。候选1024帧覆盖2M/4M RAW/RGB×普通/隔离IPA；安装后代表性256帧控制、三次40请求生命周期、16MP RAW/RGB各36帧及cam/GStreamer各6帧通过。原214树2254文件/链接/模式恢复。真实颜色/几何/性能、后置四摄、GPU ISP和完整rootfs开放。

外部原IPA214/APK203密钥复用，strip后重签IPA；私钥不进仓库，二次逐字重建未验。当前r13→r11/config-r6使用实际224七包及225事务前world/repo/配置，保持fae1/e49；原生降级模拟通过，未完整往返。
''')
(repo / 'linux-port/packages/samurai-camera-config/README.md').write_text('''# Realme X2 Pro 相机配置包

当前config/stack为0.1.0-r8，固定libcamera/IPA/tools/gstreamer/v4l2为99990.7.2-r13。配置payload保持CPU ISP/system heap、heap模块自动加载与权限，目录0755/文件0644。通用堆video/uaccess，FastRPC池root0600。[225记录](../../../reference/kernel225/README.md)。

16MP默认关闭，须模块参数和用户态Quad双实验开关；普通UID10000的cam/GStreamer默认入口已回归。r13补独立曝光/增益Auto/Manual、启动控制及捕获模式元数据。普通/隔离IPA候选均通过，产品YAML保持。

r13→r11/config-r6回退使用224实际七包及225事务前world/repo/配置，保持fae1/e49；降级模拟通过，未完整往返。本包不含内核、设备树或私钥。
''')
(repo / 'linux-port/camera/libcamera/README.md').write_text('''# IMX471与CPU ISP补丁

当前libcamera r13/config-r8、CAMSS fae1、IMX471 e49。原helper/1000nm属性/LUT、原生Quad CPU实验/dma_heap、逐配置sensorInfo、捕获快照及RAW统计/停止取消补丁保持；225补独立曝光/增益控制、线程start输出和无效统计目标保持。[完整20补丁锁](../../packages/libcamera/source-lock.json)、[225证据](../../../reference/kernel225/README.md)。

本目录[source-lock](source-lock.json)中的213三补丁源码明确标为历史，当前完整输入在产品配方。候选1024帧控制、安装后256帧控制、72帧16MP元数据、三次40请求生命周期及普通客户端通过。模式元数据取捕获来源，不回显当前请求；光学延迟未标定。

219真实取流和223暗场噪声是像素证据。完整模式TPG普通Bayer不证明真实Quad颜色；CFA/几何/颜色/标定、后置四摄、GPU路径和实时性能仍开放。
''')
(repo / 'linux-port/camera/README.md').write_text('''# Realme X2 Pro 相机接入

前摄IMX471支持约2MP/4MP RAW与CPU RGB取流，实验4608×3456 RAW/RGB也可取流。当前boot219/Image183、e49、fae1、完整libcamera r13/config-r8。225已部署独立曝光/增益Auto/Manual、AeEnable优先级、切换冻结/恢复、启动前控制及捕获来源元数据。[225记录](../../reference/kernel225/README.md)、[部署锁](deployment-lock.json)。

候选普通/隔离IPA八例1024帧、安装后RAW2M/RGB4M256帧控制通过。候选两IPA与安装后各40请求启停重配通过；安装后16MP RAW/RGB各36帧、cam/GStreamer各6帧通过。相机休眠，16MP双实验开关已关。RAW-only CPU统计无RGB DMA输出；通用堆video0660/uaccess，FastRPC池root0600。

房间关灯：223 RAM统计的RAW有效值62–133/std约2.66且有帧间变化，RAW/RGB各6帧非全零；225未保存场景或改变照明。真实CFA/几何/FOV/方向/颜色/光学延迟/标定、GUI和RGB实时性能尚未验收。[历史暗光](../../reference/kernel223/dark-frame-classification-validation.json)。

后置GW1/3M5/IMX319/人像四路尚未完成实拍验收，未知PLDO输入不猜；GPU ISP黑帧/IOMMU退出告警仍开放。内部TPG普通Bayer不能证明真实Quad颜色。[内核源锁](kernel/source-lock.json)、[20补丁配方](../packages/libcamera/README.md)。宿主canonical内核仍216/旧CAMSS源，不能刷其旧输出；完整kernel/rootfs整合待办。

当前r13→r11/config-r6回退用实际224七包及225事务前world/repo/配置，保持fae1/e49，降级模拟通过、未完整往返。历史r11→r8与r7/82c配套回退见224/223。前摄本阶段收尾，后续优先后摄、GNSS和蜂窝主要阻塞。
''')
path = repo / 'linux-port/docs/HARDWARE-STATUS.md'
s = path.read_text(); a = s.index('用途：'); b = s.index('\n\n', a)
s = s[:a] + '用途：当前硬件验收清单。最后核对2026-10-16，阶段225。完整r13/config-r8已安装，前摄标准曝光/增益控制通过；boot219/e49/fae1保持，全外设goal active。[225报告](../../reference/kernel225/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。' + s[b:]
a = s.index('| 摄像头 |'); b = s.index('\n', a)
s = s[:a] + '| 摄像头 | boot219/e49/fae1保持，完整r13/r8已装。CPU RAW/RGB独立Auto/Manual、AeEnable优先级、忽略/冻结/恢复/启动控制与捕获模式元数据通过；候选1024帧、安装后256帧、16MP RAW/RGB各36帧、三次40请求启停重配、cam/GStreamer通过。暗场非全零证据仍223，最终taint/fault0、49payload保持 | 物理曝光/延迟/颜色/几何/CFA/方向/GUI/实时性能、后置四路、GPU ISP、未知PLDO输入、冷启/长稳及完整kernel/rootfs开放；16MP实验已关、TPG普通Bayer不验真实Quad颜色 |' + s[b:]
path.write_text(s)
(repo / 'sessions/225-camera-standard-exposure-controls.md').write_text('''# 225：前摄标准曝光与增益控制

2026-10-16。完整r13/config-r8安装，boot219/Image183/e49/fae1保持。0018补独立Auto/Manual、AeEnable优先级、忽略/冻结/恢复/启动控制与捕获来源元数据；0019修完整构建发现的线程输出遗漏，0020修同算法回归复现的无效统计旧目标回退。r12未部署。

48算法断言、候选1024帧、安装后256帧、三次40请求生命周期、16MP RAW/RGB各36帧及普通客户端通过。原SDK2254文件/链接/模式恢复、20补丁和13包保留；最终电源休眠、taint/fault0、191成员私人归档核对。无刷写/重启、照明改变或场景保存。

前摄本轮收尾，后续优先后摄、GNSS/蜂窝关键阻塞及宿主musl交叉编译。真实画质、光学延迟和全外设goal仍开放。[完整记录](../reference/kernel225/README.md)、[加速安排](../reference/kernel225/ACCELERATION-PLAN.md)、[检查点](../NEXT-SESSION.md)。
''')

handoff = '''# Realme X2 Pro 当前检查点

2026-10-16，225收尾：完整libcamera r13/config-r8已安装，前摄独立曝光/增益控制通过；boot219/e49/fae1保持，全外设goal active。[225记录](reference/kernel225/README.md)、[边界](WORKING-BOUNDARIES.md)、[历史through224](archive/NEXT-SESSION-through224-2026-10-16.md)。

## 当前部署与已验证状态

- 运输reference/kernel225/host.py，严格USB邻居/原公钥；guard /var/lib/samurai/k225-baseline/boot-id-private.txt，与219-runtime/220至224-baseline同boot。218及219-baseline/before-reboot旧身份不可用。225事务verified，构建/原生测试均终态；BT只扫描，不新增振动。
- boot219 156f0370…/DTB a214fd6b…，Image183 bfa72dd9…/logdump183 e73754c7…；225未刷/重启。IMX471 e49dab26…/29536B、CAMSS fae1ed40…/777360B及loaded-note核对。772ko保持，CCI/PM8008等指纹见219。
- libcamera/IPA/tools/gstreamer/v4l2=99990.7.2-r13，config/stack=0.1.0-r8；944包/937无关记录/49payload保持。CPU/system heap YAML不变，通用堆root/video0660+uaccess，FastRPC池root0600。WP手动UID10000，重载须现取argv/env，桌面/PipeWire保持。
- IMX471 CCI1 master1/0x10、MCLK2 19.2MHz、4lane/CSIPHY2/独立TITAN_TOP；默认1928×1088/2304×1728。4608×3456须模块+用户态双实验开关，当前N。TPG普通Bayer不证明真实Quad颜色。
- 220逐配置sensorInfo、223 CAMSS真实SOF号与捕获控制快照、224 CPU RAW-only统计及live请求取消修复保持。225的0018补独立Auto/Manual、AeEnable优先级、自动期间忽略手动值、切换冻结/恢复、start前控制；来源cookie随DelayedControls历史，模式/值按捕获来源而非当前请求。0019线程start输出转发，0020无效统计保持最新准备目标。
- r13候选2M/4M RAW/RGB×普通/隔离IPA八例1024帧九阶段控制通过；安装后系统默认RAW2M/RGB4M256帧通过。147/35帧捕获模式不同于新请求但元数据正确，换算<1µs。候选两模式及安装后各同Camera五次重配40请求（20完成/20取消）通过。安装后16MP RAW/RGB各36帧、cam/GStreamer各6帧通过，实验N/WP恢复。48实际算法断言通过；光学2/1帧延迟未标定。
- 暗光证据仍223：4MP RAW/RGB各6帧只RAM统计，RAW62–133/std约2.66/相邻约56.2%变化，均非全零。225未改变照明或保存场景；CPU ISP内部读RAW统计，客户端不检查场景像素。亮光颜色/几何/实际曝光未验收。
- 225最终相机/CCI/CAMSS休眠，两前摄电源关/用户0、图案0/参数N；GPS0/Signalsfalse/rate30，watch空闲0workers、chrony Normal；三DSP running、BT关无连接、taint/五fault0、NV源保持。Modem State−1/原因2/Power1；UIM absent/no-atr是221历史结果，不证明未插卡。

## 源码、产物与回退依据

- canonical kernel /home/cy122/pmos-samurai-kernel136/kernel仍216 IMX cc756279…/对象1388a070…/旧DTB22c1…及原CAMSS82c源；25 tracked/11 untracked、16798符号保持。当前IMX源61931497…/e49/a214与223 CAMSS另存，不刷旧canonical输出。223 SOF四源/模块在私人kernel223，公共camera/kernel/0005及内核源锁锁定；180源/对象/模式按Linux JSON核对，225未改内核源锁。
- 当前canonical配方/配置/部署锁r13/r8，完整20补丁/13包/34ARM64 ELF/5IPA/Qt/Python保留。SDK /home/cy122/x2pro-linux/libcamera214-root原/work/libcamera2254文件/链接/模式恢复，无before225快照；当前缓存work/libcamera225-r13-built，r12为225-built、r11为224-r11-built。r12首构建失败及无效统计失败保留，未部署；同算法fixture未改。原IPA214/APK203私钥外置复用，二次逐字重建未验。
- 当前r13→r11/config-r6仅降级七包，使用设备/var/lib/samurai/k224-r11-package-candidates/forward及私人224/camera-forward-repo-r11；恢复225事务k225-r13-package-transaction前world/repo/配置，重载WP，保持fae1/e49。签名/payload/降级模拟通过，未完整往返。r11→r8及r7/82c是历史配套回退，不混用。IMX/boot回退依据见through224，操作前现取身份。
- 私人kernel225/current-work-private.json；225原生191成员归档逐成员核对，r12主机失败日志另存私人225。USB严格邻居/64KiB为截断绕过，根因开放。224归档416、223为281成员。

## 续作与已知风险

前摄本阶段控制链收尾，下一步优先后摄/GNSS/蜂窝主要阻塞，不无端重复通过的矩阵。SDK C++仍ARM模拟且无ccache；先验证匹配Alpine/musl的宿主cross-native2/Meson和增量缓存，再实测收益。用户已授权并启动三路只读研究：GNSS、后摄及BT/传感器/蜂窝；主流程筛选结论，手机操作始终串行。[安排](reference/kernel225/ACCELERATION-PLAN.md)。

真实CFA/几何/颜色/方向/光学曝光/延迟/标定/GUI/性能、后置GW1/3M5/IMX319/人像及未知PLDO输入开放，不猜供电。GPU ISP211 CMA/黑帧/unmap349 WARN/taint512开放，149 CCU修复保持。

GNSS无fix/正CNR、室内窗边；221GPS强制/GLO-BDS-QZSS-GAL启用/四黑名单0不证明RF，多频GET error57不证明无L5。209缩小UTC误差未改善约6秒报告，勿盲重复。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。207MCFG173文件/8807671B RAM复制、mdtime/PDC活动无pending通过，mcfg.tmp仍0B；SIM/注册/数据/通话/SMS开放，外发需明确目标。

BT phase5、传感器FastRPC/SSR/首启、Wi-Fi/USB PM、音频长稳/耳机（暂无）、充电保护、指纹/NFC实卡与rootfs132整合按[清单](linux-port/docs/HARDWARE-STATUS.md)继续，全goal active。
'''
size = len(handoff.encode())
assert size <= 6500, size
(repo / 'NEXT-SESSION.md').write_text(handoff)
d = json.loads((private / 'current-work-private.json').read_text())
d.update(state='225 r13/r8 installed controls, full-mode and standard clients passed; final health and191-member archive verified; canonical locks promoted; source audit/mirror finishing',
    transition_pending=False, active_native_session=None, active_build_session=None,
    known_acceptance_issue='Resolved: same invalid-statistics fixture and all manual cases passed; physical optical delay/image quality remain open',
    rollback_packages='/var/lib/samurai/k224-r11-package-candidates/forward',
    next='Finish225 source audit and copy-only public mirror, then prioritize rear-camera/GNSS/cellular blockers and native-host matching-musl compilation',
    installed_manual_control_frames=256, native_archive_members=191, next_session_bytes=size)
(private / 'current-work-private.json').write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps(dict(stage=225, documentation_updated=True, next_session_bytes=size, full_goal_active=True)))
