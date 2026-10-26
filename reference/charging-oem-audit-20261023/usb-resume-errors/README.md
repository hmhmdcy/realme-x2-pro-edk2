# r5 USB：PM返回值不能证明物理恢复

纯离线小审计，原始源为现有source354，复用storage.mounted_build()只读定向小文件；hash见source-manifest.json。未操作设备、SDK、共享树、候选主线或Image。候选patch只在本目录，尚未整内核编译或部署。

## 已核实的三层边界

| 层 | 实际源码 | 函数语义 |
| --- | --- | --- |
| Qualcomm legacy glue | dwc3-qcom-legacy.c426–459 | 没有PWR_EVNT_LPM_IN_L2事件位时437行只dev_err；随后关clock、尝试关interconnect、is_suspended=true，459仍return0。不是已通过L2验证。 |
| DWC core resume | core.c2620–2691 | DEVICE的2633、系统OTG/DEVICE的2676忽略dwc3_gadget_resume的int；核心初始化成功后最终return0，即使gadget resume失败。OTG runtime路径本来不做此操作。 |
| Gadget soft-connect | gadget.c2801–2818 | soft_reset错误被返回；但2816的__dwc3_gadget_start错误被忽略，之后只返回run_stop结果。端点config/EP0 OUT/IN启用可在3001–3020返回错误。原start本身已有dev_err，因此这是**错误返回被丢弃**，并非所有情况下完全无日志。 |

另外glue的interconnect disable/enable错误仅dev_warn，suspend/resume仍0（443–445、482–495）；resume的clock enable失败则会回滚先前启用clock并返回错误（473–479）。不能把所有非0硬件步骤都说成同一种错误，也不应盲目把所有best-effort改为fatal。

`PWR_EVNT_LPM_IN_L2_MASK` 是当前代码读取的事件状态位，不是本审计已认证的实时PHY状态API。resume还会清L2 in/out事件（486–490）。缺位为何发生，需要实际状态/时序；本候选不把这条原有告警直接改成abort、不猜增延时或PHY quirk。

## soft-disconnect/connect的真实失败点

- `dwc3_core_soft_reset`（core.c322–373）：非HOST置CSFTRST、清RUN_STOP，轮询位清；超时返回-ETIMEDOUT。分版本1000次udelay(1)或10次msleep(20)，不把fake计数认作本机实耗。
- `dwc3_event_buffers_setup`虽签名为int，本版558–579所有路径都返回0；没有把stub注入的虚构非0当成实际可达故障。
- `__dwc3_gadget_start`（gadget.c2946–3040）：start_config或EP0 OUT/IN enable失败返回底层errno；IN enable失败会关已启用的OUT。此层错误目前被soft_connect忽略。
- `dwc3_gadget_run_stop`（2647–2721）：runtime-suspended时直接0；否则**先在2695/2699把pullups_connected置true/false**，再写RUN_STOP、轮询DSTS.DEVCTRLHLT最多2000次，超时-ETIMEDOUT。故pullups_connected即使为true，也可以是失败后的软件记录，不能认证物理连接。该函数不是500ms轮询：500ms是下述EP0等待常量。
- `soft_disconnect`（2727–2799）：无pullup则直接0；有pullup先connected=false，停止active transfers。EP0不在setup时最多等DWC3_PULL_UP_TIMEOUT=500ms；超时只告警/强制reset EP0后继续。随后run_stop(false)错误被返回，但gadget stop、UDC NOTATTACHED仍会更新，因此软件NOTATTACHED也不证明硬件halt成功。
- `dwc3_gadget_suspend`（4993–5011）：soft-disconnect失败且softconnect=true时尝试重连，忽略该重连结果并回-EAGAIN；若softconnect=false，原stop错误不会使它返回失败。这也是有限条件下PM0的来源，不在本次最小resume候选中改动。
- `dwc3_gadget_resume`（5013–5019）：无gadget_driver或softconnect=false时0；否则返回soft_connect错误。0还可能意味着这次没有发起重连。

## 精确函数抽取与fake结果

`build-reference.py`按实际源抽取10个完整函数，保存reference-functions.inc与function-manifest.json，周边仅fake MMIO/PM/端点命令/时间等待，不模拟真实USB、DMA、中断、PHY或主机。

原版、diagnostic、propagate三个变体分别通过42项断言，ASan/UBSan、-Wall -Wextra -Werror；总126项。明确覆盖：

- L2位缺失仍关clock/返回0，interconnect错误告警仍0，clock enable错误实际传播。
- soft-reset和RUN_STOP真实函数的fake位超时；RUN_STOP失败仍可pullups=true；停止失败仍可NOTATTACHED。
- EP0 setup等待超时后可返回0；gadget_driver缺失/softconnect=false不发起重连。
- DEVICE与系统OTG/DEVICE吞掉gadget resume错误；OTG runtime不重连；core-init错误原来就传播。
- 实际__gadget_start的三个命令失败原样返回errno，但soft_connect及原core最终可0；propagate候选可把这些errno传到core调用者。

