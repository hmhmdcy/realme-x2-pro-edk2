# 57. 实装驱动原始日志：补齐 Windows 受理缓冲之前的观察点

2026-10-10。来源：sessions 41–56 的结论、精确匹配实装 qcusbser.sys/PDB、旧 RX46
目标 ETW，以及本轮一次有界 Windows 会话。证据和验证见 [reference/rx57](../reference/rx57/README.md)。

**新进展是观察方法已实际可用，尚未取得稳定性修复。** 本轮日志/计数/raw 全部一致，
旧启动缺回执及 TX 缺帧没有重现。保持 TOP_CFG=0x11、RX53 console 边界整帧 RX，
F1/console/兼容与原生终端、RX48 回退；未构建、刷机、重启手机或安装驱动。

## 57.1 哪些是修复，哪些只是定位

RX41 修复受理后 FIFO 重复首字节；RX53 修复长 console 输出期间的明确 RX 触发。
RX43 撤回原始文件里已有、显示却隐藏的旧缺输出样本。RX55 的新六字节缺口是实测
异常，9550 字节的新 passing 样本不能撤回它。完整结论表沿用 session 56 §56.1。

重复普通 echo、F1、reset、仅掩码、旧零等待或未重现故障的通过样本，不再算根因进展。
这轮增加实际的前缓冲观察，目的在真实缺口时区分 USB/EUD 与驱动后续接收，而不是
再次证明普通命令可执行。没有证据证明问题无解或是量产熔丝导致。

## 57.2 新资料如何对应现有证据

按已经缩小的边界搜索，而不是泛搜“RX 丢回执”。精确配置/函数名搜索未找到可直接
使用的公开配置指南；方法来自本机 **实际系统服务文件** 的精确机器码，不把旧驱动
源码当实装版本。系统文件与审查文件 SHA256 均为
`ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151`，
匹配 PDB GUID `66581f50-52c9-4a32-9ac6-fe0c57b94a80`、age=1。

