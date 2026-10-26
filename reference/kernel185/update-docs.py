"""Update the current checkpoint from verified records; preserve the previous one."""
from pathlib import Path
import hashlib
import json

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel185'
final = json.loads((ref / 'final-validation.json').read_text())
pm = json.loads((ref / 'powered-suspend-validation.json').read_text())
boot = json.loads((ref / 'reboot-runtime-validation.json').read_text())
scans = json.loads((ref / 'scan-comparison-validation.json').read_text())
post = json.loads((ref / 'postresume-scan-validation.json').read_text())
assert final['installed_and_loaded_module_verified'] and final['bluez_original_configuration_restored']
assert final['taint'] == 0 and not any(final['full_boot_fault_counts'].values())
assert pm['suspend_and_rtc_resume_passed'] and pm['initial_combined_trial_passed'] is False
assert scans['transport_fix_passed'] and post['transport_fix_passed'] and boot['new_boot_confirmed']
current = root / 'NEXT-SESSION.md'
snapshot = root / 'archive/NEXT-SESSION-through184-2026-10-15.md'
assert not snapshot.exists()
snapshot.write_bytes(current.read_bytes())

readme = f'''# 185：蓝牙功率脉冲与H4边界修复及实机部署

2026-10-15。无人值守外设适配goal仍active，范围包含GPS、实体摄像头、蓝牙、传感器、蜂窝通信等。185是工作阶段号；实际仍kernel183/logdump183、boot/DTB172、runtime/modules132、Mesa149、UCM173。本轮仅替换同release的一个hci_uart模块，未刷分区。边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 修复与构建

184两次新启动均有两条`phase=2 baud=115200 chunk=1 partial=0 first=00`重组错误；185扫描前的原模块对照又出现一次相同错误。现场及[上游QCA源码](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux.git/+/f5ca7a7161028db5ac5bcd06db03d7f2e340a20d/drivers/bluetooth/hci_qca.c)表明功率脉冲阶段先发送原始UART单字节，再重开端口进入HCI。

[补丁](qca-power-pulse-rx.patch)只在有限功率脉冲窗口、没有未完成帧和padding时接收前导NUL，并使用只读`ibs/pulse_rx_nuls`计数；后续有效数据继续送原H4解析器，普通模式、帧内0、padding及其它异常保留。开/关控制器延迟保持，同时拒绝0字节写入并在写失败时恢复flow control与标志。补丁针对本地原源SHA8f50e48f…，新源645ded49…，需要原有phase诊断上下文，不能称为直接适用于任意主线版本。

实际提取qca_recv、qca_send_power_pulse及当前h4_recv_buf的C验证：ASan/UBSan、1049场景、1030次分配与释放匹配；五种故意破坏窗口/部分payload/消费计数/短写/flow恢复的负例全部被检出。[主机验证](host-tests-validation.json)、[源码检查](source-validation.json)。仅主机报告中的runtime=false表示当时尚未进行实机试验，后续依据单独记录。

目标模块与依赖共同Kbuild、W=1告警0，vermagic和183构建符号核对通过，Image/DTB/config及原183的12个tracked源保持。单目标modpost会产生局部符号表，因此已恢复完整16793行Module.symvers及770模块的modules.order。[构建](module-build-validation.json)里的runtime_deployed=false是构建时快照。只安装hci_uart，btqca/btbcm保持原文件；最终784个树文件含770个模块仅1个明确覆盖。[清单](module-override-validation.json)

## 扫描对照与默认部署

原模块LE12秒、BR/EDR12秒、混合20秒均收到响应，但新增一次UART重组错误。候选同样三轮通过、错误增量0，独立HCI/MGMT均见真实Inquiry与LE scan，未见配对/连接命令；每组23个桌面/Wi-Fi/DSP/taint健康样本通过。[对照](scan-comparison-validation.json)

发现缓存中已存在1组配对/绑定，未删除或改写。为只扫描测试暂时设置ReconnectAttempts=0及空ReconnectUUIDs，原配置逐字备份；D-Bus保持Pairable/Connectable/Discoverable=false，DiscoveryFilter AutoConnect=false，未调用Pair/Connect。各次结束均关闭扫描/控制器，原密钥逐字段核对保持，新缓存中没有密钥。

候选SHA256 f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020，已原子安装到`/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+/kernel/drivers/bluetooth/hci_uart.ko`。标准OpenRC服务重载使用默认路径，已加载ELF build-id匹配，依赖保持，taint0，原BlueZ配置恢复。[部署](deployment-validation.json)

## 新启动与PM

按本次启动身份/分区哈希、784文件模块清单、GUI/无线/音频/DSP离线核验，完整证据取回并验证SHA后，冻结F2FS，发一次审查过的RESTART2进入bootloader。查到新的fastboot身份及产品后仅发一次reboot，**没有flash**。新183启动服务自动加载默认候选、0秒日志及九类所列故障均0，脉冲计数3、Phosh/声卡/Wi-Fi5180/ADSP/modem恢复，SLPI未启动。[新启动](reboot-runtime-validation.json)。这是受控热重启验证，未做物理断电冷启动。

蓝牙开启、无连接且不处于discoverable/connectable/pairable状态，先5秒RTC IRQ预检，再45秒s2idle。实际休眠{pm['suspend_residency_seconds']:.3f}秒，success+1/fail+0、RTC IRQ+1、taint0、同boot且同加载模块；11项错误增量0，2392个PM结束回调全err0，其中QCA4个。前后控制器仍开启、脉冲计数5保持。[PM](powered-suspend-validation.json)

第一组合试验在醒后2秒的Wi-Fi5180检查失败，因而没有进入扫描，**仍记失败**。[失败](combined-trial-failure-validation.json)。随后Wi-Fi自行恢复至5180、无需手动重绑/重连；未测精确恢复时长，不能认定Wi-Fi PM完整验收。[观察](postresume-inspection-validation.json)

同boot另起仅扫描试验，不重复休眠；LE/BR/EDR/混合三轮均通过，独立捕获{post['postresume']['hci_packets']}个HCI包、MGMT实际LE与经典响应、23个健康样本，无配对或连接指令且协议错误0。[醒后扫描](postresume-scan-validation.json)。此结果是延后独立扫描通过，不将原组合失败改成成功。

## 失败与最终状态

保留初始目标modpost缺btqca/btbcm符号及in-tree extra-symbols无效两次构建失败、checkpatch标题/分隔元数据失败、主机测试stub告警，以及旧验证器假定无既有配对/固定6个MGMT发现事件的失败。改为保存既有配对并核对真实各transport起停事件，允许内核在一个D-Bus扫描内暂停/重启Inquiry，不删除多余记录。

重启前首次核验未规范化`./`路径，修正后又误把784个清单文件等同770模块；均在重启前失败，原partial副本保持。最终所有784文件逐一匹配，仅声明hci_uart覆盖。新启动第一次采集早于正常OpenRC启动bluetoothd，D-Bus激活失败原样保存；改为观察实际service owner就绪，未重复重启或借此手动启动服务。

最终{final['uptime_seconds']:.2f}秒：新185所记录183 boot、taint0，原BlueZ配置恢复、服务运行，蓝牙关/扫描关/连接0、密钥保持；候选文件及加载build-id核对，784文件/770模块、NV/原固件/boot/logdump/persist哈希通过。Phosh运行、Wi-Fi5180、PCM闭/双功放静音，ADSP/modem running，SLPI offline/供电0且本boot未启动。十二类所列全boot故障0、脉冲计数{final['pulse_rx_nuls']}。[最终](final-validation.json)

## 回退与继续

旧模块SHA ae57a822…，在手机`/var/lib/samurai/k185-deploy/hci_uart-original-private.ko`、baseline副本及主机私人包中保持。回退须先核对新取的设备身份、停止BlueZ并按原samurai-bluetooth卸载，再原子恢复此release旧模块、启动标准服务核验；不用rmmod -f，也不用旧boot身份做新切换。原主模块树清单132保留，185清单明确仅此覆盖。软件/rootfs132更新可能覆盖本次修复。

私人原始日志、周围设备/密钥/调制解调器资料在E:/edk2-samurai-out/kernel185和手机k185*；两份完整包SHA验证，公开只含脱敏记录。[切换前封存](before-reboot-archive-validation.json)，最终包SHA见各报告。内核源码tracked13，git diff --check通过，无新整包Image构建或刷写。

此阶段修复并验证蓝牙UART启动错误、规定范围扫描和一次开启状态s2idle；配对/连接/蓝牙音频按边界未测试，物理冷启动及长稳仍开放。184光线名称补丁仍仅独立候选库，lux准确度/惯性/SLPI停启未修复；GPS真实fix、实体摄像头及蜂窝业务也未验收。下一步优先利用当前未启动过SLPI的新boot补文件服务/OEM元数据与ready握手证据，然后推进GPS/摄像头/蜂窝软件路径，完整goal继续active。
'''
(ref / 'README.md').write_text(readme, encoding='utf-8', newline='\n')
checkpoint = f'''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段185，外设适配goal active。当前kernel183/logdump183、boot/DTB172、modules132且hci_uart覆盖185、Mesa149/UCM173。一轮受控热重启及一次s2idle，无flash。规则见[边界](WORKING-BOUNDARIES.md)。用户暂无耳机，不重复问。

## 当前部署与实机依据

| 项目 | 最后核对结果 |
| --- | --- |
| 组合 | #183 SMP PREEMPT Oct15 00:20:49；Image bfa72dd9…、logdump e73754c7…、boot172 77e1a272…、DTB172 22c1f2ad…保持 |
| 蓝牙修复 | 有界功率脉冲窗口处理前导NUL，帧内0/padding/普通错误保留；短写与flow失败恢复。hci_uart SHAf6c5ed35…已装默认路径，原ae57a822…保持 |
| 验证 | 实际QCA/H4 C代码1049场景/ASan/UBSan及5负例通过；原模块扫描新增重组1，候选3模式0；热重启自动服务加载，0秒日志重组0 |
| 蓝牙PM | 开启无连接s2idle45.205秒，RTC IRQ1、success1/fail0、2392回调err0/QCA4，前后同模块；延后独立3模式扫描通过，无配对/连接指令 |
| Wi-Fi限制 | 组合试验醒后2秒未关联5180，扫描前检查失败；随后自行恢复，未手工重连。原失败保持，精确恢复时长未测 |
| 当前{final['uptime_seconds']:.2f}秒 | taint0、Phosh、Wi-Fi5180；ADSP/modem running，SLPI offline/供电0且此boot未启动。蓝牙服务在/关/扫描关/连接0；原配置及密钥保持，PCM闭/功放静音 |
| 核验 | 784树文件/770模块仅1覆盖、boot/logdump/persist/NV/原固件通过；12类所列全boot0，脉冲计数6，不称所有功能完成 |
| 光线184 | wise_light实体96测量、原始通道变化；libssc独立候选库CLI41样本与SensorProxy光线/接近Claim/Release通过。lux仍0/惯性缺失，系统库与自动服务未改 |

依据：[185](reference/kernel185/README.md)、[最终](reference/kernel185/final-validation.json)、[重启](reference/kernel185/reboot-runtime-validation.json)、[PM](reference/kernel185/powered-suspend-validation.json)、[组合失败](reference/kernel185/combined-trial-failure-validation.json)、[醒后扫描](reference/kernel185/postresume-scan-validation.json)。184完整状态逐字保留[through184](archive/NEXT-SESSION-through184-2026-10-15.md)，原相对链接按工作区根解释；[184](reference/kernel184/README.md)与[SSC兼容层](linux-port/ssc/README.md)保留。

## 源码、产物与回退依据

- WSL内核/home/cy122/pmos-samurai-kernel136/kernel tracked13：原183的12源保持，加hci_qca.c SHA645ded49…。[模块构建](reference/kernel185/module-build-validation.json)、[补丁](reference/kernel185/qca-power-pulse-rx.patch)。整包Image/DTB/config保持，完整Module.symvers及modules.order恢复。构建报告的runtime=false是部署前快照，后续见185部署报告。
- 旧hci_uart手机k185-deploy/hci_uart-original-private.ko、baseline及E:/edk2-samurai-out/kernel185完整封存。停BlueZ/原工具卸载后才恢复模块，不强制卸载。rootfs132更新可能覆盖hci_uart185/UCM173/Mesa149，原132模块清单保持。
- 当前boot身份在k185-reboot-runtime、k185-final；185 preflash属于切换前boot，下一次操作重新取身份。184final及183all各属于旧boot，不混用。
- 当前镜像及重要回退E:/edk2-samurai-out/kernel183、181等保持；logdump181及旧178/180/181音频失败保持。SD1的172/171原件、BDS164/固件172/FdtBlob129保持。
- 183前boot的活跃双工合成crash原客户端恢复、左右声学及2次PM见[183](reference/kernel183/README.md)。当前boot未重做声学/SSR；185蓝牙PM不能代替完整音频PM验收。UCM173由callaudiod管理，不强制补端口模块。

## 续作与已知风险

1. 完整目标GPS、摄像头、蓝牙、传感器、蜂窝等仍active。当前SLPI此boot未启动，可用于新的受控试验；优先原00121文件服务/OEM元数据、LSM6DS3C注册与ready停启。184同boot第二次start−110、v3 --debug失败和所有旧固件试验保持，不盲目重复start。
2. 184libssc 0.4.4 OEM名称配置候选仍未替换系统库/自动服务；lux均0，准确度/接近日常/惯性/持续服务未验收。C28/C35历史磁力计结果不冒充当前固件，加速度/陀螺仍缺。
3. GPS LOC历史控制链和55个in-progress报告不算fix；继续UTC/aiding及标准定位服务。蜂窝sim-missing，IPA/双槽/错误传播可推进，真实注册/数据/通话/SMS未验收。
4. 摄像头内部TPG三帧DMA不算实体出图；继续PM8008四输入/冷地址/复位/chip-enable本机供电契约，再CCI/C-PHY/用户态。不借外机校准。
5. 蓝牙UART启动错误已有修复/扫描/热启动/一次开启PM证据；连接/音频、物理断电冷启动及长稳仍开放，按边界只扫描。Wi-Fi醒后关联延迟、USB/充电/显示/触摸及其它待办见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(checkpoint.encode()) <= 6500, len(checkpoint.encode())
current.write_text(checkpoint, encoding='utf-8', newline='\n')
status = root / 'linux-port/docs/HARDWARE-STATUS.md'
text = status.read_text()
first = next(line for line in text.splitlines() if line.startswith('用途：'))
intro = '用途：当前硬件验收清单。最后核对：2026-10-15，阶段185仍kernel183/logdump183、boot/DTB172、modules132且hci_uart覆盖185、Mesa149/UCM173。本轮修复并部署蓝牙功率脉冲与H4边界，通过原/候选扫描、热重启自动加载、开启状态45.205秒s2idle及延后醒后扫描。组合试验醒后2秒Wi-Fi关联检查失败保持，随后自动恢复，未测精确恢复时长；见[185](../../reference/kernel185/README.md)。184独立光线库候选保持，lux/惯性/SLPI重启未修复，系统库/自动服务未改。完整外设goal active；音频旧183 boot声学/SSR与PM证据不混入新boot，见[183](../../reference/kernel183/README.md)、[184](../../reference/kernel184/README.md)，规则见[边界](../../WORKING-BOUNDARIES.md)。'
text = text.replace(first, intro, 1)
old = next(line for line in text.splitlines() if line.startswith('| 蓝牙 |'))
new = '| 蓝牙 | 185有限功率脉冲NUL处理与短写/flow修复已部署；原扫描错误1/候选0，3模式真实响应；热重启自动加载及0秒日志重组0；开启状态s2idle45.205秒/RTC1/QCA4回调err0，延后3模式扫描与密钥保持通过 | 配对/连接/音频、物理断电冷启动及长稳未验收，按边界只扫描；Wi-Fi立即醒后检查导致原组合试验失败，不能改记全部通过 |'
text = text.replace(old, new, 1)
old = next(line for line in text.splitlines() if line.startswith('| Wi-Fi |'))
new = '| Wi-Fi | 2.4/5GHz已有实际通信回归，本轮5180MHz；185 s2idle后自行恢复关联、无需手工重连且所列驱动故障增量0 | 醒后2秒未关联5180触发检查失败，精确恢复时长未测；物理冷启动、完整休眠通信恢复及长稳待验，当前关联不代表全部解决 |'
text = text.replace(old, new, 1)
status.write_text(text, encoding='utf-8', newline='\n')
session = '''# 185：蓝牙功率脉冲解析修复、默认模块部署与PM

