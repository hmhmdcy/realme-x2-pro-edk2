# 42. 下一会话交接：原生多字符终端稳定性（2026-10-09）

用途：澄清 session 41 的成功范围，交接剩余问题和短提示词。
来源：[session 41](41-rx-ahb2phy-wait-state-fix.md)、reference/rx41 原始证据与当前驱动。
本次只更新文档，没有开串口、操作设备、构建或刷机；下面设备状态是 session 41 的最后记录。

**session 43 更正与新入口：** 本交接引用的数次“缺命令输出”后来经原始抓取、
哈希核对确认为漏看了解码 stdout 未显示的响应，并非这些样本的 shell/TX 失败。
当前事实、设备状态与未解缺回执见 [session 43](43-native-terminal-evidence-audit.md)。
本文件保留当时排查问题的历史范围，不能继续把已更正样本作为缺输出证据。

## 42.1 已修复的是哪一层

原来的故障是：已收到多字节帧，连续读取 RX_DAT 却重复首字节，或后续读到 90。
session 41 将已确认地址的 SM8150 SOUTH AHB2PHY TOP_CFG（0x088ee010）设为 0x11，
完成回读确认，在共享 TX 锁内读完并缓存整帧，再打印/投递 tty。

这是真实多字节帧的设备侧读取修复，没有把原生输入拆成单字节来假装成功。
UEFI 两次重启均读对 ABC/DEFG；Linux 独立重复读对，并读对完整 14 字节。
原生单帧 `X=ok\n` 接收和投递 5 字节，随后兼容终端查询 `$X` 得到 `ok`，证明该输入在同一 shell 执行。
这个查询使用逐字终端，不能据此宣称原生终端的即时输出也已正常。

临时 `eud-terminal.cmd` 仍逐字发送，是保留的兼容路径；它与上述整帧修复分别验证。
len=2 始终保留给头部 F1 `[90][02]`，tty 使用 len=1、3..14；两字节尾片须改为单字节帧。

## 42.2 尚未确定的问题与判据

有些 OUT 发送没有捕获回执；有些原生命令已读对、投递 tty，却没有捕获命令输出。
尚未确定这两种现象是否同因、属于哪一层，也未确定是原先已有还是候选改动引入。
不要称其为已确认的“新问题”，也不要说所有 payload/USB/终端问题已经解决。

| 观察到的证据 | 能证明什么 | 不能证明什么 |
|---|---|---|
| 主机 Write/USB 提交完成 | 主机 API 的提交结果 | 设备已受理、shell 已执行 |
| 空抓取或无完整回执 | 该次没有捕获确认 | USB 拒收、RX 读错、设备宕机 |
| 新回执含完整期望 payload | 该次设备 RX 读取正确 | 所有帧可靠受理、命令执行或输出正常 |
| tty 实际插入计数等于长度 | 字节已进入 tty 接收缓冲 | shell 已读/执行、终端行编辑已完成 |
| 可核对的 shell 状态变化 | 对应输入确实执行 | 即时 TX 输出完整、每次命令可靠 |
| 预期响应与结束标记在原始抓取中完整出现 | 该次可见响应成立 | 长期无损、无重试或 exactly-once |

现有回执无序号/去重；同一 payload 的旧回执不能冒充新测试。
重试可能重复输入或执行，优先幂等短命令，受理即停止重发。
0 stray 只表示解帧不需跳过字节，不能当无损证明。

## 42.3 起点、路径与最后状态

* 当前保留候选：`E:\edk2-samurai-out\logdump-rx41-native-ordered-tty.img`。
  镜像、Image、eud.c 的完整 SHA256 与回退 rx33 镜像见 session 41 §41.5。
* Windows 源码副本：`E:\RealmeX2Pro edk2\linux-port\eud.c`。
  真正构建树：`/home/cy122/x2pro-linux/linux`，目标 `drivers/tty/serial/eud.c`。
  实际 initramfs：`/home/cy122/x2pro-linux/initramfs`；Windows 的旧 init 副本不能覆盖它。
