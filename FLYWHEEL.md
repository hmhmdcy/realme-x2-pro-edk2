# 免按键测试飞轮：构建、部署、观测与回退

用途：增量部署与历史协议证据导航。整理日期：2026-10-23；实际设备、源码及回退包以[检查点](NEXT-SESSION.md)核对，当前操作规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。资料提取和验证范围见[适配工作流](linux-port/docs/PORTING-WORKFLOW.md)。

## 一轮工作流程

1. 确定本轮缺口和改动范围，优先复用原厂提取物与已验证实现；只核对相关设备状态、载荷和已有回退。
2. 增量构建受影响目标，检查改动相关的ABI、模块、IPA协议/签名或模式配置；未改组件复用结果。
3. 按最小更新路径部署：配置/软件包优先；模块更新先停相关消费者并确认可安全卸载；启动链、DT、不可热换组件或故障恢复确有需要时再刷写或重启。进入bootloader前按该路径完成关流与文件系统处理，状态不明先查询。
4. 核对实际加载的改动，验证目标功能、相关错误和资源释放；到能判断结果即止。相同相关载荷的已有案例直接引用，计数或报告修订优先重审缓存证据。
5. 清理临时记录器/服务，保存一份问题所需日志。部署/回退变化更新检查点，功能结论变化更新硬件清单；过程保留在一处并链接，无需逐步收据或每轮重做回退演练。

全量Image/rootfs、全设备回归、跨启动和长稳测试在相关改动或发布整合时安排，不作为每个配置/驱动迭代的固定步骤。成功的有状态安装事务保持终态；需要新实验时使用适配当前状态的新事务。

## EUD与F1

历史命令通道使用`id=0x90`。`[90][02]`为已验证的F1 bootloader命令，长度2不能用作普通二字节TTY分片。TOP_CFG=0x11后的完整payload读取与RX53 console/IRQ处理已有真机证据；受理与输出仍有独立稳定性边界。

- [31 F1验证](sessions/31-flywheel-f1-verified.md)、[41原生RX](sessions/41-rx-ahb2phy-wait-state-fix.md)、[53 console边界](sessions/53-console-boundary-rx-service.md)
- [65 WSL TX缺口](sessions/65-wsl-full-packet-console-overlap-and-tx-gap.md)：EUD作为辅助观测，关键设备侧日志应保存完整副本并校验导出。
- [143线程化候选拒收](sessions/143-threaded-console-live-regression-and-rollback.md)、[144回执竞态](sessions/144-eud-reboot-handoff-and-display-clock-review.md)：工具和源码按对应验证范围使用。

EUD与普通USB NCM/SSH共存已有验收，[USB路径](linux-port/docs/USB-NCM-SSH.md)可用于当前任务。协议寄存器与旧实现细节见[EUD](EUD.md)、[RX-CONSOLE](RX-CONSOLE.md)。

## 构建、停机与回退证据

- [164固件构建](reference/kernel164/README.md)：实际BdsDxe差异、DTB与其他模块比较。
- [165同组合验收](reference/kernel165/README.md)：新身份停机、F2FS冻结、单次F1和独立启动收据。
- [157 RAM启动阻塞](reference/kernel157/README.md)、[158恢复](reference/kernel158/README.md)：特定失败现场的处置，不能脱离RAM-only状态证据复用。
- [旧完整流程、命令表与工具说明](archive/docs-before-maintenance-2026-10-14/FLYWHEEL.md)：按对应阶段解释时序和路径，当前版本与回退依据由检查点定位。

## 日志与维护

原始日志、身份、密钥和录音保存在私人目录；可审查补丁和脱敏收据按[会话索引](sessions/INDEX.md)组织。当前边界由WORKING-BOUNDARIES维护，工具参数与验证规模按具体工作选择。