2026-10-15。仍kernel183/logdump183及boot/DTB172；本轮仅hci_uart同release模块覆盖185，无刷分区。实际QCA/H4代码1049主机场景与5负例通过，原模块扫描新增错误1、候选0；默认服务、热重启自动加载、开启无连接s2idle45.205秒/2392回调err0/QCA4及延后LE/BR/EDR/混合扫描通过。原组合在醒后2秒Wi-Fi5180检查失败仍保留，Wi-Fi随后自动恢复；既有密钥保持且未发起配对/连接。

完整修复、构建、回退、失败及私人证据路径见[185记录](../reference/kernel185/README.md)。[最终](../reference/kernel185/final-validation.json)是本次新boot；[当前检查点](../NEXT-SESSION.md)、[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。传感器、GPS、实体camera、蜂窝业务及完整goal仍开放。
'''
(root / 'sessions/185-bluetooth-power-pulse-h4-repair-and-pm.md').write_text(session, encoding='utf-8', newline='\n')
(ref / 'checkpoint-validation.json').write_text(json.dumps(dict(stage=185,
    previous_checkpoint_preserved=True, previous_checkpoint_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    current_checkpoint_bytes=len(checkpoint.encode()), current_kernel_build=183, goal_status='active'), indent=2) + '\n')
print(json.dumps({'checkpoint_bytes': len(checkpoint.encode()), 'previous184_preserved': True,
    'bluetooth_repair_and_failed_wifi_guard_both_documented': True, 'goal_status': 'active'}))
