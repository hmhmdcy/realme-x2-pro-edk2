# 52. 同一 USB owner 的长日志缺 RX，持续 IN 对照（2026-10-09/10）

**RX 缺回执仍未修复，但触发范围进一步缩小：** 沿用 RX51 的长日志与 7 字节输入，
改用持续 libusb owner，保存目标 OUT/IN 的完整字节。两次输入都只发一次、USB OUT
完整成功完成，但没有设备回执或 RX/tty 计数；不关闭连接就能用一次 Ctrl-U 恢复。
因此这次失败不需要 Windows qcusbser 或串口 reopen，不能只围绕旧会话重置排查。

同时发现观察工具会影响 TX：读取、保存和显示串行执行时缺了 8 个零；把持续读取
移到独立线程后，本次 512 帧全部匹配，RX 故障却仍存在。不是宣布全部 TX 已修复。
完整证据和可重复离线核对见 [reference/rx52](../reference/rx52/README.md)。

## 52.1 状态、边界和新搜索

先核对三节点 OK、COM14、9505 Shared/not Attached、无已知 helper。Git master 为
d97bc81；实际 driver/Image/DTB/config/init/BusyBox/安装终端哈希与 RX48/RX51 相等。
本轮没有修改手机源码、刷机或重启。TOP_CFG=0x11 整帧读取、F1、console、兼容终端
都保留；两次 USB owner 在 finally 释放并 detach，没有再启动 Windows 管理员抓包。
WSL root 加载 usbmon 并运行诊断，是已有 Linux 权限路径，没有新的 Windows UAC。

