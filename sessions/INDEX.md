# 会话与证据索引

用途：定位现有会话及reference证据。结构整理：2026-10-14；由generate-session-index.py按文件清单生成，保持原始记录的标题与结论。

最后核对的部署见[检查点](../NEXT-SESSION.md)，当前操作规则见[WORKING-BOUNDARIES](../WORKING-BOUNDARIES.md)，验收范围见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。

## 会话文件

| 记录 | 原文标题 |
| --- | --- |
| [12-final-image-and-log-gap.md](<12-final-image-and-log-gap.md>) | 12-final-image-and-log-gap |
| [13-eud-log-ring-implemented.md](<13-eud-log-ring-implemented.md>) | 13-eud-log-ring-implemented |
| [14-eud-log-ring-verified.md](<14-eud-log-ring-verified.md>) | 14-eud-log-ring-verified |
| [15-full-debug-and-crash-root-cause.md](<15-full-debug-and-crash-root-cause.md>) | 15-full-debug-and-crash-root-cause |
| [16-commits-noise-and-cpufreq-bug.md](<16-commits-noise-and-cpufreq-bug.md>) | 16-commits-noise-and-cpufreq-bug |
| [17-submodule-solution-a.md](<17-submodule-solution-a.md>) | 17-submodule-solution-a |
| [18-mainline-kernel-in-firmware.md](<18-mainline-kernel-in-firmware.md>) | 1) 先备好 EUD 日志通道：重启后约 3.5 s 出现 9501，那时执行 |
| [29-eud-console-tty-command-channel.md](<29-eud-console-tty-command-channel.md>) | 29-eud-console-tty-command-channel |
| [30-artifacts-and-workflow.md](<30-artifacts-and-workflow.md>) | 30-artifacts-and-workflow |
| [31-flywheel-f1-verified.md](<31-flywheel-f1-verified.md>) | 31. 飞轮 F1：Linux 自己重启进 fastboot（2026-10-08 晚，真机验证） |
| [32-rx-printk-interference.md](<32-rx-printk-interference.md>) | 32. RX 探针：前置 printk 改变读回，多字节推进仍待验证 |
| [33-rx-access-and-production-policy.md](<33-rx-access-and-production-policy.md>) | 33. EUD RX：访问路径、上下游与量产权限排查（2026-10-08 至 09） |
| [34-temporary-eud-terminal.md](<34-temporary-eud-terminal.md>) | 34. 临时 EUD 终端：继续 Linux 驱动移植（2026-10-09） |
| [35-rx-next-session-handoff.md](<35-rx-next-session-handoff.md>) | 35. 下一会话交接：继续原生多字节 RX 排查（2026-10-09） |
| [36-rx-usb-descriptors-and-legacy-qcusbser.md](<36-rx-usb-descriptors-and-legacy-qcusbser.md>) | 36. EUD RX：USB 描述符与旧 qcusbser 源码（2026-10-09） |
| [37-rx-source-search-and-phy-lifecycle.md](<37-rx-source-search-and-phy-lifecycle.md>) | 37. 搜索原生多字节 RX 修复：源码差异与 PHY 生命周期（2026-10-09） |
| [38-rx-pre-linux-and-usb-boundaries.md](<38-rx-pre-linux-and-usb-boundaries.md>) | 38. 原生 RX：UEFI 对照与 USB 包边界（2026-10-09） |
| [39-rx-tight-arrival-poll.md](<39-rx-tight-arrival-poll.md>) | 39. 接收窗口假设：UEFI 紧轮询仍重复首字节（2026-10-09） |
| [40-rx-register-map-and-stock-firmware-audit.md](<40-rx-register-map-and-stock-firmware-audit.md>) | 40. 完整寄存器表与原厂 SM8150 固件审查（2026-10-09） |
| [41-rx-ahb2phy-wait-state-fix.md](<41-rx-ahb2phy-wait-state-fix.md>) | 41. SM8150 AHB2PHY 等待周期使原生多字节 RX 推进（2026-10-09） |
| [42-native-terminal-next-session-handoff.md](<42-native-terminal-next-session-handoff.md>) | 42. 下一会话交接：原生多字符终端稳定性（2026-10-09） |
| [43-native-terminal-evidence-audit.md](<43-native-terminal-evidence-audit.md>) | 43. 原生终端输出证据更正与缺回执边界（2026-10-09） |
| [44-rx-receipt-counters.md](<44-rx-receipt-counters.md>) | Session 44: missing-receipt boundary measured with RX counters |
| [45-rx-mask-before-arrival.md](<45-rx-mask-before-arrival.md>) | Session 45: RX enable mask before arrival does not fix missing receipts |
| [46-rx-irq-and-host-trace-boundary.md](<46-rx-irq-and-host-trace-boundary.md>) | Session 46: real IRQ reception and the missing host-frame boundary |
| [47-native-terminal-session-boundary.md](<47-native-terminal-session-boundary.md>) | 47. 原生终端持续会话与重开边界（2026-10-09） |
| [48-irq-grace-and-tx-journal.md](<48-irq-grace-and-tx-journal.md>) | 48. IRQ 宽限诊断与可校验 TX 记录（2026-10-09） |
| [49-usb-in-and-partial-timeout-audit.md](<49-usb-in-and-partial-timeout-audit.md>) | 49. USB IN 与部分超时数据核对（2026-10-09） |
| [50-windows-receive-and-driver-buffer-audit.md](<50-windows-receive-and-driver-buffer-audit.md>) | Session 50：当前连接正常；补齐 Windows 接收观测和实装驱动缓冲边界 |
| [51-console-overlap-and-issued-frame-loss.md](<51-console-overlap-and-issued-frame-loss.md>) | 51. 长 console 输出期间缺 RX，恢复状态缺一个已发 TX 帧（2026-10-09） |
| [52-same-owner-usb-overlap-and-continuous-in.md](<52-same-owner-usb-overlap-and-continuous-in.md>) | 52. 同一 USB owner 的长日志缺 RX，持续 IN 对照（2026-10-09/10） |
| [53-console-boundary-rx-service.md](<53-console-boundary-rx-service.md>) | 53. 在 console 完整 TX 帧边界服务 RX（2026-10-10） |
| [54-console-rx-regression-and-host-counter-audit.md](<54-console-rx-regression-and-host-counter-audit.md>) | Session 54: repeated console RX, console F1 and the next TX observation |
| [55-windows-perf-counter-and-reproduced-tx-gap.md](<55-windows-perf-counter-and-reproduced-tx-gap.md>) | Session 55: reproduced TX loss before the Windows accepted-buffer counter |
| [56-source-boundaries-and-focused-research.md](<56-source-boundaries-and-focused-research.md>) | Session 56: consolidate the remaining faults and search at the missing boundary |
| [57-driver-raw-logging-boundary.md](<57-driver-raw-logging-boundary.md>) | 57. 实装驱动原始日志：补齐 Windows 受理缓冲之前的观察点 |
| [58-reopen-first-frame-and-driver-completion-gates.md](<58-reopen-first-frame-and-driver-completion-gates.md>) | 58. 三次缺帧的重开共性与驱动失败读分支 |
| [59-joint-capture-and-forced-odd-reopen-gap.md](<59-joint-capture-and-forced-odd-reopen-gap.md>) | 59. 联合抓取与主动奇数帧重开实验 |
| [60-even-reopen-reversal-and-toggle-candidate.md](<60-even-reopen-reversal-and-toggle-candidate.md>) | Session 60 — even-IN reversal and a host toggle candidate |
| [61-eud-wdf-package-and-build-preparation.md](<61-eud-wdf-package-and-build-preparation.md>) | Session 61 — dedicated EUD WDF package inputs and build preparation |
| [62-eud-wdf-build-and-test-signed-package.md](<62-eud-wdf-build-and-test-signed-package.md>) | Session 62 — full EUD WDF build and file-only test-signed package |
| [63-single-device-driver-compatibility-and-trial-tools.md](<63-single-device-driver-compatibility-and-trial-tools.md>) | Session 63 — live single-device compatibility and guarded rollback tools |
| [65-wsl-full-packet-console-overlap-and-tx-gap.md](<65-wsl-full-packet-console-overlap-and-tx-gap.md>) | 65. WSL 整包 console RX 通过，连续会话仍缺 tty TX（2026-10-10） |
| [66-verified-kernel-logs-and-builtins.md](<66-verified-kernel-logs-and-builtins.md>) | Session 66 — 校验 Linux 日志，逐项修复内建依赖与 early mapping |
| [67-usb-provider-and-dtb-activation.md](<67-usb-provider-and-dtb-activation.md>) | 67. USB PHY 内建生效，CPU7 DTB 候选未进入实际启动树 |
| [68-firmware-dtb-and-cpu7-opp-verified.md](<68-firmware-dtb-and-cpu7-opp-verified.md>) | 68. 固件 DTB 激活，CPU7 高 OPP 真机通过（2026-10-10） |
| [69-usb-gadget-state-and-eud-coordination-audit.md](<69-usb-gadget-state-and-eud-coordination-audit.md>) | 69. USB 功能未配置，EUD 共存边界只读核对（2026-10-10） |
| [70-pm8009-resource-and-touch-prerequisites.md](<70-pm8009-resource-and-touch-prerequisites.md>) | 70. PM8009 资源缺失影响范围与触摸前提（2026-10-10） |
| [71-native-s3706-touch-bringup.md](<71-native-s3706-touch-bringup.md>) | 71. 本机S3706触摸接入（2026-10-10） |
| [72-usb-ncm-and-autonomous-ssh.md](<72-usb-ncm-and-autonomous-ssh.md>) | 72. 普通USB NCM与自动SSH接入（2026-10-10） |
| [73-native-sofef03f-dsi-dsc-display.md](<73-native-sofef03f-dsi-dsc-display.md>) | 73. 原生SOFEF03F DSI/DSC与60Hz显示输出（2026-10-10） |
| [74-sm8150-display-boot-handoff.md](<74-sm8150-display-boot-handoff.md>) | Session74：SM8150 DPU5命令显示接管（2026-10-10） |
| [75-a640-render-and-sofef03f-clock-fix.md](<75-a640-render-and-sofef03f-clock-fix.md>) | Session 75：A640 实际渲染与 SOFEF03F 花屏修正 |
| [76-charging-source-and-safety-review.md](<76-charging-source-and-safety-review.md>) | Session76：X2 Pro 充电设备树、相关内核与安全边界 |
| [77-bq28z610-live-gauge-and-display-regression.md](<77-bq28z610-live-gauge-and-display-regression.md>) | Session77：BQ28Z610 真实读数接入与显示启动回归 |
| [78-first-boot-display-controls-and-pageflips.md](<78-first-boot-display-controls-and-pageflips.md>) | Session78：相同镜像的首次显示接管对照与页面翻转 |
| [79-mp2650-read-only-bus-and-current-settings.md](<79-mp2650-read-only-bus-and-current-settings.md>) | Session79：MP2650 总线接入与当前配置只读核验 |
| [80-gauge-identity-and-stock-cell-observations.md](<80-gauge-identity-and-stock-cell-observations.md>) | Session80：电量计身份差异与原厂双电芯读取 |
| [81-stock-gauge-state-temperature-and-display-timeouts.md](<81-stock-gauge-state-temperature-and-display-timeouts.md>) | Session81：原厂电量计状态、温度及显示超时复查 |
| [82-charging-policy-units-and-android-backup-provenance.md](<82-charging-policy-units-and-android-backup-provenance.md>) | Session82：充电策略单位、保护源码与 Android 备份来源 |
| [83-androidr-and-cyborg-charging-source-comparison.md](<83-androidr-and-cyborg-charging-source-comparison.md>) | Session83：Android R 官方源码与 cyborgdc2000 充电实现对照 |
| [84-display-boot-tracing-and-timeout-snapshots.md](<84-display-boot-tracing-and-timeout-snapshots.md>) | Session84：显示首次启动跟踪与超时快照 |
| [85-oem-chemistry-and-short-ic-observations.md](<85-oem-chemistry-and-short-ic-observations.md>) | Session85：原厂化学类型查询、短路 IC 无应答与 Android 温补分支 |
| [86-mp2650-input-status-and-real-display-timeout-snapshot.md](<86-mp2650-input-status-and-real-display-timeout-snapshot.md>) | Session86：MP2650 输入状态接入与真实显示超时快照 |
| [87-stage-wrap-up-and-wifi-prerequisites.md](<87-stage-wrap-up-and-wifi-prerequisites.md>) | 阶段收尾与 Wi-Fi 启动依赖（2026-10-10） |
| [88-wifi-dependency-build-and-read-only-firmware-service.md](<88-wifi-dependency-build-and-read-only-firmware-service.md>) | Session88：Wi-Fi依赖内核、只读固件服务及部署前交接 |
| [91-wifi-rmtfs-and-connected-traffic.md](<91-wifi-rmtfs-and-connected-traffic.md>) | Session91：Wi-Fi 服务链路、WPA2 与真实双向流量 |
| [92-connectivity-drivers-and-runtime-validation.md](<92-connectivity-drivers-and-runtime-validation.md>) | Wi-Fi、蓝牙扫描与 NFC 控制器实测（2026-10-11，session92） |
| [93-connectivity-startup-and-coexistence.md](<93-connectivity-startup-and-coexistence.md>) | 连接启动与 Wi-Fi/蓝牙共存（2026-10-11，session93） |
| [94-deferred-bluetooth-and-startup-isolation.md](<94-deferred-bluetooth-and-startup-isolation.md>) | session94：延后蓝牙 UART，恢复显示与首次 MPSS 启动 |
| [95-bluetooth-autoload-and-dual-band-regression.md](<95-bluetooth-autoload-and-dual-band-regression.md>) | session95：蓝牙自动加载、双频 Wi-Fi 与显示回归 |
| [96-wifi-msa-lifecycle-and-provisioned-addresses.md](<96-wifi-msa-lifecycle-and-provisioned-addresses.md>) | session96：Wi-Fi MSA回收、蓝牙独立扫描与本机NV地址 |
| [97-automatic-radio-addresses-and-boot-regression.md](<97-automatic-radio-addresses-and-boot-regression.md>) | 阶段97：自动本机地址供应与双频回归（2026-10-11） |
| [98-independent-radio-identities-and-key-delete-trace.md](<98-independent-radio-identities-and-key-delete-trace.md>) | 阶段98：独立无线地址供应与密钥删除时序定位 |
| [99-aw8697-haptics-and-ufs-readiness.md](<99-aw8697-haptics-and-ufs-readiness.md>) | 99：AW8697 原生振动接入与 UFS 就绪竞态 |
| [100-all-source-readiness-and-first-mpss-crash.md](<100-all-source-readiness-and-first-mpss-crash.md>) | 100：全源就绪等待已部署，首次MPSS启动崩溃仍待修复 |
| [101-adsp-native-apr-reply-and-radio-regression.md](<101-adsp-native-apr-reply-and-radio-regression.md>) | 101：ADSP真实版本回复、振动人工验证暂缓及无线基线 |
| [102-wcd934x-and-real-max98937-identification.md](<102-wcd934x-and-real-max98937-identification.md>) | session102：WCD934x接入与真实双MAX98937识别 |
| [103-native-max98937-card-pcm-and-zero-microphone.md](<103-native-max98937-card-pcm-and-zero-microphone.md>) | session103：MAX98937原生声卡、有限PCM与全零麦克风 |
| [104-native-digital-microphones-and-first-boot-radio-failure.md](<104-native-digital-microphones-and-first-boot-radio-failure.md>) | 阶段104：数字麦克风恢复采样，首次无线崩溃仍待修 |
| [105-apr-rebind-and-first-modem-crash-smem-diagnostics.md](<105-apr-rebind-and-first-modem-crash-smem-diagnostics.md>) | 阶段105：APR重绑登记恢复，首次MPSS无崩溃原因项 |
| [106-first-modem-hello-race-and-core-query-tracing.md](<106-first-modem-hello-race-and-core-query-tracing.md>) | 阶段106：首次modem HELLO/服务公告竞态有直接trace证据 |
| [107-qrtr-hello-reply-and-automatic-wifi-start.md](<107-qrtr-hello-reply-and-automatic-wifi-start.md>) | 阶段107：QRTR HELLO应答/公告顺序修复，首次自动Wi-Fi通过 |
| [108-display-flicker-and-panel-state-handover.md](<108-display-flicker-and-panel-state-handover.md>) | 阶段108：显示滚动花屏、错误关屏黑屏与交接（2026-10-11） |
| [109-pmos-userdata-phosh-and-desktop-audio.md](<109-pmos-userdata-phosh-and-desktop-audio.md>) | 109：userdata F2FS、Phosh 与桌面音频 |
| [111-slpi-fastrpc-and-display-regression.md](<111-slpi-fastrpc-and-display-regression.md>) | 111：本机 SLPI、FastRPC 与显示回归 |
| [112-startup-sensor-registry-and-reboot.md](<112-startup-sensor-registry-and-reboot.md>) | 112：完整启动日志、传感器注册表与正常重启 |
| [113-sensor-power-and-extended-rpc.md](<113-sensor-power-and-extended-rpc.md>) | 阶段113：本机传感器供电与扩展FastRPC |
| [114-complete-rootfs-and-qmi-ipa-foundation.md](<114-complete-rootfs-and-qmi-ipa-foundation.md>) | 阶段114：完整用户态 rootfs 镜像、原生 QMI/LOC 与 IPA 源码候选 |
| [115-own-ipa-modem-and-zram-rootfs.md](<115-own-ipa-modem-and-zram-rootfs.md>) | 阶段115：本机IPA、ModemManager与完整zram rootfs |
| [116-camss-foundation-and-own-sensor-binaries.md](<116-camss-foundation-and-own-sensor-binaries.md>) | 阶段116：CAMSS基础移植与本机摄像头二进制来源 |
| [117-parser-boundaries-and-same-boot-desktop-recovery.md](<117-parser-boundaries-and-same-boot-desktop-recovery.md>) | 阶段117：解析边界与同启动恢复桌面 |
| [118-final-reset-read-build-and-host-space-recovery.md](<118-final-reset-read-build-and-host-space-recovery.md>) | 阶段118：复位最终读候选与主机构建空间恢复 |
| [119-k118-deployment-and-real-gpu-pixel-failure.md](<119-k118-deployment-and-real-gpu-pixel-failure.md>) | 阶段119：部署#118与真实GPU像素失败 |
| [120-cci-device-tree-and-camera-pmic-contract.md](<120-cci-device-tree-and-camera-pmic-contract.md>) | 阶段120：CCI设备树及本机摄像头PMIC契约 |
| [121-pm8008-no-irq-and-native-reset-contract.md](<121-pm8008-no-irq-and-native-reset-contract.md>) | 阶段121：PM8008无IRQ支持与本机复位契约 |
| [122-complete-k121-rootfs-and-verified-build-cleanup.md](<122-complete-k121-rootfs-and-verified-build-cleanup.md>) | 阶段122：匹配#121完整rootfs与经验证的旧构建清理 |
| [123-camss-dt-dma-interconnect-and-strict-disabled-validation.md](<123-camss-dt-dma-interconnect-and-strict-disabled-validation.md>) | 阶段123：CAMSS DT、DMA/ICC与严格disabled节点校验 |
| [124-native-cphy-shared-rail-and-frequency-contract.md](<124-native-cphy-shared-rail-and-frequency-contract.md>) | 阶段124：原厂C-PHY表、共享电源与频率契约 |
| [125-native-cpas-qos-full-iova-window-and-mount-serialization.md](<125-native-cpas-qos-full-iova-window-and-mount-serialization.md>) | 阶段125：原厂CPAS、完整IOVA窗口与挂载并发修复 |
| [126-tpg-dma-guards-full-rootfs-and-real-deployment.md](<126-tpg-dma-guards-full-rootfs-and-real-deployment.md>) | 阶段126：DMA 守卫、完整 rootfs 与实际刷入验证 |
| [127-rootfs-user-owner-fix-and-live-system-resource-ownership.md](<127-rootfs-user-owner-fix-and-live-system-resource-ownership.md>) | 阶段127：rootfs账户权限修正与实机系统资源属主 |
| [128-wcn3990-pairwise-key-delete-and-5ghz.md](<128-wcn3990-pairwise-key-delete-and-5ghz.md>) | 阶段128：WCN3990 单播密钥删除等待与5GHz |
| [129-initial-console-node-and-real-boot-verification.md](<129-initial-console-node-and-real-boot-verification.md>) | 阶段129：初始console节点与实际启动验收 |
| [130-standard-bluez-discovery-and-startup-integration.md](<130-standard-bluez-discovery-and-startup-integration.md>) | 阶段130：标准BlueZ扫描与开机地址供应 |
| [131-fixed-size-pixel-validation-and-delayed-gpu-fault.md](<131-fixed-size-pixel-validation-and-delayed-gpu-fault.md>) | 阶段131：真实离屏尺寸对照与仍存在的迟发GPU故障 |
| [132-persistent-mp2650-real-boot-and-complete-rootfs.md](<132-persistent-mp2650-real-boot-and-complete-rootfs.md>) | 阶段132：MP2650持久节点、真实刷入与完整rootfs |
| [133-usb-power-budget-and-charge-contract.md](<133-usb-power-budget-and-charge-contract.md>) | 阶段133：USB输入预算与充电控制契约（2026-10-12） |
| [134-usb-input-budget-real-boot-and-display-startup-failure.md](<134-usb-input-budget-real-boot-and-display-startup-failure.md>) | 阶段134：USB输入额度标准接口、真实部署及显示启动失败 |
| [135-mdss-reset-candidate-rejected-and-stable132-rollback.md](<135-mdss-reset-candidate-rejected-and-stable132-rollback.md>) | 阶段135：MDSS复位候选拒绝、真实回退及音频新线索 |
| [136-legacy-gpu-vm-trace-and-ccu-address-correlation.md](<136-legacy-gpu-vm-trace-and-ccu-address-correlation.md>) | 阶段136：legacy GPU VM追踪与CCU地址核对 |
| [137-wcd-resource-cleanup-display-failure-and-rollback.md](<137-wcd-resource-cleanup-display-failure-and-rollback.md>) | 阶段137：WCD资源清理、显示失败与132回退 |
| [138-readonly-charger-recharge-threshold.md](<138-readonly-charger-recharge-threshold.md>) | 阶段138：本机充电恢复阈值的只读核对 |
| [139-slimbus-unsubmitted-tx-unwind-and-live-boot.md](<139-slimbus-unsubmitted-tx-unwind-and-live-boot.md>) | 阶段139：SLIMbus未提交发送回收与实际启动 |
| [140-first-dma-diagnostics-and-display-startup-timeouts.md](<140-first-dma-diagnostics-and-display-startup-timeouts.md>) | 阶段140：首次DMA诊断与显示启动超时 |
| [141-normal-wake-and-loss-free-startup-display-trace.md](<141-normal-wake-and-loss-free-startup-display-trace.md>) | 阶段141：普通亮屏和新启动显示追踪 |
| [142-startup-irq-gap-and-eud-console-latency.md](<142-startup-irq-gap-and-eud-console-latency.md>) | 阶段142：启动中断空档与EUD控制台延迟 |
| [143-threaded-console-live-regression-and-rollback.md](<143-threaded-console-live-regression-and-rollback.md>) | 阶段143：线程化控制台实机回归与140回退 |
| [144-eud-reboot-handoff-and-display-clock-review.md](<144-eud-reboot-handoff-and-display-clock-review.md>) | 阶段144：重启回执竞态定位与显示时钟核对 |
| [145-dsi-deployment-and-session-closeout.md](<145-dsi-deployment-and-session-closeout.md>) | 阶段145：实际部署、启动追踪失败与本轮收尾 |
| [145-dsi-observation-and-old-build-cleanup.md](<145-dsi-observation-and-old-build-cleanup.md>) | 阶段145：DSI追踪构建与E盘旧产物清理 |
| [146-gpu-gmem-isolation.md](<146-gpu-gmem-isolation.md>) | GPU GMEM 隔离实验（2026-10-13） |
| [147-a640-gmem-alignment-fix.md](<147-a640-gmem-alignment-fix.md>) | A640 GMEM 迟发 CCU fault 修复（阶段147，2026-10-13） |
| [148-vulkan-vm-bind-diagnostic-candidate.md](<148-vulkan-vm-bind-diagnostic-candidate.md>) | 阶段148：Vulkan VM_BIND候选与验证 |
| [149-vulkan-ccu-alignment-fix-and-deployment.md](<149-vulkan-ccu-alignment-fix-and-deployment.md>) | 阶段149：Vulkan CCU 空洞复现、地址对齐修复与部署 |
| [150-no-mesa-patch-gpu-research.md](<150-no-mesa-patch-gpu-research.md>) | A640 GPU 无 Mesa 本地补丁研究 |
| [151-gpu-closeout-and-hardware-handover.md](<151-gpu-closeout-and-hardware-handover.md>) | GPU 修复收尾与硬件交接 |
| [152-display-lifecycle-candidate-and-boot-handoff-reproduction.md](<152-display-lifecycle-candidate-and-boot-handoff-reproduction.md>) | 阶段152：显示生命周期候选、真实接管失败与桌面恢复 |
| [153-panel-gpio-handoff-and-first-startup-underflow.md](<153-panel-gpio-handoff-and-first-startup-underflow.md>) | 153：GPIO接管已进入桌面，首次DSI欠载及唤醒闪烁仍开放 |
| [154-dsi-host-init-rejected-and-runtime-display-recovery.md](<154-dsi-host-init-rejected-and-runtime-display-recovery.md>) | 154：停止继承DSI CTRL不足以修复首次白屏 |
| [156-first-frame-backlight-and-early-desktop.md](<156-first-frame-backlight-and-early-desktop.md>) | 156：首帧后亮屏与桌面提前启动 |
| [159-same158-second-boot-display-verification.md](<159-same158-second-boot-display-verification.md>) | 159：第二次158启动与显示回归 |
| [169-native-audio-service-lifecycle-and-two-boots.md](<169-native-audio-service-lifecycle-and-two-boots.md>) | 166—169：原生音频服务生命周期修复与两个独立启动 |
| [170-microphone-speaker-acoustic-self-test.md](<170-microphone-speaker-acoustic-self-test.md>) | 170：麦克风声学自测未检出扬声器编码音 |
| [171-speaker-sd1-and-acoustic-loop.md](<171-speaker-sd1-and-acoustic-loop.md>) | 171：扬声器从SD0改为板上SD1，三麦克风及桌面检出编码音 |
| [172-wcd-headset-detection-and-speaker-regression.md](<172-wcd-headset-detection-and-speaker-regression.md>) | 172：WCD耳机检测初始化与扬声器回归 |
| [173-ucm-headset-routing-and-desktop-duplex.md](<173-ucm-headset-routing-and-desktop-duplex.md>) | 173：耳机UCM路由与桌面双向音频 |
| [174-port-interrupt-stop-and-card-reprobe.md](<174-port-interrupt-stop-and-card-reprobe.md>) | 174：端口中断停止回归与声卡重探测 |
| [175-card-regmap-clock-lifetimes-and-reset-nack.md](<175-card-regmap-clock-lifetimes-and-reset-nack.md>) | 175：声卡、regmap与clock生命周期及父设备复位NACK |
| [176-reset-addresses-and-reprobe-regression.md](<176-reset-addresses-and-reprobe-regression.md>) | 176：复位地址刷新与10次声卡恢复回归 |
| [177-system-s2idle-and-post-resume-audio.md](<177-system-s2idle-and-post-resume-audio.md>) | 177：系统s2idle与恢复后左右声道验证 |
| [178-related-models-and-adsp-restart-failure.md](<178-related-models-and-adsp-restart-failure.md>) | 178：相关机型复查与ADSP重启断链失败 |
| [179-related-models-and-pdr-rx-lock-reproduction.md](<179-related-models-and-pdr-rx-lock-reproduction.md>) | 179：相关机型参考与 PDR/QMI 接收锁阻塞 |
| [180-pdr-peer-lifetime-and-irq-quiesce.md](<180-pdr-peer-lifetime-and-irq-quiesce.md>) | 180：PDR 世代/寿命修复及父中断退出 |
| [181-offline-irq-cleanup-and-adsp-recovery.md](<181-offline-irq-cleanup-and-adsp-recovery.md>) | 181：离线 IRQ 清理及受控 ADSP 恢复通过 |
| [182-active-capture-crash-recovery.md](<182-active-capture-crash-recovery.md>) | 182：活跃录音期间的一次合成 ADSP 崩溃报告恢复 |
| [183-offline-stream-and-active-crash-pm.md](<183-offline-stream-and-active-crash-pm.md>) | 183：修复离线 WCD 流清理并验证活跃播放恢复和两次 s2idle |
| [185-bluetooth-power-pulse-h4-repair-and-pm.md](<185-bluetooth-power-pulse-h4-repair-and-pm.md>) | 185：蓝牙功率脉冲解析修复、默认模块部署与PM |
| [186-slpi-lifecycle-native-failure-and-a11-reference.md](<186-slpi-lifecycle-native-failure-and-a11-reference.md>) | 186：SLPI停启故障、失败FastRPC原型与本机A.11参考 |
| [200-static-mmcx-boot-and-front-camera-regression.md](<200-static-mmcx-boot-and-front-camera-regression.md>) | 200：静态MMCX成对启动与前摄跨启动回归 |
| [201-gnss-utc-validity-and-geoclue-assistance.md](<201-gnss-utc-validity-and-geoclue-assistance.md>) | 201：GPS绝对有效期、自动UTC补时与标准GeoClue接入 |
| [223-camera-capture-sof-control-snapshots.md](<223-camera-capture-sof-control-snapshots.md>) | 223：SOF捕获号与控制快照配套部署 |
| [224-camera-raw-statistics-and-stop-cancellation.md](<224-camera-raw-statistics-and-stop-cancellation.md>) | 224：相机RAW统计与停止取消修复 |
| [225-camera-standard-exposure-controls.md](<225-camera-standard-exposure-controls.md>) | 225：前摄标准曝光与增益控制 |
| [226-gnss-raw-reception-and-aiding.md](<226-gnss-raw-reception-and-aiding.md>) | 226：GNSS原始测量与辅助对照 |
| [227-fastrpc-publication-and-module-owner.md](<227-fastrpc-publication-and-module-owner.md>) | 227：FastRPC完整发布与模块保活候选 |
| [228-fastrpc-native-module-pinning.md](<228-fastrpc-native-module-pinning.md>) | 228：FastRPC新启动、保活与五路传感器实测 |
| [229-daylight-front-camera-colour.md](<229-daylight-front-camera-colour.md>) | 229：白天前摄真实颜色统计 |
| [230-clean-intree-fastrpc-and-native-sensors.md](<230-clean-intree-fastrpc-and-native-sensors.md>) | 230 树内FastRPC真实加载与传感器验收 |
| [231-gnss-rfs-stock-layout-audit.md](<231-gnss-rfs-stock-layout-audit.md>) | 231：GNSS RFS 原厂布局和文件服务审计 |
| [232-rear-pmic-reset-and-address-candidate.md](<232-rear-pmic-reset-and-address-candidate.md>) | 232：后摄 PM8008 复位/地址依赖候选 |
| [233-pmic-native-deployment-and-managed-cycles.md](<233-pmic-native-deployment-and-managed-cycles.md>) | 233：后摄 PM8008 依赖部署与原生循环 |
| [234-bt-rx-state-and-uart-artifact-evidence.md](<234-bt-rx-state-and-uart-artifact-evidence.md>) | 234 蓝牙帧状态诊断与串口产物核对 |
| [235-imx319-of-runtime-and-isolated-p-power.md](<235-imx319-of-runtime-and-isolated-p-power.md>) | 235 IMX319真实驱动与独立P两路供电候选 |
| [236-imx319-real-id-and-live-of-fix.md](<236-imx319-real-id-and-live-of-fix.md>) | 236 后摄真实ID与live OF属性修正 |
| [237-imx319-first-raw-and-camss-unwind.md](<237-imx319-first-raw-and-camss-unwind.md>) | 237 IMX319首批RAW与CAMSS失败回收 |
| [238-imx319-control-and-related-linux-solutions.md](<238-imx319-control-and-related-linux-solutions.md>) | 238：IMX319控制链与近机型Linux方案 |
| [239-softisp-startup-and-linux-camera-gnss-research.md](<239-softisp-startup-and-linux-camera-gnss-research.md>) | 239：软件 ISP 首参修复与 Linux 摄像头/GNSS 搜索 |
| [283-vfe175-wb-parameters-and-startup-queue.md](<283-vfe175-wb-parameters-and-startup-queue.md>) | 283：VFE175白平衡参数与首帧队列 |
| [284-vfe175-demosaic-and-coherent-kernel.md](<284-vfe175-demosaic-and-coherent-kernel.md>) | 284：VFE175 Demosaic36与完整内核模块 |
| [285-vfe175-cst-colorimetry.md](<285-vfe175-cst-colorimetry.md>) | 285：VFE175 CST12与色彩范围 |
| [286-vfe175-gamma-and-output-depth.md](<286-vfe175-gamma-and-output-depth.md>) | 286：VFE175 Gamma16与FULL输出位深 |
| [287-vfe175-demux-mnds-and-layering.md](<287-vfe175-demux-mnds-and-layering.md>) | 287：原厂依据与VFE175 Demux/MNDS16 |
| [288-coherent-kernel-full-nv12-transport.md](<288-coherent-kernel-full-nv12-transport.md>) | 288：统一内核部署与硬件FULL NV12传输 |
| [289-tpg-phy-history-gamma-sram-clock.md](<289-tpg-phy-history-gamma-sram-clock.md>) | 289：TPG PHY历史隔离与Gamma SRAM时钟 |
| [290-vfe175-full-route-and-standard-tpg.md](<290-vfe175-full-route-and-standard-tpg.md>) | 290：原厂FULL路径修复、完整部署与标准硬件TPG验收 |
| [291-two-sensor-physical-full-color-validation.md](<291-two-sensor-physical-full-color-validation.md>) | 291：两颗传感器真实CSI硬件FULL与独立RAW色彩对照 |
| [293-vfe175-standard-white-balance-and-full-regression.md](<293-vfe175-standard-white-balance-and-full-regression.md>) | 293：VFE175标准白平衡参数及FULL回归修复 |
| [294-vfe175-metadata-lifetime-and-zero-histogram.md](<294-vfe175-metadata-lifetime-and-zero-histogram.md>) | 294：VFE175 metadata 生命周期与零直方图失败 |
| [295-vfe175-bhist-counts-and-startup-validity.md](<295-vfe175-bhist-counts-and-startup-validity.md>) | 295：VFE175有效BHIST计数与首包有效性缺陷 |
| [296-vfe175-bhist-sram-initialization.md](<296-vfe175-bhist-sram-initialization.md>) | 296：VFE175统计SRAM初始化与首包修复 |
| [297-shared-sof-statistics-frame-identity.md](<297-shared-sof-statistics-frame-identity.md>) | 297：共享SOF帧号与统计断粮恢复 |
| [298-black-level-mapping-and-hardware-scene.md](<298-black-level-mapping-and-hardware-scene.md>) | 298：黑电平映射与暗绿硬件对照 |
| [299-factory-bls-eeprom-and-inline-libcamera.md](<299-factory-bls-eeprom-and-inline-libcamera.md>) | 299：原厂BLS、本机EEPROM与在线libcamera候选 |
| [300-hardware-ipa-and-lifecycle.md](<300-hardware-ipa-and-lifecycle.md>) | 300：标准硬件IPA与生命周期收敛 |
| [301-imx319-control-response-timing.md](<301-imx319-control-response-timing.md>) | 301：IMX319控制响应时序 |
| [302-sensor-controls-and-effective-sof-context.md](<302-sensor-controls-and-effective-sof-context.md>) | 302：硬件IPA传感器控制与有效SOF上下文 |
| [303-hardware-ae-candidate-and-joint-latch-preparation.md](<303-hardware-ae-candidate-and-joint-latch-preparation.md>) | 303：硬件AE与联合控制的实机验证 |
| [304-original-eeprom-wb-lsc-and-xml-misalignment.md](<304-original-eeprom-wb-lsc-and-xml-misalignment.md>) | 304：原厂EEPROM WB／LSC与旧XML错位核查 |
| [305-s5k3m5-selection-geometry-and-four-camera-regression.md](<305-s5k3m5-selection-geometry-and-four-camera-regression.md>) | 305：长焦标准几何与四摄回归 |
| [306-s5k3m5-factory-bls-timing-and-hardware-ae.md](<306-s5k3m5-factory-bls-timing-and-hardware-ae.md>) | 306：长焦原厂BLS、时序与硬件AE |
| [2026-10-06-diagvendor-capture.md](<2026-10-06-diagvendor-capture.md>) | 诊断镜像 boot-samurai-diagvendor —— 抓原厂按键驱动失败原因 |
| [2026-10-06-eud-first-test.md](<2026-10-06-eud-first-test.md>) | EUD 试水结果 + 会话交接（2026-10-06 16:5x） |
| [2026-10-14-categorized-publication.md](<2026-10-14-categorized-publication.md>) | 2026-10-14 代码与资料分类提交 |
| [2026-10-14-documentation-maintenance.md](<2026-10-14-documentation-maintenance.md>) | 2026-10-14 文档维护 |
| [display-handoff-152-165.md](<display-handoff-152-165.md>) | 显示交接修复过程：152—165 |
| [maintenance-2026-10-19.md](<maintenance-2026-10-19.md>) | 2026-10-19：暂停交接与主机编译产物清理 |

