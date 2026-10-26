# 显示交接修复过程：152—165

用途：从维护前检查点整理的历史过程与证据导航。整理日期：2026-10-14；未新增实机验收。最后核对状态见[当前检查点](../NEXT-SESSION.md)，功能验收边界见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。

| 阶段 | 改动、观测与结论 | 原始证据 |
| --- | --- | --- |
| 152 | worker同步候选拒收，未混入后续候选 | [会话](152-display-lifecycle-candidate-and-boot-handoff-reproduction.md)、[证据](../reference/kernel152/README.md) |
| 153 | probe采用GPIOD_ASIS，prepare才初始化方向，避免先破坏固件显示 | [会话](153-panel-gpio-handoff-and-first-startup-underflow.md)、[证据](../reference/kernel153/README.md) |
| 154 | native power_on停CTRL后重写时序，仍有首次白屏及DSI欠载 | [会话](154-dsi-host-init-rejected-and-runtime-display-recovery.md)、[证据](../reference/kernel154/README.md) |
| 155 | 同154镜像重启无DSI错误，用户仍反馈偶发唤醒闪屏与启动慢 | [证据](../reference/kernel155/README.md) |
| 156 | 原厂首帧背光策略；TX后亮屏门控及24次DPMS通过，首次仍78条DSI错误。greetd提前至无线等待前，Phosh79.67→20.62秒，无线45秒等待/NV流程保持 | [会话](156-first-frame-backlight-and-early-desktop.md)、[证据](../reference/kernel156/README.md) |
| 157 | 停机提前至PHY配置前，但首次CTL -22更早，停机路径未执行。重探测/桌面恢复后发生来源未知新boot，pstore为空；RAM boot UFS探测阻塞，未挂载磁盘文件系统 | [证据](../reference/kernel157/README.md) |
| 158 | 根据当前RAM身份一次F1受理后停机仍被存储探测阻塞；保存SysRq w、确认RAM-only后一次SysRq b切换，只刷logdump158。SM8150在清boot CTL前停全部绑定DSI，首帧与before-PHY回退保持 | [证据](../reference/kernel158/README.md)、[补丁](../reference/kernel158/before-ctl-stop.patch) |
| 159 | 同158镜像第二次启动，无刷写；Phosh19.56秒，两次累计48次DPMS/24门控。601.09秒同boot/PID稳态关键错误0，最后uptime1826.80；临时服务退出runlevel | [会话](159-same158-second-boot-display-verification.md)、[证据](../reference/kernel159/README.md) |
| 160 | 第三次同镜像启动，Phosh19.43秒、显示关键错误0。用户确认启动变快，但白屏发生在EDK2到首个Linux命令行之前，彼时实体复验未完成 | [证据](../reference/kernel160/README.md) |
| 161 | 空RMR候选离线7项真实函数及完整构建通过；新boot WARN1/taint512/DMA prepare917，软件验收失败。实体效果未观察，因果未知，候选拒收、SMMU源码恢复 | [证据](../reference/kernel161/README.md) |
| 162 | 按新的161身份正常停机，刷回不可变原始158；Phosh20.24秒、显示/WARN/audio DMA prepare0、taint0。重建158不是原始字节副本，未用于回退 | [证据](../reference/kernel162/README.md) |
| 163 | TLMM就绪后配置本机GPIO6/active-low，逻辑1保持复位并释放GPIO。实际probe13.2707晚于SMMU13.18，不能由注册顺序推断先于SMMU。48次DPMS、第二轮12门控、601秒稳态通过 | [证据](../reference/kernel163/README.md) |
| 164 | BeforeExitBootServices通过TLMM配置GPIO6物理低；14项普通/ASAN/UBSAN真实函数及2负对照通过。候选仅BdsDxe变更，只刷boot164；首次WARN1/DMA prepare917、Phosh35.32秒 | [证据](../reference/kernel164/README.md)、[固件补丁](../reference/kernel164/before-exit-panel-reset.patch) |
| 165 | 同boot164/kernel163重启无刷写；Phosh21.45秒、24次DPMS/12门控、601.15秒同boot/PID通过，显示/GPU/WARN/audio DMA prepare0、taint0；临时记录器禁用 | [证据](../reference/kernel165/README.md) |

158的22项真实函数普通/ASAN/UBSAN、完整构建/W=1/checkpatch/FAT通过。770模块中两个仅GNU build-ID不同，其余全部字节一致，原模块132兼容复用。首次158记录从SSH就绪后230.65秒开始，92.94秒无丢失快照为晚期live，不能称首帧快照；159早期服务17.72秒记录、93.05秒无丢失，初始wait在PP TX done后44微秒完成。160为225微秒。163第一轮trace漏最终恢复的第12门控，工具补等待后复测，原始失败记录保留。

164原代码重编译全部模块与实际boot132一致；DTB/BootShim/header/ramdisk/compat/尾部保持。32条配置/ELF RWX/LTO提示的4种模板在原代码重编译中重现，构建不是零提示。只读mmap日志记录BeforeExitBootServices回调Success，无ring丢失。

165之后，用户确认EDK2后无白屏/花屏，黑屏等待后出现命令行。反馈后的只读核对属于更晚的新boot；165的DPMS、601秒与启动耗时不转移为新boot测量。本轮显示交接按已测范围收尾，冷启动、休眠、黑屏等待时长及长稳仍开放；164音频首次失败与157重启原因未知。

完整维护前检查点及其他入口原文保存在[逐字快照](../archive/docs-before-maintenance-2026-10-14/README.md)。
