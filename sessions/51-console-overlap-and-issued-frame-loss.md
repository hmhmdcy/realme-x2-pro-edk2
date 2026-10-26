# 51. 长 console 输出期间缺 RX，恢复状态缺一个已发 TX 帧（2026-10-09）

**本轮取得新异常证据，未修复稳定性：** 在一条长内核日志传回期间，仅提交一次
7 字节原生输入；4 秒没有回执，后续计数与 shell 状态证明它未进入受理 RX/tty。
恢复连接时还缺了状态行开头的一个 4 字节帧：不可变 TX 记录有它，Windows raw 没有。
这不是重复 RX41 已修复的 payload 推进，也不是把解码过滤误报成缺输出。
证据与独立核对在 [reference/rx51](../reference/rx51/README.md)。

## 51.1 状态与新的代码依据

先核对 9501/9500/9505 均 OK、COM14、9505 Shared/not Attached、无已知 helper。
Git 主仓库为 d8094c7，干净；实际 WSL 内核仍是 RX48 B，eud.c/Image/init/DTB 与
安装终端哈希未改。读取交接与 41/42 历史边界，保留 TOP_CFG=0x11 整帧 RX、
LEN=2 的头部 F1、console 和默认兼容输入。本轮不刷机、重启或新管理员抓包。

实际 driver 的 console_write 在整条消息期间持有 UART 锁并关闭本地 IRQ；RX
handler 拿到同一锁后才增加 IRQ 计数。当前非 RT 的 printk core 在 con->write 外层
也关本地 IRQ。只把驱动内层改成每帧解锁不足以消除外层影响，未做这种盲改。
tty TX worker 每帧解锁，CONFIG_PREEMPT=y；此前未验证的“不抢占 worker”前提
不适用于本配置。grace/watchdog 自身也需拿 UART 锁，waits=0 不能证明锁持有期间
没有延迟。源文件范围、SHA、配置与未修改 core 的 Git revision 在 source-audit.json。

