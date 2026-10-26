# PD-disabled owner R2：真实 context 引用保护

R2 只修复 [036 原候选](../pd5v-owner-feasibility/README.md) 的独审生命周期阻项：quiesce 锁内复制 client 后，另线程 release 可在锁外回调开始前销毁 context。R1 源码、两对象与补充收据完整保留。本版默认关闭，无消费者、无部署；其它 PD/供电/物理 off/路由限制都继承 R1。

[r1-to-r2.patch](r1-to-r2.patch) 是窄差异；[pd5v-owner.patch](pd5v-owner.patch) 是固定 Image363 关联 qcom base 上的完整候选。真实接口见 [qcom_pmic_typec_5v.h](qcom_pmic_typec_5v.h)，精确合同见 [contract.json](contract.json)。

- client 必须提供真实 `get_unless_zero`、`put` 和 `cancel_join`。缺任何一项均在硬件 I/O 前 EINVAL 拒绝。`get` 必须保活 context 与回调代码/数据，且不阻塞、不重入；它是引用操作，不是 PD/route permission。
- acquire 在 I/O 前持一份 context 引用；失败在锁外 put，成功由 lease 持有。quiesce 在锁内、原 lease 引用仍存在时再 pin 一份，才把回调/context复制出去；锁外 join/put。因此并发 release 和 callback 内同步 release 均可立即释放原 lease 引用，context 仍活到回调结束。
- release 在锁内清实际 lease/client，锁外 put。这个 put 可真正销毁包含 lease 的 heap context；release 此后不再读 lease/context。
- 已有主引用却额外 pin 失败，是明确 `EOWNERDEAD` 生命周期错误；不借用旧回调、不假报 join、不作 unmatched put。PM 返回失败且保持 blocked/error，resume 不清错。
- registry 新增一份真实 kref。remove 若无法 join，会保留 removed/blocked 旧 slot、lease/context/device/regulator 引用，拒绝新 probe 接管；最后真实 release 再撤 slot/释放，避免错误尾变成新绑定窗口。这是引用收尾，不是新重试/恢复机制；没有新增 terminal flags、PD 写或默认行为分支。

内部 quiesce/complete/destroy 仍只由 generic device 生命周期串行调用；使用者只调用真实设备 acquire、validate、release。所有 join/put 都不持 PD5V/registry 锁。现有 12 个不受影响的控制函数以及 qcom parent/Makefile/公共容器源逐字保持，见 [unchanged-functions.json](unchanged-functions.json)。

[test-result.json](test-result.json)：只执行 8 组受影响用例，真实生产函数配 Linux/IO 假边界。heap context 与其嵌入的 lease 真正 free，ASan/UBSan、Werror 通过。覆盖 mandatory ops 零 I/O、初始 get 失败/后续 I/O 错的 put、普通 release 销毁、quiesce 解锁点并发 release、callback 内 release、额外 pin 失败的 PM 拒绝、remove 保留旧绑定并最终收尾、pin 成功但 join 不释放的失败。原 7 组没有重跑，复用冻结收据并明确它不等于 R2 并发证明。

[build-result.json](build-result.json)：原 helper SHA/32GiB backing 校验后，只在 R2 独立私有 source/O 执行原 W=1 命令，两个对象实际通过且零诊断。共享源/头/Makefile/.config/Module.symvers 前后哈希不变，有效配置值不变；私有 Kconfig仅补 `CONFIG_VIDEO_QCOM_CAMSS_ICP=n` 注释，已单列。无 Image/module 链接、无 SDK/手机/SSH/USB/Git、新 anchor、卸载或 sysctl 修改。

本版只修软件 lifetime，不证明 PD inactive 的实机状态、physical attach epoch、DPDM/EUD 路由或 5V。后续仍须独立复审、完整会话接入以及真实物理窗口；不能把引用保护当充电或 APSD 许可，也不混入当前保留 Image363 的启动实验。