这证明的是**软件控制流和返回值边界**。没有证明r5发生了哪一个错误或候选能恢复实机USB。r5 dmesg-after目前仅匹配到12083.320060的HS-PHY not in L2；未找到soft reset failed、failed to config endpoints、failed to enable ep0、wait for SETUP phase timed out或interconnect失败字符串。日志保存/覆盖和缺少RUN_STOP失败日志限制该负证据，不能从未找到推导链路正常。

## 两个互斥候选

两份patch都以此目录缓存原源为基准，**选择其一，不叠加**。私有副本patch --dry-run通过，见patch-check-result.json；没有写共享源。

- `diagnostic-only.patch`：优先的低行为改动取证候选。L2告警增加已读取的原始status和wakeup，无新MMIO；core两个gadget resume调用检查并dev_err，soft_connect给端点start错误增加明确阶段日志。所有原有返回值、是否继续run_stop、PM流程保持。它可说明“回调0内部有失败”，但本身不会修复数据恢复。
- `propagate-errors.patch`：独立的错误传播候选。soft_connect遇端点start错误停止继续RUN_STOP并返回；core捕获gadget返回值，仍执行原系统SUSPHY恢复，再返回错误。保留L2告警为advisory。这个变体改变失败路径，不能凭fixture直接部署认证。实际core.c2818–2825的系统PM上层在错误时会标runtime-suspended；其资源/状态恢复和下次行为仍需单独评审与受控验证，不能宣称是完整错误回滚实现。

未改USB descriptor、电流预算、角色、时钟/PHY时序或EUD，不包含bind/unbind、reset、cycle-port、参数写入或新Image。

## 下一次只读取证的最小分层

| 侧/字段 | 能说明什么 | 不能说明什么 |
| --- | --- | --- |
| 手机 `/sys/class/udc/<实际UDC>/state`、function、current_speed；现有gadget configfs UDC绑定值/MaxPower | UDC软件state、绑定驱动、记录速度、描述符申报 | state_show只返回gadget->state（UDC core.c1839–1847），并非询问主机端口。configured可能陈旧，不能认作电缆/主机/NCM恢复。MaxPower不是已接受预算。 |
| DWC内部softconnect | 软件曾请求connect；pullup函数2827先写此标志 | 不是主机可见连接。UDC的soft_connect是**只写属性**（1803–1837），不应cat它或为了“查询”写connect。 |
| DWC内部pullups_connected | RUN_STOP软件记录（超时前就设置） | 不保证硬件运行或收到USB reset。 |
| DWC内部connected | 本版gadget.c4243在USB reset处理中置true，4157/4194等处清false | 不保证NCM配置或实时物理存活。三个内部bit并无此缓存源码中的被动RO sysfs导出；未来只能用已有合适日志/已存在观测点或新获批诊断，**不假装现有state能直接读到它们**。 |
| 手机DWC/parent `power/runtime_status`、power/control、wakeup；原始dmesg中的USB reset/disconnect/conndone/error时间 | PM软件状态和事件先后 | runtime-active不等于物理连接；不触发resume去“读状态”。 |
| 手机usb网卡operstate/carrier、统计与实际接口绑定；合法native USB预算回调记录 | gadget网络接口及USB配置事件的软件证据 | 单独有usb0或预算数值不证明电脑枚举、传输已恢复。 |
| Windows真实0525 NCM实例与其Parent/LocationPaths/ContainerId；EUD9500及9501；已知NCM父hub端口的GET_CONNECTION_INFORMATION_EX | 枚举是否存在、NCM接在哪个真实父端口、ConnectionStatus/ConfigurationValue/Speed/VID:PID | EUD control仍在不表示NCM数据端口在；不能只查EUD的port1就认定NCM父端口或电缆故障。 |
| Windows NCM网络适配器的PnP状态、接口状态、IP/路由、收发统计；同窗口严格key的SSH或已有合法数据传输 | 主机驱动与数据通道相继恢复的证据 | 静态IP/旧路由或逻辑Configured本身不够。 |

主机可复用现有query-usb-hub.ps1中仅GET_NODE_INFORMATION/GET_CONNECTION_INFORMATION_EX的查询实现，**使用新独立输出目录**，不覆盖旧raw、也不运行reset/cycle-port/restart或改供电预算。实际NCM父端口须在当前健康枚举时先按PnP拓扑建立映射，故障时保留同一端口/同一时间基的结果；VID/PID仅作筛选，完整实例路径留私有原件。

注意debugfs“只读文件”也未必无副作用：本版 `debugfs.c566–599` 的link_state读取575行主动 `pm_runtime_resume_and_get`，最后put_sync；读取会影响PM，不纳入被动基线。regdump是live MMIO且regset关联dev（1012–1019），同样不默认为无副作用取证。当前不读这些项、不进行直接寄存器访问。

根会话最新独占只读console采样已确认runtime只有nop tracer、所需lock/sched/irq/rtc/power事件及stacktrace trigger存在；未arm trace、未PM。这只能支持未来事件取证可行性，不能补出DWC内部bit或把r5失败路径反推为某一个已发生的errno。实际console参数证据已补入上级pm-preparation-gap/trace-plan/README.md。

下一窗口的目标是同步区分：电源源状态、手机controller/UDC软件状态、真实主机父端口、NCM驱动和数据传输。任一单项的logical configured或PM err=0都不能代替完整物理恢复证据。