第一次失败后继续查阅 [Linux usbmon 文档](https://docs.kernel.org/usb/usbmon.html)：
它记录驱动与 HCD 之间的请求，不能保证物理总线事务；必须核对 callback actual
length、`=` 数据与可能的截断。本次所有正长度 IN 均保存完整，逐字节等于 raw。
[串口驱动规范](https://github.com/torvalds/linux/blob/master/Documentation/driver-api/serial/driver.rst)
及实际内核 8250 console 的锁/中断恢复逻辑没有提供 EUD 接收 FIFO 保留语义；不能
拿普通 UART 的 receive-ready 假设盲改 EUD。RX51 已核实 legacy console 整条日志
持 UART 锁，外层非 RT printk 也关本地 IRQ。IRQ 入锁前延迟仍未实测。

不重复 TOP_CFG 零等待、DAT/padding/ZLP、reset、仅掩码或普通 echo 循环。
本次只有一个明确的软件变化：持续读 IN 与保存/解码/显示分离。

## 52.2 相同触发、同 owner 恢复

两份独立 Python 诊断从 RX49 工具派生，USB interface 0，IN 81/OUT 02，最大包长
16；PyUSB 1.2.1-2，保留已验证的取消/timeout 部分数据语义。普通数据只提交一次，
回执界限 4 秒；只有这次固定 overlap probe 超时会进入只抓取状态，不自动重发数据。
继续发送必须先人工 `u` 并取得新回执。最多 12 次手动步骤、300 秒，实际各 7 步。

每个 owner 的操作：

```text
u
send P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch
overlap
u
send dd if=$P/tx_journal of=/tmp/R52J1 bs=4096 count=1
send base64 /tmp/R52J1
send cat $P/rx_stats $P/irq_watch;printf 'R51H=%s\n' "$R51H"
x
```

B 使用 R52J2。`overlap` 只触发一次与 RX51 相同的 49 字节命令：

```sh
printf '<6>R51LOCK:%0990d:R51END\n' 0 >/dev/kmsg
```

单次 kmsg write 1009 字节，低于此内核 1024 字节限制。匹配带内核时间前缀的 marker
后等 152 ms，发 `R51H=1\n`，wire `90 07 52 35 31 48 3d 31 0a`，一次。shell 回显不
触发 marker。A/B 的 marker→probe→end 分别为 59000.760→59153.822→59801.320 ms
和 35247.449→35400.212→36046.771 ms。均 4 秒超时，随后只抓取直至人工恢复。

| 计数边界 | A | B |
|---|---|---|
| 基线 frames / bytes=tty / irqs / empty | 71 / 656 / 72 / 1 | 94 / 903 / 96 / 2 |
| 同 owner 首次恢复 Ctrl-U：frames / bytes / tty_before / irqs / empty | 76 / 706 / 705 / 78 / 2 | 99 / 953 / 952 / 102 / 3 |
| 最终 frames / bytes=tty / irqs / empty | 86 / 830 / 88 / 2 | 109 / 1077 / 112 / 3 |

恢复增量恰好是触发日志的 4 帧/49 字节加 Ctrl-U 的 1 帧/1 字节，失败 probe 的 7
字节没有进入受理 RX/tty；R51H 最终为空。两次都多一个 empty IRQ，没有 reopen 或
捕获期控制传输。IRQ active=1，bad/no_tty/overrun/poll_frames/watchdog/drops/fault=0，
queued=0；grace waits=0，不能证明持锁期间没有延迟或已修复等待分支。

每次 24 个 OUT（22 个数据帧/252 字节和两次 Ctrl-U），全部一次提交、完整成功完成；
23 个回执，唯一缺 probe。单独的完整 OUT 仍不是物理 USB ACK 或 EUD FIFO 受理证明。
这次额外 empty IRQ 被限定在同 owner 的日志/恢复区间，实际到达时点仍未测量。

## 52.3 TX 和主机读取路径的单变量对照

| 样本 | A：读取/保存/显示串行 | B：持续读取与 sink 分离 |
|---|---:|---:|
| UTC 启动（本地 +8） | 2026-10-09 15:52:01（23:52:01） | 2026-10-09 16:11:46（10 日 00:11:46） |
| 完整正长度 IN / raw | 13220 字节、2220 次 | 13245 字节、2225 次 |
| 零长度取消状态 -2 / 正长度状态 0 | 9356 / 2220 | 4075 / 2225 |
| 正长度 IN 与 raw、各 read 事件 | 全部逐字节相等 | 全部逐字节相等 |
| 长日志实收零的个数（预期 990） | 982 | 990 |
| 512 帧软件 TX 快照的直接/连续重复计数匹配 | 510 | 512（逐帧相等） |
| 日志期间最大的 IN completion→下一次 submission 空窗 | 8423 us | 854 us |
| 关闭时 worker_alive / errors / pending | 空 / 空 / 0 | 空 / 空 / 0 |

A 快照 seq 13619..14130、CRC ec6724e1，缺两个 console `90 04 30 30 30 30` 帧，
共 8 个零。247 个相同帧的连续区间只收到 245 个，**不能指定具体丢失序号**；分析
使用唯一首尾各 16 帧锚点及连续重复计数，不靠 edit-distance 补字。
最初仅见 marker/end 就称“长日志完整”的中途判断已更正，以 raw 的 982 个零为准。

B 快照 seq 15842..16353、CRC 0c22f5a8，512 个记录在原 raw 中连续逐帧相等，990
个零完整。读取线程只 read/入队，另一个 sink 保存/解码/显示并处理回执；队列峰值
2，结束前完全排空，所有返回数据都保存。IN 请求间隙和 TX 结果在这一组对照中
明显改善，支持主机请求节奏影响的方向；一次对照不证明每个旧 TX 故障都因此发生，
也不证明默认 Windows 终端或长期稳定性已修复。RX 缺命令在 B 中仍原样复现。

## 52.4 最终状态、归档和下一项修改

00:23:07 +08:00 快照：三节点 OK、COM14 关闭、9505 Shared/not Attached、无已知
helper；USB owner 已释放/detach。手机继续运行 RX48 B，无刷机/重启，新旧镜像、
终端和回退保持。原始 raw/bin/执行 helper 字节不变，派生文本 UTF8 LF；目标 USB
trace 仅 gzip 压缩，解压 SHA 与原始相等。未提交第三方完整源码/驱动/镜像。

下一项应针对长 console 持锁/关 IRQ 期间的 RX 服务，而不是再采普通通过样本。
可评估在完整 TX 帧边界使用现有整帧 RX collector，将 tty/回执/F1 延后到锁外；
必须单独记录 console 来源、避免误算 IRQ/poll，处理已消费帧留下的空 IRQ，保留
TOP_CFG=0x11、原子帧读取、F1 与 TX 节奏。不能仅按帧解锁而忽略 printk 外层 IRQ。
该候选尚未实现或刷入，根因及修复仍待实测。离线证据验证和 docs-health-check
clean 后仅推 fork/master；RX51 的 Windows 缺帧与其他 reopen 故障仍是独立开放项。
