# PD5V context R2 薄审

固定新源 `19bb52a981b0a44ab4069013df5d866717e7870f2ab1fe86a9fb7eb8bc7e1b32`、头 `30c92b72f2a5384cc51f2c0b1df9e98d277cb44d47ea4074d668fd715b869656`，窄差异 `024341cd…ca3a4`、完整补丁 `473905ef…184ce`。原 036 的 callback/context 生命周期阻项已在本轮新增软件范围闭合，未发现另一个接入阻断。此前 [036 审查](review.md) 与原件保留；这不撤销其历史结论，也不是完整 APSD 或硬件批准。

acquire 缺失 mandatory get/put/cancel_join 在任何硬件 I/O 前 EINVAL；初次 get 失败同样零 I/O。成功先持有真实 context 主引用，再进行原物理/电源/控制操作。失败在放开组件锁后 put，成功将主引用交给实际 lease。header 明确 get 必须不阻塞、不重入，并保活 callback 代码和数据，不能是固定 permission boolean。

quiesce 在组件锁内、原 lease 主引用仍存在时取得额外引用，再复制 callback/context；放锁后 join/put。因此另一线程在 unlock 点 release，或 cancel_join 内同步 release，都不会使回调借用已释放的 context。release 清除实际 lease/client 后在锁外 put；这个 put 可以真正释放含嵌入 lease 的 heap context，后续代码只使用仍有 lease kref 的 PD5V 对象，不再读 lease/context。额外 pin 失败记录 EOWNERDEAD，既不借用旧回调也不假报 join，PM 保留 blocked/error。

registry 新持一份实际 kref。remove 若无法 join，removed/blocked 旧对象、旧 slot、lease/context/device/regulator 引用保留，新的 probe 返回 EBUSY；最后真实 release 才撤 slot并收尾。p→registry 的撤 slot 嵌套没有对应 registry→p 反向：acquire 的 registry lookup 在进入组件锁前已放开 registry。所有 join/put/free 均在两个组件锁外。quiesce/complete/destroy 仍依赖文档规定的 generic device 生命周期串行调用，不是给消费者任意并发调用的 API。

已只读检查实际窄 diff、完整源、8组新增测试的真实函数抽取/确定性交错 fixture，以及最终对象收据。测试 `dd82be75…1d1f8` 和构建 `a7a7b841…3845b` 绑定上述源；对象 `e6dd8c4a…791df` / `a578eef6…c6c06` 的 W1 构建无诊断。fixture 确实 heap-free context/嵌入 lease，但 kernel/IO/锁调度边界为 fake，不能称全并发证明。qcom parent C/公共容器头/Makefile 与036逐字相等，物理门、上电和四个控制零写路径未扩大。完整 hash 绑定见 [context-r2-review.json](context-r2-review.json)。审查者没有运行入口、测试、构建、设备/SSH/SDK、挂载或 Git mutation。

当前默认关闭、无消费者、无 DT 实装或新 Image/module 部署。真实电气 off/vSafe0V、新 attach、PD/VOOC、EUD/PHY/DWC route、预算和完整 session 许可均不由本轮引用修复证明。
