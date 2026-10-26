# 59. 联合抓取与主动奇数帧重开实验

2026-10-10。[证据和离线复核](../reference/rx59/README.md)。

**尚未修复，但已得到更有区分力的实测。** 在“前 owner 收到 75 个短 IN 帧、只发
两条短 OUT”的预先定义条件下，普通重开后首次 Ctrl-U 受理，首个 console 帧仍
丢失。新 seq12407 缺 `90 04 5b 31 30 30`，其余 511 条软件发送记录直接匹配。
同次驱动原始日志、ReceivedCount、终端 raw 都少六字节；ETW 未见带正长度的
失败 IN。数据翻转失配目前最吻合，**物理 DATA0/1、ACK 仍未测到，不能称根因已证实**。

用户已明确提供持续授权，后续同范围诊断不再逐次申请 UAC。授权并不扩大刷写范围：
TOP_CFG=0x11/整帧 RX、RX53 console RX、F1、兼容/原生终端与 RX48 回退均保留。
本轮未改手机源码、镜像、安装终端，未刷机/手机重启/换驱动或做额外 PHY/reset。

## 59.1 原先准备的三首状态联合测量已执行

冻结 RX58 helper `dcee7311...`，一次 UAC，只临时改 COM14 两项日志配置，启用/恢复
各重载其叶节点一次；同步 USBXHCI/UCX/USBHUB3 ETW。完成后恢复，独立状态复查。

| owner | 收到短 IN 帧 / wire 字节 | 非空 OUT 请求 | 首 Ctrl-U | 首 TX 前缀 |
|---|---:|---:|---|---|
| 1 | 54 / 324 | 1 | 第一次受理 | 完整 |
| 2 | 54 / 324 | 2 | 第二次受理 | 完整 |
| 3 | 1413 / 8438 | 10 | 第一次受理 | 完整 |

全部 9086 字节在驱动原始日志、接收计数、host raw 一致；1521 个成功 IN 完成的长度
顺序逐一等于日志记录。CRC `a2500b15`、seq10674..11185 的 512 帧全部直接匹配
（前 RX57 owner 137 + 本轮 375），没有复现 TX 缺口。

前两个 owner **实际到 20 秒诊断期限后在 finally 关闭**，并非手动 Ctrl-]；第三个
80.253 秒手动关闭。没有超时后继续输入或重复数据。这个偏差保留，不包装成全手动。
第二个首同步缺回执依然发生；开日志没有消除它。

ETW 1573 对 bulk dispatch/completion 全部配对，EventsLost/BuffersLost=0。18 条失败
IN 都是关闭时的零长度取消（NT `c0000120` / USBD `c0010000`）；不存在失败正长度。

## 59.2 先用旧样本提取奇偶规律，再定义干预

独立严格解码结果：

| 已证明首帧缺失样本 | 前 owner 收到短帧数 |
|---|---:|
| RX51 seq11733 | 689，奇数 |
| RX53 seq7287 | 10623，奇数 |
| RX55 seq7376 | 89，奇数 |

旧 RX46 的前 owner 31 帧也是奇数，下一段从时间戳中部开始；它没有 CPU journal，
只能作弱对照。原 RX46 ETW 的 83 条成功 IN 长度共 489 字节，12 条失败全部零长度。
当前 54→54→首前缀完整是偶数对照。首次完整 PnP 重载后通过，不能与普通串口重开
混算；RX57 结束于奇数帧而 RX58 第一个通过，正是这个边界条件。

新 [parity-plan.md](../reference/rx59/parity-plan.md) 在运行前定义：两 owner，60/100
秒上限，总捕获 <=180 秒。第一条 Ctrl-U 必须首次受理；按观测帧数手动发送一次
abc/abcd，不带换行，不执行命令，以构造奇数 IN、偶数短 OUT。第一 owner 完全排空
并手动关闭；第二普通重开，Ctrl-U 清掉未完成文本，再冻结/导出 journal。

helper `18c0f157...` 的语法/七个模拟失败路径/Stop 三种有界重试检查通过。首次复用
测试脚本时，仅测试中的授权 guard 文本未同步，模拟在写配置前退出；修正后通过。
桌面 UAC 等待期间拟取消启动，但保护检查发现启动刚完成并退出；没有执行取消操作。
两项配置、两次目标叶重载、ETW/串口 finally 仍在原授权范围内。

