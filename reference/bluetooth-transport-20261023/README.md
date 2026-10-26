# 蓝牙传输与 PM 候选：2026-10-23

本目录由蓝牙传输代理独占。只读现有资料、原厂适配依据和固定源码；未 SSH、未占用 SDK、未修改共享源码或共享内核构建输出，未加载模块、刷写或重启。生成的 C、ELF、构建和运行日志均在私有 `E:/edk2-samurai-out/bluetooth-transport-20261023/`；公开保留测试脚本、源码、补丁和脱敏报告。

源基线与 [185 脉冲修复](../kernel185/README.md)、[204 RX wake](../kernel204/README.md)、[206 恢复](../kernel206/README.md)、[234 接收诊断](../kernel234/README.md)一致。WSL 两棵实际树的 `hci_qca.c` 均为 `645ded4980918a2d0a22dd2d56327bbc69c08e3689e9d313158f0d263e291d90`，不含 234 临时诊断；相关文件固定于 [source-lock.json](source-lock.json)。本次不覆盖其它会话的 kernel45x、检查点或已安装载荷。

## QCA PM 修复与边界

原 `qca_suspend()` 把单字节 SLEEP 写返回 0 当作成功，随后设置 TX_ASLEEP、增加计数并关 TX clock vote；同时把 `wait_event_interruptible_timeout()` 的负返回当作成功。r1 仅修正这两类返回契约：写必须接受 1 字节，其它非负返回映射 `-EIO`；等待 0 映射超时，负返回保留并清 `QCA_SUSPENDING`。

进一步审查发现，r1 继承了原有恢复缺口：SLEEP 写前已取消 awake work、删除重传/空闲 timer，错误后仅清标志。若 TX_WAKING 且 ACK 不到，后续 enqueue 只增加等待队列，不能自行恢复进度。因此 r1 工件保留为中间候选，不作为推荐运行版本。

[r2 完整补丁](qca-suspend-recovery-r2.patch)保留 r1 返回值修正，并仅对本次已停止 IBS 的错误路径恢复机制：持 IBS 锁清标志，排除 IBS disabled、SSR、BT off 后，按实际 TX 状态恢复。WAKING 重挂重传 timer 并补 TX clock vote；AWAKE 重挂 idle timer；已经接受 SLEEP 的 ASLEEP 保持，只有仍有等待帧才转 WAKING。复用现有 timeout/ACK 路径，不假装收到 ACK，不重放无状态检查的旧 awake work。早期 FW/SSR 等待失败不额外启动机制。[r1→r2 差异](qca-suspend-recovery-r1-to-r2.patch)

固定源中的 `serial_clock_vote()` 注释要求 IBS 锁，两个 `__serial_clock_on/off()` helper 都为空 TODO，无睡眠、TTY 解引用或外部 clock API；r2 在锁内调用符合此版本契约。未来实现这两个 helper 时仍需满足该契约。收到 ACK 时若仍在 SUSPENDING，原逻辑继续忽略；错误清标志后，重传 WAKE 的 ACK 可删除 timer 并排空等待队列。RX_SLEEP 的实际状态保留，后续 RX_WAKE 继续原处理，不伪造 RX_AWAKE。

## 验证与产物

- [返回值测试](test-qca-suspend-contract.py)提取真实 suspend/resume，33 例覆盖 0、负写、越界正返回、真实 signal 值 `-ERESTARTSYS`、超时、正常 PM、ROM/off、FW/SSR。基线 16 个契约违例，r1/r2 均 0，ASan/UBSan 通过。[报告](qca-suspend-contract-validation.json)
- [恢复测试](test-qca-pm-recovery.py)直接提取实际 enqueue、retrans/idle timeout、ACK、RX、clock vote 和 PM 函数，19 场景覆盖 WAKING 失败后的发送进度、AWAKE idle 恢复、SUSPENDING 内外 ACK、已接受 SLEEP 后队列、RX_SLEEP/WAKE、SSR 和成功 resume。r1 的前进/恢复反例保留；r2 全部 0、分配回收相等，ASan/UBSan 通过。[报告](qca-pm-recovery-validation.json)
- [独立构建](build-qca-module.py)从真实 Image363 提取配置，使用原 Module.symvers，在私有 source-view/O 中构建 hci_uart 与原 btbcm/btqca 依赖；W=1、KCFLAGS=-Werror，0 诊断，intree=Y、k363 vermagic、183 导入符号均匹配。共享相关输入前后不变。[r1](module-build-validation.json)、[r2](qca-pm-r2-module-build-validation.json)

r2 待部署模块为私有目录的 `hci_uart-qca-pm-r2-k363-intree-stripped.ko`，140136 B，SHA256 `fe14136068584d212625a7c2bfb20b72e082539daa10dfcecd877e43531fc32d`。未剥离原件和 r1 原件保持。r2 源 SHA256 `74ffff64a7368acc044535dda71535dcdfa31bd0668961c40ada4072b9715339`。模块构建成功不等于实机 PM 或完整蓝牙功能通过；包线在本轮协调下准备独立候选，设备切换需由主线安排。

第一次仅构建 hci_uart 未把 provider 模块列入同一 make，modpost 失败；原报告/日志保留，随后同一命令加入 btbcm/btqca 后通过。扩展 r2 返回值 fixture 首次因仅在 r2 使用的 host helper 被 Werror 视为未使用而失败；修正 shim 声明后实际重编通过，初次失败日志留在私有目录。

## GENI 与 phase5

[GENI 离线候选](geni-rts-mode-lock-candidate.patch)把 manual_flow 与 RFR 同步放入同一个短 `uart_port_lock_irqsave` 临界区，保留 console、RS485 和 suspended 语义。[实际函数测试](test-geni-rts-contract.py)复用 234 的真实驱动/core 函数，加入实际 serdev ttyport 调用、锁/IRQ 检查、4 个受控 RTS 交错及异常边界。原 16 例 2 个模式反例；旧裸同步虽然模式为 0，却触发 31 次锁/IRQ 违约并覆盖一次 RS485；新候选均 0。[报告](rts-contract-validation.json)

此测试的寄存器、锁、IRQ 与回调交付仍是 host 模型，不是 kernel lockdep 或硬件时序证据。[GENI 实际对象构建](geni-object-build-validation.json)已在同一私有 source-view/O 中以 W=1、KCFLAGS=-Werror 通过，0 诊断，369768 B；共享输入及两份 QCA r2 模块保持。未链接 Image、未部署。两次早期对象构建准备先因 WSL 自动退出后挂载不在而未找到源/配置；补调用现有 storage 验证/挂载入口后构建成功，未格式化或更改存储规则。

历史 `phase=5 baud=3200000 chunk=13 partial=0 first=ff` 不足以定位丢失 04：234 已证明非空 skb 可 len0、且 chunk 后部也可报错。本次没有吞 FF、补 04、降低波特率或声称已修复 phase5。推荐运行候选仅为 PM r2，仍待设备实测；GENI 保持离线对象候选。

配对、连接、A2DP/HFP、BLE 业务及外部蓝牙事件唤醒仍需主线安排实机验收。现有 WCN3990 capability 表不启用 HFP 硬件 offload，接收表包含 SCO；软件 HFP 所需的用户态配置、音频路由和真实耳机条件另行验证。
