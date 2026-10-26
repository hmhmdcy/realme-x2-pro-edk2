# USB 插拔中断的系统唤醒配置

2026-10-24：已构建、冷更新装机并通过一次 RTC 待机恢复。实际结果见[装机与待机记录](../../charging-session-20261023/usb-irq-wake-update/README.md)及[RTC结果](../../charging-management-20261023/usb-irq-wake-rtc001-result.json)。真实 USB 插拔唤醒尚待现场测试，不能用 RTC 代替。

实际 Image504 对应 `spmi-pmic-arb.c` 的 IRQ chip 设置 `IRQCHIP_MASK_ON_SUSPEND`，`qpnpint_irq_set_wake()` 将请求传给父中断。旧 USB provider 仅申请 `usbin-plugin`、`usbin-src-change`，没有启用 IRQ wake。来源文件及哈希见[source-result.json](source-result.json)。这是当前内核源码确认的配置缺口；没有声称旧驱动已经实测无法唤醒。

新代码在 suspend 中遵循已有 power-supply 的 `power/wakeup` 开关，逐一启用两个已成功注册的 IRQ；resume 逆序释放自身持有的引用。部分启用失败会回退并恢复轮询；释放失败保留所有权位，避免下次重复启用。devres 在停止工作后、释放 PSY/IRQ 前清理，shutdown 也释放自身引用。预算、解码、真实 IRQ 通知和上一轮 prepare/complete 通知修正保持。

[十组实际 C 函数测试](test-result.json)覆盖成对启停、首/次 IRQ 失败、回退失败、恢复失败和 PSY 生命周期；API 为模型，不冒作实物中断测试。[实际单模块构建](ko-result.json)W1/Werror 零诊断，49 个强导入均来自既有内核导出；未重建 Image。模块 SHA 为 `13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4`。

没有改 charger、充电帽、CC/CV、保护、桌面或相机。当前版本只证明启动、一次 RTC 挂起恢复及相关回调成功；物理唤醒、其它电源模式和长待机功耗仍需分别验证。
