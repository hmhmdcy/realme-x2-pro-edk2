# EUD 终端：兼容输入与可选原生多字符输入

> session 47 加入 `-Native`：启动时先用 Ctrl-U 同步，持续打开同一个串口，
> 粘贴/命令模式按最多 14 字节原生帧发送；两字节尾片拆成 1+1，保留 F1。
> 默认仍为兼容单字节输入。RX47 在 RX46 IRQ B 真机验证命令、长命令、交互清行、
> 重启后 20 行输出与 shell 状态读回，但长状态输出仍有实际 TX 缺字，且曾触发
> 看门狗退回轮询。可用路径已有，稳定性尚未彻底解决。
> 证据、限制和最终状态见 [session 47](../../sessions/47-native-terminal-session-boundary.md)。

2026-10-09，默认模式兼容 rx33；`-Native` 需要 RX41 之后的完整 payload 修复和回执。
当前实测候选为 `logdump-rx53-console-rx.img`，TOP_CFG=0x11 方法保留。
主机终端仍是 RX47 同一源码；RX48 新诊断、CRC 快照、兼容/F1/重启结果和限制见
[session 48](../../sessions/48-irq-grace-and-tx-journal.md)。其 512 个发送记录全匹配 raw，
但未重现此前 TX 缺字，宽限等待分支也未触发，稳定性仍开放。
RX49 在不改内核的持续 libusb 对照中，进一步匹配了完整 USB IN/raw 与发送快照，
并实测保留部分取消数据；切回此 Windows 终端后原生 echo 正常。边界与限制见
[session 49](../../sessions/49-usb-in-and-partial-timeout-audit.md)，不扩大为长期无损保证。
RX50 的一次 Windows 诊断会话正常，完整状态输出与 287 个重叠发送记录匹配。
新错误/队列观测仅在独立诊断副本中，未替换本终端；该样本可正常使用，旧故障没有
复现。见 [session 50](../../sessions/50-windows-receive-and-driver-buffer-audit.md)。
工具的原始源码与测量见
`../../sessions/33-rx-access-and-production-policy.md`、
[session 34](../../sessions/34-temporary-eud-terminal.md)。

RX51 已在长 console 日志接收期间复现缺回执：一次 7 字节输入未进入已受理 RX/tty。
恢复状态还缺一个已发 4 字节 console 帧，512 记录中其余 511 帧直接匹配 raw。
镜像和本终端均未改；这限制了之前正常样本的稳定性结论，不宣称当前根因已定。
见 [session 51](../../sessions/51-console-overlap-and-issued-frame-loss.md)。诊断副本只做
一次明确触发实验，缺回执即停止数据，不通过重复有副作用命令掩盖丢失。

RX52 通过完整目标 USB OUT/IN，在同一 libusb owner 内也复现该 7 字节缺 RX；
人工 Ctrl-U 首次恢复，证明这次失败不需要 qcusbser/reopen。诊断读取与 sink 分开
后，本次 TX 快照 512/512 匹配、IN 请求间隙改善，RX 仍失败；没有替换本终端或
宣称普遍修复。见 [session 52](../../sessions/52-same-owner-usb-overlap-and-continuous-in.md)。
手机镜像、TOP_CFG=0x11/F1/默认兼容模式都保留，稳定性继续排查。

RX53 仅刷 logdump，在完整 console TX 帧之间及时收 RX、延后回执/tty/F1；同样的
长日志输入在 USB 和 Windows 均取得 via=console 回执、执行，各 512 TX 帧匹配。
本终端源码未换，原生/默认兼容与 IRQ F1/重启保留。最终安装终端仍缺首条状态一个
已发 4 字节前缀，整体稳定性尚未解决；见
[session 53](../../sessions/53-console-boundary-rx-service.md)。console 来源回执会显示在
旧过滤器之外，但 native ACK 匹配正常；不为隐藏它而改写真实 RX 来源。

