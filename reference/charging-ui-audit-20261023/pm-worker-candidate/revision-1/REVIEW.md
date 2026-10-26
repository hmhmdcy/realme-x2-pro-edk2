# 未来新 PM 事务 worker：待根会话审核的离线候选

本目录只准备候选，**没有部署、没有启动、没有访问手机／SDK**。旧 r5 脚本和输出未改。`worker.py` 导入时不建目录、不改 umask、不加载 live helper、不启动进程／PM；只有明确的执行参数才能进入实际调度。审核后的启动与手机、摄像头、蓝牙窗口协调继续由根会话决定，worker 不查询聊天、不自行借还窗口。

primitive 按已审核原件逐字节复制，SHA256 固定为 `fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1`，没有更改它。worker 是本机 RMX1931 的小范围固定事务，没有另建通用调度框架。

## 必须由根会话提供的审核参数

`--execute`、`--window-confirmed` 均必需。后者只记录根会话已协调独占窗口的声明，不是 worker 自行推定设备空闲。

其余参数均显式传入：

- `--transaction`：新的 `charging-pm-...` 名称；禁止 `charging-pm-r5`。对应输出目录和 trace instance 都必须不存在，不能覆盖或重放。
- `--output-root`：已存在的绝对父目录，只在其中新建本事务子目录。
- `--boot-id`、`--manifest-sha256`、`--release`：人工审核的当前采用身份。worker 在任何 I²C 读取之前先检查 boot/release，随后检查 manifest、manager 文件、各模块文件／loaded notes。
- `--live-helper`、`--live-sha256`：复用已审核的现有 live-session.py；只调用其 `state()`，不调用 bind/shadow/guard 等旧事务函数。
- `--previous-receipt`、`--previous-receipt-sha256`：根会话在恢复旧 r5 后生成并审核的终态收据。**本目录不伪造该收据，也不根据 alarm 空或 trace 名不同推断旧事务已结束。**

前 r5 收据必须同时包含：`transaction="charging-pm-r5"`、`terminal=true`、`restored=true`、`worker_exited=true`、`boot_id` 等于本轮采用 boot、`worker_pid=21491`、`worker_path="/root/charging-management-20261023/charging-pm-r5.py"`。worker 再只读检查同 boot 的 `/proc/21491/cmdline`：原 argv 路径仍存在就拒绝；空 cmdline、读取失败或状态不明也拒绝；PID 不存在或已被明确不同 argv 复用才可继续。这个 gate 在 manager／模块核验和任何 I²C 状态读取之前执行，并单独保存结果。

若需要跨新 boot 接续，先由根会话恢复、采用当前身份并生成这份新审核收据；worker 不自行更改旧 boot 证据或判定恢复完成。

## 调度和证据

`dispatch()` 是单次真实调度函数：新建目录→只读前置采集→前置判定→新建独立 trace→调用固定 primitive 一次→保存 primitive 原结果→停 trace／保存原始 trace 和独立清理结果→最多等待 3 秒取新样本→只读结束采集→严格分类。没有自动重试或自动恢复／重启／绑定／切换 USB。

保留原只读前置范围：相机四设备 suspended、M2M无用户／运行／fatal／pinned／orphans、四用户服务各一 uid10000、GNSS非活动、音频关闭及功放 powered0/muted1、s2idle 和 RTC wakeup 已启用、控制充电健康。没有重放旧 +5 秒 RTC 预试验。

不同结果分别保存：

- `previous-transaction-result.json`／`preflight-result.json`：旧事务与前置拒绝证据；此时不建 trace、不调用 PM。
- `primitive-result.json`：primitive 的原始 returned／aborted／failed 及自身 alarm 清理结果；若出现实现外异常，另保存 `primitive-exception.json`。
- `phase-private.json` 与 append-only `phases-private.jsonl`：最新阶段及逐阶段证据；不会只在返回后才写阶段。
- `pm-trace-private.txt`、`trace-cleanup-result.json` 或 `trace-cleanup-final.json`：原始 trace 和清理独立记录。只清理本 worker 成功创建的 instance，不碰已存在 instance；清理失败不自动再次尝试。
- `before-private.json`／`after-private.json` 与 `result.json`：前后只读状态和最终分类。任何例外都保留 passed=false。

## 通过门槛

`passed=true` 需要全部证据，不把 sysfs 返回当通过：

- primitive 正常返回且已消费／清空自己的 alarm，没有清理错误；BOOTTIME−MONOTONIC 驻留在 1 至 20 秒内。
- suspend_stats 的 success 恰好加 1，fail 和所有已有 failed_* 不变。
- RTC IRQ 恰好加 1，并且本轮 `/sys/power/pm_wakeup_irq` 等于从 `/proc/interrupts` 实际识别的 RTC IRQ 号。该属性不存在或无法读取就证据不足；不能只凭 alarm 空／IRQ计数冒认 RTC 唤醒。
- trace 有完整且无溢出的 entries header；charger、USB source、protection、gauge 的 suspend/resume 实际 callback 各唯一且 error0，charger 先挂起、供应者先恢复。prepare/complete 的空 ops 包装不冒充 driver callback。
- boot/release/manifest／模块身份保持，样本真实有效／在线／保护正常／控制请求有效／错误0；charger 配置、原生输入额度、相机状态与四用户服务身份保持，taint0，dmesg未截断且没有新增目标故障。

返回但未睡、非 RTC／未知唤醒、缺 trace／stats／结束健康状态、alarm 或 trace 清理错误，都只能是拒绝／失败／证据不足，不能 passed。

## 离线验证

`python .../pm-worker-candidate/test-worker.py` 当前 **21 个测试方法通过**，测试实际 dispatch/classify/trace/old-worker gate 函数，使用 fake board，部分方法包含多个拒绝分支子例。还直接复用了旧成功 PM 的缓存 trace 验证解析兼容；这仅证明解析器兼容旧格式，不把旧 PM 通过转移给新 worker。

覆盖显式 execute／窗口参数、旧 r5 名称与已有目录拒绝、boot/manifest/模块/旧事务活着或未知拒绝、旧事务 gate 先于任何 I²C／manager 访问、primitive aborted／异常、trace部分建立失败、返回但零驻留、非 RTC或未知 IRQ、缺 stats／trace／健康／清理、dmesg截断或新增故障、结束采集失败仍保留 primitive／trace证据、导入无副作用和 primitive hash保持。见 [test-result.json](test-result.json)。
