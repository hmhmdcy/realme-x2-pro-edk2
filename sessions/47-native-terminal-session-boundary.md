# 47. 原生终端持续会话与重开边界（2026-10-09）

**已有可用的原生多字符终端路径，尚不能称稳定性彻底解决。**
保留 TOP_CFG=0x11、整帧 payload 与 RX46 IRQ B；本轮只改主机终端，没有刷机。
打开一次串口后连续发送的原生命令均受理，重开后的命令和首个 Ctrl-U 则没有
设备 RX。现有 ETW 的端点 reset 提供了具体调查方向，但物理 DATA0/1 未测到。
重启后的长状态输出又发现真正的缺字，并首次实测看门狗退回轮询。

前置阅读：HANDOVER-NEXT.md、RX-CONSOLE.md、FLYWHEEL.md、sessions 41/42，
以及 RX43 的缺输出更正、RX44 计数、RX45 掩码排除和 RX46 IRQ/ETW 证据。
主机 source audit 与原始验证在 [reference/rx47](../reference/rx47/README.md)。

## 47.1 新来源对应新的实验

先确认 9501/9500/9505 OK、COM14、usbipd 6-5 Shared/not Attached，唯一串口 owner。
当前内核/Image/init/BusyBox 哈希仍与 RX46 B 相同。先离线审查已有 trace 与实际
qcusbser 2.1.3.5，没有再次申请管理员抓包，也没有改驱动或主动 reset。

原始 trace 的四个 CLEAR_FEATURE ENDPOINT_HALT 请求分别针对 IN 81/OUT 02，
成功完成；对应 USBHUB3 function=1e pipe-reset 记录。两组时间对应串口 helper 的
会话边界。微软原始文档说明，reset 后若主机与设备 data toggle 不一致，设备可能
将下一包当作重复包丢弃。这是明确来源支持的假设，不是这台 EUD 的物理证明。
完整事件与源哈希在目标子集，所有设备的 ETL/XML 留在外部目录。

