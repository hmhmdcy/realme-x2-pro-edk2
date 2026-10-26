# 48. IRQ 宽限诊断与可校验 TX 记录（2026-10-09）

**本轮取得了发送侧的可复核证据，尚未解决长期稳定性。** 当前安装
`logdump-rx48-tx-journal.img`，保留 TOP_CFG=0x11、整帧 RX、F1、console 和默认兼容终端。
CRC 有效的 512 帧发送快照全部与主机 raw 对应；这个样本没有重现 RX47 的缺字。
不能把本轮成功改写成 RX47 缺字不存在，也不能将未触发的 watchdog 分支称为已修复。

前置读物仍是 HANDOVER-NEXT.md、RX-CONSOLE.md、FLYWHEEL.md、sessions 41/42，
以及 RX43 的更正、RX44-47 的计数/IRQ/会话边界证据。
原始数据与验证在 [reference/rx48](../reference/rx48/README.md)。

## 48.1 状态、授权和实验范围

开始时确认 9501/9500/9505 OK、COM14，usbipd 6-5 Shared 而非 Attached，仓库
master/fork/master=b660d24 且干净。实际 Linux 源码/Image 与 RX46 B 哈希相同，
已安装主机终端与 RX47 源码相同。先分别以新 Ctrl-U 和 F1 回执核对当前状态。

只刷了两次 logdump：先 A 的 watchdog 宽限诊断，再 B 的 TX 软件记录器。两次都
独立核对 fastboot 序列号 62bc28a1/product msmnile；boot 未刷。实际 initramfs、
BusyBox、DTB 保留，构建脚本逐字节核对 FAT 中新 Image 与不变 DTB。
没有再次管理员 ETW、改驱动、force bind、PHY reset、DAP mux、APDP 或熔丝操作。
串口单一 owner，手动小步；所有退出/异常通过 finally Close/Dispose。

## 48.2 有来源的 IRQ 诊断 A

RX47 的 watchdog 在第一次读到 pending 时即停 IRQ；打印 console 整条消息持 UART
锁并禁本地 IRQ，工作线程先获得锁可能与正常 IRQ 服务竞争。这是源码支持的解释，
不是已测根因。本轮保留 20 ms 状态观察；第一次 pending 只记录，放锁给 IRQ
执行机会。持续未受理达到 100 ms 才停 IRQ、转原轮询，避免第一次观察就判失败。
100 ms 是五个观察周期的有界诊断选择，不是 USB 延迟校准。

新增只读 `irq_watch` 记录 waits/recovered/cleared/waiting/max_ms/first/last/err。
GIC pending/active/masked 用 `irq_get_irqchip_state()`，调用在 UART 锁内、禁抢占/IRQ；
实际直接 GICv3 无睡眠 bus_lock，并审查了描述符锁和 fasteoi 处理路径。
位义：有效 80、pending 01、active 02、masked 04；三个读取并非原子同时快照，
错误会清有效位，err 是保留的错误记录。没有修改 GIC 状态。
源码/官方依据见 [source-audit.md](../reference/rx48/source-audit.md)。

A 启动 console、TOP_CFG=11/original=0、hwirq524 和 shell 完整。持续 owner 下：
两次长状态命令、30 行编号输出并紧接另一个状态命令、最后 irq_watch 查询，
共 19 个数据帧/254 字节加启动 Ctrl-U=255 字节，全部一次提交受理；编号输出完整。
受理 printk 插在第 18 行末尾与换行之间，原始记录保留；这是 console 与 tty 交错，
编号字符没有丢失，不要求多个 writer 的输出整行连续。
frames/irqs=16、bytes/tty=200 的中间计数一致；waits/recovered/cleared/max_ms 均 0，
active=1、fault=0。F1 第 2 OUT 经 IRQ 进入 fastboot。
**没有进入首次等待、恢复或超时分支，不能宣布竞态修复已验证。**

## 48.3 保持 TX 节奏的记录器 B

B 在 A 上增加软件环形记录，不改 TX ID/LEN/DAT 次序、每帧最多 4 数据字节、
每寄存器 200 µs、每帧 2 ms 等待。每次 `eud_send_frame()` 完成这些已发出的写入后，
在已有 UART 锁内保存 len、source（tty=1/console=2）和 4 字节数据。
记录增加少量内存/执行开销，不能声称观测绝对不扰动时序。

只读 binary sysfs `tx_journal` 原子复制最近 512 帧：48 字节 LE 头、6 字节记录，
最大 3120 字节。头含 `EUDTXJ48`、版本/大小/数量/记录大小、首尾序号、CRC32/IEEE。
CRC 覆盖整份快照，计算时 CRC 字段置零。序号仅用于软件记录，不是 USB ACK。
读取须从 offset=0 一次提供足够 buffer；小 buffer 返回 EINVAL，非零 offset EOF。

第一次编译漏改 shutdown 的第三个发送调用，构建失败，保存错误日志和源码；
修正后重新编译无 warning/error，才打包并刷 B。失败版本未刷入设备。
新增 `irq_state` 是显式只读 GIC 查询，`irq_watch` 本身不读硬件；实测 idle
`gic=80 err=0`（有效、未 pending/active/masked），API 可在当前映射上读取。