RX54 未改本终端或 RX53 候选，9 次手动长日志输入均经 console 受理/执行，
6 次空 IRQ 正确计数、IRQ 仍 active=1/fault=0；console 来源 F1/同候选 reboot
及原生新回执/输出通过。并未诱发连续 8 次空 IRQ，也没有修复 RX53 已证明的 TX
缺前缀。下一项独立诊断只读累计接收计数，尚未实测、不修改安装终端；见
[session 54](../../sessions/54-console-rx-regression-and-host-counter-audit.md)。

RX55 已在独立诊断 owner 上实测 GET_STATS：seq7376 缺 4 字符（6 线缆字节），
raw 与驱动受理缓冲累计计数同为 309，软件记录应为 315，排除纯应用读取/显示
丢失。EUD/USB/驱动前段仍待区分；启动首 Ctrl-U 本次也未受理，第二次成功，
之后 19 数据帧只发一次都有回执。未改本终端、未刷机/重启，finally 关闭串口；见
[session 55](../../sessions/55-windows-perf-counter-and-reproduced-tx-gap.md)。

## TX 和 RX 的状态

方向以手机为准：

| 方向 | 当前状态 | 临时终端的处理 |
|---|---|---|
| 手机 TX → PC | 内核每帧发送最多 4 个 payload 字节，长输出拆成多帧；限速后可用 | 持续读取、解帧、显示，并保存日志 |
| PC → 手机 RX | RX41 已修复整帧 payload；打开串口后的首帧可能未受理，持续打开的原生输入已实测 | 默认按单字节回执发送；`-Native` 先同步，再发送长度 1 或 3..14 的帧 |

TX 以前有小 FIFO 溢出、双 console writer 等问题，当前采用 200 μs/寄存器写与
2 ms/帧的节奏。它不是 RX 的“读不出下一字节”现象；也不保证任意帧长或绝无丢失。
0 stray 仅表示重组无需跳过字节，不是无损证明。

## 启动

先关闭其他 EUD 抓包/串口程序。Windows PowerShell 自带运行环境，不需要 pyserial。

```powershell
& 'E:\eud-host\eud-terminal.cmd' -Reconnect
# 当前 RX53 候选上使用原生输入；保持终端打开后连续输入命令。
& 'E:\eud-host\eud-terminal.cmd' -Native -Port COM14
```

项目内同一份入口：`linux-port/scripts/eud-terminal.cmd`，也可直接双击。
不指定端口时，从当前 EUD 9505 设备自动找 COM；需要时可加 `-Port COM14`。
`-Reconnect` 在开串口前调用已有 eudtool 的 com-off/com-up；需要手机已启动 EUD。
它不等于修复 resource-in-use：遇到端口钉死仍需换 USB 口或重启主机。
未加此参数且找不到 COM 时，工具会尝试一次 com-up。

终端始终排空输出；退出和异常路径都在 finally 中 Close/Dispose 串口。
只输入 ASCII，适合 shell 命令、路径和驱动诊断；可粘贴整条命令。
原生模式把当前队列分成最多 14 字节；逐键输入时队列可能只有 1 字节。
不用手工拼 EUD 帧。

| 按键 | 含义 |
|---|---|
| Enter | 发送换行执行 |
| Backspace | 发送 DEL 删除字符 |
| Ctrl-C | 清除主机未发送队列，向手机发送中断字符 |
| Ctrl-U | 清除主机未发送队列，向手机发送清行字符 |
| Ctrl-] | 本地退出并关闭串口 |

这是简易字符终端，尚不支持方向键历史、全屏应用或 Unicode 输入。若需要 Ctrl-]
之外的方法退出，应等工具正常结束，不要强杀正在持有串口的进程。
完整的 `eud: tty byte=..` 和原生 `eud: rx frame ...` 受理行默认只保留在日志中；`-ShowAcks` 可显示它们。
破损的诊断行可能仍显示出来。
远端 shell 的 `ESC[6n` 光标查询只在显示端过滤，避免 Windows 终端自动回复后
被 ReadKey 当作键盘输入转回手机；原始日志仍保留查询。

## 一次发送一条命令

```powershell
& 'E:\eud-host\eud-terminal.cmd' -Reconnect -Command 'uname -r'
& 'E:\eud-host\eud-terminal.cmd' -Reconnect -Command 'dmesg | tail -n 60'
& 'E:\eud-host\eud-terminal.cmd' -Native -Port COM14 -Command 'uname -r'
```

