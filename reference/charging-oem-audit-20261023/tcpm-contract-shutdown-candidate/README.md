# 高电压合同 shutdown 前真实请求 5V：离线候选

2026-10-25。源码和保留产物均在此目录，最终检查也将编译临时目录固定于此处；初次测试编译器使用默认临时目录的情况保存在 retained-failures.json。未访问手机、SSH、USB、刷写或重启，未运行完整 Image 构建，未改变旧候选、镜像层或 Git 状态。当前实现和检查均为离线证据，**不表示 9V、ADC 精度或完整 PD 已通过实机验收，也不允许据此启用高压**。

`tcpm_prepare_sink_shutdown(port, timeout_ms, read_vbus_uv, context)` 新增终端受电准备接口。它使用现有 AMS、PDO/RDO 生成器和协议 worker，先封锁新的 PPS/AVS、公开 PD/角色选择，再把选择器限制到实际 source/sink 能匹配的固定 5V PDO；不修改、覆写或伪造双方 PDO。PD 连接每次都发送新的 Request，只有本次 SOP Accept 和 SOP PS_RDY 才完成专用 completion；Reject、Wait、发送失败、reset、超时均保留为失败。原状态机的复位、放电阈值、告警和保护处理保留。

协议完成后还需 3 次新 VBUS 转换在 4.75–5.50V 范围内，相隔 20ms。该范围是待校准和实机确认的候选板级验收策略，不是新增的规范要求。采样前后以及返回前检查相同合同状态序列；合同变化返回 `-EAGAIN`，9V、欠压或不稳定样本不能凭缓存通过。`supply_voltage` 仅作协议状态证据，绝不作为测量值。失败后终端只选 5V 的策略仍保持，可以重试此准备接口。

ADC callback/context 是接口参数，**通用 `struct tcpc_dev` 布局逐字保持**。调用者负责保证 port 和 provider 存活、串行化 unregister/控制器 teardown。执行 ADC callback 时 `port->lock` 和 `swap_lock` 都已释放，允许 provider 反查 TCPM；callback 必须有自己的有限转换时间，API 超时不能中断一个不返回的 provider。

QCOM 可选接入 `io-channel-names = "vbus"`，只接受实际 `qcom,spmi-adc5`、`IIO_VOLTAGE`、`ADC5_USB_IN_V_16` 通道，并用真实 OF 父节点相等及 `reg = 0x3100` 确认来自本 Type-C 所在同一 PMIC。此内核的 ADC5 processed 路径直接返回 µV，consumer 原样使用，不能再乘 1000。provider 不存在时不安装 reader；非固定 5V 的 Samurai sink/device 配置缺 reader 时拒绝 probe。板级 ADC8/引用接线及实际原函数缩放测试由相邻 [板级候选结果](../tcpm-measured-vbus-board-candidate/dtb-result.json)提供，原 PDO 没有提高；[单位结果](../tcpm-measured-vbus-board-candidate/adc-unit-result.json)记录 raw8670 → 9,000,000µV。当前仍缺物理精度、原厂对照、偏差和真正转换时序验收。

成功准备后才进入原有 IRQ/work/TCPM join，再依次关闭 BIST/TX/filter/EN、逐项读回，成功才放 PDPHY 电源引用及恢复 sink。Full-PD probe 在协议已开始后失败，也会先尝试同一准备路径。未开始协议或准备失败的强制清理只 join 回调，不声称已确认 5V 或完成该关闭序列。TCPM join 后再次 join 最后可能排入的 CC debounce。

**remove 失败边界仍未解决为安全高压移交。** 当前 platform `.remove` 返回 void，不能拒绝解绑或阻止 devres 释放。准备失败时 shutdown 保留活动协议；remove 则必须结束全部 IRQ/work/TCPM 回调以避免释放后访问，并记录原错误，不恢复 SNK_ONLY、不声称 5V、不假设保留 L2 引用等同 provider/devres 存活。这是必须在高压采用前解决的外部移除策略和关机失败策略边界；本候选没有冒充“所有失败下仍能安全关机”。

验证结果：

- [TCPM 控制测试](test-contract-result.json)：14 个完整生产函数，覆盖真实 RDO、Accept/PS_RDY、SOP' 排除、拒绝/超时/reset、cached5V+physical9V、ADC 错误/不稳定/超时、合同竞态、无锁重入及终端策略保持。
- [QCOM 生命周期测试](test-qcom-result.json)：18 个完整生产函数，复用既有真实关闭读回测试并补成功请求先后、失败 shutdown、void remove、最后 CC debounce、重复调用及关闭后错误。
- [IIO consumer 测试](test-adc-result.json)：2 个完整生产函数，核 provider/channel/type、缺失/defer、错误传播、µV 原样转交。以上测试以 ASan/UBSan、`-Wall -Wextra -Werror` 通过；调度器、硬件、IIO、IRQ/工作和设备生命周期边界有显式模型，不能当实机证据。
- [对象构建](build-result.json)：复用已有源码与构建目录，在私有 mount namespace 只读挂载旧层，直接复用原 W=1 编译命令检查 6 个相关对象，零诊断。最后的同 PMIC 身份收紧只重编 port，5 个对象按源码和对象哈希复用；没有 make、Image 链接、配置生成或旧层 copy-up。C/E/WSL 余量已分别核对，全部输出均在此目录，父 mount 状态保持。
- [源码与 API 布局核验](source-review.json)、[可审查补丁](shutdown-contract.patch)绑定实际基线和最终源码。

下一步先由根会话整合板级候选、明确移除及关机失败策略，再安排有界物理 ADC/5V/9V 协议验证。手机 506 的真实 10 小时计时不受此候选影响。
