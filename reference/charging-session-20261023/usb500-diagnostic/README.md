# USB500 因果采集候选：只读 Windows 单 Hub 监视

本代理只执行离线代码、结构解析测试和缓存审查，没有运行硬件查询或 trial，没有连接手机，没有改 main、r6 updater、相机 SDK、Windows SDK、驱动、供电规则或 USB 配置。根会话另行执行了一次独立100mA只读基线，见下述实物返回修正；500试验尚未执行。实际执行仍需根会话取得相机/蓝牙明确交接并审核新设备事务。

## 已实现

- `UsbHubReadOnly.cs`：复用 main `query-usb-hub.ps1` 的 SDK 10.0.26100.0 pack1 布局，只允许 `GET_NODE_INFORMATION=0x220408` 与 `GET_NODE_CONNECTION_INFORMATION_EX=0x220448`。句柄 desired access 为0；没有 reset/cycle/写/安装/设备重启 IOCTL。
- `watch-one-hub.ps1`：仅选择唯一的 `05c6:9500` EUD hub，固定其 interface/句柄；默认100秒、200ms一轮，记录其全部1–15个端口。不遍历其它 hub，不自动切换到重新发现的路径。每个 GET 有100ms默认超时；只取消该读请求。取消未完成时中止该读进程，保留 native buffer 至进程退出，不发后续查询。
- `start-bounded-watch.ps1`：PowerShell7 主机 watchdog，隐藏启动唯一的只读 reader，最迟在监视时长+20秒结束自己的 reader 进程树，涵盖初始 PnP 查询/编译卡住。它不操作 USB/PnP 设备。输出 `WorkerExited`；被 watchdog 截断的采集不可视为完整。
- `test-parser.ps1`：实际编译同一 C#，只执行 byte-array decoder/allowlist，解析 PowerShell AST；完全不构造 HubSession、不调用 PnP、CreateFile 或 DeviceIoControl。revision2 共62个离线案例通过（保留原54项，增加实际缓存/严格例外边界），见 `test-result.json`。Windows SDK 三份头仅只读核对，与 main 已验证收据的 SHA 全部相同。原54版源码和收据保存在 `revision-1/`。

根会话第一次独立100mA基线证实 overlapped GET 路径可用，26轮182个GET成功返回；空端口2–6的130个解析失败阻止了ready，因此没有500试验。实际响应都是**恰好35字节全零**，包括ReturnedIndex=0。这是本机EUD的经验返回，不能按SDK默认语义臆造为有功率拒绝。revision2只允许这一精确模式作为absent，公开保留 `ExpectedPort`、`ReturnedIndex` 和 `EmpiricalZeroAbsent=true`；任意非零字节、非35长度或其它错索引继续拒绝，特别不能将index0+status5归到目标端口。所有原始bytes继续保留。缓存重解26轮中NCM实际端口7稳定26轮、control端口1稳定26轮；详见 `cached-baseline-redecode.json`。原基线失败收据/原件保持，没有把缓存重审冒称新的实机通过。根会话需用新目录再做独立100基线，确认修正版ready/完整采集后才能考虑500。

## 数据与目标端口

`metadata-private.json` 保留固定 hub interface、Node 原始bytes、总线供电属性、采集参数和两个源码 SHA；`ports-private.jsonl` 每轮记录所有端口。每个端口都有 UTC、GET 起止 monotonic 毫秒、原始响应 Base64，及解析后的 `Status`（即 SDK `ConnectionStatus`）、完整状态名、VID/PID、configuration、speed、IsHub、address、pipe count。每轮另存起止时间及是否完整；不能把依次读取的多个端口当同时快照。

布局关键点：node76字节，type=5、port count=6、bus-powered=75；connection固定头35字节，VID=12、PID=14、configuration=22、speed=23、IsHub=24、address=25、pipe count=27、**ConnectionStatus=31**。不是默认对齐的32。PipeList每项11字节，长度/索引/BOOLEAN/溢出都检查。失败状态下描述符可能全0，仍保存该状态，不把 VID/PID 缺失改写成断开或丢弃功率证据。