网络查找了 printk/console/串口锁的现有依据：
[Linux printk 文档](https://docs.kernel.org/core-api/printk-basics.html)说明旧 console 同步
输出会阻塞甚至长时间关中断；[console API](https://docs.kernel.org/driver-api/tty/console.html)
给出 nbcon 的线程/原子写及所有权要求。这是待验证的机制，不能代替本机 IRQ 延迟
测量；完整日志成功也不代表同时到来的输入会成功。QUIC timeout 初始化仍无已确认
物理语义，不重复旧 timeout/reset/仅掩码/零等待实验。

## 51.2 一次有界重叠实验

独立 eud-console-overlap.ps1 从 RX50 诊断副本派生，没有替换安装终端。
仍使用同一个 SerialPort owner、原始 Read/raw/队列错误观测和 finally Close/Dispose。
Ctrl-O 只可在输入排空后手动 arm 一次；仅在收到带内核时间前缀的 R51LOCK 时
排队固定 `R51H=1\n`，不被 shell 回显触发，不重试该数据帧。超过 ACK 界限即停。
默认兼容终端与 F1 长度保留。PS5.1 编译/marker 边界离线核对通过；最初默认 PS7
的 Add-Type 缺 Framework SerialPort 引用，只是离线工具环境问题，未打开端口。

启动 Ctrl-U 第一次即获新回执，frames/irqs=41、bytes=337、tty_before=336。
随后人工输入，基线 frames/irqs=48、bytes/tty=409、empty/watchdog/fault=0：

```text
P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch
Ctrl-O
printf '<6>R51LOCK:%0990d:R51END\n' 0 >/dev/kmsg
```

生成的单次 kmsg write 为 1009 字节，低于此内核 1024 字节限制。990 个零及结尾
R51END 全部在 raw 中。marker 首次记录在 owner 时钟 54079 ms；7 字节帧一次提交
在 54231 ms；结尾记录在 54867 ms。主机观察到的 marker→end 为 788 ms。
这是输出接收期间的主机提交，不是物理 OUT 到达或实际锁延迟的直接证明。
4 秒没有 probe 回执，终端停止，58.265 s finally 关闭，pending_input=true、队列已空。
raw 4085 字节/689 帧，111 次非空 Read，最大队列 174 字节、零观察到的串口错误。
11 个正常数据帧共 121 字节均获回执，失败 probe 另占一帧 7 字节，没有盲目重发。

## 51.3 恢复计数与唯一已发帧缺口

再次核对无 owner/设备 OK，打开未改动的 RX50 诊断副本。两次有界启动 Ctrl-U 中
第一份未获回执，第二份成功；不能把该会话边界问题归给之前的长日志。
该回执 frames=53、bytes=459、tty_before=458，正好是基线加长日志命令的 4 帧/49
字节，再加一次 Ctrl-U；probe 的 7 字节没有计入。irqs=54、empty=1，发生时点只能
限定在基线到该回执之间，不能指认是 probe 或 reopen。IRQ 仍 active=1/fault=0。

沿用 shell 中 P，先取不可变快照，再导出并查询：

```text
dd if=$P/tx_journal of=/tmp/R51J1 bs=4096 count=1
base64 /tmp/R51J1
cat $P/rx_stats $P/irq_watch;printf 'R51H=%s\n' "$R51H"
Ctrl-]
```

最后输出 R51H= 空值，frames/irq_frames=63、bytes/tty=583、empty=1，其余坏帧、
overrun、watchdog、drops、fault 为 0，active=1。grace waits/recovered/cleared 仍为 0。
恢复 raw 9141 字节/1532 帧，264 次非空 Read；最大队列 165 字节，没有观察到错误。
10 个数据帧、124 字节一次受理；启动重试一次。最终 pending/queued 均无，串口关闭。

快照 3120 字节、512 帧、seq 11397..11908、CRC 621cfafd。跨两个 raw 直接比较：

| 范围 | 结果 |
|---|---|
| 首 336 个记录 | 与失败 owner 的最后 336 帧逐帧相等 |
| seq 11733，console，`90 04 5b 20 35 38` | 记录有 `[ 58`，恢复 raw 没有 |
| 后 175 个记录 | 与恢复 owner 的前 175 帧逐帧相等 |

共 511/512 直接匹配；唯一缺口是恢复状态行 `[ 5863.839589]` 的第一个四字节帧，
raw 实际从 `63.839589]` 开始。恢复端口/日志早已打开、两次 Ctrl-U 之后才生成该
行，不是将 owner 前的旧记录计为缺失。所有 Read 返回字节连续进入 raw，零 resync
或尾部残帧，未靠 stdout、补字或 edit-distance 宣称匹配。

软件 TX 记录仅证明 MMIO 写已发出；缺口仍可能位于 EUD TX、USB 或 Windows
驱动接收，不能当作物理 USB/ACK 证明。没有串口错误也不能排除未报告的损失。
RX、TX 的两个异常可能有关，也可能独立，不宣称本轮已找到共同根因。

## 51.4 结束状态与下一步

23:32:41 +08:00 最终快照：三节点 OK、COM14、Shared/not Attached，无已知 helper。
TOP_CFG/driver、Image、DTB、实际 init/BusyBox、安装终端及回退均保留；没有刷机。
普通空闲命令恢复成功，有长日志与 reopen 异常证据，不能沿用 RX50 的“本轮未复现”。
只归档目标数据；原始 raw/bin/已执行 helper 保持字节一致，派生文本 UTF8 LF，
原始/导出 SHA 在 exports.json。完整三方源码/驱动没有提交。

下一项有意义的对照：同一 marker 条件下，通过持续 libusb owner 保存目标 OUT/IN
完成及全部 raw，再对应 IRQ/tty 与不可变 journal；改变主机路径以区分 Windows
接收和设备边界。随后若仍指向设备，可增加低侵入 IRQ 入锁前时间/console 时长记录，
不得把外层 IRQ 关闭、host 时钟重叠或等待计数当已测物理事实。不要重复正常 echo/
编号输出充当进展，也不直接删 console、回退多字符或重发有副作用的命令。
本轮证据核对与 docs-health-check clean 后，仅推 fork/master。