trace 只给出转移头部，没有捕获原始 R46G payload；27/v1 与 26/v0 存在，28/29
数据事件不存在。查询本机 provider 模板也没有取得 payload。旧 qcusbser 源码
可见 IN/OUT reset，但版本不同，不能拿其函数名冒充实装调用栈。
详细限定和 [微软来源](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
见 [source-audit.md](../reference/rx47/source-audit.md)。

## 47.2 保持串口打开与重开的手动对照

`eud-open-session.ps1` 一次打开，显式逐步输入，单步只发一个 OUT，无自动重试，
最多 12 步；每步独立 raw/events，退出及异常 finally Close/Dispose。
未改内核、USB 配置、ZLP、TOP_CFG、TX 节奏或 shell/init。

| 样本 | 发送与实际结果 |
|---|---|
| open-once 01-u | 1 OUT；计数 frames=irqs=5、bytes=14、tty_before=13，active=1/fault=0 |
| 02-a / 03-b / 04-c | LEN14/14/10，各 1 OUT；完整期望 payload、echo 输出和 prompt |
| 05-u | 1 OUT；frames=irqs=9、bytes=53，增量 4 帧/39 字节=14+14+10+1 |
| reopen-native-d | 重开后 echo R47D 的 1 OUT，无回执、raw=0 |
| open-after-d 01-u | 新会话第一次 Ctrl-U 的 1 OUT，也无回执、raw=0 |
| 02-u | 同一 owner 第二次 Ctrl-U 受理；frames=irqs=10、bytes=54。D 与首个 u 没有新增 RX，只有此次 u=1 字节 |
| 03-id / 04-u | 各 1 OUT 成功；id 返回 uid=0 gid=0，最终 frames=12、bytes=58 |

这些样本支持保持 owner 与启动同步；不证明所有重开故障都源自 data toggle，
也不把此前 Windows/libusb 双路径缺回执改写成 Windows 唯一故障。
串口发送数不等于物理 USB packet 数，尤其不能凭 LEN14 推算 DATA PID 奇偶。

## 47.3 实际终端实现与使用

更新 `linux-port/scripts/eud-terminal.ps1`，同一副本安装到 E:\eud-host；cmd 入口未改。
默认仍是已验证的兼容单字节终端。新模式：

```powershell
& 'E:\eud-host\eud-terminal.cmd' -Native -Port COM14
& 'E:\eud-host\eud-terminal.cmd' -Native -Port COM14 -Command 'uname -r'
```

启动 Ctrl-U 独立发送、按原有 500 ms+jitter/最多 10 次等待受理；同步期间暂存键盘。
之后取当前队列最多 14 字节，LEN2 尾片拆成 1+1；真正原生帧按完整 payload 等回执。
数据帧只提交一次，缺回执默认 4 s 停止剩余输入、报错、finally 关闭，不自动重跑。
Ctrl-C/Ctrl-U 仍取消本地主机队列。逐键输入可能只有一字节；粘贴和命令模式实测
使用真正多字节帧。完整受理行只在显示端过滤，raw/text 从不删行。

新模式仍无序号/去重，不能保证 exactly-once；回执超时也不能证明命令没执行。
启动/超时参数、键盘限制、日志与退出说明见
[终端指南](../linux-port/docs/EUD-TERMINAL.md)。原生命令超时停止路径是源码审查，
本轮成功命令没有触发该路径。没有故意制造设备故障来测试它。

实际使用 Windows PowerShell 5.1，与 cmd 入口相同。静态 AST 无语法错误。

| 实际测试 | 帧与结果 |
|---|---|
| native-host-tail | echo R47HOST123\n；14/1/1，所有数据 1 次，完整输出/prompt；避免 2 字节尾片 |
| native-host-single-14 | Ctrl-U 第 2 次才同步；echo R47HOST1\n 的 LEN14 数据只发 1 次，输出完整 |
| native-host-multiframe | 38 字节命令，14/14/10，各 1 次；完整 R47NATIVE-MULTIFRAME-OUTPUT-1234 |
| compatible-host-regression | 不加 -Native；默认逐字、16 ACK、零重试，R47COMPAT 输出/prompt |
| native-interactive | 粘贴 echo 的 14+1；输入未完成行，再 Ctrl-U+id，LEN4，清行后 id 正常；4 数据帧 ACK，30 字节含 startup |
| native-after-reboot | LEN14 echo、34 字节 printf、变量赋值/读回、两次 54 字节状态命令；14 数据帧全部 1 次；182 字节含 startup |
| native-final-installed | 实际 E:\eud-host\cmd，最终重启后 LEN13 echo，1 次；R47END1 与 prompt 完整 |

前三个 CLI 测试发生在最后显示过滤扩展之前，分帧/同步逻辑相同；最终源码又经过
默认兼容、交互、重启与实际安装入口测试。退出均 Close/Dispose，raw 无重同步字节
或尾部残留，这只证明解帧完整。

## 47.4 新发现的真实 TX 缺字与看门狗退回

第一次同镜像重启后，20 行 `R47TX-001`..`020` 输出与 `retained` 变量读回完整。
但 rx_stats 原始输出出现：

```text
irqs=11 irq_frames=11 poempty=0 watchdog=0 drops=0 fault=0 active=1 queued=0
```

未改动的 sysfs_emit 源码应输出 `poll_frames=0 empty=0`；缺了 `ll_frames=0 `，
共 12 字符。独立 raw 解码确认，不是 stdout 过滤的旧误报。
其余帧/字节 totals=11/128，输入完整。不能据此区分 EUD TX、USB IN 和 host。

因为出现了新实质疑点，重复同一长查询检查。此次所有 4 个输入帧均一次受理，
最后 LEN12 用 `via=poll`，原始日志首次有 RX46 IRQ fallback fault=4/watchdog=1。
第二份状态完整：frames=15、bytes=tty=182、irqs=irq_frames=14、poll_frames=1、
active=0、queued=0，bad/overrun/drops=0；shell 命令继续成功。

看门狗源码在首次看到 pending 时就停 IRQ。console 整条 printk 均持 UART 锁、
禁止本地 IRQ，tty TX 每帧也持同锁；工作线程可能先于待处理 IRQ 获锁。
这种竞态/延迟是合理解释，但尚未测到 IRQ pending/进入的精确时间，不标为根因。
本轮不凭这一现象猜改延时；保留源与可复核样本供下一步修复。

## 47.5 F1、重启和最终状态

关闭每个终端 owner 后单独测试 F1。第一次 via=irq、1 OUT 成功；第二次在实际
fault=4 退回后 via=poll，第 5 OUT 受理。两次均由独立 fastboot devices/getvar
确认序列号 62bc28a1、product msmnile。没有任何 fastboot flash。
两次仅 reboot 同一 RX46 B；被动 boot capture 没有发 RX 测试帧。
首份 boot 10,919 帧、末份 13,689 帧，stray=0/pending=0，均有 TOP_CFG=11/
original=0、hwirq524 请求/使能、实际 shell 启动。

最终安装入口 echo R47END1，startup 与 LEN13 均第一次受理，87 TX 帧、零 stray/
buffered，完整输出/prompt。startup 快照 frames=irqs=1、bytes=1、active=1/fault=0；
随后数据回执 `via=irq`，无需再开一次串口查询。COM14 关闭，当前枚举与哈希见
reference/rx47/final-state.json；它是最后核实的快照。

| 保留/变更产物 | SHA256 |
|---|---|
| 不变 logdump-rx46-rx-irq-b.img | ba1689b380b40aeee2714ae7c41b44a7db3365ef61c0937b607b12537b6c320e |
| 不变实际 Image | e0f256d7b08410bc7cd17db03aa2351338753bb7b9add562d3bcedc29964fba3 |
| 不变实际/镜像 eud.c | 673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f |
| 新主机终端源码/已安装副本 | 9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57 |
| 原主机终端、外部备份 | f9bdc49e022ce4f9b1537e61ab8c5e7c2ea15a91c6447e15e64372aef8a6dc97 |

实际 init SHA e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab，
BusyBox SHA 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22 未改。
RX44 回退镜像/源码见 session 46；本轮没有移除备份或用户已有内核修改。

## 47.6 下一步与未扩大结论

先解决已保存的 TX 缺完整帧观测与看门狗“首次 pending 即失效”的判断，查实际
IRQ/console 锁进度和 TX 交付证据，再设计一个有来源的新小步。不要继续重复
旧零等待 DAT、padding/ZLP、mask-only、PHY reset 或无差别延时搜索。
端点 reset/data-toggle 可继续作为源支持方向，不能以未验证的物理假设改系统驱动。

CTRL/COM 已在量产机可用；SWD/JTAG 的 USB transport 与 AP DAP 回执权限是两层，
当前没有 AP DAP ACK，TRACE 未验证，熔丝没读。没有证明可用的通用解锁法，
不需要用刷 APDP/熔丝或切 DAP mux 来解释本轮 COM 故障。授权的 OEM debug policy
或工程机只可能提供附加观测，不是已验证的本机修复。

验证 RX47 原始证据、RX46 历史证据及 docs-health-check clean 后，仅推 fork/master。
原生终端能用是进展；新 TX 缺字与 watchdog 仍未解，目标保持开放。