默认先收集5秒基线，至少3轮连续完整成功读取且唯一的 `0525:a4a1`、configuration1、非hub、已连接、最小合法 device descriptor，才把实际端口号固定并写 `ready.json`。不能沿用历史端口1（它是EUD control `05c6:9501`），也不能硬猜NCM端口。无NCM、多个候选、其它端口读失败或目标不稳定时不写ready、非零退出，禁止启动试验。试验中即使目标 VID/PID 清零仍跟踪固定端口；若相同 NCM 出现在另一端口，报告 `TargetSeenOnDifferentPort`，由根会话审查拓扑变化。

| Status | 名称/结论范围 |
| --- | --- |
| 0 | NoDeviceConnected；没有供电拒绝因果信息 |
| 1 | DeviceConnected；还需配置、身份和设备 native callback 证据 |
| 2 | DeviceFailedEnumeration；不能据此称供电不足 |
| 3 | DeviceGeneralFailure；不能据此称供电不足 |
| 4 | DeviceCausedOvercurrent；与功率预算不足不同 |
| 5 | DeviceNotEnoughPower；Windows USB 栈明确返回功率预算拒绝 |
| 6–8 | 带宽/层级/legacy hub限制，逐一保留 |
| 9–10 | 正在枚举/reset 暂态；采集器未发 reset |
| 其它 | 数字原样保留为Unknown，不猜含义 |

`CM_PROB_FAILED_START` 不用于判定功率原因。固定NCM端口在500描述符阶段出现status5、100恢复阶段又正常配置，是比现有证据更直接的主机功率拒绝证据；仍不能据此断言电脑物理供电能力不足、线损、EUD电路或某一供电规则是最终原因。只有2/3、缺席或未捕获5时，结论应为枚举/一般失败或原因未明；200ms采样仍可能漏过短暂状态，未观察到5不能排除它。

## 下一次实验步骤（尚未执行）

1. 根会话确认 r6 更新成功且 worker 已退出，实际 manifest 为 `944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d`，三模块 loaded-note/新 service 完整；取得相机和蓝牙独占交接。确认同boot/guard/原SSH密钥，当前 SDP100、两个物理输入100mA、CC250mA/CV原上限、fresh保护、无 latch/fault/timeout。任何等待或保护故障不进入试验。
2. 先在100配置做一次**独立、只读**基线采集，确认新 native GET 路径可用、唯一NCM端口识别正确、时长与进程退出有收据。此步不改变手机。失败则只取回日志，不能尝试500。
3. 审核新的设备事务候选及故障测试后，准备全新 local/remote 事务目录、唯一 request/PID。不能重放 `usb-reenumerate`、`usb-power500`、r4或旧 launch。r6版本与本次 worker/helper SHA 固定；共享充电 service 锁、独占窗口和先前未知 worker 退出检查都需明确。
4. 启动新的主机监视进程。例如根会话可在隐藏/后台 worker 中调用以下**主机采集命令**，并 fetch 同一 PID/新目录；不要在本轮直接执行：

   ```powershell
   pwsh -NoProfile -NonInteractive -File "E:/RealmeX2Pro edk2/reference/charging-session-20261023/usb500-diagnostic/start-bounded-watch.ps1" -OutputDirectory "E:/edk2-samurai-out/charging-management-20261023/usb500-causal-r6-host-NEW_ID" -DurationSeconds 100 -IntervalMs 200
   ```

