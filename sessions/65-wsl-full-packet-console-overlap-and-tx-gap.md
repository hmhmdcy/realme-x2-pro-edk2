# 65. WSL 整包 console RX 通过，连续会话仍缺 tty TX（2026-10-10）

**WSL 能绕过 qcusbser，但没有解决全部终端问题。** 长日志期间一次 14 字节原生输入
通过 console collector 完整受理，BusyBox 独立读回正确值；随后同一 owner 的状态输出
缺 9 个完整 TX 帧。CRC 有效的手机软件发送快照确认缺 36 个 payload 字节、54 个线缆
字节，另外 503 帧直接匹配。此缺口也不存在于 WSL 虚拟 HCD 的完整 IN 数据中。
因此这个连续会话样本不需要 qcusbser 或串口 reopen，不能称 Windows 候选已修复。

证据及离线核对见 [reference/rx65](../reference/rx65/README.md)。完整稳定性仍未达到。

## 65.1 设备核实与限定启动

用户选择 WSL 路径并告知手机已连接。先看到 18d1:d00d fastboot，设备 62bc28a1，
product=msmnile；只执行一次 fastboot reboot 启动现有镜像，没有刷分区。冷启动后
9500/9501 正常而 9505 未出现，按已审查的正常 COM 启用路径执行一次 eudtool com-up：
CTL CLR0、SET20、SET1000、SET2000、等待200ms、CLR2000，五次写均完成5字节。
没有使用 reset opcode09、com-off、forcebind、SWD/JTAG/熔丝或 PHY/时钟探针。

00:29:51.3942701Z 基线：三节点 OK，COM14，oem102.inf/qcusbser2.1.3.5，软件键0008；
USBIP 6-5 Shared/not Attached，无已知 owner、临时日志或 EUD ETW。驱动、安装终端、
RX53 logdump 及 eudtool 哈希均与原值相同。原 TOP_CFG0x11 整帧/RX53 console IRQ/
LEN2 header-only F1/原生及兼容终端/RX48 回退保留；本轮没有另做 MMIO 回读或 F1。

WSL Ubuntu 实测 kernel6.18.40.1、PyUSB1.2.1-2，原已验证取消部分数据 backend SHA
0c86fc30…ffba60。按正常 attach 接管已 Shared 的 9505；IN81/OUT02、interface0、
MPS16。只读当前配置，不 reset/重新配置/自动解绑。Windows COM 没有被打开。
[Microsoft WSL USB 流程](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)
说明 attach 期间 Windows 不能同时使用设备；WSL USB/IP 仍经过 Windows 下层 USB。

## 65.2 一个新条件：busy-console LEN14/wire16

沿用 RX52 已验证的独立持续 IN reader/sink 和部分取消处理，只把旧7字节 probe 换成
`R65H=12345678\n`，14字节，wire `900e523635483d31323334353637380a`。
一次49字节触发命令生成同长度1009字节 kmsg 记录；marker 后约152ms只发一次 probe。
没有把重复旧7字节成功样本当新进展，也没有自动数据重试。

主 owner `wsl-full` 启动00:30:28.257587Z，依次手动：

```text
u
send unset R65H;P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch
overlap
send printf 'R65H=<%s>\n' "$R65H";cat $P/rx_stats $P/irq_watch
send dd if=$P/tx_journal of=/tmp/R65J bs=4096 count=1
```

Ctrl-U 首次取得新回执。marker/probe/end/receipt 为
36395.652 / 36548.576 / 37195.691 / 37279.884ms；probe 完成16字节，回执 latency
731.308ms，明确 via=console，独立 printf 输出 `R65H=<12345678>`。
990个零完整，基线 frames7/bytes=tty84；查询时 frames18/bytes=tty205/console_frames1。
后状态 raw 残缺，不能直接从那条残缺输出宣称所有故障计数为零。

全部22个 OUT（含启动同步）只发一次、完成且有回执；没有 LEN2 tty 帧，查询尾2字节
拆成两个 LEN1。目标 usbmon 没有零长度 OUT 或捕获期控制传输；这不证明物理 ZLP/PID。
raw6547字节、1108帧与所有正长度 IN 完全相同；含两个 -2 状态的完整6字节返回，
都正确保存。全捕获最大 completion→下一 IN submission 间隙4610us，因果尚未证实。

180秒界限到达前179.325秒开始保存快照，命令完成跨过界限约0.73秒，之后只关闭，
没有在主 owner 导出快照。关闭记录180731.390ms，sink排空、无活 worker/errors。
这是轮询边界在命令间检查的实际限制，不能称严格180秒内结束；下一工具应在发送前
预留命令及 finally 时间。x 输入到达后进程已结束；launcher finally 完成 detach。

## 65.3 CRC 有效快照确认 WSL TX 缺口

