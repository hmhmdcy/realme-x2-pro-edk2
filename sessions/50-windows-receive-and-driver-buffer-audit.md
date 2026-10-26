# Session 50：当前连接正常；补齐 Windows 接收观测和实装驱动缓冲边界

2026-10-09，Asia/Shanghai。用途：区分当前可用状态与历史偶发故障，给异常窗口
留下新证据，停止重复正常编号输出。关联：sessions 47–49、reference/rx50。

## 50.1 当前状态与本轮范围

**本轮连接正常，没有复现缺回执或缺字。** 排查对象仍是 RX47 真实缺少 12 字符、
重开 owner 后没有设备 RX 的历史观测；不是重做已经修好的 TOP_CFG=0x11 整帧
payload，也不是声称现在每条命令都有故障。用户询问是否只是纠结旧问题后，明确
区分“当前能用”和“长期/重开后的稳定性未证实”，本轮收尾，不追加同类成功实验。

开始/结束均核实 9501/9500/9505 OK、COM14、usbipd 6-5 Shared/not Attached；
Git master/fork/master 为 b957120，工作树原先干净。实际内核路径是
/home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c，SHA e25d7fe2...；
Image SHA 5565d694...。RX48 B 镜像 SHA 61c0315c... 未改。
没有手机刷写/重启、新管理员抓包、驱动/注册表/滤镜修改或 reset/PHY/fuse 操作。
已安装终端及兼容模式 SHA 9c7a16f1... 未改，console/F1 保留 RX48 的实测状态。

## 50.2 新观测依据及诊断副本

互联网查阅微软官方串口文档及参考源码，并读取实际 System.dll 的 IL 调用点。
发现原终端 BytesToRead 查询会调用 ClearCommError，但不保留返回的错误码；原版
也没有 ErrorReceived 记录。不能从旧的“没显示错误”推出没有缓冲溢出。

另存诊断副本 eud-terminal-rx-audit.ps1 + EudRxAudit.cs，不替换 E:\eud-host 中的
终端。-RxAudit 在同一个串口句柄上保存 ClearCommError 的错误/队列值，并记录
异步错误通知、每次实际 Read 的偏移/长度、轮询间隔和解码显示耗时；不改缓冲大小、
flow control、USB 操作或设备输入格式。检查字符缓存为零，否则拒绝继续。
原 raw/text、ESC[6n 显示过滤、原生回执边界、最多 LEN14、LEN2 尾片 1+1 都保留。
启动 Ctrl-U 可以有界同步，数据只提交一次；本样本均首次受理。finally 关闭/dispose
串口、移除 C# 事件处理器并关闭日志。180 秒检查在主循环之间，不是显示阻塞时的
硬截止；实际会话 76.214 秒、人工 Ctrl-] 正常退出。诊断增加主机开销，不称完全中性。

具体实现、实际程序集及精确驱动分析见 reference/rx50/source-audit.md。
已运行来源：脚本 SHA f337b789...，C# SHA 123034ac...，日志开头保存完整值。

## 50.3 一次手动持续 owner 的结果

只开一次 COM14；启动 Ctrl-U 的新回执显示 frames/irqs=29、bytes=235，active=1，
fault/watchdog=0。确认新回执后，沿用上一轮 shell 中的 P，人工依次输入：

```text
cat $P/rx_stats
dd if=$P/tx_journal of=/tmp/R50J1 bs=4096 count=1
base64 /tmp/R50J1
cat $P/irq_watch
Ctrl-]
```

11 个数据帧、101 字节，加一次 Ctrl-U；12 次 OUT 均一次发送并收到对应回执。
rx_stats 输出完整，含原来发生缺字的 poll_frames/empty 字段；frames/irqs=32、
bytes/tty=251、poll_frames/watchdog/drops/fault=0、active=1，输入计数与当时边界一致。
irq_watch waits/recovered/cleared=0，仍未验证 IRQ 宽限分支。

原始捕获 8996 字节、1508 EUD 帧、258 次非空 Read，零 resync/尾部残帧。
每次实际返回长度对应 raw 中连续偏移，全部字节入 raw；没有“修补”缺失数据。
观察到最大接收队列 150 字节、最大轮询间隔 93 ms、最大 Read 1 ms、最大
raw/解码/显示处理 39 ms；错误采样/异步错误通知均为零。记录的 ReadBufferSize=4096
是属性设置，不是内部 high-water 阈值实测。上述结果仅适用于本次正常样本。

tmpfs 不可变快照 3120 字节、512 记录、seq 9311..9822、CRC d8df3fa2。
其中先前的 225 帧在 owner 启动前，不能在本捕获核验；其余 287 帧（seq 9536..9822）
与 raw 的前 287 帧直接逐帧相等，包含完整 rx_stats 输出。不是把全部 512 帧称为
已匹配，也不是物理 USB ACK。快照之后的 dd/base64/irq_watch 输出不在该快照内。

## 50.4 精确实装驱动的新增依据与结束状态

找到本地 CAB 的 qcusbser.sys 与安装文件 SHA 完全相同；qcusbser.pdb 的 GUID/age
与 PE RSDS 相同，节表逐字节相同。解析匹配符号和完整 PDB C 结构后，确认
2.1.3.5 的 vPutToReadBuffer 在高水位/剩余空间不足时会拒收整个 block，并设置
QUEUEOVERRUN；SerialGetCommStatus 返回后清除此错误。早期拒收分支没有在该函数
中增加 BufferOverrunErrorCount，不能只靠一个累计值为零排除故障。
这消除了“源码版本不同”的一部分不确定性，**没有证明旧缺字是 Windows 溢出**。
新版 WDF 的 Errors=0 行为不可套到实装旧 WDM。没有改驱动或盲目增大缓冲。

结束快照 23:00:03 +08:00：枚举仍正常、Shared/not Attached、已知 EUD helper 无，
串口已 finally 关闭。手机、内核、Image、init/BusyBox、DTB、安装终端和回退均未改。
第三方 DLL/PDB、完整符号/类型/反汇编和微软源码只留本地；发布审过的身份/字段、
自写可复核工具及捕获，不发布驱动二进制。

现在可按现有原生终端正常使用。后续若真实异常出现，应保存当次 raw/接收观测和
不可变 TX 快照，再定位到设备发出前、USB/驱动接收或显示层；不能把继续正常通过
的样本当根因修复。缺回执的 OUT 物理交付、端点数据翻转和 IRQ grace 仍开放。
本轮独立证据校验与 docs-health-check clean 后，仅推 fork/master。
