"""Replace stale current summaries after preserving their historical evidence."""
from pathlib import Path
import hashlib, json, os

root = Path('/mnt/e/RealmeX2Pro edk2')
history = json.loads((root/'reference/kernel151/document-history.json').read_text())
for entry in history:
    assert hashlib.sha256((root/entry['source']).read_bytes()).hexdigest() == entry['original_sha256'], 'Current document changed; reconcile before writing'
live = json.loads((root/'reference/kernel151/closeout.json').read_text())
assert live['new_gpu_faults_since_stage149'] == 0 and live['taint'] == 0
assert live['checks']['installed_library_matches_deployed_fix']
assert live['checks']['same_boot_as_verified_deployment']
assert live['current_kernel_build'].startswith('#147 ')
assert live['active_test_processes'] == live['remaining_gpu_test_trace_instances'] == live['pending_devcoredumps'] == 0

hardware = '''# RMX1931 Linux 硬件状态与未完成项目

用途：当前硬件验收清单。最后核对：2026-10-13，阶段151。现机为内核147、software132加Mesa149本地库。以[本轮收尾收据](../../reference/kernel151/closeout.json)、[GPU验收](../../reference/kernel149/README.md)和下列各功能证据为准；操作规则见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

**已复现的A640 CCU GPU故障已修复并部署，可以结束本轮GPU故障定位。** 147修复旧式GLES地址对齐，149修复Vulkan自动VM_BIND地址对齐。149完成185次像素读回零差异、36次Settings面板打开及PM、稀疏重绑定、旧地址重放、Vulkan/GLES并发验收。151同启动六次被动观察中无新增fault，taint0，桌面保持。150无Mesa补丁的降级候选未部署；它的验证不能混入149系统驱动的验收。

这个结论限定当前已复现故障和已测负载。所有Vulkan扩展、长时间压力及跨启动GPU回归仍需验收；显示首次接管与DSI问题也是独立待办。普通Mesa包更新可能覆盖本地修复，旧rootfs132镜像不含该库更新。

## 当前功能与待办

“未完成”包括仍有真实缺陷、功能尚未接入，以及仅做过部分验收；不能将这三类都写成完全不能用。

| 功能组 | 已证明的能力 | 尚未修复或验收 |
| --- | --- | --- |
| GPU | 当前可复现GLES/Vulkan CCU故障已修复并部署，硬件渲染回归通过 | 将Mesa补丁纳入可复现软件包和新rootfs；完整扩展、长期及跨启动回归 |
| 原生显示 | 原生60Hz输出、触摸桌面可用；当前窗口DPU/DSI计数0 | 首次接管超时、DSI欠载与历史滚动花屏缺少永久修复验收；开关屏、休眠、持续绘制长稳 |
| 音频 | 原生声卡、双MAX98937和WCD934x；有限PCM播放成功，DMIC0/1/2有非零样本 | SLIMbus首次DMA准备失败和停止生命周期；实际扬声器声音、拾音质量、耳机、声学保护与休眠未完整验收 |
| 电池与充电 | BQ28Z610电量/温度和MP2650输入观测已接入；本轮健康Good、接线ONLINE1/Full | 正常充电控制、USB输入预算、温度/保护/失联链及持续充电闭环；134输入预算候选不在当前147中 |
| 摄像头 | 内部TPG真实DMA/IRQ/raw10三帧通过，原厂传感器来源已核对 | 实体传感器到C-PHY/CAMSS的出图、PM8008供电、libcamera或等效用户态及多模式图像验证 |
| 其它传感器 | 历史接近/磁力计独立样本及SLPI服务证据保留；本轮SLPI offline | 加速度、陀螺仪、完整磁力计/lux、自动旋转与接近日常功能；不能合并不同启动的局部成功 |
| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础已接入，本轮modem running | SIM注册、真实移动数据、通话/SMS及SSR、冷启动、休眠；历史sim-missing不算业务验收 |
| GNSS定位 | LOC start/stop、位置/NMEA/SV事件链通过 | 真实有效定位fix、持续定位与桌面定位服务；此前55次位置报告仍为in-progress |
| 指纹 | 尚无功能验收 | 本机传感器/SPI/供电、安全环境及用户态认证链 |
| NFC | NCI控制器初始化、上电查询、关闭和重复通过 | RF读卡/标签、时钟请求及eSE业务，尚无真实读卡验收 |
| 振动 | AW8697驱动与电气检查通过 | 物理振动和桌面反馈未确认；按用户边界不新增脉冲 |
| 蓝牙 | 原生BlueZ自动服务及LE/BR/EDR/混合扫描通过，本轮服务started | 历史UART重组错误未闭环；配对/数据/音频、冷启动/休眠长稳未验收，当前只扫描不连接 |
| Wi-Fi | 2.4/5GHz已有实际通信回归，本轮关联5180MHz | 物理冷启动、休眠恢复与长稳；历史连接故障不能仅凭当前关联判定全部解决 |
| 普通USB与OTG | NCM网络、SSH/SCP及与EUD共存可用 | OTG、USB3、冷启动/休眠及长期稳定；EUD部分宿主接收/退出路径仍有独立验收待办 |
| 触摸 | 用户确认可解锁、操作应用，原生驱动工作 | 边缘/方向/多触点与休眠后恢复、长稳 |

已有基础还包括UFS访问、CPU调频表、PMIC温度与按键/EUD。CPU高频压力、UFS持续负载、整机功耗、冷启动及系统休眠唤醒仍需跨功能验收；不能以驱动注册或短窗口健康代替日用完成。

## 下一阶段顺序

先修显示接管和生命周期，再推进充电控制保护及音频首次DMA问题。随后处理完整传感器、实体摄像头、蜂窝业务与GNSS真实fix；指纹、NFC读卡和外围设备功能继续保留。Wi-Fi、蓝牙、USB和触摸以已经可用的能力为基础补稳定性，不重复从零接入。

参考证据：[显示140至145](../../sessions/145-dsi-deployment-and-session-closeout.md)、[SLIMbus139](../../sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[DMIC104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md)、[充电132](../../sessions/132-persistent-mp2650-real-boot-and-complete-rootfs.md)、[充电138](../../sessions/138-readonly-charger-recharge-threshold.md)、[实体camera前的TPG126](../../sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md)、[传感器112](../../sessions/112-startup-sensor-registry-and-reboot.md)、[Wi-Fi128](../../sessions/128-wcn3990-pairwise-key-delete-and-5ghz.md)、[蓝牙130](../../sessions/130-standard-bluez-discovery-and-startup-integration.md)。

阶段151以前的完整状态记录已经移入[历史快照](../../archive/HARDWARE-STATUS-through150-2026-10-13.md)，不再把旧136 GPU故障或145设备状态写作当前待办。
'''

