# 49. USB IN 与部分超时数据核对（2026-10-09）

**取得了独立接收边界证据，仍未证明长期稳定性已解决。** 不改 RX48 内核，
本轮无刷机、无手机重启、无新管理员 ETW。持续 libusb owner 下的 60 行输出完整；
CRC 有效的 512 个已发 MMIO 记录匹配 raw，全部 11,066 个 raw 字节也匹配 usbmon
IN 数据。还实测一次取消完成带 6 字节，PyUSB 正确保留了它，没有丢掉部分数据。

当前镜像/回退/哈希仍见 [session 48](48-irq-grace-and-tx-journal.md)，原始证据和独立
验证见 [reference/rx49](../reference/rx49/README.md)。TOP_CFG=0x11、整帧 RX、console/F1、
兼容/原生终端和固定 TX 节奏均保留。不能因本轮成功撤回 RX47 的真实缺字。

## 49.1 先核实时态，再查主机读取语义

开始时 master/fork/master=6ea8338、Git 干净；实际 WSL eud.c/Image 与 RX48 B 相符，
9501/9500/9505 OK、COM14，usbipd 6-5 Shared/not Attached，上一轮所有 owner 已关。
新 Ctrl-U 第一次提交受理：frames/pending/irqs/irq_frames=3、bytes=15、tty_before=14，
active=1、fault=0，finally 关闭。没有自动运行旧探针或 reset。

搜索官方 libusb 同步 I/O、PyUSB libusb1 实现和 Linux usbmon 文档，并读取实际安装的
PyUSB 1.2.1-2：其私有 read 在超时且 transferred>0 时返回已收数据，零数据超时才
抛异常。不能把旧空捕获归咎于“超时必然丢字”。源与限定见
[source-audit.md](../reference/rx49/source-audit.md)。

先离线核对 7 组已归档 IN，不重复硬件实验：

| 历史样本 | raw / 完整 IN 字节 | 有数据 IN 完成 | 结果 |
|---|---:|---:|---|
| RX46 libusb-native-d-ready | 186 / 186 | 32 | 逐字节一致 |
| RX46 libusb-native-e | 186 / 186 | 32 | 逐字节一致 |
| RX46 libusb-native-f-full | 216 / 216 | 37 | 逐字节一致 |
| RX46 libusb-metrics-after-f | 321 / 321 | 54 | 逐字节一致 |
| RX43 libusb-native-b | 174 / 174 | 30 | 逐字节一致 |
| RX43 libusb-stty | 0 / 0 | 0 | 673 次取消完成，无 IN 数据 |
| RX43 libusb-dmesg-tail | 1377 / 1377 | 230 | 逐字节一致 |

这些 trace 没有截断 payload，也没有非零状态且带数据的完成。stty 的零字节只定位到
该虚拟 HCD 的 IN 边界，不证明物理 OUT 被拒绝；不可当作 USB packet/ACK 测量。

## 49.2 新对照的手动边界与工具修正

只把现有 Shared 的 9505 attach 到 WSL，没有 bind/force、换驱动、设备 reset 或配置
变更。WSL debugfs 已挂载；加载 usbmon 模块供只读监测，没有 Windows UAC。
`eud-usb-session.py` 一次 claim，独立 IN 读取与目标 usbmon 记录；每次人工输入才
发送，最多 12 个发送步骤，900 秒入口时限在步间检查，单帧回执另限 4 秒；
原生帧最多 14 字节，LEN2 尾片拆 1+1。
启动 u 单独发送一次，受理前不允许命令；数据帧只发一次，缺回执停止余下输入并退出。
正常/异常都结束线程并 dispose USB，外部再 detach。没有协议序号/去重承诺。

首版只做 u 与 P 赋值：4 数据帧/43 字节全部受理，160 IN 帧/940 字节完整匹配 raw。
显示却漏过滤 BusyBox `ESC[6n`，主机终端自动回复显示在本地主机输入行。正常关闭
owner 后修正显示层，raw/text 保留原始查询；不把这个 UI 问题当作设备丢字。
首版源码由修正前后差异重建，SHA 与此前实测的 2fc26164... 完全一致，明确标注。

关闭首版后，WSL 重新启动（新 uptime=34.59 s），usbmon 消失、9505 已恢复 Shared
而非 Attached；一次准备启动找到 0 个设备，发生在创建日志、claim 和 OUT 之前。
没有以此算失败 RX。重新加载监测/attach，立即启动修正版，未重启手机或更改 WSL
全局配置。修正版实际源码 SHA 69bb5700... 写入运行 metadata。