取回已存 `/tmp/R65J`，没有重新取当前 journal 或重跑 overlap。第一次独立导出
`base64 /tmp/R65J` 得到4156字符，应为4160；解码3117字节，CRC失败，保留原始结果。
之后另一个有界 owner 用 `gzip -c /tmp/R65J | base64`，得到1030字节 gzip，gzip完整性
与内部 journal CRC均通过，解压3120字节，CRC44ba763a，seq7868..8379。
完整快照来自这次独立接收，未向损坏 raw 补字或按期望修正。

使用唯一16帧锚点、整段直接比较及缺口中唯一幸存帧，512记录中的503帧完全匹配。
缺失 seq8221、8223..8228、8230..8231，全部 source1（tty），每帧 payload4。

```text
软件记录： empty=1 watchdog=0 drops=0 fault=0 active=1
实际收到：`ty=1t=0 `（末尾有一空格）
```

软件记录证明 CPU 发出的 MMIO 值，不是硬件接收/物理 USB ACK。USBmon 全部正长度
数据与 raw 逐字节相同，因此排除仅在 Python 保存、解码或显示层丢失；EUD 发出/
硬件 FIFO、物理 USB 与 Windows USB/IP 下层仍未区分。后续两次新 Ctrl-U 均读到
IRQ active1/fault0、empty1，说明接收 collector 仍工作，不能把 TX 丢失当 IRQ RX失效。
损坏 base64 与有效快照比较，唯一缺4字符 `IDNk`；这是另一处输出缺口，未校验的
第一次导出不能用来归因或直接作 journal。

两个导出 owner 分别24.462秒、22.341秒，只有同步和导出，数据无重试；手动 drain/x，
finally 释放/detach。第二 owner 的所有7041字节、第三的2826字节均等于完整 IN。

准备时另有三次前置失败，均未发 bulk 输入：WSL已停止导致attach拒绝；WSL重新启动后
usbmon未加载，打开trace前退出；离线脚本误命名inspect.py遮蔽标准库，在import阶段退出。
后两次launcher finally detach；修正启动/usbmon预检并把脚本改名后才完成导出。
没有把这些工具错误算成新的手机故障。元数据与错误说明保留。

## 65.4 搜索、使用范围与下一项

结合新样本重新搜索 EUD COM TX FIFO/ready、USB/IP取消和libusb数据丢失。
[Qualcomm downstream EUD 驱动](https://android.googlesource.com/kernel/msm/+/44024ba70818aa7ddee42a5dc17991ef9c48c2d2/drivers/soc/qcom/eud.c)
有 TX IRQ 分支，但未给出本机已验证的无损 FIFO/ready 协议。
[usbmon 官方说明](https://docs.kernel.org/usb/usbmon.html)限定软件/HCD边界；本轮按 callback
实际长度核对全部数据。搜索没有找到可直接采用且匹配本触发条件的现成修复，不能
把其他芯片 FIFO、其他 USB/IP 实现的取消 issue 当本机根因。

当前没有可称稳定可靠的 tty/console。EUD COM 是90/LEN/data协议，当前安装路径没有
提供普通UART文本接口；需要现有eud-terminal.cmd（兼容默认或-Native）/WSL专用libusb
封装解码与回执工具，PuTTY等不能直接替代。工具能正确处理协议，不保证传输无损；
以后可加虚拟COM/PTY转接供通用终端使用，但那不替代底层丢帧修复。

后续EUD待办针对这个连续WSL、source1 TX缺口，检查缺口邻近IN请求/取消空窗及已审查的
真实TX/FIFO语义，再设计单变量诊断；不泛改延时、reset/零等待/掩码或重复普通成功输入。
Windows普通重开首包候选仍是独立未加载/未验证项，RX62/63完整验收矩阵仍保留，WSL
通过一个LEN14条件不能替代它，也不能宣称长期可靠或手机/Windows单独根因已经确定。

用户本轮最新决定优先推进Linux内核问题，不继续耗费在EUD上。本轮完成归档后不再
追加EUD实验；上述TX与Windows候选审查保留为待办。EUD仅作辅助观察，关键内核日志
应先在设备内保存完整副本，导出后核对长度/哈希/CRC。用户进一步明确：在下一个会话
先读取日志，再根据实际日志判断内核问题，目前并不知道有什么内核故障。当前不再
读取设备或预设具体内核症状，不凭通道现状虚构Linux根因或把短passing日志当完整验收。

00:39:08.7931485Z 最终核实：三节点OK、COM14旧绑定、Shared/not Attached、无已知owner/
日志/ETW；原驱动/终端/logdump/eudtool哈希不变。没有刷机、换驱动、UAC或安全设置改变。
只修改证据与交接文件，离线核对/docs-health-check通过后仅推fork/master。