checkpoint = '''# Realme X2 Pro 当前检查点

2026-10-13，阶段151收尾。**已复现的A640 GPU CCU故障修复成功并已部署，本轮GPU定位结束。** 保留147内核和149 Mesa修复库；150不修改Mesa的降级候选只完成研究和独立进程验证，未部署。

## 当前实际状态

手机为内核#147、boot132/logdump147/modules132，software132加`mesa-vulkan-freedreno-26.2.4-r1`的本地修复库。`uname -r`仍带k132，`uname -v`实际为#147，不能按目录kernel136或旧版本后缀判断镜像。当前源码仍在WSL`/home/cy122/pmos-samurai-kernel136/kernel`。

151只读收尾六次观察、约20.6秒：同149验收启动，修复库和原库备份SHA一致，桌面与taint0保持，累计GPU fault3、新增0，WARN/DPU/DSI/DMA prepare0，无活动GPU测试、临时GPU追踪或待取core。Wi-Fi关联5180MHz，BlueZ服务started，modem/adsp running，SLPI offline。未刷写、重启或新增GPU负载。[收尾收据](reference/kernel151/closeout.json)

包数据库在2026-10-13 15:31之后与149收据摘要不同，原因未建立；仍936包，Mesa软件包版本仍26.2.4-r1，已部署修复库没有被覆盖。本轮数据库摘要稳定。初次收尾检查因旧数据库匹配断言失败已留档，不能宣称全部软件文件自149保持不变。这是独立的软件元数据待核对项。

## GPU 结论与保留材料

147针对旧式内核管理VM/GLES起点64 KiB对齐，20次像素验证和6次持续绘制通过。149针对自动VM_BIND地址对齐，原版和同构建基线均有空洞复现失败对照；修复库185次像素读回、160,820,781像素零差异，36次Settings面板打开，PM、稀疏重绑定、旧地址重放、Vulkan/GLES并发通过。[147](sessions/147-a640-gmem-alignment-fix.md)、[149](sessions/149-vulkan-ccu-alignment-fix-and-deployment.md)

这是当前故障和已测负载的验收，不等同所有Vulkan扩展、长期压力与跨启动全覆盖。显示接管、DSI及其它硬件待办独立保留。没有新故障证据时，不从旧136失败状态重复开始GPU定位。

公开Mesa补丁：`linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch`。已部署库SHA256为`97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e`；原库与回退工具在手机`/var/lib/samurai/k149-deployment`，主机材料在`E:/edk2-samurai-out/kernel149`。完整构建源码在手机`/var/lib/samurai/k148-mesa`；SDK在`/tmp/k148-sdk`，重启后重新核对并准备。

普通Mesa升级可能覆盖本地`.so`，旧完整rootfs132也不含149更新。后续应把0015纳入对应Mesa软件包构建并生成匹配新rootfs；完成包更新后重新核对库和回归。不要只恢复旧rootfs后仍宣称GPU修复保持。

150候选通过拒绝EN_VM_BIND与VA_START回退GET_IOVA，会失去稀疏绑定、地址捕获重放及lazy BO。MSRTSS内部依赖lazy路径但仍报告支持，是新发现的未测风险。该候选未完整构建或部署，不能删除149库补丁后直接继续使用现有内核。[研究](reference/kernel150/README.md)、[功能与其他机型比较](reference/kernel150/peer-device-comparison.md)

## 下一阶段

优先显示首次接管/DSI生命周期，再推进充电控制保护和音频首次DMA准备失败。实体camera、完整传感器、蜂窝业务、GNSS真实fix、指纹、NFC读卡及振动物理确认仍未完成；已经可用的触摸、Wi-Fi、蓝牙扫描与USB需要补冷启动/休眠/长稳。[当前硬件清单](linux-port/docs/HARDWARE-STATUS.md)

规则仅以[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)为准。切换前重新读取实际设备状态，不复用旧切换身份或重复发送状态未明的切换命令。保护重要分区、NV、校准和工厂备份；电池FET/OTP/解封与温控边界保持；蓝牙只扫描不连接，振动不新增脉冲，私人数据不公开。

原始日志和身份在手机`/var/lib/samurai/k151-closeout`及主机私有输出目录。历史147至150的旧检查点已保存到[历史快照](archive/NEXT-SESSION-through150-2026-10-13.md)。本轮会话见[151收尾](sessions/151-gpu-closeout-and-hardware-handover.md)。
'''