命令模式先发送 Ctrl-U 清理旧的半行，再发送命令和换行；最后继续排空输出，默认
静默 3 s 后退出。可用 `-TailSeconds 10` 延长静默等待。
不要同时运行交互终端和命令模式。
退出码表示桥接是否完成，不是远端 shell 命令的退出码；远端结果要查看输出。

兼容模式的单字符重试基准默认 500 ms，另加 0..399 ms 扰动；最多发送 10 次，收到回执即停。
成功字符之间再留 200..299 ms。该较短节奏已用于临时单字符路径实测，F1 的单步
探针脚本仍保留原来的秒级命令间隔。需要保守节奏可加 `-RetryMs 2200`。
某字节用尽重试次数仍无回执，工具停止剩余输入、报错并关闭端口，不自动重跑整条命令。
若换行已经受理但回执丢失，命令可能已经执行；先看输出，再决定是否重输。

原生模式只有启动 Ctrl-U 使用上述有界重试；同步完成前暂不读取键盘输入。
之后每个命令帧只提交一次，按完整 payload 查找回执，默认等待 4 s；可用
`-NativeAckTimeoutMs` 调整等待上限。缺回执就停止剩余输入、报错并 finally 关闭串口。
不会自动重发可能已经执行的命令；先检查 `.raw/.txt` 输出，再决定是否重输。
Ctrl-C/Ctrl-U 仍会取消主机未发送队列。

现有内核回执没有序号/去重，延迟的同值回执仍是协议限制；两种模式都不承诺
exactly-once。长 TX 输出还可能丢失完整帧，RX47 已保留真实缺字样本。
`-Native` 是主机使用已验证整帧 RX 的方式，不代替 TOP_CFG=0x11 设备修复。

## 只读发送诊断（RX48）

在一个已同步的交互 owner 里先保存快照，再传输临时文件：

```sh
P=/sys/bus/platform/devices/88e0000.serial
cat $P/irq_watch
cat $P/irq_state
dd if=$P/tx_journal of=/tmp/R48J1 bs=4096 count=1
base64 /tmp/R48J1
```

文件名使用新名字；binary sysfs 必须 offset=0 一次提供足够空间，最大 3120 字节。
不要直接 cat 二进制到终端。用 reference/rx48/analyze-journal.py 验版本、长度和 CRC
后才比对原始帧；校验失败不能作丢帧定位。记录证明已发 MMIO 值，不是 USB ACK。
irq_watch 是软件计数，irq_state 是显式只读 GIC 查询；详见 session 48 的位义/限制。

## 日志与后续工作

默认日志在 Windows `%TEMP%\eud-terminal-时间戳.*`，启动时打印完整路径。
可用 `-LogBase 'E:\edk2-samurai-out\my-driver-test'` 指定文件名前缀：

* `.raw`：EUD 原始输入帧；
* `.txt`：未过滤的设备输出，保留受理日志；
* `.events.txt`：兼容模式记录每字节；原生模式记录长度、payload、startup sync、发送与受理时间。

退出时打印 ACK 数、重试数、收到的帧数、最大 payload、stray 和残留字节数。
原始日志仍可用 `decode-eud-capture.py` 重组。

退出时原生模式另报已受理的数据帧数与同步状态。退出码不验证远端完整响应。

RX43 起解码脚本在 stdout 显示全部响应；旧版本只打印 `eud:` 行，而 `.txt`
一直保留了完整输出。原生单帧诊断用 `eud-step.ps1`，直接保存新 `.raw/.txt/.events.txt`，
拒绝覆盖，限定一次完整帧和有界重试；`-TailSeconds 5` 可延长回执后排空时间。
最长总时间仍受 `-Seconds` 限制，延长等待本身不是投递修复。

现在可通过此终端查看 dmesg、设备节点和 sysfs，继续定位具体驱动。
内核镜像仍走 `FLYWHEEL.md` 的 `[90][02] → fastboot → 只刷 logdump → reboot` 流程。
发 F1 前先用 Ctrl-] 关闭终端，让单步工具独占端口。此终端不会自动刷分区。
