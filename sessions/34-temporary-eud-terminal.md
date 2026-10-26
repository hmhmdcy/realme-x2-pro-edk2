# 34. 临时 EUD 终端：继续 Linux 驱动移植（2026-10-09）

用途：区分手机 TX/RX 状态，把 session 33 已验证的单字符输入接成可操作的主机终端。
使用方法见 `linux-port/docs/EUD-TERMINAL.md`，原生 RX 问题仍见 sessions 32/33。

## 34.1 结论

以手机为准，**TX 已能每帧发送 4 个 payload 字节，并组合成长输出；RX 的原生
多字节推进仍未解决**。两边不是相同的“只能取得首字节”问题。
TX 之前的 FIFO 溢出与 console 双 writer 问题，当前依靠 200 μs/寄存器写、
2 ms/帧和单 writer 改善；不能据此保证任意帧长、任意速率或绝无丢失。

临时主机终端已落地，输入自动排队为 `[90][01][char]`，等现有内核的
`eud: tty byte=..` 受理日志后才继续。输出持续读取、重组、显示并保存。
不再需要为每个字符手动调用一次 eud-step。

本轮**未修改内核、未刷任何分区**。测试的是既有 rx33-console 内核。
原生多字节排查暂时不再阻塞所有 Linux 移植工作。

## 34.2 工具与边界

* 仓库源码：`linux-port/scripts/eud-terminal.ps1`、`eud-terminal.cmd`。
* 可直接运行的工具副本：`E:\eud-host\eud-terminal.cmd` 与同目录 ps1。
* 可交互输入，也可 `-Command 'uname -r'` 一次运行一条命令。命令模式先用 Ctrl-U
  清旧半行，末尾加换行；退出码表示桥接完成情况，不是远端命令退出码。
* 自动查 EUD 9505 的 COM 号。`-Reconnect` 在打开串口之前调用已有 eudtool 的
  com-off/com-up；它不能解除 qcser resource-in-use 锁死。
* 默认单字节重试 500 ms 加 0..399 ms 扰动，最多发送 10 次；成功字节间隔
  200..299 ms。受理即停止重发；用尽次数则停止剩余输入并关闭串口。
* Ctrl-C 中断手机；Ctrl-U 清行；两者同时取消主机未发送队列。Enter、退格可用，
  Ctrl-] 本地退出。当前只支持 ASCII，不提供方向键历史或完整 VT100。
* 串口使用 try/finally Close/Dispose；正常退出、超时与异常都关闭。
* `.raw` 保存原始帧，`.txt` 保存未过滤的设备输出，`.events.txt` 记录每字节
  发送、重试、受理时间。默认在 Windows TEMP，可用 -LogBase 指定。

受理日志仅含字符值，没有序号或接收端去重。ACK 丢失仍可能导致重复字符，
换行已受理但 ACK 丢失时命令也可能已经执行；此工具不承诺 exactly-once。
超时后先查看输出，不自动重新执行整条命令。这是交互临时方案，不是文件传输协议。

## 34.3 真机证据

原始记录在 `E:\edk2-samurai-out\rx34-*`，选取的成功记录另存 `reference/rx34/`。
表中 ACK 数包括准备时的 Ctrl-U 与末尾换行。

| 测试 | 手机返回 | ACK / 重试 / TX 帧 |
|---|---|---|
| 命令模式 id | uid=0 gid=0 | 4 / 1 / 40 |
| echo TX-ABCD1234567890 | 完整 TX-ABCD1234567890 | 24 / 35 / 223 |
| uname -r | 7.3.0-rc6-rmx1931-samurai+ | 10 / 11 / 98 |
| printf TTY-0123456789 > /dev/ttyEUD0 | 完整 TTY-0123456789 | 37 / 49 / 338 |
| echo CONSOLE-0123456789 > /dev/console | 完整 CONSOLE-0123456789 | 39 / 59 / 358 |
| 最终键盘测试：Ctrl-U、ix、退格、d、Enter，再 Ctrl-C | uid=0 gid=0；随后 ^C 和提示符 | 7 / 15 / 72 |
| 最终 eud-terminal.cmd 入口执行 id | uid=0 gid=0；端口正常重开/关闭 | 4 / 9 / 41 |

成功记录分别为 `rx34-terminal-id`、`rx34-terminal-tx3`、`rx34-terminal-uname`、
`rx34-terminal-tty`、`rx34-terminal-console2`、`rx34-terminal-interactive2`。
最终 cmd 入口的记录为 `rx34-launcher-id`。
上述抓包最大 payload 均为 4，stray 和残留字节均为 0；这不是无丢帧证明。
直接 tty 输出的实际相邻帧包括长度 4 的 `TTY-`、`0123`、`4567`，明确包含多个
payload 字节；不是靠单字节 TX 帧拼出来的假象。

前两次长命令测试没有成功：一次连 Ctrl-U 都无 ACK；另一次在字符 63（c）处
用尽当时的 5 次尝试。工具停止了剩余队列并关闭串口。之后改为最多 10 次并加入
重试扰动；较短 500 ms 节奏先以 uname 验证，再用于 tty/console 与键盘测试。
F1 单步工具原来的秒级间隔没有改。

tty 测试之后 EUD 枚举消失，随后发现同设备在 fastboot。用户确认是手动重启到
fastboot；不是工具自行触发 F1 的证据。仅 fastboot reboot 回原内核后继续 console
测试，没有刷镜像。

## 34.4 键盘测试发现并修正的显示问题

第一版把远端 `ESC[6n` 查询直接显示给 Windows 终端。终端会生成光标位置回复，
ReadKey 又把回复逐字符送入手机；在慢速链路上回复到达时，shell 已结束等待，
于是出现多余的 `[6;5R` 等字符。

最终版在显示端流式识别并过滤该查询，保留日志原文；其他 CSI 显示控制序列继续
透传。受理行也在跨帧重组后按整行过滤，其他内核日志不作为受理行隐藏。
最终键盘测试仅收到预期的 `15,69,78,7f,64,0a,03` 七个 ACK，没有额外 ESC 输入。
Ctrl-] 返回退出码 0 并打印 Closed COM14；之后能重新打开端口。

离线将真实 tty 抓包限制为每次 3 字节读取，调用同一 Receive-Eud 函数，仍准确
重组 338 帧，解码文本与原记录完全一致；完整受理行隐藏，输出标记保留。

## 34.5 后续

先用临时终端运行 uname、dmesg、sysfs/设备节点检查，继续 panel、touch、Wi-Fi、
充电等具体驱动工作。内核改动仍走 FLYWHEEL.md 的 logdump 迭代流程。
发 F1 前先 Ctrl-] 关闭终端，避免多个程序争用端口。
原生 RX 的下一步需要 USB OUT、芯片握手/时钟等新证据，见 session 33，
不把此次临时桥接记作多字节 RX 修复。
