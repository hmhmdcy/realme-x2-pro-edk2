# 58. 三次缺帧的重开共性与驱动失败读分支

2026-10-10。证据与离线复核见 [reference/rx58](../reference/rx58/README.md)。

**问题仍未解决，但范围进一步缩小。** RX57 第二次获准抓取已完成且恢复；本轮只读
旧证据、实装驱动和在线资料，没有再开串口、UAC、改注册表/PnP、attach、刷机或
重启手机。TOP_CFG=0x11/整帧 RX、RX53 console RX、F1、现有两种终端及回退保留。

## 58.1 把旧样本对在同一个位置

独立脚本先验证旧 SHA256SUMS、快照 CRC、严格 wire framing，再用唯一连续 20 帧
锚点确定位置；随后逐帧核对两侧，不做插值/编辑距离或补造缺字节。

| 样本 | 缺失 seq / wire | 缺失位置 | 其余直接匹配 | 启动同步 |
|---|---|---|---|---|
| RX51 | 11733 / `90 04 5b 20 35 38` | `[ 5863.839589]` 的首四字节 | 336 前 owner + 175 当前 = 511 | 第一次无回执，第二次受理 |
| RX53 | 7287 / `90 04 5b 20 20 20` | `[   95.409512]` 的首四字节 | 151 前 owner + 87 当前 + 273 恢复 = 511 | 第一次受理 |
| RX55 | 7376 / `90 04 5b 20 31 36` | `[ 1688.479011]` 的首四字节 | 27 前 owner + 484 当前 = 511 | 第一次无回执，第二次受理 |

三个都是 **重开 Windows owner 后首条 Ctrl-U 状态输出的第一个 console 帧**。
RX55 首段 raw 与 ReceivedCount 都为 309，软件已发应为 315，少六个 wire 字节。
RX53 首次同步已成功，反驳“TX 缺帧必须伴随启动 RX 丢失”；不能强行合并两种故障。
RX57 的首前缀完整、512 帧匹配，仍只是 passing 对照；开日志可能改变时序。

这是三个样本的共性，不是故障率或 reset/数据翻转根因证明。CPU journal 不测物理 ACK。

## 58.2 精确驱动里，日志也有盲区

系统服务文件与审查文件 SHA256 同为 `ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151`，
匹配 PDB GUID `66581f50-52c9-4a32-9ac6-fe0c57b94a80`、age=1。只读反汇编重核函数边界、
全函数代码哈希及六段 150 条指令；没有加载或修改驱动。

1. L2 `ef6c/ef75` 检查 USB IRP 状态；只有零状态在 `ef9e` 记录正文。
   非零路径 `efff` 只记录 type 3、四个状态字节，**没有实际长度或失败正文**。
2. L2 `f0d2/f0e2` 仍把状态/URB 长度放入 ring；不是在 L2 一律清掉失败正文。
3. L1 正常完成分支 `d696..d6f2` 把状态/长度/缓冲复制到 IOB，并调用 `IOB+0x60`；
   还存在 cancellation/state gating。StartTheReadGoing `28467/2846e` 明确绑定
   这个间接回调到 ReadIrpCompletion `25408`，补上旧直接调用搜索未覆盖的关系。
4. ReadIrpCompletion `25442/25445` 仅在状态零且长度正时进入 padding/vPut；
   非零状态跳过正文入串口缓冲。故障时若存在有效部分数据的失败完成，可能在此被拒绝。

**尚未测到真实缺口对应的失败完成。** 失败时长度正也可能不是有效返回正文，须结合
API/status/实际传输证据。因此“原始日志也缺”仍不能单独判定 EUD/物理 USB 已丢。
RX57 的关闭期六条取消记录不能冒充 RX51/53/55 故障期原因。

## 58.3 重新提取后查到的资料

[Microsoft URB bulk 结构](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_bulk_or_interrupt_transfer)
帮助解释返回长度与短包；不保证所有失败正长度都有效。
[Microsoft usbsamp](https://raw.githubusercontent.com/microsoft/Windows-driver-samples/main/usb/usbsamp/sys/bulkrwr.c)
有按完成状态分支的实例，但它是不同框架/驱动，不能当本机补丁。
[libusb 上游](https://github.com/libusb/libusb/blob/master/libusb/io.c) 的部分取消概念已在 RX49 用过，
新的部分是本机日志/接收分支的精确边界。
[URB reset 文档](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/usb/ns-usb-_urb_header)
沿用 RX47/56：实际 selector 映射 0x1e，不能假设它重置 host DATA0/1。没有新 reset 实验。

定向词与来源限制在 focused-research.json。未找到现成 EUD COM 修复；没联系他人。
没有新增熔丝证据；COM 已工作不能证明 SWD/JTAG 可用，其他外设也未提供当前问题的修复。

**2026-10-10 RX59 更正：** 上一句关于 0x1e 的措辞错误。SDK 与微软文档定义
0x1e 为 CLEAR_FEATURE + 重置主机数据翻转；0x30 才保留主机翻转。设备实际是否同步
仍须测量，不能把文档当物理 PID 证据。旧 focused-research.json 保留历史并明确被
[session 59](59-joint-capture-and-forced-odd-reopen-gap.md) 更正；准备的联合方案已于
后续持续授权下执行，实际结果在 session 59，以下仍保留本节发布时的状态。

## 58.4 下一项已准备，尚未运行

[measurement-plan.md](../reference/rx58/measurement-plan.md)：一次独立新 UAC，仍只临时
改 COM14 两项日志、启用/恢复各重载叶节点一次；同步 USB ETW，最多三次手动依次
重开的首状态，总抓取不超过 180 秒，最后 owner 导出一个冻结快照。每个串口 finally
关闭，帮助进程 finally 停跟踪和恢复。不刷机/手机重启/换驱动/额外 reset。

语法、七种模拟失败路径及实际 Stop 函数有界重试通过；只读 Plan 核对当前身份/配置。
模拟未测实机调度。方案已打开并请求新的单次授权，**不能复用 RX57 两次已用 UAC**。
当前证据发布时没有执行；获批后的运行必须另保存实际结果，不能把准备当抓取完成。

只读状态：三节点 OK，无已知 owner，Shared/not Attached，两项配置不存在，未产生新
control/log/ETL。内核源码 `39e464f8...`、Image `33efc6bc...`、候选 `50f951a4...`、
安装终端 `9c7a16f1...` 均未改。继续只推 fork/master。