在**同一个已同步 owner**里依次执行（Enter 实际发送 LF）：

```sh
P=/sys/bus/platform/devices/88e0000.serial
printf 'R48BASE-%03d\n' $(seq 1 30)
cat $P/irq_state
cat $P/rx_stats
dd if=$P/tx_journal of=/tmp/R48J1 bs=4096 count=1
base64 /tmp/R48J1
cat $P/irq_watch
```

先保存 tmpfs 文件，再传 base64，避免传输过程中窗口变化。CRC 验证通过：
3120 字节、512 记录，seq 7415..7926、CRC a3e1b9b4。
这 512 个软件已发 MMIO 帧全部与 base64 输出前的 raw 帧匹配，没有内部缺帧。
30 个编号行与状态字段完整；rx_stats frames/pending/irqs/irq_frames=13，
bytes/tty=113、bad/overrun/watchdog/drops/fault=0、active=1。
最后 irq_watch 仍为 waits/recovered/cleared=0，未触发宽限分支。
总计 20 个原生数据帧/197 字节加 Ctrl-U=198 字节，数据全部一次受理；
接收 1860 帧，stray/buffered=0。零 stray 本身仍不证明无完整帧丢失。

记录器证明 CPU 发出的 MMIO 值；**它不能证明 EUD 物理发送、USB ACK 或设备 FIFO
收到这些值。** 本样本只是软件记录和主机捕获一致，不能把 RX47 的 12 字符缺失
定位到具体 TX/USB/host 层。非空比对间隙须逐项审查，未知前缀/尾部不当成丢帧。

## 48.4 兼容、F1、重启和最后状态

默认兼容终端 `echo R48COMPAT` 返回完整输出/prompt。启动 Ctrl-U 重试 1 次，
命令字符都受理；16 ACK、194 TX 帧、零 stray/buffered。只观察到启动重试，
没有后续独立计数证明首次 OUT 在哪层丢失，勿据此扩大到 data-toggle 根因。

B 的 F1 第 2 OUT 经 IRQ（irqs=38/fault=0）进入 fastboot，独立设备查询确认。
仅 reboot 同一 B，无第三次刷机。被动捕获 13919 帧、stray/pending=0、sent=0,0，
TOP_CFG、IRQ arm 与 shell 正常。已有 early ioremap WARNING 仍在，未在本轮修复。

重启后实际安装入口 `-Native -Command 'echo R48END1'`，启动 Ctrl-U 与 LEN13
数据均首次受理，完整 echo/输出/prompt；87 TX 帧、零 stray/buffered。
启动快照 frames/irqs=1、bytes=1、active=1/fault=0。所有 COM14 owner 已关闭。
21:47:31 +08:00 最后快照 9501/9500/9505 OK、仅 COM14，usbipd Shared/not Attached；
具体枚举/hash 是该时刻的记录，下一轮仍先核实实时状态。

| 当前/回退产物 | SHA256 |
|---|---|
| 当前 logdump-rx48-tx-journal.img | 61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d |
| 当前实际 Image | 5565d69447afa60d18aab045030b3ccedb1188daa9022bb379d8a6e38ef9117d |
| 当前实际/镜像 eud.c | e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066 |
| A logdump-rx48-watchdog-grace.img | 9a1740c26cd6de899ef1255262f4a83b920e7f36982a8ec02aff549d599396b4 |
| A Image | 0e4580dabe7a779a4168e6fec03c968adae6c155a2f259fb01b9178dd7ccd511 |
| A eud.c | f76c670a2c5be73521154b666dc42574ee4690966953ca8fb18202de92faf1f6 |
| 回退 RX46 B logdump | ba1689b380b40aeee2714ae7c41b44a7db3365ef61c0937b607b12537b6c320e |
| 回退 RX46 B eud.c | 673c485843bc551788a0eb90499207371110807d4700a1f3f20d42b76e4e921f |
| 不变主机终端源码/安装副本 | 9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57 |

实际 init SHA e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab、
BusyBox SHA 999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22 不变。
DTB 字节一致；用户原有 DTS/rpmh/earlycon/内核修改和备份保留。镜像保留外部目录。

## 48.5 下一步须带来的新证据

当前连续原生命令可用，但长期稳定性仍开放。宽限分支需一次真实 pending 等待
样本的 GIC/IRQ 进展；不能反复查询直到凑出“成功”证明。
TX 缺字若再出现，先保存不可变 journal 并验 CRC，将软件已发帧与原始 USB IN/
串口帧比较；下一种独立边界可用 libusb/usbmon **IN payload**，不是重复旧 OUT
回执实验。CRC 不通过就不作定位；同一临时文件可有界重取，不重跑可能执行的命令。
不凭 TX status 常置位复制厂商残缺流控，不猜改等待时间。

本轮再次阅读官方 generic IRQ 和同机型厂商 TX 实现；后者没有提供可直接采用的
完整 LEN/流控算法。来源与限定单列在 source-audit。保留此前 Windows/libusb 缺回执
与 ETW reset 的边界，不称已找到物理根因；不需要尝试熔丝/调试权限解锁。
验证本轮证据、历史 RX46/47 和 docs-health-check clean 后，仅推 fork/master。
