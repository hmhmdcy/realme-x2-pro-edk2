# EUD-off route supplier：最小源码方案，未实现

建议新增一个 **boot-off专用、默认关闭、同内核编译的 supplier**，并给已知 EUD生产者加显式跨owner入口。第一版永久封住本次启动的 EUD生产者，释放一次消费token也不重新启用EUD；不兼容运行期来回切换route。supplier自身不读关电CSR、不写CSR/AHB/SCM、不调用role或PHY。现有COM quiet API继续只用于真正已绑定COM的软件quiet，ENODEV不改成成功。当前没有实现、没有token或route grant，`owner_entry_gate()` 继续EOPNOTSUPP。

## 实际覆盖范围

| 当前固定源 | 地址或入口 | 对方案的约束 |
| --- | --- | --- |
| 原Image363及501继承的COM `eud.c` | `eud_probe` 请求并映射088e0000–088e1fff，随后写CSR+1014=1 | 完整0x2000资源申请包含CSR，但disabled DT不阻止以后overlay或重新建platform设备。hook必须在任何映射／硬件触碰前执行。 |
| 同一COM probe/remove | 对088ee010用`devm_ioremap`裸映射、读写AHB2PHY TOP_CFG；remove恢复旧值 | 这4字节不属于前述0x2000资源，普通region claim不能替它加锁。原COM没有`.pm`；未部署R2的PM gates不能当运行源已有能力。 |
| 原earlycon | `eud_setup`直接`early_ioremap(mapbase+1014)`并写1；FIFO由early console写 | 不经过platform probe和普通资源request；后期bus notifier／claim挡不住已经发生的早期写或仍存活的映射。 |
| full `qcom_eud.c` | resource0映射主窗；resource1只取物理地址，enable/disable经SCM写mode manager；IRQ线程可切USB role | 主窗claim能先阻断新probe，不能仅挡sysfs enable而留下已注册IRQ／role路径。当前无适用full-EUD DT绑定，仍不能把它当缺席许可。 |
| legacy DWC glue | qscratch0a6f8800–0a6f8bff；probe复位/时钟/子设备，vbus_override写QSCRATCH；PM开关时钟、interconnect | 它不是EUD CSR owner，不能代替supplier证明EUD-off。现代码没有回调route supplier。 |
| 现USB PHY DT资源 | HS1 088e2000–088e23ff；QMP1 088e8000–088eafff，QMP2 088eb000–088ebfff | 不能为了排斥EUD把088e整片占掉，破坏实际PHY。 |

当前配置还包含OF_DYNAMIC/OVERLAY和SERIAL_EUD_EARLYCON；因此disabled COM／无已绑定设备／读取API返回ENODEV只描述当前枚举状态。必须承认实际调用顺序：COM先申请主0x2000才触碰AHB，full-EUD也先申请主窗才可能注册IRQ或执行SCM；主窗claim能阻断这两个新probe，不能把其后的裸map／SCM夸成已证明的新probe绕过。它仍不覆盖earlycon、未登记region的旧映射或任意外部writer，resource树不是所有MMIO/SCM访问的强制器。因此claim可作防止已知新probe的辅助手段，不能单独代替受信初态和早期producer排除。本轮没有缓存到当前精确`drivers/base/dd.c`／`kernel/resource.c`，没有做bus-notifier veto证明，也不据notifier返回值设计任何安全门。

## firmware先生产什么，Linux再消费什么

现501的BDS源是固定 `cfae4eef…ffd21`。`SamuraiArmEudOffHandoff()` 在StartImage前只验证已知完整CSR值并注册BeforeEBS事件；真正清0／完整读回发生在 `SamuraiEudBeforeExitBootServices()`。它的本地静态结构和DEBUG RAM日志可作外部观察证据，**没有供Linux消费的结构化完成记录**。VOID回调失败不能阻止继续启动；DT布尔或命令行标志只表达请求，不等于硬件读回。

最小新增handoff应仍由这个实际BeforeEBS阶段生产：

