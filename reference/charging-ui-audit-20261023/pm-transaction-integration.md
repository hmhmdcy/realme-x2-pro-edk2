# 一次性 PM primitive：未来事务接入

实现：[pm-transaction.py](pm-transaction.py)。它只是可导入的库，没有 main／CLI 自动睡眠入口；本子任务未安装到手机、未改旧 r5 或主 charging-pm 脚本。调用者仍需取得独占手机／RTC 窗口，核对当前启动身份、模块与状态，并创建全新的事务目录，不能重放旧 r5。

## 操作顺序

1. 保存 `preflight`，若已有 RTC alarm 直接中止并保留。
2. 保存 `sync_begin`，执行 `os.sync()`，保存耗时和 `sync_complete`。这一段尚未创建本事务 alarm；即使 sync 很慢，也不会吃掉自己的 15 秒目标。
3. 保存 `wakeup_count_read_begin`，读取 wakeup_count，保存耗时和 `wakeup_count_read_complete`。**必须在 arm 之前读取。** 该 sysfs 读取会等正在处理的事件清零；如果先 arm，再被这个等待拖到 alarm 消费之后，读出的新计数就可能吸收自己的 RTC 事件，之后写回会错误地允许无未来 alarm 的入睡。
4. 再确认没有外部 alarm，记录 RTC IRQ 基线，读取当前 RTC 秒数并 arm 新目标，校验 readback，保存 `alarm_armed`。
5. 保存 `entering_mem`。日志可能阻塞，因此把它放在最终检查之前。之后重新读取 alarm、RTC 当前秒数、IRQ；alarm 不等于本目标、剩余不足或 IRQ 已变化，都取消本事务，**不写 mem**。
6. 把步骤 3 的原始 wakeup_count 写回。不重新读一个新计数。计数已变化／有事件正在处理／内核拒绝握手时，立即取消，**不写 mem**。
7. 成功握手后不再写日志或进行慢工作；记录两个时钟后，只调用一次 mem 写。握手接受后才发生的事件由当前内核 `pm_wakeup_pending()` 处理；无法在用户态消除最后一个指令间隙，所以须保留该内核握手保护。
8. 返回后记录单调／BOOTTIME 差值和 `returned_from_mem`，清理仍由自己持有的 alarm。返回 `outcome=returned` 只表示 sysfs 调用已返回，**不是**“实际睡够时间／RTC 唤醒／全部驱动恢复通过”；调用者还须结合 trace、suspend_stats、IRQ、驱动／服务状态验收。函数明确始终返回 `whole_device_pm_acceptance=false`。

RTC since_epoch 是整数，最终剩余时间使用 `target - rtc_now - 1` 保守下界。默认请求 15 秒、要求下界至少 4 秒。所有中止和调用错误都不自动重试；最多有一次 mem 写入尝试。

## OS 边界

`SysfsPMIO` 提供真实 Linux 实现。alarm、wakeup_count 和 state 均以一次 `os.write(fd, payload)` 调用写入；返回短写视为 EIO，不从偏移处继续写第二段。父调用只根据返回证据推进。

读取 wakeup_count 的内核等待是可中断的，不能靠 `O_NONBLOCK` 可靠限时，也不应留下一个无法取消的 Python 后台线程。实现用一次性子进程读取，父进程 `subprocess.run(..., timeout=10)`；超时由 Python 终止并回收该读取子进程，报告 ETIMEDOUT，尚未 arm。没有持久观察进程。sync 本身可以阻塞，阶段日志明确停在 sync_begin，且此时本事务没有未来 alarm 被消耗。

清理只在当前 wakealarm **仍等于本事务 target** 时写 0；如果已经为空，记录 consumed/cleared；如果被换成别的目标，保留。写 arm 前先记“暂定自己目标”，以便短写／异常可能已安装目标时仍可正确清理。清理自身失败明确报告 unknown_or_failed，不盲目再次取消。

RTC sysfs 没有带 token 的原子“比较并取消”；相同时间戳被外部同时重设不能区分，读后取消也不是跨进程原子操作。因此调用者仍要协调独占 RTC 窗口，这个比较检查用于避免清掉已经明确变更的目标，不能替代全局协调。

## 调用示意

未来新的 PM worker 核对身份、创建新目录并准备 trace 后，可使用：

```python
spec = importlib.util.spec_from_file_location('pm_tx', helper_path)
pm_tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm_tx)

# persist_phase 应把 entry 连同本事务 pid/id 写到当前事务目录，
# 失败应抛出异常，让事务在 mem 之前中止，保留原始故障。
io = pm_tx.SysfsPMIO(persist_phase)
transaction = pm_tx.suspend_once(io, alarm_delay_seconds=15,
                                minimum_remaining_seconds=4,
                                wakeup_count_timeout_seconds=10)
# 持久化 transaction。不要自动重试；其后审原 trace/stats/IRQ/状态。
```

正常返回、握手拒绝、清理失败三类结果要分别记录。保持原 RTC／PM preflight 和结束后的驱动验证；不要把此 primitive 的绿色单元测试转写为实机 PM 通过。

## 定向测试

运行 PC 的 WSL Linux（不进入相机 SDK）：

```powershell
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/charging-ui-audit-20261023/test-pm-transaction.py'
```

[pm-transaction-test-result.json](pm-transaction-test-result.json)：**27 个测试方法通过**，测试实际 suspend_once 与真实 SysfsPMIO 实现，使用假的 OS／sysfs 边界；部分方法再逐一覆盖 I/O 和非法参数子例。覆盖 35 秒 sync、20 秒 in_progress 等待、超时、已有／新外部 alarm、日志延迟导致提前 expiry、剩余不足、IRQ 变化、原 count 写回拒绝、不在 arm 后重读计数、短写不续写、写入失败、KeyboardInterrupt 清理、mem 错误不重试，以及握手接受后才来的 RTC 事件由模拟当前 kernel pending 检查阻止实际睡眠。最后一例故意返回 `outcome=returned` 但驻留为 0，验证库不会把“sysfs 返回”当作验收。
