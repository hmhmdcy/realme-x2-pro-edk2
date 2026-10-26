# 240交接：从哪里继续

当前续作先读[269收尾](../kernel269/README.md)和[检查点](../../NEXT-SESSION.md)：整屏旋转已确认修复，新完整内核未部署；Snapshot意外重启与modem watchdog仍未解决。用户要求收尾，以下240阶段的优先级、旧缓冲缺陷及身份均为历史，不再作为当前状态。

2026-10-16。文档交接及约束清理时，原适配goal为 **paused**；完整适配未完成。本次仅维护本地文档和脱敏镜像，没有SSH、手机复测、构建、安装、刷写或重启。240阶段的progress及原始失败、健康、归档收据保留。当前操作规则仅见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)；下述优先级和当轮方法可按任务调整。

## 接手顺序

1. 读[当前检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)和[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。状态从当前检查点读起；[240收尾原文](../../archive/NEXT-SESSION-through240-2026-10-16.md)是暂停前的历史快照。
2. 用户后续要求继续、修复或测试即可按该请求推进，无需重复确认。接手设备时核真实设备和启动身份，查看当前应用/worker与已有事务，选择所需诊断范围。手机可能已被用户操作，最后的idle、包数或fault计数只作为历史参考。
3. 建议优先处理Snapshot缓冲所有权/帧率，拍照、切换及长稳按诊断需要安排；已部署CPU回退可作为对照。当前只验证递增PTS、GTK CPU映射及释放恢复；用户尚未确认实际画面/颜色，完整相机验收仍开放。
4. 继续S5K3M5电源/驱动构建与GNSS初始化差异研究。蜂窝有卡业务、其它后摄、传感器/蓝牙长稳及完整rootfs仍在待办，不因交接缩减目标。

## 续作重点和完成条件

| 工作 | 已有依据 | 下一步及完成条件 |
| --- | --- | --- |
| Snapshot预览 | [30秒重试](snapshot-mmap-r2-frame-flow-validation.json)：1436递增PTS、600次1080p CPU映射、0paintable Bus Error；301次回收错误 | 修PW交付/Gst持有账本不一致，验证错误不再增长、帧持续到达且正常退出释放。pending与回收错误分别计数，不以窗口存活或sink调用代替验收 |
| 显示/GPU | [故障停止](snapshot-fault-stop-validation.json)、[最后健康](final-health-validation.json)；历史480GPUfault，停止后无新增 | Cairo＋线性DMA CPU映射可作对照。默认Vulkan根因仍开放，与旧CCU及211告警分案；可按任务复现GPU故障，记录负载、退出及恢复结果 |
| 拍照/切换 | Snapshot有完整应用代码路径，本轮没触发快门 | 验证插件、缓冲生命周期及实际拍照保存/切换。可按需要本地保存和分析私人样本、正常补光；无需另设拍照确认。纯色测试按用户延期 |
| S5K3M5 | [源审](s5k3m5-source-validation.json)，917init/模式3表已核；未编译部署 | 可推进准备脚本复用、P固定9/0x22共享lease、真实C回调故障注入和本机19.2MHz模式构建。上电依赖正确供电及共享消费者处理；723.2MHz不是已验PLL值。部署核当前身份，卸载父驱动先释放并移除消费者 |
| IMX319光学 | [竖放24组](upright-analysis.json)非零，但大部分接近黑电平 | 保留RAW/RGB同request及实际处理参数对应关系，按需使用统计或私人样本分析；曝光响应、非零或噪点均未完成颜色/光学验收 |
| GNSS | [239机型及Linux路线](../kernel239/RELATED-LINUX-SOLUTIONS.md)；ODM来源已核、运行采用链未证 | 建议对照匹配Android运行映射/初始化日志与Linux QMI；按假设继续检索或复测，已有矩阵可作对照。需要正CNR/真实fix，室内窗边、无SIM不替代适配故障结论 |

`use-bufferpool=false`没有部署；试验该路径时核对匹配PW版本的[上游锁顺序修复](https://github.com/PipeWire/pipewire/commit/30ff8da174121567c06a576bf2a83e71779ee991)，观察停流及释放。降低候选caps到30fps也不等于传感器降帧，1.6.8相机set_format没有处理FrameDurationLimits。固定版本源码入口见[240记录](README.md)。

## 工作区与证据位置

| 范围 | 位置及用途 |
| --- | --- |
| Windows编辑源 | `E:/RealmeX2Pro edk2`；从根检查点读当前状态 |
| 手机运输代码 | `reference/kernel240/host.py`；严格原公钥及私人端点。恢复后核身份，不能按旧地址/guard盲发动作 |
| 私人主机证据 | `E:/edk2-samurai-out/kernel240`；`native-evidence-private.tar.gz`及manifest含266项记录，另存发行APK、安装及启动事务；不纳入公开镜像 |
| 手机实验根 | `/var/lib/samurai/`；240终态记录以`k240-`开头，新实验用新上下文，不覆盖已有证据 |
| 最后启动身份 | `k236-runtime/boot-id-private.txt`只适用于已核对的236启动；变了须建立新基线，不改旧guard假装匹配 |
| 模块权威清单 | `k237-camss-install/module-inventory-after-private.json`，775ko/789项；[最后模块/加载note核对](final-health-validation.json) |
| canonical内核 | `/home/cy122/pmos-samurai-kernel136/kernel`，240核对时等于after228；私人228的`canonical-after-private.json`为依据，旧相机输出按当前模块/板源核对后复用 |
| libcamera SDK | `/home/cy122/x2pro-linux/libcamera214-root`；r15源/对象在`/work/libcamera239-r15-built`，原214恢复、r14缓存保持；产物见239记录 |
| 相机部署锁 | [deployment-lock.json](../../linux-port/camera/deployment-lock.json)，含r15/r10、14个发行包及两项启动覆盖hash；完整rootfs未整合 |
| 公开文档镜像 | WSL `/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150`；为脱敏副本，不能当作含私人身份的原始执行输入 |

## 启动配置和回退

当前Snapshot回退配置为`GSK_RENDERER=cairo`、`GDK_DISABLE=gl,vulkan,offload`，保留DMA-BUF和默认PW pool，可作为其它路径试验的恢复点。已验[用户desktop/service](snapshot-launcher-install-validation.json)及[真实session D-Bus激活](snapshot-dbus-activation-validation.json)。读取Phosh实际session bus地址；`/run/user/10000/bus`曾被检查器错误假设为存在。新服务目录创建后核对缓存刷新与实际激活环境。

- 用户覆盖：`~/.local/share/applications/org.gnome.Snapshot.desktop`和`~/.local/share/dbus-1/services/org.gnome.Snapshot.service`。副本见[相机目录](../../linux-port/camera/README.md)。手机`k240-snapshot-launcher-transaction`保存manifest及原文件未变依据。回退前检查有无用户后续修改，匹配后才移除或恢复相应覆盖。
- Snapshot包：手机`k240-snapshot-host-packages/apks/packages.adb`为本轮可信离线候选索引；`k240-snapshot-app-transaction`保存world/包库前镜像、安装及卸载模拟。只增14包，不属于r15七包升级；执行卸载前针对当前包库重新求解。
- libcamera七包：r15→r13/config-r8依据为`k225-r13-package-candidates/forward`实际旧包及`k239-r15-package-transaction`前镜像。原生降级模拟通过，完整往返未测。应用故障不要求刷boot或热卸相机父设备。
- 240没有新内核产物，S5K候选不能当作已部署版本；完整boot/DTB/模块回退沿用239归档和部署锁。

## 脚本使用注意

`start-*`、`native-*`、`install-*`、`relay-*`、`verify-snapshot-dbus*`涉及手机进程、设置、trace或包事务。可按当前状态复用单项或组合实验；多数脚本断言上下文目录不存在，需要使用新上下文或适配重入逻辑，保留旧收据。`close-checkpoint.py`和`save-launcher-profile.py`写有当时的收尾文案，复用时同步当前状态，避免恢复旧active或覆盖新交接。

`prepare-s5k3m5.py`/`revise-s5k3m5.py`存在一次性备份及include追加，复用时处理已有文件和重复追加。已核917init/模式表可直接复用；需要新证据时也可重新采集OEM表。新P电源profile尚未实现，完整上电还依赖共享供电、锁、账本、registration及异常回收，契约见240归档。

收据按实验时刻解释：CPU恢复通过不抹去原Vulkan故障；受控Megapixels存活12秒不等于复现用户闪退；用户“重试”已执行30秒，仍无明确的实屏画面/颜色反馈。

## 文档维护完成方式

维护当前入口及对应专题，历史过程通过链接引用。按[DOCS-INDEX流程](../../DOCS-INDEX.md#检查与同步)生成索引、查本地链接/体积及镜像一致性。仅同步用`--copy-only`，需要发布时按该流程操作并保留用户既有暂存内容；原始日志、身份、密钥和场景数据不公开。交接结果见[handoff-validation.json](handoff-validation.json)，本次清理见[约束复核](constraints-review-validation.json)；文档检查不作为新的手机验收。
