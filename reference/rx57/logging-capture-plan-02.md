# RX57：一次 COM14 驱动原始日志抓取方案（首轮在打开串口前退出；第二轮待授权）

2026-10-10。用途：在真实 TX 缺帧时增加 Windows 串口受理缓冲之前的字节观察。
这是一项诊断准备，不是修复，也不是继续重复普通 echo。当前手机仍用 RX53 镜像，
TOP_CFG=0x11、整帧 RX、console、F1、原安装终端与 RX48 回退全部保留。

## 依据与改动范围

实装 qcusbser.sys 2.1.3.5 的系统文件与审查文件 SHA256 相同：
ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151。
匹配 PDB、异常表函数边界和机器码共同确定配置及原始日志调用。
单读、多读 worker 都在后续串口受理之前记录 USB 成功读出的字节。
历史 RX46 ETW 有最多 6 个同时未完成的 IN 请求，因此不能只审查单读 worker。

只对 COM14 的这个设备实例操作：
`USB\VID_05C6&PID_9505\8&5580DC5&0&5`。
它当前对应的软件键是
`HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e978-e325-11ce-bfc1-08002be10318}\0008`。
两个配置值当前均不存在；如基线改变，脚本拒绝继续。

| 临时新增的值 | 类型 | 内容 |
|---|---|---|
| QCDriverConfig | REG_DWORD | 0x80000000，只置日志位，其余配置保留驱动默认值 |
| QCDriverLoggingDirectory | REG_SZ | `\??\E:\edk2-samurai-out\rx57\driver-logs-02` |

这些配置在设备创建时读取。预计只对上述 COM14 叶节点做两次 disable/enable：
启用日志一次，恢复原配置一次。每次 disable 的 finally 都尝试 enable 同一实例。
这需要新的管理员 UAC 授权；之前那次 ETW 授权没有包含注册表写入和端口重载。
不操作 9500/9501，不安装或替换驱动，不刷机，不重启手机，不 attach USBIP，不启动 ETW。

## 已准备的文件及执行顺序

`driver-log-admin-02.ps1 -Mode Plan` 只读核实设备、驱动、端口所有者和原配置。
`prepared-hashes-02.json` 固定整个方案、帮助脚本和未改动 RX55 诊断依赖的 SHA256。
`launch-approved-logger-02.ps1` 仅在得到新授权后使用，核对依赖并启动一次隐藏的管理员
Windows PowerShell 5.1；管理员脚本不拥有 COM 口。

管理员脚本先写 `control-02/backup.json`，再添加两值、重载端口，写 ready 状态。
正常用户的 `capture-windows-02.ps1` 必须在 ready 后 60 秒内开始，使用一个 COM14 owner，
最多运行 180 秒。启动 Ctrl-U 最多两次；得到新回执后，手动小步进行：

1. Ctrl-P 保存当前接收计数、队列和错误信息。
2. 一次发送 `dd if=/sys/bus/platform/devices/88e0000.serial/tx_journal of=/tmp/R57J`。
3. 确认对应新回执与命令结束，再一次发送 `base64 /tmp/R57J`，保存不可变 TX 快照。
4. Ctrl-P 记录排空后的计数；Ctrl-] 退出。数据帧不自动重试；缺回执时停止后续命令。

诊断脚本自己的 finally 关闭/Dispose 串口并处理未完成查询；包装脚本 finally 请求恢复。
管理员帮助脚本在请求后或总计 300 秒期限后恢复，只删除本次写入且仍等于预期的值，
保留外部冲突并报告 restore-failed，关闭注册表对象，重载同一端口并核实状态。
恢复后再检查两个值均不存在、三节点 OK、无 owner、Shared/not Attached。
保留驱动原日志和主机 .raw 的原字节与哈希。脚本硬终止不能保证 finally；必须检查恢复结果。

## 判据与限制

驱动 Rx 日志按时间 8 字节、类型 1 字节、长度 4 字节及正文解析。类型 0/5 是读数据，
错误/其他类型单列；不完整记录明确标出。解析器只做过合成样本测试，真实日志尚未生成。
日志函数的文件写入并非无损硬件分析仪，不能把“文件解析完整”直接等同于物理 USB ACK。

在真实缺帧附近对照软件 TX 快照、驱动 Rx 原始日志、GET_STATS ReceivedCount 与应用 raw：
日志含帧、计数/raw 缺帧时，指向驱动后续路径；日志和 raw 都缺帧时，继续核对早期
USB/EUD 路径及日志写入完整性。普通通过或日志改变时序后故障消失，都不能宣布修复。
本次不再次验证已通过的 F1/普通 echo，也不猜 reset、padding、熔丝或新寄存器值。

已完成的模拟验证覆盖恢复成功、第二项写失败、首次重载失败、外部配置冲突，以及
disable/enable 失败时的 finally；它们没有调用真实注册表写入、PnP 或串口。

首轮一次 UAC 已用：两项配置写入后，脚本误把本机 PnpDevice -PassThru 返回的设备对象当错误码，进入 finally 并退出；没有打开串口或发送测试帧。原 status.json 的 restore-failed 留存，独立只读复核证明两值均已不存在、三个节点 OK、管理员进程退出。第二轮删除 PassThru 数值判断，依靠 ErrorAction Stop、明确禁用状态 CM_PROB_DISABLED=22 和启用后的完整身份检查。模拟 cmdlet 已改为返回设备对象，补测同类错误。第二轮仍需另一次 UAC，不能沿用第一次的次数授权。
