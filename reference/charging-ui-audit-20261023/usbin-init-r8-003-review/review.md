# USBIN003：供电状态与电池状态的缓存独审

本轮真实断接已被采集：362 个连续样本、425.578 秒，终态
`cycle_complete`。helper 在物理断开稳定窗口内把 `1358` 从 `c0` 清为
`40`，`clear_verified`；采集中的环境、最终健康和 CV 门通过，fetch 时
7 个自有进程均已 absent。该结论不包含根会话后续 finish/commit/unload。
原始日志和身份只留私有缓存；[review.json](review.json) 记录输入 SHA、
白名单事件值及相对时间。本审查没有设备、SSH、SDK 或收尾动作，也未修改
controller/helper/主文档。

**重接后没有“正在充电”图标，不能从这段数据判为一分钟以上的 DBus 延迟。**
重接后的 51 份标准 Battery 样本覆盖约 61.15 秒，全部 `Discharging`，
`current_now` 为 **-45 至 -20mA**。UPower Battery/Display 没有转成
`State=1 (Charging)`，与这段净放电读数一致。外供在线和净充入是不同值：
同段 mp2650 converter 后来恢复 `Charging`，不能替代 Battery 的净状态。

## 值与时间

以下为从 capture 起点计算的秒数；kernel 项是 netlink 接收时刻，DBus 项
用首尾时钟映射估计。它们不是物理触点或屏幕像素时间。

| 阶段/正确事件值 | 相对时间（秒） | 可解释的间隔 |
| --- | ---: | --- |
| 拔线前 Battery uevent `Charging`、`+4000µA` | 120.389786 | 同窗口确实曾有净充入读数 |
| UPower Battery / Display `State=1` | 120.438626 / 120.441652 | Battery uevent 后约 48.84 / 51.87ms |
| 断开 ACOK uevent `Online=0` | 354.560104 | 数字供电掉线锚点 |
| source 完整 uevent `Online=0` | 354.672804 | ACOK 后 112.70ms |
| UPower source / charger line `Online=false` | 354.558531 / 354.577724 | 外供变化已很快广播，详见下方顺序限制 |
| UPower Battery / Display `State=2` | 358.670877 / 358.673666 | ACOK0 后约 **4.1108 / 4.1136 秒**；完整 source0 后约 4.00 秒 |
| UPower daemon `OnBattery=true` | 358.681820 | ACOK0 后约 4.1217 秒 |
| Battery uevent `Discharging`、`-5000µA` | 359.495340 | ACOK0 后 4.9352 秒；**比已记录 State2 晚 0.8245 秒** |
| 重接 ACOK uevent `Online=1` | 364.303903 | 数字供电恢复锚点 |
| UPower charger line `Online=true` | 364.318846 | ACOK1 后约 **14.94ms** |
| UPower daemon `OnBattery=false` | 364.342549 | ACOK1 后约 **38.65ms** |
| source uevent `Online=1` | 364.857157 | ACOK1 后约 553.25ms |
| UPower source line `Online=true` | 364.866046 | 对应 source1 后约 **8.89ms** |
| source uevent 完整额度 `100000µA` | 364.960839 | 未升级为 500mA 或更高 |
| mp2650 converter uevent `Charging` | 366.108508 | ACOK1 后约 1.8046 秒，属于 converter 状态 |
| 重接后的 Battery/Display `State=1` | **未出现** | 同段 Battery 始终净放电，不能把无此事件写成已测延迟 |

不能强行把所有事件串成固定的“source→ACOK→Battery uevent→DBus”顺序。
断开最早的 source uevent 在 354.554216 秒，但没有 `ONLINE` 属性，不能冒认
为完整 `Online=0`；UPower 还可能据通知读取当前 sysfs 值。因此对应 line
的 false 可以早于第二个完整 source0 uevent。Battery 的 Discharging uevent
也晚于 State2；该 uevent 不能被指为这次 State2 的先行原因。

拔线后的正确 State2 约延后 4 秒，附近标准 Battery 也由 Charging/正读数
转为 Discharging/负读数。缓存能确认这个总过程，但不能单独分摊电量计读数、
内核更新与 UPower 调度各占多少时间。这里始终按正确值配对；不拿相反
State 或仅 UpdateTime/Percentage 当“响应”。

## 100mA 是否升级

本记录所有已知读取及带额度的 source uevent 中，source budget 仅有
`0 / 100000µA`，native 授权仅有 `100000µA`；输入限值始终为 `100000µA`。
断开有 0/ENODATA 暂态，重接第一份样本的 source/native 各有一次 ENODATA，
随后恢复 SDP100；这些未知值没有被填成 100，也不构成高额度授权。
充电请求帽保持 250mA，整包 CV 保持 8.725V。

因此，本次 one-bit 初始化已证实执行成功，但**没有证实 source/native 预算
升级**。采样和事件覆盖之外的瞬时状态不在此断言内。100mA 下本窗口既曾短时
报告净充入，也在重接后持续净放电，不能把 converter 处于 Charging 一概
等同于电池实际净充电。

## 屏幕观察范围

用户估计“拔线约 6 秒变为无充电、重接超过一分钟仍无充电图标”，作为独立
目测保留，没有与 capture 时钟精确对齐。约 4 秒的 State2 事件可供解释和
后续定位，但它不是已测的 6 秒屏幕像素延迟；重接后的无 Charging 状态也
不能改写成“应当显示 Charging”。本次没有屏幕录像或像素时间戳。

首尾时钟偏移变化约 2.4µs，映射端点一致；仍不能排除区间内抵消的时钟
变化。离线样本中的 telemetry flags 被清零且 `flags_fresh=false`，不能把
这些 0 当作原始 gauge flags。原始 Battery 标准 status/current 与所选
uevent/DBus 值均保留在私有原件中；公开材料没有原始日志、UUID、MAC 或 PID。