## 59.3 干预重现了真实首帧缺口

第一 owner 的新状态 54 帧，手动一次 LEN4 `61 62 63 64` 得到 21 帧回执/tty echo，
共 **75 帧、448 wire 字节**。只有两条非空短 OUT（3/6 wire 字节），无 ZLP；都受理，
无重试。GET_STATS 排空，39.798 秒手动 Ctrl-]，finally close/dispose/detach。

第二 owner 首 Ctrl-U 3007ms 发送、3058ms 收到新回执；输出从 `26.214153]` 开始。
首状态及清行输出在 raw / ReceivedCount / 驱动正文里均为 **330 wire 字节**，CPU
软件发送快照应为 **336**。不是“首同步没进 RX，所以没有输出”。

CRC `c4ac3649`、seq12165..12676：

- 前 RX58 owner 167 帧、第一 owner 75 帧、第二 owner 269 帧，合计 511 条直接匹配。
- 唯一缺 seq12407，source=console，wire `90 04 5b 31 30 30`，payload=`[100`。
- CPU 完整行是 `[10026.214153] eud: tty byte=15 ...`；不靠猜测时间戳补齐。

第二 owner 两个只读命令的 9 个数据帧都只发一次并有回执；dd 明确读出 3120 字节。
70.718 秒手动关闭，1415 个 IN 帧、8446 wire 字节，输入队列/缓冲/错误/保留查询均零。

同步 ETW：1535 对 dispatch/completion 全配对，丢事件/缓冲均零；1490 个成功 IN
完成共 8894 字节，其长度顺序与两份驱动日志逐一相等。12 个失败 IN 全是两次关闭
时的零长度取消。故此样本没有证据支持“驱动因失败正长度完成而拒绝那个首帧”。
缺帧已经在成功 USB 完成及原始 logger 正文之前；EUD/物理传输/主机控制器仍需区分。

每次 Open 的 EP81/02 CLEAR_FEATURE ENDPOINT_HALT 都在 ETW 看到成功控制完成。
另有 7 组完整 16 字节 OUT 后的零长度请求出现 transaction error、cancel、成功，
与实际非空数据请求分开记录；不能把数据帧数当作包含 ZLP 的物理 OUT 奇偶数。
这些出现在后续 journal 命令，**第一 owner 的两条短 OUT 不涉及它们**。

## 59.4 文档更正与新搜索资料

更正 RX58 §58.3 的一句：**0x1e 重置主机数据翻转；0x30 才保留它。** 本机微软 SDK
usb.h 的枚举值/别名及 [Microsoft URB 文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
一致。RX56 的 selector=2→0x1e 映射正确。设备收到 CLEAR_FEATURE 后实际是否同步
未直接测到；奇偶干预支持失配候选。旧 reference/rx58/focused-research.json 保留为
历史来源，在本轮 focused-research.json 明确标为被更正，避免悄悄改旧证据/校验值。

新检索读到 Qualcomm 作者的 [2026-09-29 v9 EUD 系列](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/)
及近期测试回复：主要是 UTMI/PHY/端口/role 支持；[第 7 个补丁](https://patchew.org/linux/20260929213513.2401005-1-elson.serrao@oss.qualcomm.com/20260929213513.2401005-8-elson.serrao@oss.qualcomm.com/)
修虚拟 detach 的 role。它们涉及 hub/control 路由，不能直接套到本机 tty COM。
没有新熔丝证据、SWD/JTAG/TRACE 可用性证明或现成 COM 首包补丁；未联系外部人员。

## 59.5 当前状态与下一项

两轮 helper 均 restored，ETW stopped，无 failure/restore_failure；第二 helper 实际
168.238 秒退出。独立复查：9500/9501/9505 三节点 OK，无 owner，Shared/not Attached，
两项临时配置不存在，ETW 查询无活动会话。驱动 `ad2ace07...`、候选 `50f951a4...`、
安装终端 `9c7a16f1...` 未变。完整 ETL/所有设备 XML 留本地，不入 Git。

下一项是 **相同短 OUT、相似时间界限下的偶数 IN 反向干预**，不是继续随机 echo：
若完整首帧恢复，再依据实装 reset 路径评估保持数据翻转/启动同步的可逆修复。
直接 PID/ACK 仍需合适观测手段；不通过刷熔丝、换驱动或反复 PHY reset 寻找答案。
只推 fork/master，整体目标保持 active。
