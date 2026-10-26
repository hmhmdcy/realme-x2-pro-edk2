"""Save verified240 camera-app progress without claiming full peripheral completion."""
from pathlib import Path
import ast,hashlib,importlib.util,json
import host
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=host.PRIVATE
read=lambda n:json.loads((R/n).read_text())
h=read('final-health-validation.json');e=read('evidence-validation.json')
assert h['taint']==0 and h['snapshot_per_user_desktop_and_real_dbus_cpu_flags_verified']
assert not any(h['fault_delta_since_faulting_snapshot_stopped'].values()) and h['fault_counts']['gpu']==480
assert e['all_members_verified'] and e['native_members']==266
flow=read('snapshot-mmap-r2-frame-flow-validation.json')
assert flow['source_pts_strictly_increasing'] and flow['cpu_mmap_downloads']==600 and flow['paintable_bus_errors']==0
assert flow['pipewire_buffer_not_recycled_errors']==301
spec=importlib.util.spec_from_file_location('snapshot227',R.parent/'kernel227/prepare-fastrpc.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
assert helper.snapshot()==json.loads((P.parent/'kernel228/canonical-after-private.json').read_text())
backup=P/'checkpoint-before-close-private.md';assert not backup.exists();backup.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-16，240为progress，完整适配goal active。已定位Megapixels后端/配置缺口，Snapshot前摄CPU预览两轮跑通并持久保存启动环境；缓冲回收、拍照/切换/颜色及GNSSfix仍开放。[240证据](reference/kernel240/README.md)、[239完整依据](archive/NEXT-SESSION-through239-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与状态

仍236启动/boot235，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，233及更早无效。运输reference/kernel240/host.py，私人240/current-work-private.json。无活动构建/worker/传输或切换待决；原生266成员私有归档逐一核对。三授权只读代理已完成，手机串行操作；不得开启新未授权代理。

默认libcamera/IPA/tools/GStreamer/V4L2=99990.7.2-r15，config/stack=0.1.0-r10，49载荷不变。Snapshot51.0-r0签名发行包经主机HTTPS中继/手机原可信钥验签/原生离线apk安装，只增14至958，原944记录逐字不变，world仅新增snapshot版本钉住；移除模拟恰好14项。持久相机仓库仍239 r15索引；Snapshot安装候选k240-snapshot-host-packages/apks/packages.adb，事务k240-snapshot-app-transaction。

桌面“相机（Snapshot）”：用户.local/share/applications/org.gnome.Snapshot.desktop与dbus-1/services/org.gnome.Snapshot.service两覆盖，GSK_RENDERER=cairo / GDK_DISABLE=gl,vulkan,offload。desktop DBusActivatable=false直接exec；真实session bus从Phosh环境读，不猜/run/user/10000/bus（不存在）。新建服务目录后曾命中旧缓存，ReloadConfig后实际StartService已验CPU环境，自己的无窗口服务已TERM。原签名desktop/service及Phosh全局GPU/schema未改。事务k240-snapshot-launcher-transaction有两文件hash/owner/mode；回退先核hash再移除两覆盖。仅用户级部署，完整rootfs集成仍未完成。

最终789项默认模块/加载note/49相机载荷/958包匹配；两sensor/CCI/CAMSS suspended、四camera rails OFF/users0、MCLK1/2关，三DSP/SensorProxy三Has/Wi-Fi/chrony正常。BT poweredtrue/discoverfalse/既有1连接只观察；GNSS idle0/rate30/signalsfalse/watch idle/timeprepared/dataworker0；MM−1/reason2/power1、用户无SIM。没有新GNSS SET/搜星、刷写或重启。

## 源码、产物与回退依据

boot235 44c6a215…/100663296B、DTB469e1456…、Image183 bfa72dd9…、logdump183 e73754c7…保持。MFD6021a359…、lab5198e2bd…、provider2223f337…、IMX319176f68d7…、前摄e49dab26…、CAMSSff9fdfa3…、FastRPC2abde0ea…、BT185f6c5ed35…保持；775ko/789文件权威k237-camss-install/module-inventory-after-private.json。r15→r13/r8七包模拟回退及225实际七包、239事务/world/repos保留，未完整往返。旧236用户态hash含r13，不盲套；240 final-health核新49载荷和原其余hash。

r15源/对象libcamera214-root/work/libcamera239-r15-built；原2142254文件恢复、r14缓存保留。0022首参同步修复/初始矩阵/实际处理身份已验；旧零帧严格失败仍保留。canonical精确after228，240没有编译/部署新内核，旧相机输出不能整刷。

S5K3M5源码reference/kernel240/s5k3m5.c SHA9e97813c…，表头6a746dc4…、power include040ae270…，917init+模式3的53写、WRITE8流控/30ms停流、PM引用/残留rail回收和selection高度修正已源审；未编译/部署。19.2MHz/CCI1master0 0x2d/reset23/MCLK3/CSIPHY3，模式2104x1560/LLP9648/FLL1663、pixel481930000为OEM元数据，link723.2MHz未实测；gain1..16整数，细步长开放。准备脚本有一次性备份和include追加操作，重跑前审幂等性，不能盲跑。

P现lab mask9 L1/L4且有IMX319消费者，不热卸有children的MFD或lab。S5K需VIO pm8150l_l1、VANA P L6 2.8V、VDIG P L2量化1.056V；新0x2b union固定子组9/0x22共享lease设计尚未实现。所有mutating/is_enabled同锁，跨组busy无写/无fault；注册readyfalse且EN0返回0；VSET先于enable也须lease护栏；仅账本0+七EN0+global原值一致可释放，复位失败保留fault/lease；不猜VIN、不接AF L3。IMX319首P EBUSY需干净回滚后可重试。后续先做真实C回调故障注入/编译，需新boot部署而非热卸。

## 续作与已知风险

Megapixels2.1/libmegapixels0.2.3缺samurai配置→UVC fallback只认uvcvideo，不走r15。无pipeline方向回调可exit1、空切换缺保护；session出现no pipeline，但没对应栈/操作，不能断定每次闪退触发。受控窗口活12s，-2为主动收尾；SSH claim被拒不覆盖活动桌面路径。

用户打开的Snapshot默认Vulkan出现VK_ERROR_DEVICE_LOST；5s观察新增10GPUfault，精确停止后无新增。内核历史共480GPUfault/taint0，绝不能写240全程fault0；也不能混同旧CCU和211 GPU ISP WARN。Cairo且禁dmabuf首轮挂起0帧；用户解锁后r2收18缓冲但8paintable Bus Error，不能只禁DMA。

GTK4.24.1支持线性DMA CPU mmap，保留默认PW bufferpool和dmabuf、禁gl/vulkan/offload后16秒765递增PTS/324mmap、用户要求30秒重试1436递增PTS/600mmap，实际1920x1080 XR24:0、Cairo已记、无/dri FD/新增fault0/完整恢复，0paintable Bus Error。不把sink调用当实际显示帧数，空V4L2 trace不作无帧证据。仍分别163/301次was not recycled，这是PW交付/Gst账本不一致而非普通慢帧；pending队列警告为有界合并。PW1.6.8相机set_format未设FrameDurationLimits，caps30不保证源降帧；Snapshot无FPS开关。先保留此CPU工作回退，后续修buffer所有权/帧率与拍照、切换、长稳，不部署use-bufferpool=false（上游另有锁顺序死锁修复30ff8da）。用户30秒重试已做，实际画面文字反馈仍待；不再索取纯色或截图。

用户手机竖放，IMX319配对24request均非零；稳定2ms RAWmean64.290/std0.756/max85，32ms69.864/std10.211/max387/92.35%≤80，RGBmean41.97/max153。曝光响应不等于正常光学/颜色；无场景图片保存/展示/传输、无加光。其它后摄/颜色仍开放。

GNSS实际ODM gps.conf与社区固定源相同；HAL实际库固定vendor路径无ODM fallback，device.mk安装ODM但ZIP未见bind/overlay采用链。HAL binder配置setter可达不代表运行采用，需匹配Android运行映射/日志；不以RF_LOSS报告逻辑猜LNA，不重跑已覆盖同CID/GSV/辅助矩阵。室内窗边无SIM，不据此代替正CNR/fix证明。蜂窝有卡业务、传感器/蓝牙长稳与全机kernel/rootfs继续待办。
'''
assert len(checkpoint.encode())<=6500,len(checkpoint.encode());(ROOT/'NEXT-SESSION.md').write_text(checkpoint)

status=ROOT/'linux-port/docs/HARDWARE-STATUS.md';old=status.read_text();(P/'hardware-status-before240-private.md').write_text(old)
a=old.index('用途：');b=old.index('\n\n',a)
new=old[:a]+'用途：当前硬件验收清单。最后核对2026-10-16，240。libcamera r15/config-r10保持；新增Snapshot CPU前摄预览和用户启动配置，拍照/切换/缓冲回收仍开放。默认Vulkan发生480条GPU fault，停止后及CPU两轮无新增、taint0，不能写本轮全程fault0。GNSS无fix，完整goal active。[240](../../reference/kernel240/README.md)、[239近机型](../../reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+old[b:]
new=new.replace('**已复现的A640 CCU GPU故障已修复并部署，可以结束本轮GPU故障定位。**','**149已复现的A640 CCU故障修复保持；240新增Snapshot默认Vulkan负载的GPU fault，需独立继续定位。**')
lines=new.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):
  lines[i]='| 摄像头 | 236启动/235boot/e49/IMX319176f/CAMSSff9、r15/r10保持；49载荷和789模块匹配，Snapshot14新增至958包且原944记录不变。前摄两轮CPU预览324/600次1080p线性DMA mmap，0paintable Bus Error/无GPU FD/新增fault0，全恢复；桌面及真实D-Bus启动已验 | Megapixels缺机型配置/后端；Snapshot原默认Vulkan出现GPUfault480，已改仅该app CPU回退。仍有163/301次缓冲账本错误及积压，拍照/切换/颜色/长稳未验。后摄近黑仍开放；S5K917init/模式3候选仅源审、未编译部署，共享电源lease未实现；GW1/人像/完整kernel-rootfs待完成 |'
 elif line.startswith('| GPU |'):
  lines[i]='| GPU | 149已复现GLES/Vulkan CCU修复及原像素回归保持；240停止故障Snapshot后及CPU mmap两轮新增fault0/taint0 | 240 Snapshot默认Vulkan新增GPUfault480/VK_ERROR_DEVICE_LOST，CPU回退未修GPU根因。211 GPU ISP退出IOMMU WARN另案保留；Mesa可复现包/rootfs、完整扩展和长稳待完成 |'
status.write_text('\n'.join(lines)+'\n')

camera=ROOT/'linux-port/camera/README.md';(P/'camera-readme-before240-private.md').write_bytes(camera.read_bytes())
camera.write_text('''# Realme X2 Pro 相机接入

当前236启动/boot235、前摄e49/IMX319176f/CAMSSff9和libcamera r15/config-r10保持。240补桌面接入：Megapixels缺本机配置且不走libcamera；Snapshot原默认Vulkan出现GPU故障，现使用仅该应用的Cairo＋线性DMA-BUF CPU映射回退。[问题、失败与修复证据](../../reference/kernel240/README.md)、[部署锁](deployment-lock.json)。

桌面“相机（Snapshot）”及实际D-Bus激活均继承GSK_RENDERER=cairo、GDK_DISABLE=gl,vulkan,offload。用户级desktop/service覆盖，原签名包文件不变，不改Phosh全局环境；新服务目录创建后已ReloadConfig并实测。原生签名安装只新增14包至958，r15/r10的49载荷和原944包记录不变。完整rootfs仍须纳入这些应用/启动配置；用户覆盖不是新rootfs镜像。

前摄16秒及用户要求的30秒重试分别取得765/1436个递增PTS、324/600次1920×1080 XR24:0 CPU mmap，0paintable Bus Error、无应用GPU设备FD/新增内核fault；关闭后图/格式/控制/rail/PM/MCLK恢复。历史480条默认Vulkan故障保留。163/301次缓冲未回收错误、帧积压仍待修，不能称完整拍照或光学验收。仍未触发快门、保存或转移场景像素；前摄纯色按用户延期。

IMX319竖放同request RAW/RGB24组均非零，32ms仍92.35% RAW≤80；非零/曝光响应不代表正常光学。S5K3M5的917初始化＋模式3表和PM候选已源审，尚未编译部署；本机P L2/L6共享lease未实现。其它后摄、颜色/方向、GPU ISP、性能/长稳和完整kernel/rootfs开放。[近机型参考](../../reference/kernel239/RELATED-LINUX-SOLUTIONS.md)。

r15首参数修复与两次start验收、r15→r13/r8七包模拟回退及实际旧包保留见[239](../../reference/kernel239/README.md)。canonical仍after228，旧相机输出不能整刷，带消费者的lab/MFD不可热卸。
''')

lock=ROOT/'linux-port/camera/deployment-lock.json';(P/'deployment-lock-before240-private.json').write_bytes(lock.read_bytes());d=json.loads(lock.read_text())
d.update(stage=240,kernel_changed_in240=False,package_count=958,snapshot_version='51.0-r0',snapshot_official_added_packages=14,original944_package_records_unchanged=True,
 snapshot_cpu_renderer='cairo',snapshot_gdk_disable='gl,vulkan,offload',snapshot_user_desktop_and_dbus_overrides=True,
 snapshot_real_dbus_activation_verified=True,snapshot_front_cpu_mmap_preview_verified=True,snapshot_30second_mmap_downloads=600,
 snapshot_paintable_bus_errors=0,snapshot_30second_buffer_recycle_errors=301,snapshot_photography_and_switching_not_verified=True,
 historical_snapshot_vulkan_gpu_faults=480,gpu_faults_after_stopping_default_snapshot=0,full_kernel_rootfs_integration_open=True,
 final_health_evidence='../../reference/kernel240/final-health-validation.json',snapshot_preview_evidence='../../reference/kernel240/snapshot-mmap-r2-frame-flow-validation.json',
 snapshot_launcher_evidence='../../reference/kernel240/snapshot-dbus-activation-validation.json')
lock.write_text(json.dumps(d,indent=2)+'\n')

state_path=P/'current-work-private.json';s=json.loads(state_path.read_text());s.update(state='240 progress closed: Snapshot CPU mmap frontend verified and per-user desktop/D-Bus persisted; buffer ownership/photography/other peripherals open',
 active_native_context=None,active_native_session=None,active_build_session=None,active_evidence_session=None,active_fetch_session=None,transition_pending=False,
 previous_goal_turn_classification='progress',snapshot_front_cpu_preview=True,snapshot_user_launchers_installed=True,snapshot_actual_dbus_verified=True,
 snapshot_recycle_errors_open=True,s5k3m5_source_only_unbuilt=True,full_peripheral_goal_active=True,
 next='Handle actual preview feedback and buffer ownership/frame rate before photography; retain source-only S5K power/driver work and GNSS zero-CNR investigation. No new pure-colour request.')
state_path.write_text(json.dumps(s,indent=2)+'\n')
for p in R.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
suffixes={'.py','.cpp','.c','.h','.inc','.patch','.md','.yaml','.rules','.conf','.desktop','.service'}
files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*')) if p.is_file() and (p.suffix in suffixes or p.name=='APKBUILD')}
(R/'source-lock.json').write_text(json.dumps(files,indent=2)+'\n')
report=dict(stage=240,active_goal_classification='progress',full_peripheral_goal_active=True,checkpoint_utf8_bytes=len(checkpoint.encode()),
 source_files_locked=len(files),python_syntax_files=len(list(R.glob('*.py'))),canonical_matches_after228=True,all_root_workers_terminal=True,
 native_members=266,snapshot_cpu_frontend_and_real_dbus_verified=True,historical_gpu_faults_preserved=480,buffer_recycle_errors_still_open=True,
 s5k3m5_candidate_only_not_built_or_deployed=True,no_new_kernel_or_flash=True)
(R/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