## Reference目录

部分阶段只保存了reference记录，可直接从这里阅读；不要求再复制一份会话正文。

| 目录 | 原文标题 |
| --- | --- |
| [kernel66](<../reference/kernel66/README.md>) | kernel66 校验与修复证据 |
| [kernel67](<../reference/kernel67/README.md>) | Kernel 67 evidence: USB provider restored; CPU7 DTB candidate not active |
| [kernel68](<../reference/kernel68/README.md>) | Kernel68: actual firmware DTB and CPU7 OPP |
| [kernel69](<../reference/kernel69/README.md>) | kernel69：USB 功能前提和 EUD 共存边界 |
| [kernel70](<../reference/kernel70/README.md>) | kernel70：资源缺失影响范围与原生硬件前提 |
| [kernel71](<../reference/kernel71/README.md>) | Session71：原生S3706触摸实现及真机验收证据 |
| [kernel72](<../reference/kernel72/README.md>) | Session72：普通USB NCM与自动SSH证据 |
| [kernel73](<../reference/kernel73/README.md>) | kernel73：本机SOFEF03F原生DSI/DSC显示证据 |
| [kernel74](<../reference/kernel74/README.md>) | kernel74：本机DPU5显示接管证据 |
| [kernel75](<../reference/kernel75/README.md>) | kernel75：主线 A640 渲染与 SOFEF03F 花屏实测 |
| [kernel76](<../reference/kernel76/README.md>) | kernel76：充电来源与安全审查（只读研究） |
| [kernel77](<../reference/kernel77/README.md>) | kernel77：BQ28Z610 真实读取与显示启动回归 |
| [kernel78](<../reference/kernel78/README.md>) | kernel78：相同镜像首次启动对照与无开关屏页面翻转 |
| [kernel79](<../reference/kernel79/README.md>) | kernel79 证据 |
| [kernel80](<../reference/kernel80/README.md>) | kernel80 证据 |
| [kernel81](<../reference/kernel81/README.md>) | kernel81 证据 |
| [kernel82](<../reference/kernel82/README.md>) | Session82 evidence |
| [kernel83](<../reference/kernel83/README.md>) | Session83 source evidence |
| [kernel84](<../reference/kernel84/README.md>) | Session84 display diagnostic evidence |
| [kernel85](<../reference/kernel85/README.md>) | kernel85: fixed OEM chemistry and short-IC observations |
| [kernel86](<../reference/kernel86/README.md>) | kernel86: MP2650 observations and a real display timeout snapshot |
| [kernel87](<../reference/kernel87/README.md>) | kernel87：阶段收尾、未部署的显示候选与 Wi-Fi 依赖 |
| [kernel88](<../reference/kernel88/README.md>) | kernel88：Wi-Fi构建与部署前交接 |
| [kernel91](<../reference/kernel91/README.md>) | kernel91：Wi-Fi RAM服务与连接验证 |
| [kernel92](<../reference/kernel92/README.md>) | Session92：连接驱动与真机验证 |
| [kernel93](<../reference/kernel93/README.md>) | Session93：真实固件名、启动隔离与共存 |
| [kernel94](<../reference/kernel94/README.md>) | kernel94：蓝牙模块启动顺序对照（Linux #93） |
| [kernel95](<../reference/kernel95/README.md>) | kernel95：正确路径的蓝牙自动加载（Linux #94） |
| [kernel96](<../reference/kernel96/README.md>) | 阶段96：Wi-Fi解绑权限回收、蓝牙生命周期与本机地址 |
| [kernel97](<../reference/kernel97/README.md>) | 阶段97：自动本机地址供应与双频启动回归 |
| [kernel98](<../reference/kernel98/README.md>) | 阶段98：独立地址供应与删除等待/脉冲诊断 |
| [kernel99](<../reference/kernel99/README.md>) | 阶段99：AW8697 原生振动 |
| [kernel100](<../reference/kernel100/README.md>) | 阶段100：无线 UFS 全源就绪等待 |
| [kernel101](<../reference/kernel101/README.md>) | kernel101：ADSP原生版本回复与无线基线 |
| [kernel102](<../reference/kernel102/README.md>) | kernel102：WCD934x与实际MAX98937识别 |
| [kernel103](<../reference/kernel103/README.md>) | kernel103：正确MAX98937/原生声卡与PCM回归 |
| [kernel104](<../reference/kernel104/README.md>) | 阶段104：三个数字麦克风原生采样 |
| [kernel105](<../reference/kernel105/README.md>) | 阶段105：APR登记与首次MPSS诊断 |
| [kernel106](<../reference/kernel106/README.md>) | 阶段106：HELLO/公告竞态与音频完成后trace |
| [kernel107](<../reference/kernel107/README.md>) | 阶段107：HELLO先应答，再公告服务 |
| [kernel108](<../reference/kernel108/README.md>) | kernel108：显示故障取证与下一会话交接 |
| [kernel147](<../reference/kernel147/README.md>) | A640 GMEM 迟发 fault 修复验证 |
| [kernel148](<../reference/kernel148/README.md>) | 阶段148：Vulkan VM_BIND 调试 |
| [kernel149](<../reference/kernel149/README.md>) | 阶段149：A640 Vulkan CCU 修复与实机部署 |
| [kernel150](<../reference/kernel150/README.md>) | A640 GPU 无 Mesa 本地补丁方案研究 |
| [kernel151](<../reference/kernel151/README.md>) | GPU 阶段收尾证据 |
| [kernel152](<../reference/kernel152/README.md>) | 阶段152：DSI竞态候选、启动接管复现及已验证回退 |
| [kernel153](<../reference/kernel153/README.md>) | 153：面板 GPIO 接管候选与首次启动欠载 |
| [kernel154](<../reference/kernel154/README.md>) | 154：DSI首次初始化候选未修复，标准DPMS恢复桌面 |
| [kernel155](<../reference/kernel155/README.md>) | 155：同一 #154 镜像的正常启动对照 |
| [kernel156](<../reference/kernel156/README.md>) | 156：首帧背光策略实机执行，首次 DSI 欠载仍待修复 |
| [kernel157](<../reference/kernel157/README.md>) | 157：首次 PHY 重配前停止固件 DSI 控制器 |
| [kernel158](<../reference/kernel158/README.md>) | 158：在 DPU 清理固件 CTL 之前停止 DSI |
| [kernel159](<../reference/kernel159/README.md>) | 159：同一 #158 镜像的第二次启动验收 |
| [kernel160](<../reference/kernel160/README.md>) | 160：同一 #158 第三次启动，早期白屏仍未验收 |
| [kernel161](<../reference/kernel161/README.md>) | 161：空 RMR 列表不再关闭 SMMU 客户端的候选 |
| [kernel162](<../reference/kernel162/README.md>) | 162：拒收161后回退原版158 |
| [kernel163](<../reference/kernel163/README.md>) | 163：在早期显示初始化期间保持面板复位 |
| [kernel164](<../reference/kernel164/README.md>) | 164：UEFI BeforeExitBootServices 面板复位候选 |
| [kernel165](<../reference/kernel165/README.md>) | 165：同一 boot164/kernel163 第二次启动软件验收 |
| [kernel166](<../reference/kernel166/README.md>) | 166：音频 PM/DMA 错误回收候选，实机拒收 |
| [kernel167](<../reference/kernel167/README.md>) | 167：拒收166后回退kernel163 |
| [kernel168](<../reference/kernel168/README.md>) | 168：SLIMbus服务生命周期与原生音频恢复 |
| [kernel169](<../reference/kernel169/README.md>) | 169：同一kernel168第二次启动与停止回归 |
| [kernel170](<../reference/kernel170/README.md>) | 170：麦克风检测扬声器编码测试音，未检出可信信号 |
| [kernel171](<../reference/kernel171/README.md>) | 171：参考 OnePlus/Realme 原厂链路，修正扬声器 SD1 并检出编码音 |
| [kernel172](<../reference/kernel172/README.md>) | 172：绑定 WCD934x 耳机检测，修正偏置电压和状态错误 |
| [kernel173](<../reference/kernel173/README.md>) | 173：部署耳机 UCM 路由，验证桌面播放与录音 |
| [kernel174](<../reference/kernel174/README.md>) | 174：SLIM 端口中断停流、暂停回归与声卡重探测缺陷 |
| [kernel175](<../reference/kernel175/README.md>) | 175：jack、regmap、MCLK 生命周期修复与父设备复位超时 |
| [kernel176](<../reference/kernel176/README.md>) | 176：WCD934x 复位后地址刷新与重复绑定回归 |
| [kernel177](<../reference/kernel177/README.md>) | 177：kernel176 的系统 s2idle 与恢复后音频验证 |
| [kernel178](<../reference/kernel178/README.md>) | 178：相关机型复查与 ADSP 重启断链错误 |
| [kernel179](<../reference/kernel179/README.md>) | 179：相关机型复核与 PDR 接收锁阻塞重现 |
| [kernel180](<../reference/kernel180/README.md>) | 180：PDR 世代与释放修复、父中断退出及剩余离线写错误 |
| [kernel181](<../reference/kernel181/README.md>) | 181：离线 IRQ 清理修复与 ADSP 停启、左右声学验证 |
| [kernel182](<../reference/kernel182/README.md>) | 182：活跃桌面录音中的单次 ADSP 自动恢复 |
| [kernel183](<../reference/kernel183/README.md>) | 183：离线流清理修复、活跃播放恢复及当前内核两次 s2idle |
| [kernel184](<../reference/kernel184/README.md>) | 184：外设适配继续推进 |
| [kernel185](<../reference/kernel185/README.md>) | 185：蓝牙功率脉冲与H4边界修复及实机部署 |
| [kernel186](<../reference/kernel186/README.md>) | 186：SLPI停启、FastRPC共享池故障与本机A.11固件 |
| [kernel187](<../reference/kernel187/README.md>) | 187：本机A.11 SLPI惯性流与标准客户端实测 |
| [kernel188](<../reference/kernel188/README.md>) | 188：自动SSC服务、桌面访问通过与休眠崩溃回退 |
| [kernel189](<../reference/kernel189/README.md>) | 189：FastRPC冻结等待修复与连续三轮传感器休眠恢复 |
| [kernel190](<../reference/kernel190/README.md>) | 阶段190：修复GNSS辅助能力发现的提前indication竞态 |
| [kernel191](<../reference/kernel191/README.md>) | 阶段191：完整XTRA辅助注入与LOC异步生命周期修复 |
| [kernel192](<../reference/kernel192/README.md>) | 阶段192：两颗PM8008真机识别与原厂相机供电序列解码 |
| [kernel193](<../reference/kernel193/README.md>) | 阶段193：前摄IMX471实体识别与CCI/MCLK电源域验证 |
| [kernel194](<../reference/kernel194/README.md>) | 阶段194：IMX471 OF接入候选与PM8008复位地址初始化 |
| [kernel195](<../reference/kernel195/README.md>) | 阶段195：PM8008失败复位回退与前摄VIO精确OF引用 |
| [kernel196](<../reference/kernel196/README.md>) | 阶段196：普通IMX471实体probe、OF媒体端点与运行时供电 |
| [kernel197](<../reference/kernel197/README.md>) | 阶段197：修复CAMSS端点校验，建立实体前摄媒体链路 |
| [kernel198](<../reference/kernel198/README.md>) | 阶段198：前摄首次实体RAW取帧，定位高频运行问题 |
| [kernel199](<../reference/kernel199/README.md>) | 阶段199：CAMSS运行时MMCX性能请求，恢复正常频率实体取帧 |
| [kernel200](<../reference/kernel200/README.md>) | 阶段200：静态MMCX设备树与CAMSS成对启动，前摄跨启动取流 |
| [kernel201](<../reference/kernel201/README.md>) | 阶段201：GPS辅助数据有效期、自动UTC补时与GeoClue接入 |
| [kernel202](<../reference/kernel202/README.md>) | 阶段202：GPS首会话UTC准备与真实自动辅助数据恢复 |
| [kernel203](<../reference/kernel203/README.md>) | 203：GNSS/MM 签名软件包落地与相关机型对照 |
| [kernel204](<../reference/kernel204/README.md>) | 204：补齐蓝牙 UART RX 唤醒与休眠引脚 |
| [kernel206](<../reference/kernel206/README.md>) | 206：修复 modem 工作文件服务，继续 GNSS 实测 |
| [kernel207](<../reference/kernel207/README.md>) | 207：补齐本机原厂 MCFG 文件服务与 TFTP 块号回绕 |
| [kernel208](<../reference/kernel208/README.md>) | 208：取得原厂 GNSS 接收器诊断，核对时间、ADC 与 XTRA |
| [kernel209](<../reference/kernel209/README.md>) | 209：UTC 精度单变量对照未改善接收器报告，核对常态相机缺口 |
| [kernel210](<../reference/kernel210/README.md>) | 210：前摄接入正常设备树并自动绑定，真实 RAW 取流通过 |
| [kernel211](<../reference/kernel211/README.md>) | 211：前摄裁剪、独立供电域与用户态取流 |
| [kernel212](<../reference/kernel212/README.md>) | 212：同一boot镜像第二次启动与默认CPU ISP |
| [kernel213](<../reference/kernel213/README.md>) | 213：暗场与首帧全黑的区分，IMX471用户态候选 |
| [kernel214](<../reference/kernel214/README.md>) | 214：完整相机包已部署，默认客户端通过 |
| [kernel215](<../reference/kernel215/README.md>) | 215：IMX471 内部测试图寄存器位宽修复并实测 |
| [kernel216](<../reference/kernel216/README.md>) | 216：补齐 IMX471 原厂模拟增益范围并验证 RAW 响应 |
| [kernel217](<../reference/kernel217/README.md>) | 217：原厂三模式验证、完整分辨率候选与时序差异 |
| [kernel218](<../reference/kernel218/README.md>) | 阶段218：原生尺寸Quad Bayer CPU候选 |
| [kernel219](<../reference/kernel219/README.md>) | 阶段219：原厂模式实机取流与时序修复 |
| [kernel220](<../reference/kernel220/README.md>) | 220：切换模式后的曝光元数据 |
| [kernel221](<../reference/kernel221/README.md>) | 221：GNSS星座配置与卫星黑名单只读核对 |
| [kernel222](<../reference/kernel222/README.md>) | 222：请求间断错配复现与SM8150帧同步候选 |
| [kernel223](<../reference/kernel223/README.md>) | 223：捕获帧与控制快照配对已部署 |
| [kernel224](<../reference/kernel224/README.md>) | 224：RAW自动统计、曝光元数据与停止清理已部署 |
| [kernel225](<../reference/kernel225/README.md>) | 225：标准曝光与增益控制已部署 |
| [kernel226](<../reference/kernel226/README.md>) | 226：GNSS原始测量与辅助数据四轮对照已完成 |
| [kernel227](<../reference/kernel227/README.md>) | 227：FastRPC 发布、回调对象及模块引用候选 |
| [kernel228](<../reference/kernel228/README.md>) | 228：FastRPC手机实测通过，树内产物待新启动验收 |
| [kernel229](<../reference/kernel229/README.md>) | 229：白天前摄真实颜色信息已确认 |
| [kernel230](<../reference/kernel230/README.md>) | 230：树内FastRPC新启动与真实传感器验收通过 |
| [kernel231](<../reference/kernel231/README.md>) | 231：GNSS 文件服务与原厂 RFS 布局核查 |
| [kernel232](<../reference/kernel232/README.md>) | 232：后摄 PM8008 复位和依赖候选已构建 |
| [kernel233](<../reference/kernel233/README.md>) | 233：后摄 PM8008 依赖已部署并完成原生暖/冷循环 |
| [kernel234](<../reference/kernel234/README.md>) | 234：蓝牙帧状态诊断与真实串口产物核对 |
| [kernel235](<../reference/kernel235/README.md>) | 235：IMX319 真实驱动、独立 P 两路供电候选与磁盘暂存 |
| [kernel236](<../reference/kernel236/README.md>) | 236：后摄候选实际部署、live OF 修正与 IMX319 实际 ID |
| [kernel237](<../reference/kernel237/README.md>) | 237：IMX319 首批真实 RAW 与 CAMSS 失败回收修正 |
| [kernel238](<../reference/kernel238/README.md>) | 238：IMX319 增益换算、48帧控制与同平台方案核对 |
| [kernel239](<../reference/kernel239/README.md>) | 239：实际 ISP 首参修复、r15 默认部署与近机型核对 |
| [kernel240](<../reference/kernel240/README.md>) | 240：相机应用故障、Snapshot CPU 预览与后摄统计 |
| [kernel241](<../reference/kernel241/README.md>) | 241：本机 GNSS HAL 初始化与 Linux QMI 差异 |
| [kernel242](<../reference/kernel242/README.md>) | 242：ROM 对照、modem 文件一致性与 GNSS 时钟关联采集 |
| [kernel243](<../reference/kernel243/README.md>) | 243：开窗接收复测、active MCFG 与 DIAG 传输诊断 |
| [kernel244](<../reference/kernel244/README.md>) | 244：Linux 首次启动 DIAG 握手与真实 GNSS 测量 |
| [kernel245](<../reference/kernel245/README.md>) | 245：GPS锁对照、DIAG重连边界与MEMSHARE实测 |
| [kernel246](<../reference/kernel246/README.md>) | 246：真实RF/时钟日志与modem原始零C/No |
| [kernel247](<../reference/kernel247/README.md>) | 247：启动期MEMSHARE真实请求与OEM配置差异 |
| [kernel248](<../reference/kernel248/README.md>) | 248：保存当前Linux并验证PC恢复 |
| [kernel249](<../reference/kernel249/README.md>) | 249：用户态仓库整合、独立复现与上游维护 |
| [kernel250](<../reference/kernel250/README.md>) | 250：Android 实际 GNSS HAL 初始化与室外正信号 |
| [kernel251](<../reference/kernel251/README.md>) | 251：原厂 realme UI 2.0 室内 GNSS 与 Linux 对照 |
| [kernel252](<../reference/kernel252/README.md>) | 252：原厂室内 SBAS 跟踪、基带零测量与 Linux 对照 |
| [kernel253](<../reference/kernel253/README.md>) | 253：原厂GPS弱信号、UTC实注与射频/初始化对照 |
| [kernel254](<../reference/kernel254/README.md>) | 254：GPS SEARCH 的新鲜度与原厂初始化实测 |
| [kernel255](<../reference/kernel255/README.md>) | 255：PGA来源、外部频率估计与XO初始化核对 |
| [kernel256](<../reference/kernel256/README.md>) | 256：原厂室外无线调试取得持续GNSS定位 |
| [kernel257](<../reference/kernel257/README.md>) | 257：从原厂F.16返回Linux，恢复完整系统并验证无线SSH |
| [kernel258](<../reference/kernel258/README.md>) | 258：Linux室外无线GNSS持续定位，完成原厂对照 |
| [kernel259](<../reference/kernel259/README.md>) | 259：GeoClue 定位生命周期修复与室外复测 |
| [kernel260](<../reference/kernel260/README.md>) | 260：桌面 GNSS 定位通过与无 SIM 电源管理 |
| [kernel261](<../reference/kernel261/README.md>) | 261：中文、应用商店与屏幕键盘检查 |
| [kernel262](<../reference/kernel262/README.md>) | 262：前摄保存 JPEG、缓冲持有复现与 CPU 复制路径 |
| [kernel263](<../reference/kernel263/README.md>) | 263：公共相机缓冲生命周期，正常取流进展与断连竞态 |
| [kernel264](<../reference/kernel264/README.md>) | 264：公共相机缓冲生命周期修复、原生包部署及实际快门 |
| [kernel265](<../reference/kernel265/README.md>) | 265 公共相机缓冲退役修复与系统部署 |
| [kernel266](<../reference/kernel266/README.md>) | 266：相机架构复核与标准元数据候选 |
| [kernel267](<../reference/kernel267/README.md>) | 267：公共 PM8008 供电、标准 IMX319 与新设备树实机启动 |
| [kernel268](<../reference/kernel268/README.md>) | 268：公共相机切换修复与前后摄应用实测 |
| [kernel269](<../reference/kernel269/README.md>) | 269：内核维护收敛、板级旋转修复与收尾 |
| [kernel270](<../reference/kernel270/README.md>) | 270：恢复相机实测与第二颗后摄适配（进行中） |
| [kernel271](<../reference/kernel271/README.md>) | 271：长焦原生细分增益、配套部署与自动曝光实测 |
| [kernel272](<../reference/kernel272/README.md>) | 272：GW1 主摄标准驱动候选、板级描述与离线验证 |
| [kernel273](<../reference/kernel273/README.md>) | 273：GW1 主摄实机接入、四摄取流与未完成项 |
| [kernel274](<../reference/kernel274/README.md>) | 274：主摄镜头光学响应、标准镜头驱动候选与 ISP 分层 |
| [kernel275](<../reference/kernel275/README.md>) | 275：标准镜头与 libcamera 生命周期部署，定位共享 I/O 依赖 |
| [kernel276](<../reference/kernel276/README.md>) | 276：公共 CCI 供电收敛、标准手动对焦和多摄回归 |
| [kernel277](<../reference/kernel277/README.md>) | 277：RAW 空间清晰度统计与标准 FocusFoM 实机部署 |
| [kernel278](<../reference/kernel278/README.md>) | 278：标准单次自动对焦、不可变帧统计与镜头回执 |
| [kernel279](<../reference/kernel279/README.md>) | 279：优先复用现有方案的 CAMSS ISP 源码候选 |
| [kernel280](<../reference/kernel280/README.md>) | 280：纠正 ISP 型号依据，补 CSID175 像素输入路径 |
| [kernel281](<../reference/kernel281/README.md>) | 281：原厂 HAL 静态依据与 VFE175 CAMIF 候选 |
| [kernel282](<../reference/kernel282/README.md>) | 282：复用多流修复，补 VFE175 FULL 双平面输出 |
| [kernel283](<../reference/kernel283/README.md>) | 283：VFE175 白平衡参数后端与首帧参数队列 |
| [kernel284](<../reference/kernel284/README.md>) | 284：匹配 Demosaic36，完成候选内核与模块链接 |
| [kernel285](<../reference/kernel285/README.md>) | 285：VFE175 CST12色彩转换后端 |
| [kernel286](<../reference/kernel286/README.md>) | 286：VFE175 FULL位深转换与Gamma16后端 |
| [kernel287](<../reference/kernel287/README.md>) | 287：原厂依据、VFE175 Demux与MNDS16后端 |
| [kernel288](<../reference/kernel288/README.md>) | 288：统一内核部署与首个硬件FULL NV12链路 |
| [kernel289](<../reference/kernel289/README.md>) | 289：内部TPG历史隔离与Gamma SRAM时钟修复 |
| [kernel290](<../reference/kernel290/README.md>) | 290：原厂FULL后处理协议、公共驱动修复及完整部署 |
| [kernel291](<../reference/kernel291/README.md>) | 291：两颗实体传感器接入硬件FULL及独立RAW色彩对照 |
| [kernel292](<../reference/kernel292/README.md>) | 292：VFE175 参数节点、稀疏 pad 与真实部署后的 FULL 回归 |
| [kernel293](<../reference/kernel293/README.md>) | 293：VFE175 标准白平衡参数实机闭环与 FULL 回归修复 |
| [kernel294](<../reference/kernel294/README.md>) | 294：VFE175 统计通路和 metadata 生命周期 |
| [kernel295](<../reference/kernel295/README.md>) | 295：VFE175 BHIST 有效计数、实景曝光响应与首包缺陷 |
| [kernel296](<../reference/kernel296/README.md>) | 296：VFE175 统计 SRAM 初始化与首包修复 |
| [kernel297](<../reference/kernel297/README.md>) | 297：图像／统计共享 SOF 帧号与断粮恢复 |
| [kernel298](<../reference/kernel298/README.md>) | 298：公共黑电平映射与暗绿硬件对照 |
| [kernel299](<../reference/kernel299/README.md>) | 299：原厂 BLS、本机 EEPROM 与 libcamera 在线候选 |
| [kernel300](<../reference/kernel300/README.md>) | 300：CAMSS 硬件 IPA 模块与生命周期收敛 |
| [kernel301](<../reference/kernel301/README.md>) | 301：IMX319 曝光／增益与硬件统计时序 |
| [kernel302](<../reference/kernel302/README.md>) | 302：硬件 IPA 的曝光／增益控制与有效帧上下文 |
| [kernel303](<../reference/kernel303/README.md>) | 303：硬件 AE 候选与联合锁存验收准备 |
| [kernel304](<../reference/kernel304/README.md>) | 304：原厂 EEPROM 的 WB／LSC 类型表与旧 XML 错位核查 |
| [kernel305](<../reference/kernel305/README.md>) | 305：S5K3M5 几何接口修复与四摄回归 |
| [kernel306](<../reference/kernel306/README.md>) | 306：长焦原厂黑电平、控制时序与硬件 AE |
| [kernel307](<../reference/kernel307/README.md>) | 307：VFE175硬件RGB网格统计 |
| [kernel308](<../reference/kernel308/README.md>) | 308：硬件RGB IPA与两摄AWB回写 |
| [kernel309](<../reference/kernel309/README.md>) | 309：四摄硬件AWB与CSI接收时钟修复 |
| [kernel310](<../reference/kernel310/README.md>) | 310：主前摄控制时序与四摄联合AE/AWB |
| [kernel311](<../reference/kernel311/README.md>) | 311：运行中AWB开关和手动白平衡请求 |
| [kernel312](<../reference/kernel312/README.md>) | 312：六模式选择、默认3A和图像缓冲恢复 |
| [kernel313](<../reference/kernel313/README.md>) | 313：硬件处理流复用单次自动对焦 |
| [kernel314](<../reference/kernel314/README.md>) | 314：公共 CAMSS 共享流与 RAW／PIX 并行 |
| [kernel315](<../reference/kernel315/README.md>) | 315：libcamera RAW 与硬件处理流接入 |
| [kernel316](<../reference/kernel316/README.md>) | 316：默认硬件ISP与产品消费者接入 |
| [kernel317](<../reference/kernel317/README.md>) | 317：原厂镜头阴影表、校准合成与硬件编码 |
| [kernel318](<../reference/kernel318/README.md>) | 318：VFE175 镜头阴影网格已验证并部署 |
| [kernel319](<../reference/kernel319/README.md>) | 319：用户空间LSC网格重采样 |
| [kernel320](<../reference/kernel320/README.md>) | 320：修正本机原厂LSC数据分组，四个零节点已消失 |
| [kernel321](<../reference/kernel321/README.md>) | 321：LSC用户空间闭环与r26正式包 |
| [kernel322](<../reference/kernel322/README.md>) | 322：原厂触发选择与广角真实个体LSC试验 |
| [kernel323](<../reference/kernel323/README.md>) | 323：长焦原厂LSC、模式映射与实际取流 |
| [kernel324](<../reference/kernel324/README.md>) | 324：主摄/前摄原厂LSC与前摄两模式实机 |
| [kernel325](<../reference/kernel325/README.md>) | 325：GW1标准测试图案与主摄两模式LSC |
| [kernel326](<../reference/kernel326/README.md>) | 326：其余三摄个体数据读取与独立解码 |
| [kernel327](<../reference/kernel327/README.md>) | 327：四摄个体 LSC 链路补齐 |
| [kernel328](<../reference/kernel328/README.md>) | 328：四摄 WB 标定来源与原厂算法路径 |
| [kernel329](<../reference/kernel329/README.md>) | 329：通用 WB 校准与 CCT 查表数学 |
| [kernel330](<../reference/kernel330/README.md>) | 330：可选个体白平衡与运行中色温控制 |
| [kernel331](<../reference/kernel331/README.md>) | 331：个体校准参考点与反向色温数学 |
| [kernel332](<../reference/kernel332/README.md>) | 332：个体参考点驱动的逐帧色温估计 |
| [kernel333](<../reference/kernel333/README.md>) | 333：原厂CCM完整数据与通用插值/编码 |
| [kernel334](<../reference/kernel334/README.md>) | 334：VFE175硬件颜色矩阵后端实测 |
| [kernel335](<../reference/kernel335/README.md>) | 335：色温、白平衡与硬件色彩矩阵联动 |
| [kernel336](<../reference/kernel336/README.md>) | 336：原厂曝光索引与lux触发语义 |
| [kernel337](<../reference/kernel337/README.md>) | 337：Bayer统计到原厂lux亮度的普通RGB路径 |
| [kernel338](<../reference/kernel338/README.md>) | 338：部署兼容原厂亮度链的 CAMSS 统计网格 |
| [kernel339](<../reference/kernel339/README.md>) | 339：每帧 Bayer 亮度与 lux index 接入候选 IPA |
| [kernel340](<../reference/kernel340/README.md>) | 340：实时 AEC/CCT 联动 CCM |
| [kernel341](<../reference/kernel341/README.md>) | 341：动态 LSC、个体校准与统一 ISP revision |
| [kernel342](<../reference/kernel342/README.md>) | 342：r27/r22 正式包与本机主摄方案对应 |
| [kernel343](<../reference/kernel343/README.md>) | 343：原厂模式树与普通取流曝光表选择 |
| [kernel344](<../reference/kernel344/README.md>) | 344：本机私有校准成为默认配置 |
| [kernel345](<../reference/kernel345/README.md>) | 345：原厂曝光分配与帧时长 knee 数学 |
| [kernel346](<../reference/kernel346/README.md>) | 346：原厂 EV／FPS 动态曝光表 |
| [kernel347](<../reference/kernel347/README.md>) | 347：从原厂调校包提取完整 IFE Gamma |
| [kernel348](<../reference/kernel348/README.md>) | 348：原厂 Gamma 已经由 VFE175 硬件生效 |
| [kernel349](<../reference/kernel349/README.md>) | 349：原厂 IFE Gamma 接入 IPA 并完成组合实测 |
| [kernel350](<../reference/kernel350/README.md>) | 350：完整提取原厂 IPE Gamma，复现原 HAL 插值与编码 |
| [kernel351](<../reference/kernel351/README.md>) | 351：恢复原厂 LTM、后级矩阵及逆 Gamma 默认开关 |
| [kernel352](<../reference/kernel352/README.md>) | 352：移植 LTM 逆 Gamma，取得原厂 ICP 固件并核实队列 ABI |
| [kernel353](<../reference/kernel353/README.md>) | 353：实现并构建 A5 ICP 队列和 ELF 内核核心 |
| [kernel354](<../reference/kernel354/README.md>) | 354：ICP DMA 别名映射后端及真实 SMMU 探测通过 |
| [kernel355](<../reference/kernel355/README.md>) | 355：原厂 A5／BPS／IPE 资源顺序与真实上电验证 |
| [kernel356](<../reference/kernel356/README.md>) | 356：A5 固件启动后端与板级内存修正（尚未打通） |
| [kernel357](<../reference/kernel357/README.md>) | 357：公共 IOMMU 引用修正与停滞现场恢复记录 |
| [kernel358](<../reference/kernel358/README.md>) | 358：原厂防频闪曝光调整与模式参数绑定 |
| [kernel359](<../reference/kernel359/README.md>) | 359：原厂曝光程序接入实际 CAMSS IPA（主机候选） |
| [kernel360](<../reference/kernel360/README.md>) | 360：Gamma／曝光合并与 r28 软件包候选 |
| [kernel361](<../reference/kernel361/README.md>) | 361：请求链实测、公共分发器修复与交接 |
| [kernel362](<../reference/kernel362/README.md>) | 362：隔离 IPA 的提交所有权与公共请求顺序 |
| [kernel363](<../reference/kernel363/README.md>) | 363：统一内核已部署、四颗传感器回归和原厂 HFI 入口核对 |
| [kernel364](<../reference/kernel364/README.md>) | 364：精确 HFI ready 已应用，IOMMU 回收通过，固件引用故障定位 |
| [kernel365](<../reference/kernel365/README.md>) | 365：静态 ICP／板级固件内存引用，以及未生效的 FAT DT 更新 |
| [kernel366](<../reference/kernel366/README.md>) | 366：将静态 ICP 板级引用装入实际 EDK2 固件 DT |
| [kernel367](<../reference/kernel367/README.md>) | 367：A5 异常重启后的正常基线恢复 |
| [kernel368](<../reference/kernel368/README.md>) | 368：确认原厂响应 3 为 SFR 故障路径，修复错误诊断与 DMA 回收顺序 |
| [kernel369](<../reference/kernel369/README.md>) | 369：取得真实 A5 故障快照，错误仍未收敛；恢复相机基线 |
| [kernel370](<../reference/kernel370/README.md>) | 370：拆分 A5 停止与 DMA/PM 释放，准备受约束的故障窗口 |
| [kernel371](<../reference/kernel371/README.md>) | 371：持有模式仍在probe返回前重启，设备基线已恢复 |
| [kernel372](<../reference/kernel372/README.md>) | 372：取得复位前原厂异常现场，定位初始化失败的错误清理路径 |
| [kernel373](<../reference/kernel373/README.md>) | 373：A5就绪与SYS_INIT实机通过，probe退出阶段仍重启 |
| [kernel374](<../reference/kernel374/README.md>) | 374：绑定完成后原厂固件三项握手通过，停机阶段仍重启 |
| [kernel375](<../reference/kernel375/README.md>) | 375：原厂A5固件完整HFI生命周期实机通过 |
| [kernel376](<../reference/kernel376/README.md>) | 376：两个IPE固件会话并存、创建与销毁实机通过 |
| [kernel377](<../reference/kernel377/README.md>) | 377：还原目标 IPE CONFIG_IO ABI；首次映射失败 |
| [kernel378](<../reference/kernel378/README.md>) | 378：配置别名移出 debug 映射；实机 CONFIG_IO 首次确认 |
| [kernel379](<../reference/kernel379/README.md>) | 379：两路 IPE CONFIG_IO 控制链路实机通过 |
| [kernel380](<../reference/kernel380/README.md>) | 380：原厂 striping 完整执行与内核 IPE 帧编码器 |
| [kernel381](<../reference/kernel381/README.md>) | 381：实机首帧 IPE 像素通路通过，零 IQ 的输出幅度仍待修正 |
| [kernel382](<../reference/kernel382/README.md>) | 382：内核生成 ICA 默认配置，实机 NV12 幅度恢复 |
| [kernel383](<../reference/kernel383/README.md>) | 383：内核原生分区计算与原厂完整帧准备差分 |
| [kernel384](<../reference/kernel384/README.md>) | 384：原生 bypass 条带与实机像素对照 |
| [kernel385](<../reference/kernel385/README.md>) | 385：多尺寸、NV21与交替会话连续提交 |
| [kernel386](<../reference/kernel386/README.md>) | 386：V4L2 m2m入口及实际18帧队列验证 |
| [kernel387](<../reference/kernel387/README.md>) | 387：四摄实际 libcamera → IPE 管线，82 帧通过 |
| [kernel388](<../reference/kernel388/README.md>) | 388：IPE 直接 DMA 与导出缓冲区所有权，最终 99 帧通过 |
| [kernel389](<../reference/kernel389/README.md>) | 389：正式 CAMSS/ICP 平台所有者与板级部署候选 |
| [kernel390](<../reference/kernel390/README.md>) | 390：正式 CAMSS/ICP 平台部署，111帧与卸载重载通过 |
| [kernel391](<../reference/kernel391/README.md>) | 391：正式安装 IPE 用户空间，默认四摄与 PipeWire 通过 |
| [kernel392](<../reference/kernel392/README.md>) | 392：在途取消、双上下文与输入错误恢复实机验证 |
| [kernel393](<../reference/kernel393/README.md>) | 393：隔离 IPE 提交前错误，正式更新核心／适配层 |
| [kernel394](<../reference/kernel394/README.md>) | 394：真实帧 ACK 丢失触发重启；保留证据并恢复正式四摄 |
| [kernel395](<../reference/kernel395/README.md>) | 395：修复 A5 强制复位到 DMA 退映射的顺序，并部署正式核心 |
| [kernel396](<../reference/kernel396/README.md>) | 396：恢复 IPE CCM 的实际命令编码和固件路由，形成内核候选 |
| [kernel397](<../reference/kernel397/README.md>) | 397：逐帧 CCM 参数归入驱动请求，固定矩阵已作用于硬件像素 |
| [kernel398](<../reference/kernel398/README.md>) | 398：纠正 IPE CCM 分支及偏移位宽，核实前后颜色转换契约 |
| [kernel399](<../reference/kernel399/README.md>) | 399：恢复原厂 CST／CV 模式树，接入内核逐帧转换链 |
| [kernel400](<../reference/kernel400/README.md>) | 400：CST／CV 与 CCM 组合实像素通过，恢复正式四摄 |
| [kernel401](<../reference/kernel401/README.md>) | 401：原厂 Gamma DMI 契约与 LUT 请求所有权已接入候选 |
| [kernel402](<../reference/kernel402/README.md>) | 402：修正原厂 Gamma DMI 格式，实像素验证通过 |
| [kernel403](<../reference/kernel403/README.md>) | 403：核实本机 LTM 契约与逆 Gamma，加入原生分区基础 |
| [kernel404](<../reference/kernel404/README.md>) | 404：原生 LTM 全帧条带几何与原厂硬件命令对齐 |
| [kernel405](<../reference/kernel405/README.md>) | 405：类型化 LTM IQ／LUT 与同请求所有权 |
| [kernel406](<../reference/kernel406/README.md>) | 406：LTM 实像素通过，修正单全帧 IP 启用策略 |
| [kernel407](<../reference/kernel407/README.md>) | 407：移植 LTM 曲线生成、曝光衰减及非零 scale／LCE 量化 |
| [kernel408](<../reference/kernel408/README.md>) | 408：恢复本机 Face 平滑状态，接入完整曲线阶段顺序 |
| [kernel409](<../reference/kernel409/README.md>) | 409：ADRC 增益转 LTM 曲线、混合与原生 LUT 通过 |
| [kernel410](<../reference/kernel410/README.md>) | 410：原厂 TMC10 提取、增益采样及 ADRC 数值链路通过 |
| [kernel411](<../reference/kernel411/README.md>) | 411：按本机 HAL 修正 TMC10 膝点，补齐 AEC 插值 |
| [kernel412](<../reference/kernel412/README.md>) | 412：TMC11 原厂树、模式绑定及 PCHIP／对比度采样 |
| [kernel413](<../reference/kernel413/README.md>) | 413：TMC11 直方图、膝点和对比度曲线生成通过 |
| [kernel414](<../reference/kernel414/README.md>) | 414：原厂 TMC11 三层触发插值与动态数值链 |
| [kernel415](<../reference/kernel415/README.md>) | 415：TMC11 状态／版本策略、IPE 元数据缓存及 LTM 选择分支 |
| [kernel416](<../reference/kernel416/README.md>) | 416：真实 IPE 版本绑定、HDR 输入域及完整 SWTMC11 执行 |
| [kernel417](<../reference/kernel417/README.md>) | 417：类型化逐帧 ISP 参数通过 Media Request 真机验证 |
| [kernel418](<../reference/kernel418/README.md>) | 418：libcamera IPE 请求链路与三方完成回收通过真机验证 |
| [kernel419](<../reference/kernel419/README.md>) | 419：逐帧IQ失ACK恢复与错误缓冲出队 |
| [kernel420](<../reference/kernel420/README.md>) | 420：生产IPE请求通道打包集成 |
| [kernel421](<../reference/kernel421/README.md>) | 421：真实统计观测、最终图像回执与统计发布重入修复 |
| [kernel422](<../reference/kernel422/README.md>) | 422：原厂 LTM 标量、LA／mask 与完整类型化帧组装 |
| [kernel423](<../reference/kernel423/README.md>) | 423：主摄原厂 TMC／LTM 接入 IPA、同帧请求与数学历史实拍 |
| [kernel424](<../reference/kernel424/README.md>) | 424：修正 LTM 衰减坐标，补统计缺失恢复，实拍完成自动对焦 |
| [kernel425](<../reference/kernel425/README.md>) | 425：恢复原厂粗级 PD10 IO，确认 DC 实际增加 IPE 处理遍次 |
| [kernel426](<../reference/kernel426/README.md>) | 426：复用四摄原厂 DS4 调校，恢复 VFE175 降采样与 PD10 寄存器编码 |
| [kernel427](<../reference/kernel427/README.md>) | 427：原厂 DS4 接入底层输出队列，实机定位到帧内停滞 |
| [kernel428](<../reference/kernel428/README.md>) | 428：原厂 Crop 纠正 DS4 色度坐标，四摄完整输出通过实拍 |
| [kernel429](<../reference/kernel429/README.md>) | 429：四摄恢复通过；真实 PD10 双遍完成，统计与重复性仍未通过 |
| [kernel430](<../reference/kernel430/README.md>) | 430：修复 DC 遍次被丢弃；同输入重复性与 LTM 粗级消费通过 |
| [kernel431](<../reference/kernel431/README.md>) | 431：原厂 bank 策略确认；生产 IPA 同帧 PD10 自动双遍实拍通过 |
| [kernel432](<../reference/kernel432/README.md>) | 432：原厂 GTM 数据恢复与 TMC11→GTM 数学验证 |
| [kernel433](<../reference/kernel433/README.md>) | 433：IFE GTM 提交契约、驱动参数与 SOF 生效回执候选 |
| [kernel434](<../reference/kernel434/README.md>) | 434：原厂 GTM 实机生效、双 bank 重复性及重开流修复 |
| [kernel435](<../reference/kernel435/README.md>) | 435：主摄生产 IPA 接通原厂 GTM／TMC／LTM 与最终成功历史 |
| [kernel436](<../reference/kernel436/README.md>) | 436：恢复原厂 BLS，定位并减轻主摄雾感与环状亮度 |
| [kernel437](<../reference/kernel437/README.md>) | 437：AWB 收敛状态与实际 WB 增益关联 |
| [kernel438](<../reference/kernel438/README.md>) | 438：广角、长焦原厂 tone 与真实 PD10 自动链路实拍 |
| [kernel439](<../reference/kernel439/README.md>) | 439：前摄原厂 IPE CCM13 与自动双遍链路 |
| [kernel440](<../reference/kernel440/README.md>) | 440：四摄原厂自动调校整合版 r32 已安装 |
| [kernel441](<../reference/kernel441/README.md>) | 441：720p／1080p 同帧 PD10 与 LTM 消费已取得实证，候选整体验收未通过 |
| [kernel442](<../reference/kernel442/README.md>) | 442：停止取消语义修复，两种尺寸同帧 PD10／LTM 全链路通过 |
| [kernel443](<../reference/kernel443/README.md>) | 443：主摄 16:9 模式补齐原厂 DS4，正常 GStreamer 两尺寸双遍通过 |
| [kernel444](<../reference/kernel444/README.md>) | 444：焦点／tone 合并同步调用，IPA6 与正常消费者验证通过 |
| [kernel445](<../reference/kernel445/README.md>) | 445：精确优化焦点网格，实机缓存基准约快两倍 |
| [kernel446](<../reference/kernel446/README.md>) | 446：焦点工作区复用，补齐四摄／RAW／实际 AF 覆盖 |
| [kernel447](<../reference/kernel447/README.md>) | 447：焦点长尾包含抢占等待，大核线程对照改善稳态 |
| [kernel448](<../reference/kernel448/README.md>) | 448：开停流管理线程容量租约，首个焦点采样已使用选定CPU |
| [kernel449](<../reference/kernel449/README.md>) | 449：用户身份、同一 Manager 循环与五分钟取流；发现旧统计重复回执 |
| [kernel450](<../reference/kernel450/README.md>) | 450：旧统计在同步 IPA 回执前释放本地所有权 |
| [kernel451](<../reference/kernel451/README.md>) | 451：一次分配编码 Camss 参数，保留原线格式 |
| [kernel452](<../reference/kernel452/README.md>) | 452：有界 FULL 所有权诊断，首次实机定位到成功FULL回调之前 |
| [kernel453](<../reference/kernel453/README.md>) | 453：BU64253 标准镜头驱动候选 |
| [kernel454](<../reference/kernel454/README.md>) | 454：复用原厂 OV02A1B 表与曝光控制的离线基础 |
| [kernel455](<../reference/kernel455/README.md>) | 455：BU64253 lifetime r3 独立候选 |
| [kernel456](<../reference/kernel456/README.md>) | 456：原 Image363 加 0064 的独立 core Image |
| [kernel457](<../reference/kernel457/README.md>) | 457：FULL供给窗口细化与现有内核trace审查 |
| [kernel459](<../reference/kernel459/README.md>) | 459：独占内核 trace 实例生命周期 helper |
| [kernel460](<../reference/kernel460/README.md>) | 460：匹配 ODM AF override 的有限原指令核对 |
| [kernel461](<../reference/kernel461/README.md>) | 461：同步 IPA 回执期间保留请求所有权 |
| [kernel462](<../reference/kernel462/README.md>) | 462 r1：前摄共享 route／reset／MCLK 的受限代码候选 |
| [kernel463](<../reference/kernel463/README.md>) | 463：按媒体角色选择 FULL 跟踪节点 |
| [kernel464](<../reference/kernel464/README.md>) | 464：把FULL空队列与应用归还请求对齐 |
| [kernel465](<../reference/kernel465/README.md>) | 465：长焦两尺寸消费者与原厂 mode2 增量 |
| [kernel466](<../reference/kernel466/README.md>) | 466：长焦 mode2 的 CSI/link 候选已收敛 |
| [kernel467](<../reference/kernel467/README.md>) | 467：长焦 mode3 两尺寸同帧双遍实际消费 |
| [kernel468](<../reference/kernel468/README.md>) | 468：原厂长焦 mode2 已单模块接入并实机开流 |
| [kernel469](<../reference/kernel469/README.md>) | 469：原厂长焦 mode2 的 720p LTM 实际消费 |
| [kernel470](<../reference/kernel470/README.md>) | 470：长焦1080p实际串行处理超过帧节拍 |
| [kernel471](<../reference/kernel471/README.md>) | 471：长焦1080p仅替换proxy的旧／新／旧比较 |
| [kernel473](<../reference/kernel473/README.md>) | 473：processed IPE Manager容量租约的底层候选与实测 |
| [kernel474](<../reference/kernel474/README.md>) | 474：组合候选的原生／隔离1080p与LTM消费 |
| [kernel475](<../reference/kernel475/README.md>) | 475：r33／r28 可回退候选物料，未安装手机 |
| [kernel476](<../reference/kernel476/README.md>) | 476：mode2 控制延迟离线执行准备 |
| [kernel477](<../reference/kernel477/README.md>) | 477：目标真实 providers 的只读 APK 解算准备 |
| [kernel479](<../reference/kernel479/README.md>) | 479：mode2 曝光／增益两帧响应的实测依据 |
| [kernel480](<../reference/kernel480/README.md>) | 480：目标真实 APK providers，只读单次解算 |
| [kernel481](<../reference/kernel481/README.md>) | 481：真实安装、精确回退、再安装准备 |
| [kernel482](<../reference/kernel482/README.md>) | 482：481 安装事务的有限默认路径 probe |
| [kernel483](<../reference/kernel483/README.md>) | 483 独立准备审查 |
| [kernel484](<../reference/kernel484/README.md>) | 484 实际安装独立审计 |
| [kernel485](<../reference/kernel485/README.md>) | 485：恢复 libcamera 的安装路径识别 |
| [kernel486](<../reference/kernel486/README.md>) | 486：测量启动器的个人 HOME 环境修复 |
| [kernel487](<../reference/kernel487/README.md>) | 487：三 sensor 静态属性候选与四摄 rotation 缺口 |
| [kernel488](<../reference/kernel488/README.md>) | 488：识别 DS4 的 0x2027 媒体总线格式 |
| [kernel489](<../reference/kernel489/README.md>) | 489：安装路径、原厂静态属性和总线格式的增量 core |
| [kernel490](<../reference/kernel490/README.md>) | 490：r34/r29 七包候选与精确 r33/r28 回退包 |
| [kernel491](<../reference/kernel491/README.md>) | 491：仅更新包的定向复验准备 |
| [rx33](<../reference/rx33/README.md>) | Session 33：有效 EUD RX 抓包 |
| [rx34](<../reference/rx34/README.md>) | Session 34 的临时终端记录 |
| [rx36](<../reference/rx36/README.md>) | Session 36：USB 描述符、旧 qcusbser 审查与已完成对照 |
| [rx37](<../reference/rx37/README.md>) | Session 37：原生多字节 RX 源码搜索与审查 |
| [rx38](<../reference/rx38/README.md>) | RX38 evidence: pre-Linux comparison and USB boundaries |
| [rx39](<../reference/rx39/README.md>) | RX39 evidence: tight arrival polling still repeats the first byte |
| [rx40](<../reference/rx40/README.md>) | RX40 source audit and baseline check |
| [rx41](<../reference/rx41/README.md>) | RX41: SM8150 AHB2PHY wait state and native RX |
| [rx43](<../reference/rx43/README.md>) | RX43: full-output audit and remaining receipt boundary |
| [rx44](<../reference/rx44/README.md>) | RX44 evidence |
| [rx45](<../reference/rx45/README.md>) | RX45 evidence: persistent RX mask alone does not fix missing receipts |
| [rx46](<../reference/rx46/README.md>) | RX46: real IRQ reception works, but a missing command adds no IRQ |
| [rx47](<../reference/rx47/README.md>) | RX47: continuous native terminal, reopen comparison and remaining faults |
| [rx48](<../reference/rx48/README.md>) | RX48: bounded IRQ grace and CRC-protected issued-TX records |
| [rx49](<../reference/rx49/README.md>) | RX49: complete USB IN comparison and a real partial cancellation |
| [rx50](<../reference/rx50/README.md>) | RX50: Windows receive observation and exact installed-driver audit |
| [rx51](<../reference/rx51/README.md>) | RX51: bounded console-overlap failure and one missing issued TX frame |
| [rx52](<../reference/rx52/README.md>) | RX52: same-owner busy-console RX loss and continuous USB IN comparison |
| [rx53](<../reference/rx53/README.md>) | RX53: service whole RX frames during console output |
| [rx54](<../reference/rx54/README.md>) | RX54: console RX/F1 regressions and exact host-counter audit |
| [rx55](<../reference/rx55/README.md>) | RX55: reproduced issued TX gap and accepted-buffer receive counts |
| [rx56](<../reference/rx56/README.md>) | RX56: exact pre-buffer source boundaries and focused research |
| [rx57](<../reference/rx57/README.md>) | RX57: built-in driver raw logger, measured before serial-buffer acceptance |
| [rx58](<../reference/rx58/README.md>) | RX58: first-frame association and exact failed-read gates |
| [rx59](<../reference/rx59/README.md>) | RX59 — joint capture and forced odd-IN reopen |
| [rx60](<../reference/rx60/README.md>) | RX60 — even reopen reversal and offline toggle candidate |
| [rx61](<../reference/rx61/README.md>) | RX61 — EUD WDF package inputs and build preparation |
| [rx62](<../reference/rx62/README.md>) | RX62 — real full driver build and file-only test-signed package |
| [rx63](<../reference/rx63/README.md>) | RX63 — live compatibility and guarded single-device trial tools |
| [rx64](<../reference/rx64/README.md>) | RX64 — supported driver-loading environment remains blocked |
| [rx65](<../reference/rx65/README.md>) | RX65 — WSL full native input succeeds; tty TX loss remains |
| [bluetooth-20261023](<../reference/bluetooth-20261023/README.md>) | 蓝牙完整功能与现有修复固化 |
| [bluetooth-host-adoption-20261023](<../reference/bluetooth-host-adoption-20261023/README.md>) | BNEP/UHID adoption 与回退审查 |
| [bluetooth-host-config-20261023](<../reference/bluetooth-host-config-20261023/README.md>) | k363 蓝牙主机协议与最小配置增量 |
| [bluetooth-host-input-cache-20261023](<../reference/bluetooth-host-input-cache-20261023/README.md>) | 现场事务输入的只读字节缓存工具 |
| [bluetooth-host-modules-20261023](<../reference/bluetooth-host-modules-20261023/README.md>) | BNEP/UHID 独立固化候选 |
| [bluetooth-host-trigger-20261023](<../reference/bluetooth-host-trigger-20261023/README.md>) | 原kmod trigger隔离验证的输入对齐审查 |
| [bluetooth-le-peer-20261023](<../reference/bluetooth-le-peer-20261023/README.md>) | 手机BlueZ GATT外设与Windows中央对端（2026-10-23） |
| [bluetooth-oem-20261023](<../reference/bluetooth-oem-20261023/README.md>) | 蓝牙原厂依据与可复用实现（2026-10-23） |
| [bluetooth-service-prereqs-20261023](<../reference/bluetooth-service-prereqs-20261023/README.md>) | 蓝牙服务前提与手机对端角色（2026-10-23） |
| [bluetooth-speaker-20261023](<../reference/bluetooth-speaker-20261023/README.md>) | 漫步者低音量连接与重连验收 |
| [bluetooth-static-fixes-20261023](<../reference/bluetooth-static-fixes-20261023/README.md>) | 蓝牙六类静态问题修复与离线验证 |
| [bluetooth-static-review-20261023](<../reference/bluetooth-static-review-20261023/README.md>) | 蓝牙当前静态审查（2026-10-23） |
| [bluetooth-transport-20261023](<../reference/bluetooth-transport-20261023/README.md>) | 蓝牙传输与 PM 候选：2026-10-23 |
| [bluetooth-windows-central-20261023](<../reference/bluetooth-windows-central-20261023/README.md>) | Windows BLE central：专用手机 GATT 对端 |
| [charging-management-20261023](<../reference/charging-management-20261023/README.md>) | Realme X2 Pro充电管理：2026-10-23 |
| charging-oem-audit-20261023（本地私人证据） | 原厂普通充电策略缺口审查 |
| charging-session-20261023（本地私人证据） | 充电周期计时修正候选 |
| charging-ui-audit-20261023（本地私人证据） | USB 充电图标延迟：离线链路审计 |
| [display-handoff-comparison](<../reference/display-handoff-comparison/README.md>) | 一加、真我 Linux 显示交接方案对比 |
| [full-upgrade-20261018](<../reference/full-upgrade-20261018/README.md>) | 2026-10-18：现有软件源全量升级完成 |
| [maintenance-2026-10-19](<../reference/maintenance-2026-10-19/README.md>) | 2026-10-19：暂停交接与编译产物清理 |
| [package-hardening-20261023](<../reference/package-hardening-20261023/README.md>) | 2026-10-23：平台修复固化与蓝牙 APK 候选 |
| [publication-2026-10-14](<../reference/publication-2026-10-14/README.md>) | 2026-10-14 分类提交与公开资料 |
| [publication-2026-10-17](<../reference/publication-2026-10-17/README.md>) | 2026-10-17：保存全部后续硬件适配源码 |
| [publication-2026-10-26](<../reference/publication-2026-10-26/README.md>) | 2026-10-26：已适配内容整理发布 |
| [repository-audit-20261018](<../reference/repository-audit-20261018/README.md>) | 2026-10-18：APK索引刷新与版本约束核对 |

## 早期拆分与快照

- [旧8—30节映射](../HANDOVER-NEXT.md#旧830节映射)
- [Linux技术与19—28节](../linux-port/docs/00-INDEX.md)
- [旧决策8—11节](../reference/DECISIONS.md)
- [2026-10-14维护前逐字快照](../archive/docs-before-maintenance-2026-10-14/README.md)
