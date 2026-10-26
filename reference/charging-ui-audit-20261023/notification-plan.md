# 最小底层通知修正建议

本文件是根会话可实施的精确方案，尚未修改／编译／部署生产代码。安全策略的 1 秒采样和源变化立即重新评估保持；只收敛用户态通知。

1. 在 charger 私有结构保存上次通知签名与 valid 位。`sm_poll()` 执行现有 `sm_step_locked()` 后，在同一 mutex 下生成签名，只有首个有效签名或离散字段变化才调用 `power_supply_changed(c->psy)`。调用仍在解锁之后。
2. 签名包含：实际 0x13 的 ONLINE 与 CHG_STAT 位／该次读取 errno；`last_error`、`stop_error`、`latched`、`source_inhibit`；`auto_requested`；离散 `target.enable/input_ua/current_ua/cell_uv`。不要包括 age/session_seconds、连续 ADC 电压／电流、普通温度微小抖动。温区变化导致目标限值变化会自然通知，故障进入与恢复也会通知。
3. 实际 0x13 可在每次策略循环末尾再读 1 次，仅用于通知签名；读取失败必须作为签名的一部分，不用上次状态伪造有效值。也可重用本循环已有的最后一次成功状态读取，但必须明确有效性和当次硬件写入前后的顺序，不能把旧样本充电位当成刚写后的硬件状态。
4. 保留已建立的 `supplied_to` 标准关系。真实 charger 变化仍让原 bq 走 0.5 秒稳定延时后上报，无须另造 UPower 刷新 daemon 或用 udev 脚本反复触发。
5. 启停、限值写入及 resume 路径的显式通知可先保留；这类操作不形成每秒事件负担。不要为这次 UI 优化改变保护判定、充电寄存器时序或电流额度。

仅以上变化会消除“charger 始终 Charging、硬件限值不变时”额外的 1Hz gauge 更新。它不能独自保证负载变化使电池净电流翻转时低于 30 秒的图标响应，因为 charger 可以保持同一状态。

若这也是用户看到的剩余延迟，应再把**原 bq 的标准 `POWER_SUPPLY_PROP_STATUS`** 结果及 errno 纳入签名，并保持实际 gauge power_supply 的生命周期引用。这样继续使用当前 bq 驱动对型号、FC 与净电流的解释，不把 CHG_EN 误作电池净充电，也不在 charger 中重复发明协议。原 bq STATUS getter 本身是即时读取，跨 mutex／I²C 路径需确认没有锁序回边；当前 bq getter 只锁自身，独立读取 gauge，无 charger 回调。

相比把原 bq poll_interval 全局改成 1 秒，这个方案少发重复全属性 uevent，同时可对真实 battery 状态边沿发通知。若将来加入方向防抖，只能针对接近 0 的边沿抖动，必须仍准确表示负净电流；不宜为了“插线图标”硬编码充电状态或仅凭 USB configured 推断供电存在。

验证应直接比较受影响窗口：稳定连接时重复 mp2650 uevent／UPower line UpdateTime 显著下降，物理断开停充与重连恢复原有验收保持，原 bq 与 UPower State 的真实转变在事件链内可追溯。无需重建 Image/rootfs、修改 Phosh 或相机栈。