| 新核对的来源 | 用途与限制 |
|---|---|
| [Microsoft IoOpenDeviceRegistryKey](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-ioopendeviceregistrykey) | 实装调用的 PLUGPLAY_REGKEY_DRIVER 打开设备实例软件键；据此找到 COM14 class 0008，不猜服务全局键 |
| [Microsoft REMOVE_DEVICE 生命周期](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/handling-an-irp-mn-remove-device-request) | 设备禁用会移除软件栈；结合 AddDevice 中读取配置，准备仅 COM14 的禁用/启用，并实际检查状态；不是手机重启 |
| [Microsoft Disable-PnpDevice](https://learn.microsoft.com/en-us/powershell/module/pnpdevice/disable-pnpdevice?view=windowsserver2025-ps) | 管理员要求与精确 InstanceId 范围；文档的 PassThru 描述未覆盖本机实际设备对象输出，首轮误判见下一节 |
| [Microsoft USB transfer sizes](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-bandwidth-allocation) | 短包可以完成较大的 IN 请求；旧请求 0x8000、实际完成 6 字节不是自动丢包证据，不再试 padding/ZLP |
| [QUIC COM issue 6](https://github.com/quic/eud/issues/6)、[当前 com_api.cpp](https://raw.githubusercontent.com/quic/eud/main/src/com_api.cpp) | RX56 找到、此次复核：问题仍开放，活动只有 stale bot；示例收发循环仍含 FIXME。没有现成 COM 稳定性补丁，也不是维护者声明本机硬件能力受限 |

实际检索词与结果边界在 `focused-research.json`。旧 reset/数据翻转/OpenOCD SWD 资料
沿用 RX56，不把它们包装成新的 COM 修复。本轮没有联系他人或发布 issue。

## 57.3 精确配置、双 worker 与一次启动脚本错误

`QCPNP_AddDevice` 在 RVA `14c85` 调用 VendorRegistryProcess；QCPTDO 创建路径在
`1b768` 调用 PostVendorRegistryProcess。两者都从 PDO 打开实例软件键。
QCDriverConfig 位 31 在 `192c5` 置全局 EnableLogging (`3a331`)，`1a847/1a84d`
复制到设备扩展 `11c2`。默认 UseReadArray/MultiWrites 为 1；本次只置日志位。
QCDriverLoggingDirectory 读成功设置 bLoggingOk，CreateLogs 采用 NT 完整目录路径。
单读 worker `24e22`、多读 L2 `ef9e` 都在后续串口受理之前调用原始日志；错误另记。
旧 RX46 ETW 按 IRP/URB 成对计算最多 **6 个并发 IN**，95 次请求均 0x8000，全部配对。
这是旧运行证据，不能直接代替当前 live worker 标志或物理 PID 测量。

先只读核实 9500/9501/9505 三节点 OK、无已知串口 owner、6-5 Shared/not Attached。
用户分别明确批准两次 UAC；每次范围都是 COM14 两项临时日志配置、启用/恢复各重载
一次、有界抓取并关闭恢复，不刷机/手机 reboot/安装驱动。两个方案、原脚本及哈希均留存。

第一次帮助进程 pid=162852：写两项后误把本机 PnpDevice -PassThru 返回的
Win32_PnPEntity 对象当作数值错误码，finally 后退出，未打开串口或发送测试帧。
原 status.json 的 `restore-failed` 保留；独立只读复核证明两值已不存在、三节点 OK、
帮助进程退出、零驱动日志。模拟返回数值的旧测试没覆盖真实返回对象，这是本轮
诊断脚本错误，不是新增 EUD 故障。

第二版删除 PassThru 数值判断，ErrorAction Stop 处理失败，确认禁用状态 error=22，
finally 启用相同实例，再等待完整身份恢复。补测 mock 返回设备对象及失败路径；
只读预演通过后，得到第二次单次 UAC 授权才执行，原方案与首轮证据没有改写。

## 57.4 实际抓取及字节对照

帮助进程 pid=179076 在 `2026-10-09T19:02:21Z` ready。只改 COM14 软件键
`HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008`：
QCDriverConfig=REG_DWORD `0x80000000`；QCDriverLoggingDirectory=REG_SZ
`\??\E:\edk2-samurai-out\rx57\driver-logs-02`。两值原来都不存在。

正常用户 Windows PowerShell 5.1 持有一个 COM14 owner，运行 136486 ms。
第一次启动 Ctrl-U 84 ms 后有新回执，不重试。15 个数据帧/175 payload 字节只发一次
全部有回执；连同同步，总主机 wire=208 字节。

手动一次 Ctrl-P、读取发送快照、再次 Ctrl-P、base64 快照、Ctrl-P、Ctrl-]。
第一次 dd 没指定块大小，512 字节读请求小于所需的 3120，驱动依原设计返回 EINVAL；
同 owner 下一条改 `bs=4096 count=1` 成功。原错误输出与命令全部保留。这是快照工具
参数遗漏，不是串口故障；不再沿用缺少块大小的旧准备命令。

| 观察点 | 实际结果 |
|---|---|
| 驱动原始 Rx 文件 | 30517 字节；1611 条完整记录，其中 1603 条 type 0 共 9550 字节；无 type 5 |
| 驱动成功读数据 → 应用 .raw | 逐字节一致；9550 字节、1603 帧、276 次应用读，0 stray/余字节 |
| 五次 GET_STATS 排空取样 | ReceivedCount 0→9550；分段 324、2502、6724、0 均等于 raw 增量；0 观察到的串口错误 |
| 驱动 Tx 文件 → 主机提交 | 442 字节完整文件，成功写正文串接与全部 208 提交字节完全一致；不冒充设备物理 ACK |
| 手机 CRC 发送快照 | seq9153..9664、512 帧；55 帧直接对应旧 RX55 raw 尾部，457 帧对应本 owner，不插值、不虚补 |
| 最终清理 | closed/Dispose、查询保留数 0；帮助进程 restore-request→restored，无失败；两值再次不存在，三节点 OK、无 owner、Shared/not Attached |

快照 SHA256 `fec672f24f4fd28cf8255e723af038883591f9eaf1570e0eb40629f8e32902f3`，
CRC `48752247`，见 `capture-summary.json` / `SHA256SUMS`。原始 Rx 文件 SHA256
`eb4d9af854517100ad91fbf395bd7b66aee25694e3d9418c36372a2f0395eb9a`。
Rx 文件尾部 type 10、六条 type 3 (`200100c0`)、type 9 是非成功读记录；解析时没有
当线缆 payload 拼入 raw。关闭期取消记录与成功数据分开，完整记录不等于物理无损保证。

## 57.5 保留状态与下一步

手机仍是 `logdump-rx53-console-rx.img` SHA256
`50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93`；
eud.c `39e464f8...`，Image `33efc6bc...`，安装终端 `9c7a16f1...` 均未变。
`state-after-attempt-01.json` 与 `final-state.json` 分别证明首轮独立恢复、末次健康状态。
本轮管理员配置已撤销；不能把当前再开端口当日志仍启用，也不能再次使用已用过的控制目录。

RX55 seq7376 `[ 16` 的六字节缺口和偶发启动缺回执仍开放。本轮没有触发它们，
只证明这套前缓冲字节观察可工作；文件写入/开启日志本身可能改变时序，不能宣称修复。
下一项必须在真实异常附近取得日志→受理计数→raw→发送快照的边界；先核对实际触发条件，
不原样循环此次 passing 流程。日志包含缺帧而受理/raw 缺，才支持驱动后段调查；日志也缺，
还须核对日志写入完整性与更早的 USB/EUD 路径。物理 USB ACK/DATA0/1 未测到。

只在新证据支持具体改动时构建；优先只刷 logdump，boot/logdump 限制不变。只推 fork/master。