prompt = '''# 下一会话短提示词

继续Realme X2 Pro Linux适配，先读NEXT-SESSION.md、linux-port/docs/HARDWARE-STATUS.md和WORKING-BOUNDARIES.md。当前内核#147/software132加已部署Mesa149本地库；已复现GLES/Vulkan CCU故障修复成功，151同boot收尾新增fault0、taint0、桌面保持，无测试/临时GPU追踪/core。150无Mesa补丁候选未部署，存在功能降级与MSRTSS未测风险，不替换现有方案。

下一阶段优先显示接管/DSI生命周期，然后充电控制保护、音频首次DMA问题；实体camera、完整传感器、蜂窝业务、GNSS fix、指纹/NFC读卡/振动物理确认及跨硬件休眠长稳仍开放。原生触摸、Wi-Fi、蓝牙扫描和USB已有基础能力。Mesa升级与旧rootfs132会覆盖本地修复，后续构建需携带0015补丁。包数据库与149摘要不同，936包/Mesa26.2.4-r1及修复库保持，原因待核对。当前源码目录kernel136实际为147；切换前核对设备状态，保护分区/NV/电池边界，不复用旧收据。
'''

for name, content in [('linux-port/docs/HARDWARE-STATUS.md', hardware), ('NEXT-SESSION.md', checkpoint), ('NEXT-SESSION-PROMPT.md', prompt)]:
    target = root/name
    temporary = target.with_name(target.name+'.k151-stage')
    assert not temporary.exists()
    with temporary.open('wb') as out:
        out.write(content.encode('utf-8')); out.flush(); os.fsync(out.fileno())
    temporary.replace(target)
print(json.dumps(dict(current_hardware_table_updated=True, checkpoint_updated=True,
    short_handover_updated=True, historical_evidence_preserved=True)))
