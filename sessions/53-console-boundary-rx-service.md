# 53. 在 console 完整 TX 帧边界服务 RX（2026-10-10）

**本轮实现并验证了针对长日志缺 RX 的改动，整体稳定性仍未解决。** 同 RX51/52 的
1009 字节日志期间，一次 7 字节原生输入在 libusb 和 Windows 两条路径都进入 RX/tty、
取得 `via=console` 回执并执行；日志 990 个零完整，两个 TX 快照各 512/512 直接匹配。
但重启后安装终端又缺了首条状态的一个 4 字节前缀，软件记录已独立确认。不得把这项
RX 改善写成所有 TX/reopen 问题已经解决。证据见 [reference/rx53](../reference/rx53/README.md)。

## 53.1 前置状态、来源与修改

前轮为 progress：RX52 已归档并推 f081526，持续同 owner、完整 OUT/IN 仍缺 RX，
主机 continuous IN 对照只改善 TX。开始再次核实三节点 OK、COM14、Shared/not
Attached、无 owner，Git 干净；实际源码/Image 保留 RX48 B。新 Ctrl-U 第一次受理，
frames=110/bytes=1078/tty_before=1077、IRQ active=1/fault=0。旧 F1 第 2 OUT 受理，
独立 fastboot 序列号 62bc28a1/product msmnile 核对后才刷候选。