* 最后记录：当前候选启动 Linux shell，TOP_CFG=0x11、原值 0；Ctrl-U 有新回执；
  COM14 已 Close/Dispose；9501/9500/9505 枚举 OK；usbipd 6-5 Shared、未 Attached。
  下次先核实实时枚举、运行模式和串口所有者，不能把此快照当当前在线状态。
* 兼容终端入口：`E:\eud-host\eud-terminal.cmd`；原生帧使用
  `linux-port/scripts/eud-step.ps1`，抓取使用新的文件名，保留 .raw 和发送时间记录。
* 仓库：`/home/cy122/edk2-samurai/repo`，只推 fork/master；
  本次文档更新前的已推送代码基线为 `eff092d495094a17ef10b976a2d22f8d54c9a294`。

## 42.4 下一轮按这个顺序推进

1. 先读 HANDOVER-NEXT.md、RX-CONSOLE.md、FLYWHEEL.md、sessions 41/42。
   sessions 35-40 是排除路径的历史；旧提示词中的“原生 RX 未修复”不再适用。
   核实实时设备状态，确认无其他串口所有者，再取得新鲜、有界的设备回执。
2. 保留 TOP_CFG=0x11 与整帧缓存方法，以当前候选和实际工作 initramfs 为起点。
   先分析 session 41 的 .raw、发送事件和代码，区分完整 RX、tty 投递与可见输出，
   不为“无回执”直接指定 USB OUT 根因。
3. 审查实际 shell/BusyBox 的行编辑、termios、tty/line discipline，以及 eud.c 的
   flip buffer、TX 队列、console/tty writer 和主机解帧/显示路径。
   终端指南记录了 `ESC[6n` 光标查询与显示端过滤：这是应核对的线索，不是已证实根因。
   先核对本地准确版本，再搜索/审查对应上下游源码，不能仅凭函数插入计数判定执行。
4. 手动做短且幂等的原生输入，记录发送、完整 RX、实际插入数、可观察 shell 效果、
   命令输出和结束标记。与兼容逐字输入对照，每轮只改变一个因素。
   核实原始抓取是否含输出但显示端隐藏，再判断 TX 或 shell 层；必要时检查等待时间，
   不能把延长等待后的偶发成功说成修复。
5. 对没有完整 RX 回执的轮次，单独追踪主机 OUT/设备受理/回执 TX。
   qcusbser 与另一主机路径的对照必须使用已修复的等待配置，旧配置下的失败不决定此问题。
   USB 提交/usbmon URB 不等同于物理总线 ACK；没有新证据不猜寄存器、PHY/时钟 reset。
6. 连续两三轮没有新信息就停止同一实验，转查源码/证据。最终要重复验证原生短命令的
   正确 payload、shell 执行和完整可见响应，并确认兼容终端、F1、console 仍可用。
   有限样本成功与长期稳定性分别报告；未解决项保留原始记录，不扩大结论。

只在新证据支持必要改动时构建，保留用户已有内核修改与备份。增量构建后用原 FAT 副本
替换 Image、核对 DTB；禁用旧 build-image.sh。新内核优先只刷 logdump；总授权范围仅
boot/logdump。发 F1 前确认旧 owner 已关闭，独立核实 fastboot 序列号 62bc28a1 后再刷。
串口始终一个 owner、try/finally Close/Dispose；不做无人值守大循环。

## 42.5 可直接粘贴的短提示词

```text
继续 RealmeX2Pro edk2 的 EUD 原生多字符终端稳定性排查。先读 HANDOVER-NEXT.md、RX-CONSOLE.md、FLYWHEEL.md 和 sessions/41、42。TOP_CFG=0x11 已验证真实整帧 payload 修复；剩余缺回执/缺命令输出原因未定，追踪 USB OUT→RX→tty/BusyBox→TX/主机抓取，审查源码，别重复旧实验。先核实设备状态，手动小步、串口 finally 关闭；优先只刷 logdump，仅允许 boot/logdump，保留 F1/console/兼容终端，记录并推 fork/master。
```
