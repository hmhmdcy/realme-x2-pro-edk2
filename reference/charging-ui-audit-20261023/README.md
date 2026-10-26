# USB 充电图标延迟：离线链路审计

2026-10-23。仅在 PC 分析源码和已有缓存；未连接手机、未使用 SDK、未改充电目录或生产模块。

## 已证实的事实

`usb-hotplug-r4/capture-private.json` 为 600.305 秒观测，570 个样本的 source online 始终为 1，没有物理断开样本。用户随后报告的拔插与延迟不在这个窗口内，不能用此缓存认证拔插或图标修复。

该窗口有 520 次 `mp2650-input` change uevent，中位间隔 1.1516 秒，对应 520 次 UPower line-power `UpdateTime` 属性通知。这是 charger 轮询无条件调用 `power_supply_changed()` 的实测成本。原 bq 电池有 1 次 change uevent；常规 UPower 电池／DisplayDevice 刷新约 30 秒一次。是否每次 charger 通知都实际执行了 bq I²C 刷新，缓存没有函数跟踪，不能用“只有 1 次 bq uevent”否定它：原 bq 只在容量、flags、status 改变时发送事件。

唯一 bq change 事件接收时间为 0.255652 秒，状态 `Discharging`，电流 −5000µA；DisplayDevice 的 `State=Discharging` 信号估算时间为 0.304020 秒，相差约 **48ms**。这是时间上的关联，且跨时钟映射只有一个锚点；不能冒充严格因果测量或显示面板绘制时间。它至少表明本轮没有“每个真实 bq 事件都被 UPower 固定缓存 30 秒”的现象。

根会话后来只读取得的当前状态也为：SDP 100mA、charger 硬件 `Charging`，原 bq 电池 `Discharging`／−4000µA，UPower/DisplayDevice 同为 Discharging。输入受限时，充电器工作和电池净放电可以同时成立；强制把桌面状态改为 Charging 会掩盖真实净放电。

## 真实通知链与源码依据

现有 charger 通过实际 gauge I²C 父设备找到原 Battery power_supply，并把其名称填入 `power_supply_config.supplied_to`。`power_supply_core.c` 以 supplier→supplicant 方向调用电池 `external_power_changed`；原 bq 在 0.5 秒后更新，只有状态／flags／容量改变才再次 `power_supply_changed(battery)`。charger notifier 仅处理 source 和 protection，不处理 battery，所以这个新关系没有产生 charger↔battery 的回授环。

但每秒 charger `power_supply_changed` 会把原先 360 秒的 bq 后备轮询反复提前到 0.5 秒。它增加 I²C 与工作队列唤醒，不应长期作为图标及时性的实现。标准关系应保留，通知应改为离散状态变化驱动；详见 [最小修正方案](notification-plan.md)。

已缓存官方 UPower **v1.91.0** 源，与根会话读到的 daemon-version 相同。这里只证明该版本主源语义，没有声称已逐字节匹配发行包补丁：

- `up-enumerator-udev.c`：change 事件直接调用 `up_device_refresh_internal(..., UP_REFRESH_EVENT)`。
- `up-device.c`：直接调用目标设备 `klass->refresh()`，此处无 30 秒节流。
- `up-device-supply-battery.c`：uncached 读取 status/current；当非 FullyCharged 且 `current_now<0` 时报告 Discharging。
- `up-device-battery.c`：直接设置 `state`；30 秒常规 poll 是后备更新，line-power 变化还会触发一段更快轮询。没有针对已收到真实事件的 30 秒 State 去抖。

Phosh 官方只读镜像固定提交 `a3cded46d6c6ad8f51678834cd17e95967cc0702` 的 battery-manager 从 UPower DisplayDevice 监听 `notify::state` 和 `notify::percentage`，生成图标并绑定到 battery-info；不依赖 USB UDC 的逻辑 configured 状态。当前实机 Phosh 精确版本尚未取得，因此此处为主源语义参考，不能代替当前二进制验证。

来源 URL 和 SHA256 见 [主源清单](upstream-sources.json)，实际内核 bq/core 源哈希见 [内核清单](kernel-sources.json)。使用了已有 source354，仅只读复制这两个小文件，没有构建或写共享树。

## 如何复用审计器

运行 PC 上的纯离线工具：

```powershell
python reference/charging-ui-audit-20261023/audit-ui-cache.py E:/edk2-samurai-out/charging-management-20261023/usb-hotplug-r4/capture-private.json --output reference/charging-ui-audit-20261023/r4-ui-audit.json
python reference/charging-ui-audit-20261023/test-audit-ui-cache.py
```

审计器读原始 capture 或包含 `capture` 的 fetch 外层对象，解析真实 D-Bus PropertiesChanged 标量、统计事件负担、按 source 样本 online 变化列出拔插区间，并把 source→battery 同时钟通知延迟与 source→DisplayDevice 跨时钟估算分开。没有记录 State 变化时保持缺失，不把 UpdateTime 或持续 online 事件捏造成一次物理拔插。当前 13 项边界检查通过，包括截断／无接口／错误布尔值、多信号、多类型、无事件、同状态、缺失 State、时钟跳变和 fetch 包装。

结果见 [r4 缓存审计](r4-ui-audit.json)。工具始终明确 `screen_icon_latency_verified=false`。下一次采集至少需要把实际动作放在已确认存活的观察器窗口内；要严格跨时钟测量，还要记录起止 REALTIME/MONOTONIC 对，并确认没有时钟跳变。仅凭内核、D-Bus 日志仍不能验收屏幕实际绘制延迟。

## 可合入候选

已按根会话后续要求生成 [最小通知补丁](notification-state.patch)：保留原 bq 引用，以实际 charger 状态和 bq 标准 STATUS／errno 及离散策略状态决定通知，稳定 poll 不再无条件发事件。实际候选函数 54 项 ASan/UBSan 案例、100 次稳定 poll 和副本补丁应用验证通过；尚未在本子任务构建内核模块或部署。新增头文件、cycle 并行改动的合并边界及锁序依据见 [整合说明](notification-integration.md)。

后续 r5 PM 异常的静态审计见 [PM 证据边界](pm-r5-offline-audit.md)。已另写 [一次性 PM primitive](pm-transaction.py) 和 [未来事务接入说明](pm-transaction-integration.md)，27 个实际实现／假 OS 边界测试通过；没有改旧 r5 或自动触发新睡眠。

取回r5实测后的 [重新定级](pm-r5-qualified.md) 明确：恢复回调／配置有证据，但3396.192秒驻留使15秒RTC计划失败。原始passed真值保留，独立qualified结果为false，未冒认RTC唤醒。
