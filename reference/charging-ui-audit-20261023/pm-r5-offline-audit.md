# 新通知模块后 s2idle 未恢复：离线审计

2026-10-23，仅审代码和 PC 缓存。没有访问手机、SDK、触发恢复或再次执行 PM。现有观测是 USB 正常复合设备未恢复；没有手机端新 PM trace、phase、RTC IRQ 或进程栈，**不能确认设备是否进入／退出睡眠、是否发生锁等待，更不能认定根因**。

## 新通知代码的锁序和依赖

构建记录的 charger 模块为 `9d9e1cd7fb0e68b741b315c1f8d74caf05288dccc38dc8024c3a64cb8d631016`，对应 C SHA256 `986e16af8289deedcbf2885211c5cd407ca2c0aff2692ca4bc7fdbfa3a6a458e`；此离线检查确认当前生产 C 匹配该源码哈希。以下结论来自当前生产代码与已保存 source354 的 bq/core 源，不是仅根据候选文档推断。

1. 新 `sm_notification_locked` 仅在 `sm_poll` 内、现有 `sm_step_locked` 返回后调用，持有 charger `c->lock`。collect 的原 gauge segment 锁、protection 的 gauge segment 锁均已释放；额外 reg13 读返回后才调用原 bq STATUS。
2. bq getter 获取 `di->lock`，过期时 update，释放 `di->lock` 后读取即时 AI／FLAGS。update 在持 `di->lock` 时可能调用 `power_supply_changed(battery)`，但该函数只用自己的 changed spinlock 置位并排异步 work，不同步调用 charger。charger notifier 明确只接受 input/protection，不接受 battery。没有从 bq lock 返回 charger lock 的源码边。
3. 最后 charger 先释放 `c->lock` 才调用 `power_supply_changed(charger)`。其异步 supplied_to 回调调用 bq `external_power_changed`，后者只 `mod_delayed_work(..., HZ/2)`，不获取 charger lock。
4. `sm_suspend` 先拿 `c->lock` 置 paused，**释放该锁之后**才 `cancel_delayed_work_sync(c->work)`，随后重新拿锁执行原 `sm_stop`。不存在“持 c 锁等待其 work 完成”的自死锁。如果 work 正在执行，suspend 会先等它的同步 I²C 与 bq getter 返回；因此底层传输异常仍可能拖延 suspend，但当前没有堆栈或超时日志证明本轮如此。
5. 新保存的 Battery 是 `power_supply_get_by_name` 引用，并有 devm put；没有新增 battery→charger device_link。既有 charger→gauge 和 charger→input/protection supplier link 保持，通知关系 supplied_to 与 PM device_link 是不同机制，未见新增反向 PM 依赖。
6. `sm_resume` 只清 paused、令通知签名失效并排立即 work；STATUS 读取不在 resume 回调本身执行。已有 gauge supplier 在 charger consumer 之前恢复。原 bq suspend 仅取消自己的 delayed work，不锁 charger，也不等待 charger callback。

**结论：没有找到新增的静态 mutex／device_link 环，不能因此证明新代码 PM 通过，也不能排除具体 I²C 等待、已有异步 PM 竞态或 USB 恢复故障。** 新模块之前只有服务和稳定事件验收，旧模块的成功 PM 结果不能覆盖这次失败。

## RTC 先消费的可能性

此次实际发送的 `pm-r5/worker.py` 顺序经核对为：

```python
target = int(rtc_since_epoch) + 15
alarm.write_text(str(target))
phase('armed-before-suspend', alarm_delay_seconds=15)
os.sync()
mono = time.monotonic()
bt = time.clock_gettime(time.CLOCK_BOOTTIME)
power_state.write_text('mem')
```

它在设置 15 秒 RTC alarm **之后**执行全局 `os.sync()`，既没有记录 sync 耗时，也没有在 sync 后重新核对 since_epoch、alarm 剩余时间或 RTC IRQ 计数。`time.monotonic()`／BOOTTIME 测量起点更在 sync 返回之后，因此即使未来取回“很短的 sysfs 调用时间”，也不能倒推出此前 sync 没有消耗 15 秒。

若 phase 写入／sync／内核进入 suspend 前的工作消耗了该窗口，RTC 中断可以在真正进入睡眠之前先发生并清空 alarm；随后 mem 进入睡眠时已没有未来的 RTC 唤醒。用户看到的外观会是“预期时间未自动醒来”。这是当前工具允许的**可行失效机制**，并非已经发生的事实。旧 PM 成功样本说明旧次该顺序碰巧仍赶上了 RTC，不证明本次也赶上。

工具也未采用 `/sys/power/wakeup_count` 的事件计数握手，无法依靠代码保证“计时到期但随后仍进入睡眠”被拒绝。仅把用户态 sync 前移能减少风险；内核进入 suspend 的同步／freezer／设备回调仍可消耗时间，所以稳妥的下次工具还应使用标准 wakeup_count 机制防止已处理的唤醒事件在入睡前丢失。

已只读核对当前 source354 的 `main.c::wakeup_count_store`、`drivers/base/power/wakeup.c::pm_save_wakeup_count/pm_wakeup_pending` 和 `suspend.c::enter_state/s2idle_enter`：[源码摘录与 SHA](pm-kernel-excerpts.json)。保存计数时要求无新事件且无正在处理事件，之后 s2idle 入口检查已保存计数是否变化；`enter_state` 本身在启用 sync_on_suspend 时也先执行 `pm_sleep_fs_sync()`。这支持上述工具修正依据，并不提供此次 alarm 是否提前消费的运行证据。

## 下一步所需证据与最小工具修正

先等待根会话安全恢复通信后读取同一 `charging-pm-r5`，不要重放该已启动事务：

- phase 若仍 armed，不能区分卡在 sync、卡在 mem 或 mem 尚未返回；当前 phase 写法在这些阶段不更新。
- RTC IRQ、wakealarm、suspend_stats 和原始 trace 可区分 alarm 是否触发、是否进入设备 PM、是否完成恢复。若有栈，重点看 c mutex／bq mutex／I²C adapter 等待位置，不能单靠“最后一个 callback_start”归因。
- 用户短按电源后的屏幕/USB/新 boot ID 只能作为进一步状态信息；不能把一次 host 端复合设备消失直接等同内核死锁。

未来另开 PM 事务时：先 `os.sync()`，记录其起止耗时；在同步之后再设置新的相对 RTC 目标；分开记录 `sync_complete`、`alarm_armed`、`entering_mem`（含 RTC 当前时间、剩余秒数、IRQ）、`returned_from_mem`；入睡前剩余时间不足直接取消本次，不自动重试。按标准 wakeup_count 读取／设置握手保护 alarm 到期与入睡的竞争，握手失败保留失败并中止。这个修正不需要更改充电／USB 驱动，也不能替代本次 PM 故障证据收集。