## 49.3 修正版持续 owner 的实际输入与结果

一次打开后手动执行，保留首版已赋值的 P，echo 验证 shell 状态仍在：

```text
u
send echo $P
send cat $P/irq_state
send printf 'R49IN-%03d\n' $(seq 1 60)
drain
send cat $P/rx_stats
send dd if=$P/tx_journal of=/tmp/R49J1 bs=4096 count=1
send base64 /tmp/R49J1
drain
send cat $P/irq_watch
x
```

drain 不发设备数据。8 个发送步骤，17 数据帧/160 字节加一次 Ctrl-U=161 字节，
每个 OUT 只提交一次并有对应回执。60 个 R49IN-001..060 连续完整，P 仍为实际设备路径；
usbmon 的 18 个 OUT payload 与手动提交逐字节相同，18 个完成均 status=0、长度完整；
首版也有 5 个相同边界的 OUT，无额外 bulk OUT 混入。这仍不是物理 USB ACK。
irq_state=`gic=80 err=0`，最后 irq_watch waits/recovered/cleared=0、max_ms=0。
状态快照 frames/pending/irqs/irq_frames=18、bytes/tty=135，bad/no_tty/overrun/
watchdog/drops/fault=0、active=1。宽限分支仍未触发，不称已验证。

tmpfs 不可变快照 3120 字节，seq 7713..8224、512 记录、CRC e05be687。
512 个软件已发帧全部匹配 base64 输出前的同一 raw；未知窗口前后不计丢失。
整个 owner 的 1858 EUD 帧/11,066 字节完整匹配 usbmon 的 1858 个带数据 IN 完成。
6675 个 IN 完成中：1857 status=0，4818 status=-2；后者有一个带 actual=6：

```text
ffff8b380ed13000 77217900 C Bi:1:002:1 -2 6 = 90046769 633d
```

这些字节是 EUD LEN4、payload `gic=`，下一帧接 `80 e`，raw 中状态为完整的
`gic=80 err=0`。取消带部分数据真实发生，读取器按安装的后端语义保留了它。
这里的 -2 是 usbmon URB 状态；未直接记录 libusb 原始返回码，不把二者等同。
zero-data timeout/cancel 不是丢字计数，不能将 4818 次取消全部当作失败接收。
所有 IN payload 均完整捕获，未以状态非零为由丢掉有实际字节的记录。

关闭日志报告 steps=8、data_frames=acked=17、stray/pending=0、无线程存活/错误；
finally dispose 后 detach。USBmon 位于 WSL 虚拟 HCD：它不能区分物理设备 TX 与
Windows USBIPD 上游丢失，也不能代表 qcusbser 路径或物理 DATA0/1/ACK。

## 49.4 最后状态和下一步

恢复 Windows 后实际安装原生终端 `echo R49END1`：启动 Ctrl-U 与 LEN13 均首次受理，
输出/prompt 完整，90 TX 帧、stray/buffered=0，串口 finally 关闭。
最后 Ctrl-U 快照 frames/irqs=27、bytes=221、tty_before=220，和本轮手动输入计数
一致，没有额外光标回复进入设备 RX；最后 LEN13 经 IRQ 受理。不是物理 exactly-once
证明，现有同值/延迟回执的协议限制不变。

22:19:10 +08:00 快照：9501/9500/9505 OK，仅 COM14，usbipd 6-5 Shared/not Attached；
镜像仍为 RX48 B SHA 61c0315c...，eud.c e25d7fe2...，主机终端 9c7a16f1...。
没有刷新 boot/logdump、phone reboot 或重测不变 F1；RX48 已实测的 console/F1 保留。
用户已有内核修改、init/BusyBox、DTB、回退与外部镜像均未改。

新证据排除了这些样本中 PyUSB/解码器丢失已经返回的 IN 数据，并验证了发送记录→
虚拟 USB IN→raw 的一段对应关系。本轮没有重现 RX47 缺字；失败 OUT 的物理交付与
GIC/IRQ 首次 pending 进展仍开放。下一步应抓到实际异常的不可变快照/IRQ 进展，
不能继续重复已成功的同类输出当作根因证明。宽限、持续 owner 和 startup sync
是可用路径与诊断，没有证据可以把长期稳定性或熔丝解锁宣告完成。
验证本轮证据和 docs-health-check clean 后，仅推 fork/master。
