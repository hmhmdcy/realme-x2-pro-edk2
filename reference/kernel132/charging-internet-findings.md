# 充电控制检索与下一步（2026-10-12）

本轮实际检索MP2650输入限流、热保护、USB预算及本机2719关联源代码；找到以下官方来源，尚未获得可直接证明本机完整充电控制的补丁。

- [MPS官方产品页](https://www.monolithicpower.com/en/mp2650.html)：芯片提供可配置的输入限制、温度及电压保护等功能。产品能力不能代替本机电池限值、热敏电路、USB协商与保护链路的证明。
- [MPS官方datasheet](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/)：下一项需将寄存器定义与已经保留的本机OEM实现、实际既有配置逐项交叉核对，区分输入电流、充电电流和OTG参数，形成错误恢复及供电失联契约。
- [MPS官方技术支持讨论](https://forum.monolithicpower.com/t/mp2650-pin-and-register-additional-information/4406)：说明充电使能与BATTFET等路径的控制差别；不是本机接线或安全配置的验收依据。

搜索未找到已验证的本机2719关联实现，继续从已保存本机源码/固件契约追踪。第132轮实际完成的是永久DT注册及标准只读观测；Charging状态、ONLINE1和输入电流读取不等于已经证明实际电池充电速率或Linux控制/保护策略。不能拿评估板或外国板默认参数填补本机缺口，完整系统目标保持不变。
