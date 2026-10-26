# 通知候选交付与锁序

候选补丁：[notification-state.patch](notification-state.patch)。它以 `a53260fce32e667debe055233ce24e28a4f3db2243228dd429ddc2c6ffc69e26` 的 charger 源为基线；根会话之后另行合入了 charge-cycle 改动，因此**不可整文件覆盖生产 C**。合入补丁中的通知相关段即可；两者没有共同修改安全策略正文。

新增生产头文件为 `charging-notify.h`。构建、源码哈希清单、测试清单、维护补丁导出及交付归档中也要包含它；现有 `build-integrated.py`／`prepare-kernel-patch.py` 的显式源列表需要根会话补入。本文及本目录没有改这些共享文件。

## 改动

- charger 保存按实际 gauge 父设备发现的 Battery 名称对应的 `power_supply_get_by_name()` 引用，验证 type 和父设备，注册 devm `power_supply_put()`。原 gauge 的 device reference 和 PM device_link 保持。
- 安全策略采样后，读实际最终 0x13，并只纳入 ONLINE／CHG_STAT 位；错误与值分别存储。
- 调用原 bq 标准 STATUS 属性，把净充电／净放电／Full 及 errno 加入签名，保留当前原生驱动对型号的解释。charger 持续 Charging 不会覆盖电池 Discharging。
- 签名包括现有 health、策略及停止错误、latch、源抑制、auto、样本有效性与离散目标限值；只在变化或首次样本时通知。连续 ADC、温度微小波动、age/session 不参与。
- source/protection notifier 仍立即排安全 poll；sysfs 显式事件保持；resume 使通知签名失效，首个新样本必发一次事件。

## 实际当前链路的锁顺序

`sm_poll` 先持有 charger `c->lock`，执行原 `sm_step_locked()`。原 source/protection/gauge 所有 I²C 事务返回时均已释放 adapter segment 锁。随后新通知采样先 `sm_read(0x13)`，该传输返回后才进入原 bq `power_supply_get_property(STATUS)`。外层持有 charger mutex，没有在持有 I²C 总线锁时获取 bq mutex。

原 bq getter 在自己的 `di->lock` 内检查 5 秒 cache；必要时更新，随后释放锁并即时读取 AI/FLAGS 计算状态。这些读取不调用 charger。bq 的 `power_supply_changed()` 只置位并排异步 work，不同步进入通知消费者。charger notifier 又明确只接受 `input` 或 `protection`，因此 battery 事件没有回到 charger mutex 的边。

最后 `sm_poll` 先释放 charger mutex，才调用 `power_supply_changed(charger)`。其异步 work 依据 supplied_to 调用 bq 的 `external_power_changed`；该回调仅排 0.5 秒延时 work，不反调 charger。当前这条链没有 `bq mutex → charger mutex` 回边，也没有 `I²C lock → bq mutex` 的新倒序。

生命周期按 devm 逆序释放：最后注册的 charger cleanup 先注销 notifier、停 work 并停充；随后自身 power_supply 被 unregister，之后才 put 新保存的 Battery 引用。注册失败时未启动 work，已获得的引用也由 devm put。候选没有添加强制卸载、解绑 gauge 或绕过原保护的路径。

## 必要定向验证

[notification-test-result.json](notification-test-result.json) 记录实际候选 `sm_notification_locked`、`sm_poll`、`sm_resume` 函数体抽取编译的 **54 项 ASan/UBSan 案例**，其中包含 100 次稳定 poll：每次仍执行安全步骤、寄存器读取和 Battery STATUS 读取，只有第一次通知。记录边界验证读取顺序为 safety step → 0x13 → Battery STATUS → 下次 poll 排队 → 解锁后的通知；覆盖独立电池状态变化、错误进入／重复／恢复、真实寄存器状态变化、无关状态位、各类离散限值、暂停和恢复。

源比较另外确认 `sm_step_locked`、collect、gauge sample、get/set property、source notifier、suspend、cleanup 与该候选基线逐函数相同。此比较只针对本通知改动，不能阻止根会话合法合并 cycle 改动。

[notification-patch-test-result.json](notification-patch-test-result.json) 证明补丁能在本审计目录的基线副本上应用，生成的两个文件与候选逐字节相同。Windows Git 的全局 autocrlf 会改变应用后的换行，所以检查命令使用局部 `-c core.autocrlf=false`；没有改 Git 全局配置。

这不是完整内核构建或实机验收。根会话合并 cycle 后应增量构建 charger 模块，并在取得手机窗口后验证：稳定状态重复事件明显减少、状态变化事件仍到达 bq/UPower、实际预算和保护不变。无需刷写 boot、改 Phosh 或动相机栈。
