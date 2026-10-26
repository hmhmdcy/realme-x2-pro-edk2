# PD5V 036 候选独审：接入前有一个 callback context 生命周期阻项

本审查固定 `qcom_pmic_typec_5v.c` SHA `036ea6c647a7350e0c862c099d450a2e0c4f683785f67d189debac913ac4ed27`，补丁 `1ac3ad957fcb5a521dabb6eab6dbcdcd8466ca5153604ffb0985ac48781c19be`。只读检查最终控制代码、真实 qcom probe/PM/remove 接入、接口、7组/22函数测试的抽取与 fixture，以及构建收据；没有运行入口、测试或编译，没有设备、SSH、SDK、挂载或共享源码写入。

## 确认的阻项

`samurai_pd5v_quiesce()` 在 `p->lock` 内复制 `p->client`，放锁后调用复制的 `cancel_join(context)`。`samurai_pd5v_release()` 只在同一锁下清除 client/lease，放锁后释放 PD5V 对象与本模块的引用，没有获取或等待 client context 的引用。下列交错符合当前接口，且头文件/contract 没有排除它：

1. quiesce 设置 blocked，复制 callback/context，放开 `p->lock`。
2. 客户端另一线程 release 正常返回，然后销毁自己的 context。
3. quiesce 调用已复制的 callback/context。

PD5V 自身的 kref/module ref 不保护客户端 context。锁外 join 避免了组件锁反向，但单纯复制指针不能保证指针寿命。作者已确认没有未写出的调用方序列化约束。**这是未来接入前的真实 API 生命周期缺口；当前没有消费者、没有部署，不是已观测的实机 UAF。** 现有 fixture 的 context 始终是测试中的活 PD5V 对象，同步 join 内释放 lease，未覆盖上述 release/free 交错；通过旧7组不能消除此缺口。

最小后续方向是独立修订 client 引用契约：acquire 持有 client ref；quiesce 在组件锁内额外 pin 复制的 context，再锁外 join，最后 put；release 清 lease 后锁外 put 自己的 ref。cancel callback 必须能够同步 release 而不等待自己结束。本文没有修改冻结候选或用文档假定替代代码修复。

## 本轮其余定向结论

- probe 只 `regulator_get()`，不 enable、不读写 PD block。双 opt-in、精确板型/Type-C 基址和供电 phandle 检查后提前返回，正常 TCPM/port/PD PHY producer 不会在特殊分支注册。默认参数关闭；普通 probe/remove 尾保持，新增普通 PM/shutdown 路径无 PD5V 动作。
- 首次 acquire 在持有组件锁时读取两套新的十字段状态，间隔至少500ms，并核 vSafe0V、真实 detach、继承 sink-only/QC-off；第二次新读时长最多250ms。随后才 regulator_enable。上电失败或上电后状态变化不发 PD 控制写且本绑定终态拒绝，不自动补写。
- 每个控制零写前重新取 status/control 并核时长、状态和 off，依序仅写 BIST/TX/filter/EN。每步保留 write、直接 readback、完整 post 结果；首次写错误即使实际已生效也不会续写、重试、恢复旧启用值或授予 lease。已上电但尚未写的失败同样因 power_attempted 保持终态；并非任意错误都能重试。
- lease 取得对象/module 引用，validate 核唯一实际 lease 对象、generation、removed/blocked/error 与新寄存器读取；未知会失效许可。registry 锁仅包 lookup/kref，不跨 I/O、组件锁或 join。destroy 撤 registry、标 removed 再 quiesce；即使不合规客户端未释放 lease，对象引用仍保留，validate 拒绝后续 I/O。
- PM prepare/shutdown/remove 在组件锁外同步调用 cancel_join；join 未释放 lease 返回或记录 EBUSY，并不假报清理完成。complete 只验证原禁用状态，不重新上电/写寄存器。特殊分支没有 runtime PM 断电机制；不能把将来的 runtime PM 或全部跨组件锁图视作已验证。

500/250ms 是工程门，不能原子阻止读取后发生的电气 attach 竞争；post 失配是失败。成功 PD-disabled lease 也不证明物理 attach epoch、PD/VOOC 全状态、USB预算、EUD/PHY/DWC route/HALT 或完整 APSD 许可。当前无 DT 实装、新 Image 或硬件验收。

## 收据边界

测试收据 `634f7dbe09fd0b3bf14ee9795a3627d334598059ee09285669daa0b9fa2666d5` 绑定上述最终源码，7组/22个实际函数通过 ASan/UBSan 和 Werror；Linux/OF/regmap/regulator/锁边界是 fake，不能称并发全证明。

原叶的旧 pre-power-fix 对象不用于最终源码证明。补充编译正在封最终配置解释收据；本审查将只在作者给出最终收据后另加 hash 绑定，编译通过不会撤销上述生命周期阻项。