再次查阅 [console API](https://docs.kernel.org/driver-api/tty/console.html)、
[workqueue](https://docs.kernel.org/core-api/workqueue.html) 和
[串口规范](https://docs.kernel.org/driver-api/serial/driver.html)。现有非 RT legacy printk
在 write 外层关 IRQ，只改驱动内层按帧解锁不足以保证及时服务，未作这种盲改。
候选在 console 首次写入前及每个**完整 TX 帧之后**调用现有整帧 RX collector：

* 仍在共享 UART 锁内，一次收完 ID/LEN/DAT；未消费完整 RX 前不开始下一帧 TX。
* 仅 normal RX startup 之后启用，stopping/F1 pending 时跳过，不干扰早期启动。
* RX 来源独立为 console，`via=console`、rx_stats 的 console_frames 和只读 console_rx
  计数，不冒充 IRQ/poll。receipt、tty、F1 均留在锁外工作线程；console 不 printk/重启。
* 已消费 RX 可能留下一个 GIC 通知，最多 credit **一次**随后 empty IRQ；仍计入
  irqs/empty，另记 empty_irqs。任何 IRQ 观察或停 IRQ 都清 credit，其他空 IRQ 仍有
  8 次故障界限。没有写 GIC pending/state。该 credit 已在两次对照各命中一次。
* 一边界只收一帧；负结果停止本日志的 console 收取，沿用已有故障/轮询处理。
* TOP_CFG=0x11、F1 头部在 DAT 前判断、TX ID/LEN/DAT 与 200 us/2 ms 节奏不变。

驱动 send_frame/probe/reboot_cmd 函数与 RX48 源码逐字节相同。构建无 warning/error，
只复制当前 FAT 模板并 mcopy 新 Image，抽取后的 Image 和不变 DTB 比较相等；没有
运行旧 build-image.sh。实际 config/init/BusyBox/用户其他内核修改保留。本轮只刷一次
logdump，无 boot、PHY reset、驱动安装、force bind 或新的 Windows 管理员抓包。

## 53.2 相同 USB 触发首次成功

使用未改的 RX52 continuous IN helper（SHA d3d68d5f...），152 ms marker delay，
每个数据帧只发一次。新 owner Ctrl-U 第一次成功，随后基线命令读三个状态文件。
7 字节 probe 仍为 R51H=1 LF，日志仍是 RX51 的 49 字节 printf 命令，没有换触发。

marker/probe/end/receipt 为 36460.179/36612.877/37259.786/37326.036 ms，回执距 probe
713.159 ms，`via=console`。基线 frames=9、bytes=tty=87、console_frames=0；最终
frames=25、bytes=tty=281，irq_frames=24、console_frames=1、empty=1，console
empty_irqs=1/credit=0。bad/no_tty/overrun/poll/watchdog/drops/fault=0，active=1。
R51H=1，24 个数据帧/280 字节加启动 Ctrl-U 均一次受理，6 个手动步骤后关闭。

raw 13623 字节/2291 帧，全部目标 IN、read 事件和 raw 逐字节相等。一条状态 -2 的
取消 IN 仍含 6 字节 `90 04 5b 20 20 31`，原 helper 正确保留；不能把取消一概视为丢失。
快照 seq 7660..8171、CRC caa7bba9，512 帧在同 raw 中连续逐帧相等，990 个零完整。
USB/software 证据仍不是物理 ACK 或直接测到的 IRQ 延迟。

## 53.3 Windows 同条件也成功

使用字节未改的 RX51 console-overlap 诊断和 RX50 C# probe，未替换安装终端。
新 Ctrl-U 首次成功，先 `unset R51H` 再设 P 和读基线，排除前一个 USB 实验的变量残值。
Ctrl-O arm，一次同样的日志/7 字节输入；marker/probe/end/receipt 为
85640/85887/86453/86494 ms，实际 marker→probe 247 ms，仍在日志结束前。
不能把 Windows 本次实际间隔称为固定 152 ms。

probe 取得 `via=console` 回执，607 ms；基线 frames=32/bytes=tty=366/console_frames=1，
最终 48/547/2，irq_frames=46、empty=2；console empty_irqs=2、credit=0，active=1、
fault/drop/bad/overrun 为 0，R51H 读回 1。22 个数据帧/265 字节加启动 Ctrl-U 均一次
受理。raw 13188 字节/2216 帧，354 次 Read，最大队列 168、无观察到的错误；finally
Close/Dispose、probe detached、pending/queued 为 0。

快照 seq 9918..10429、CRC 9b1304eb，512 帧连续逐帧匹配，日志 990 个零完整。
这支持候选对明确的 busy-console RX 触发有效，不证明旧 TX/reopen 根因统一或全解。

## 53.4 兼容、F1、重启，以及仍存在的精确 TX 缺口

安装的 -Native echo R53NATIVE 和默认兼容 echo R53COMPAT 都有完整命令输出/prompt、
零重试/stray/尾部残帧。候选 F1 第一次 OUT 通过 IRQ（irqs=68/fault=0）进入 fastboot；
独立 product msmnile 核实后只 reboot 同一候选，没有再刷。被动启动收 10623 帧，
TOP_CFG=11/original=0、IRQ arm、tty shell 正常。console 来源 F1 尚未触发，保留为
有意义的下一项回归；不能拿本次 IRQ F1 当那个新分支的验证。

重启后安装 -Native echo R53END1 首次同步并受理，完整命令/输出/prompt；但 raw
首行实际从 `95.409512]` 开始，缺预期 `[   95.409512]` 的 `[   `。这一条不是过滤误报，
所以没有把“命令成功”当作 TX 无损。立刻在持续 USB owner 中保存/导出不可变快照：

| 512 帧记录范围 | 直接比较 |
|---|---|
| 前 151 | 与最终被动 boot raw 的最后 151 帧相等 |
| seq 7287，console，`90 04 5b 20 20 20` | 软件有 `[   `；安装终端对应位置无此帧 |
| 随后 87 | 与整个 installed-final-native raw 相等 |
| 最后 273 | 与后续 USB raw 的前 273 帧相等 |

快照 seq 7136..7647、CRC 149aa951，共 511/512 直接匹配，唯一缺口确切，没有插值
或 edit-distance。生成该状态时安装 owner 已打开、3 秒后才发 Ctrl-U，不是 owner 前
未保存的旧输出。后续 USB raw 9431 字节/1581 帧，完整 IN/raw 相等、14 OUT 回执全有，
IRQ/tty 计数正常。EUD TX、物理 USB、Windows 接收之间的具体丢失点仍未知。
此时 console_frames=0，尚无新 console 接收被触发；旧 RX51 同类 Windows 已发帧
缺失仍开放，不能称本轮 RX 改动修复了 TX，也不能单凭此认定新读状态造成故障。

## 53.5 保留状态和下一步

00:52:50 +08:00 最终快照三节点 OK、COM14 关闭、9505 Shared/not Attached，无 helper。
两个 USB owner 和各 Windows owner finally 释放，手机继续运行 RX53 候选。
原始 raw/bin/执行 helper/source 保留字节，派生文本 UTF8 LF，目标 trace gzip 解压 SHA
相等；镜像/第三方二进制只留外部目录。验证和 docs-health-check clean 后仅推 fork/master。

| 当前/回退 | SHA256 |
|---|---|
| logdump-rx53-console-rx.img | 50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93 |
| Image（30181888 字节） | 33efc6bc0c1c2d7b82b80b39dc7cea2331d05cca2005376399dade92b1597952 |
| eud.c | 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4 |
| 回退 logdump-rx48-tx-journal.img | 61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d |

下一轮针对两个未完成项：有界多次 overlap 跨过 8 个空 IRQ 门槛/console 来源 F1，
以及首条状态已发 TX 帧缺失的主机接收/USB 边界。继续查实际安装驱动或可借鉴的
连续 Windows 读取实现，别再改已验证 TOP_CFG、盲猜 TX status/等待或跑普通成功
echo 当稳定性证明。缺回执不重发有副作用数据，限定 boot/logdump，目标保持未完成。
