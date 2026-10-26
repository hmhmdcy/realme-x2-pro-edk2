# 插入后一次 APSD 复测的协议核心候选

本目录补齐[已恢复的原厂一次复测流程](../apsd-lifecycle/README.md)的软件状态部分：一个实际物理连接最多发起一次命令，错误不变成反复写寄存器，旧 DONE 不冒充复测完成。代码不做 I/O、供电或电流授权，没有自动消费者，尚未接入手机。它不是完整跨驱动 session owner。

依据是固定同机原厂提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的 `usb_source_change_irq_handler`、`smblib_rerun_apsd` 和真实 detach 重置流程；完整函数与哈希沿用前述资料，不重新提取或测试原厂套件。当前实物仍为 SDP/native100；本候选不假设它是错判，也不假设复测会变成 CDP。

`samurai-apsd-once.h` 是串行调用的协议核心，零初始化为 DETACHED。每次真实 attach 分配新 epoch，重复 attach 不会重新武装。首次完整 SDP/CDP DONE 进入 READY；跨驱动 owner 在所有资源和独立 PD/role/route 前提满足后才能 claim，并在实际命令传输之前消耗本连接唯一一次尝试。写失败、结果不明、读失败、超时、取消和时钟倒退均有明确终态，不能靠轮询自动重试。只有真实 detach 后的新 attach 能重新武装，旧 epoch 的晚回执被拒绝。

与原厂失败语义的有意差异：仅 exact SDP/CDP、无 QC 状态时选择复测；原厂 mixed-result 位测试不照搬。命令返回成功只是 WAIT_CLEAR，必须从新的稳定读里先看到 DONE=0，再看到 DONE=1，才发出一次 NEW_DONE。结果可以仍为 SDP；改变的 result 而 DONE 一直为 1 仍不是完成。若硬件清零太短而采样未捕获，本实现会超时，不会猜测成功；今后需在实际 owner 中确定采样/IRQ方案和有来源依据的期限。本目录没有声称已经证明该硬件时序。

未来 consumer 的必要调用约定：

- 由同一个绑定生命周期 owner 持 session 锁调用这些方法。实际 PMIC attach/detach 与 PD/角色/PM/解绑事件负责取消，逻辑 gadget 断接不能作为重新武装事件。
- `sample` 的 serial 只分配给真正新取得的稳定两次 PMIC读取；重复 serial 被拒绝，不能给缓存值换新序号。时钟使用同一单调毫秒域；owner 即使没有新样本也要执行有界 deadline 检查。
- claim 不是硬件许可。写入前须重新验证 sink、PD inactive/无 swap/reset、EUD硬件路径交还、DWC HALT、PHY高阻及独立供电/PM约束，保留所有真实 token。现有 EUD 软件 quiet 或 PD PHY enable=0 均不能替代这些前提。
- claim 与唯一命令传输、回执必须由同一有界执行流完成。取消/detach 后先取消并 join 该执行流，不能在旧传输尚未结束时对新连接发命令；本协议不提供总线取消或进程/工作项 join。
- 无论协议成功、失败还是 detach，PHY、DWC、EUD的退出错误与资源清理独立处理；DETACHED 不代表硬件已恢复。检测成功也不代表主机 configured 或 native500mA。
- 新 result 仍交给现有严格 decoder/native预算路径；本结构没有电流字段，不更改 MP2650、双电芯保护、输入/充电/CV上限。不得放入 property getter 做隐式硬件动作。

独立复审指出首版会让同时/先前发生的超时或取消遮住晚到的 bus errno；该问题不导致重试或假成功，但丢失故障信息。现有 `error` 保留主超时/取消，另以 `write_ack/write_ack_ms/write_error` 保存同epoch唯一实际传输回执；旧epoch/第二次回执不改它。实际总线原始记录仍由owner保存。

`test-result.json`：14组直接执行本目录实际 header 函数，ASan/UBSan、Werror通过。write_done诊断变化后重跑相关13组并新增1组边界，不复用旧hash冒认新代码。覆盖全部128种7-bit首轮结果、DONE长高/结果变化、clear→同结果新DONE、两阶段超时、失败/不确定传输、真detach重新武装/旧epoch、所有活跃phase取消、读失败、时钟倒退、旧serial、等待窗口期间source改变、无效deadline、epoch溢出、未请求回执与独立late bus errno。未执行内核构建/link、硬件写、USB/SSH、SDK、部署或其它旧测试套件。

离线复核：`python3 run-tests.py`。当前只是协议核心验证；R8部署、相机窗口、USB500与图标验收结论均保持。
