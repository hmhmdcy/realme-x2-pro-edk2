# BQ 外接电源事件：本机瞬时模式立即排队候选

本叶以已用于 Image501 的 `0aa3c533…88ffe` BQ 全源为基线，只改 `bq27xxx_external_power_changed()`：`bq27xxx_samurai_instant(di)` 为真时，原 `HZ/2` 排队等待改为 0。全局 opt-in、BQ28Z610、Samurai machine 和实际 BQ 设备节点四个原条件均保留；其它 chip／机型／节点和 opt-out 仍延后 0.5 秒。原模式默认 false，本叶不修改该默认值、参数权限或启动 flag。

`notify-immediate.patch` 是相对501全源的单函数增量，`bq27xxx_battery.c` 是完整结果。反向还原该增量后，整个文件逐字等于基线。NOW／AVG、FC、Full／再充、错误与负净流状态、cache、360秒后备 poll、I2C 和所有充电保护策略不变。本叶不修改 Phosh／UPower，也不新增桌面提示。

## 原因和作用范围

R8 已通过实际 Battery 名字建立 supplied_to 关系。BQ 的原回调每次以 `mod_delayed_work(...,HZ/2)` 排原工作，后来的通知可以重排这个等待。此候选仍异步排同一 work，不在 power-supply notifier 内做 I2C，也不增加 poll 或无条件广播。已有 worker、取消和 remove 生命周期保持原代码。

已冻结的相邻 [底层时序报告](../bottom-latency-source-plan-image501/README.md) 区分 source 在线、安全额度、converter 充电状态和实际电池净流。R8 已有立即 source notifier、apply 后读取状态和按变化通知；本叶不重复修改它们。charger getter→BQ 的锁序和原通知方向不变。

此改动仅消除一个可确认的固定软件等待，不证明实际图标一定快 0.5 秒。旧真实 attach 中 Display 的 D-Bus 更新还曾早于 BQ uevent；预算未就绪、硬件或 gauge 未变号时仍如实报告旧状态。501 最近一次采集无真实 off 边沿，不能据此宣称本候选或501已完成延迟验收。

## 新验证与实际对象

`test-result.json`：7组，直接抽取最终源码的原严格 gate 和新 callback，ASan／UBSan／Werror 通过。覆盖本机 opt-in／opt-out、其它 chip／machine／node、缺失 node、既有360秒 pending work、重复通知和运行中工作重排。OF 与 workqueue 边界由 fixture 提供；这是实际回调的请求验证，不是 Linux scheduler 并发证明。未重跑旧电流、保护或整机套件。首轮 include 行尾的本地 hash 预检失败发生在编译前，保留于 `history/`，修正为明确 LF 后的实际通过收据独立保存。

`object-build-result.json`：原 Ubuntu/root kernel284 storage helper 验证／复用既有32GiB卷，直接复用旧 BQ 保存的 W=1 gcc 命令，只替换 source、输出和 dependency 路径并增加 `-Werror`。仅编一个私有 `bq27xxx_battery.o`，实际 PID816 已 wait 终态 rc0，用时约1.18秒，stdout／stderr 均空。原私有 O／source 和 shared source／CONFIG／Module.symvers 等16个跟踪输入前后 SHA 全相等；没有 make、链接、Image／ko、新 SDK／设备／Git 操作，没有卸卷或改锁。

私有对象：`/home/cy122/charging-management-20261023/gauge-notify-immediate-object-01/bq27xxx_battery.o`，SHA `8828cf5d2012cab140d2d5aaa50f8816c5809bdd5771f58466877a1fd23d43eb`。原件、编译 stdout／stderr 和私有结果仍保留；对象不进入公共交付。

原501 build／ABI 与 CCI provider addendum 的通过收据只作为原基线、配置、模块关系来源，见 `delivery.json` 的 source_receipts。此次没有重做链接或新 ELF 导出核验，因此它们不等于新 Image 的 ABI 或实机验收。

## 入口与状态

默认只查本叶 hash，不调用 storage helper 或 compiler：

```text
python -B reference/charging-ui-audit-20261023/gauge-notify-immediate-candidate/build-object.py
```

实际单对象已执行完成，`--execute` 对已存在的唯一输出／收据拒绝重放。`prepare.py` 和 `run-tests.py` 是来源／定向测试脚本，冻结后无需重跑。`delivery.json` 绑定实际 source、patch、测试、对象与来源收据。

状态：候选可审，未链接新 Image，未部署，未采新边沿；后续集成／现场窗口由根会话统一协调。本线已结束所有 WSL／guard／编译过程，并通知 USB 对象作者接用串行窗口。
