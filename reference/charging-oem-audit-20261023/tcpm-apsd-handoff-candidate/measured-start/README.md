# 真实已连接 5V 源接管修订：helper 与 PHY 供应者已完成

本子目录保留真正 off/vSafe0V 接管，并新增**已连接 5V sink** 的实际判定与真实 PD PHY 供电引用交接。它只写新子目录及独立对象 upper；前一版 8 个源码和 `delivery.json` 保持逐字冻结。主任务负责最终 Qcom probe 与共用 ADC reader 接线，因此 `full_probe_integration=false`，不能把本结果称为可部署的完整 PD/APSD 共存。

## 已实现

`qcom_pmic_typec_apsd_prepare(dev, map, &ops, context)` 的 ops 包含统一签名 `int (*read_vbus_uv)(void *context, int *uv)`，以及真实 PHY 提供的 `quiet_begin/quiet_verify/quiet_release`。helper 按值复制 ops；`context` 为原 probe/devres 生命周期里的 `struct pmic_typec`，不保留局部 ops 地址。没有把 token/布尔值当作硬件能力。

off 路径继续只用原四个物理 off 位与实际 vSafe0V/vSafe5V 状态，**不调用 ADC、quiet_begin，也不要求模拟块供电**。混合状态不等于 off，也不以缓存 ONLINE 推导电压。

connected 路径要求：

- 两次相隔 20ms 的实际物理 sink 样本：四个存在位全 on、合法 Rp、sink/去抖完成、无 water/error/noncompliant；Type-C comparator 不处于 vSafe0V。
- 每次调用真实 ADC5 channel 8 回调取得新转换值，以 shutdown 相同的 **4,750,000–5,500,000µV** 工程验收窗核对。该单位直接使用 processed µV，不乘 1000；不取 TCPM `supply_voltage`、ONLINE、缓存 power_supply 电压或最大 PDO。ADC 前后的全部物理/角色字段必须一致，每组读取/回调总时限 250ms。
- 无 QC_DONE、QC 结果 mask0x60，且 `0x1362` 的 HVDCP AUTH/AUTONOMOUS/ENABLE mask0x64 本来已清零。当前处于 QC/高压或仍开着 QC 自动状态的源被拒绝，不通过“降到 5V”或重放旧值来接管。
- 在上述新鲜 5V/sink 检查成功以后，才调用真实 `quiet_begin`。随后每次隔离写前后都再次取得 ADC/角色样本和真实 quiet 验证；连接模式与物理字段必须保持一致。APSD DONE/普通结果可以自然进展，不把它当成掉线；不改现有 native ONLINE。

实际 PHY 供应者在 `qcom_pmic_typec_pdphy.c` 中：

1. `pdphy_probe` 原来只有 `devm_regulator_get()` 和 NO_AUTOEN IRQ，没有供电引用；新增 supplier devres action 在真实 regulator/IRQ/PHY 对象仍存活时清理未转交引用。
2. `qcom_pmic_typec_pdphy_apsd_begin(context)` 仅允许在外层 TCPM port 尚未创建、PHY 自身 port/IRQ 尚未发布、无既有 runtime supply 引用时运行。它真实 `regulator_enable(vdd_pdphy)` 后标记 `handoff_powered`，并在现有 PHY spinlock 内只读实际 `0x174e/0x1744/0x174c/0x1746`，四字节必须全零。任何原有非零、读错或 enable 失败均拒绝，不写 PD 四控，也不 replay/reset 继承值。
3. `quiet_verify` 要求自己确实仍持有这条 pre-start 引用及相同未启动生命周期，再读四控。没有引用就拒绝，**不会盲读未供电模拟块**。regulator API 均在 spinlock 外；source/ADC/helper 的 prepare 不持 port/input/notifier 锁。
4. 正常 `pdphy_start` 先验证 APSD/QC 隔离，再读四控；若存在 `handoff_powered`，把**同一条真实 regulator 引用**转到原 `supply_held`，跳过第二次 enable。随后才走原 PHY reset/enable/IRQ 启动。
5. helper/供应者 devres 只对未转交引用调用真实 `regulator_disable()`；只有成功才清 powered 字段。转交之后 devres 不偷取 runtime 引用，也不产生二次 disable。`samurai_contract_shutdown` 的启动失败分支保留已转交引用，直到主任务原有的 IRQ/work/TCPM join→`finish_5v` 关闭顺序回收。release 错误保留实际 powered 状态及独立错误，不伪造归还成功。

## 最终合并接口

`probe-integration.inc` 给出主任务的最终接线片段。它必须置于真实 `pdphy_probe` 和 profile 判断之后、`tcpm_register_port()` 之前。ADC reader 由主任务绑定到既有 `tcpm->read_vbus_uv`，并与完整 PD shutdown 共用。必须同时合并 `samurai_contract_shutdown` 的错误收尾来源，不能把本目录 start 错误保留分支搭配旧的、不会 join/finish 的 probe unwind。

本目录 `qcom_pmic_typec.h` 已合并完整 shutdown 的 `read_vbus_uv`/contract 字段与上一版 `apsd_handoff` 字段；未覆盖另一代理的目录。`measured-start.patch` 的 PHY delta 以冻结的上一版 handoff PHY 为基线，公共头 delta 以已冻结 shutdown 头为基线，`source.json` 标出各自原件 SHA256。根合并应按字段和函数修改，不能整文件覆盖其它候选。

复用的板级证据：`tcpm-measured-vbus-board-candidate/adc-unit-result.json` 已用实际 ADC5 内核缩放函数确认 channel8、prescale1/16、processed µV；`dtb-result.json` 已核真实 PM8150B Type-C ADC phandle/`io-channels`。本轮不重复这些未变化的高质量测试。这些证据明确没有验证 ADC 物理校准精度。

## 新验证与范围

`test-result.json`：**3708 条断言，156 个实际 PMIC 调用故障点**。直接编译本目录生产 helper，提取执行 8 个实际 PHY 生命周期函数，包括真实 begin/verify/release、start、quiesce、finish；ASan/UBSan 通过，编译零诊断。覆盖 ADC 上下边界/错误/过期、每个阶段 QC/角色变化、缺失回调、混合状态、每个 PD 控制非零、供电引用获取/释放/转交、启动失败 join/finish、无供电不读模拟块及 disable 失败保留实际所有权。未重跑未改的 owner/ADC/DTB 测试。

`build-result.json`：只在 `/home/cy122/charging-management-20261023/tcpm-apsd-measured-start-objects-01` 私有 mount namespace/overlay 编译新 helper 和 PHY **两个 ARM64 对象**，W=1 零诊断；nm 实证供应者三个函数定义以及 `regulator_enable/disable` 的实际外部引用。编译前余量约 WSL768GiB/E142GiB；共享 lower、完整 Image、配置、initramfs、gauge、builtin 元数据和父挂载不变。

仍未完成：主任务的最终 probe/ADC reader 联编、真实源电压精度/状态观察、Request/Accept/PS_RDY 合同证据，以及真实物理 detach 后的 APSD 新周期归还。本修订继续保留上一阶段单向 fence，不把永久关闭 APSD 作为最终共存设计。全过程未访问手机、SSH、刷写、重启、切 USB、链接完整 Image 或部署。