5. 等到实际 `ready.json` 为Armed且检查主机worker仍活着、剩余时间足以覆盖约60秒设备阶段及回100后的观察，才启动那个已审核的新设备 worker。根launcher记录主机UTC发起/返回区间和nonce；设备worker记录 realtime/BOOTTIME/monotonic锚点，以及 `unbind/MaxPower500/bind/configured/restore100` 每阶段前后时间并立即flush。记录原主机/设备时钟偏移区间，不能假装两台机器monotonic可直接相减。
6. 只做一次临时500申报，绝不写 power_supply 预算或 Windows 供电规则。500被接受必须由 DWC3正常SET_CONFIGURATION带来合法native500，且设备UDC configured、fresh完整健康 managed或精确Full保持、两输入寄存器均500mA并连续约12秒；MaxPower=500和Windows configuration=1本身不等于许可。
7. 本次是诊断：建议即使500成功也在同一新worker的 finally 恢复100并重新绑定、恢复NCM。失败亦自动走同一100恢复；若恢复自身失败，要独立报告主错/恢复错和实际UDC/MaxPower/native状态，不能宣称已回100。原两份启动脚本保持100不动，不形成持久迁移。
8. 主机继续覆盖100恢复后至少约15秒；确认固定端口正常配置、设备native/双路物理输入回100、fresh managed/Full、同boot、taint0、无新增fault、相机/四服务/CC/CV保持，并确认两个worker已退出。SSH掉线只 fetch 原worker，不能再触发500或主机restart/reset。只有所有恢复证据齐全才交回窗口。
9. 将主机原始端口状态与设备各阶段时序合并，再按上表给结论。不能仅凭最终端口状态或当前CM错误倒推过去原因。

## 旧 worker 只读审查：可复用和必须变更

审查对象 SHA 在 `test-result.json` 的 `AuditedMainFiles`；没有改这些文件。

| 现有代码 | 下一候选应如何处理 |
| --- | --- |
| `usb-reenumerate.py` 的 `configure(500/100)`、独立worker、60秒有界观察和失败回100 | 可复用其只改临时gadget descriptor、正常回调授权、不写预算的方向；新事务必须增加逐阶段时间/flush及**总是回100**的诊断终态 |
| `run-usb-reenumerate.py` 的旧 `remote=.../usb-reenumerate`、旧local `.open('x')`、旧helper拷贝 | 不能复用旧目录/请求；只参考唯一worker+fetch方式，按新nonce/PID创建新路径。未知dispatch必须fetch原PID，不能重复launch |
| config manifest 来自旧私有 `service/manifest.json`，旧结果为78332c70… | 改为已成功部署r6的**实际**944f2d91…及 fresh新service verify/loaded-note；不能仅把旧记录的manifest字符串换成新值冒称已验证 |
| old health、`good` 只允许 `desired_enable=1` | 新候选应使用已审r2 health `a41942f2…f4b4f` 的安全分类，允许证据完整的Full保持（desired CHG=0），继续拒绝热/TCA等待、来源未知、错误、旧latch/timeout；不能为通过mask flags |
| 启动预检只核对manifest/source，旧worker特判r4/usb-power500两个PID | 增fresh健康/旧fault/timeout前置、服务锁和本次独占窗口；明确检查所有相关唯一worker，旧路径无文件不是失败恢复，也不能据历史空闲推定窗口可用 |
| `except` 回100，成功500后保持500；finally仅在未绑定时补100 | 诊断候选总是尝试恢复100，明确记录每次configure完成状态，区分主/恢复错误；对500写失败、100写/绑定失败、网络命令异常、收尾异常做实际事务故障测试，才能执行 |
| UIEvents/UPower和net配置 helper | 可继续只读观察与恢复既有usb0地址，但子进程生命周期/超时要独立有界并保留错误；不添加PM、拔插等待、设备重启或Windows reset/cycle来掩盖失败 |

原worker曾在响应正常路径约63秒恢复100，能作为既有证据；不能保证未来进程被杀、sysfs写卡住或内核失联时一定恢复。随后根会话要求的新设备候选已离线实现在 `device-candidate/`，复用冻结r6/health，51项实际函数故障测试通过；完整新schema、时限和unknown隔离见其README。它尚未上传或运行，不附新launcher。主机实时ready和新设备候选都须根会话审核后再决定试验。

## 离线复测

```powershell
pwsh -NoProfile -NonInteractive -File "E:/RealmeX2Pro edk2/reference/charging-session-20261023/usb500-diagnostic/test-parser.ps1"
```

这条命令只解码合成结构/既有缓存并解析源码；本代理已执行。修正版 Native GET、watchdog和设备trial均未由本代理运行；根会话第一次100基线的真实失败及返回边界如上保留。