1. 在BDS每次实际OS启动前，分配／定位一小块独占reserved RAM，先把旧记录置invalid，建立本次launch ID及明确schema/长度。地址、引用和本次ID须通过已审的EFI／DT入口传递；不能假定现ring有空闲空间，不能复用可能残留的日志行。
2. BeforeEBS保持当前一次Attempted／未知全字拒绝语义。只有实际afterCSR完整0且状态成功后，才发布该launch的有效完成记录；包含固定CSR地址／宽度、原始完整before/after、成功状态和producer退休范围。先写数据，最后发布valid并处理必要cache一致性；此处不得临时分配。失败／回调没运行／记录截断都保持invalid。
3. 生产者退休必须明确到真正的firmware producer：RAM-only SerialPortLib不触硬件；BDS direct FIFO在Attempted后已拒写；EudLogDxe timer须先停止并join／证明已退休后再作最后清0。当前timer本身不写enable，但还会读CSR，不能把DEBUG行当作它已join的证明。其它回调不得在有效记录后重新启用EUD。
4. Linux supplier复制并验证同次launch的记录、板级/资源绑定及schema后才可能发布READY。CRC只用于损坏检测，不认证任意软件；“受信”来自明确的固定firmware/kernel启动链，不是用户态写一个DT布尔。旧boot记录、请求标志、disabled节点、stdout marker或用户态通过均不能直接mint token。

顺序不能假设handoff解析天然早于earlycon。第一版新boot-off opt-in从最早入口即处于SEALED/UNKNOWN：在`eud_setup`第一处CSR/FIFO访问前显式拒绝该boot-off模式，不能先等待普通supplier probe；常规COM/full-EUD probe也在第一处硬件访问前拒绝。原功能在新opt-in关闭时保持原样。若某个早期producer在seal之前已运行，永久记录producer_seen，supplier本次启动拒绝grant，不能靠稍后console注销“补成功”。选择早期策略的具体初始化入口必须在实现时用当前启动调用序证明；未证明前不发布READY。

## 最小token与撤销合同

supplier按实际板级EUD资源注册唯一instance，使用不回退的generation、真实kref和client `get_unless_zero/put/cancel_join`。API只需acquire／validate／release；acquire要求有效boot记录、boot-off seal、无producer_seen、未blocked/removed/error。结果须区分“boot disabled并排除已知软件生产者”与“模拟路由许可”；没有可信route范围时不宣称DP/DM已交还。

新producer不得持COM window/UART/tx、full-EUD、DWC connect/owner等锁再进入supplier。第一版boot-off永久拒绝producer进入，不自动让出route给reprobe；这比支持动态切换少一套状态和恢复流程。若以后允许切换，应另做实际revoke→锁外join→确认全部token释放→producer_enter，不能在此版隐含添加。

PM、remove和任何可能改变该proof的reset必须先在supplier短锁内标blocked、推进generation、pin当前client；解锁后cancel/join，再put。consumer只发布abort并join其exact worker，再按PHY→DWC→route／PD顺序释放；worker不等待持有它join的registry，supplier也不持锁跨调组件。remove在join完成前保留supplier/context引用；失败保留tombstone并拒新绑定，不访问已释放MMIO、不虚报恢复。正常release只丢token，不改硬件、不解除本次boot seal。

最小接入点是现 `owner_enter_windows()`：真实PD5V lease／strict sink之后取得独立boot-off supplier token；boot-off分支不用`eud_com_quiet_begin()`，但仍持跨组件PM约束覆盖PHY恢复和DWC恢复，最后才释放route token。原bound-COM软件quiet分支保持独立。此修改必须等supplier与所有producer入口、PHY withdrawal、最终1341检查一起审；仅接入route token仍不能去掉当前EOPNOTSUPP。

## 不可隐去的未知项

- 现BDS没有上述结构化handoff，也没新增EudLog timer撤销证明；当前running kernel未安装producer hooks。
- EUD CSR0说明EUD禁用，尚不等于覆盖所有secure firmware／外部调试通道的DP/DM控制。supplier只可声明已审writer范围；SCM mode-manager关系仍需固定板级依据。
- DWC/PHY reset或电源域转换是否保持EUD-off不是由“源码没写CSR”自动证明。第一版遇到未证明的转换就撤销且不自动regrant；若初始DWC probe/reset已使proof无效，应拒绝，而不是为得到token忽略该转换。需要补准确reset/retention范围后才能放宽。
- 不能通过读取已关电CSR来刷新proof，也不能在resume把DT布尔重新解释成硬件成功。真实USB直连拓扑是当前观察证据，不是跨PM/reprobe的内核能力。

本轮仅冻结方案及缓存源码引用，零kernel代码、测试、构建、挂载、设备、SDK、shared source或Git操作；没有完成route grant，更没有启用APSD。
