# Boot-only EUD-off：独立离线候选

本候选选择现成 EDK2 `BeforeExitBootServices` 交接入口，避免为一个启动变量接入新的 Linux runtime owner/API。它只交付 [boot-policy.patch](boot-policy.patch)、[候选生成收据](candidate-result.json) 和私有 native DTB 副本；**没有构建 firmware，没有修改共享树、Image、内核/相机模块或设备，没有运行 SDK/SSH/USB、刷写、重启或实体试验**。CSR0、USB直连、SDP500及图标效果均未实证。

**不能据此直接刷写。** 候选对上电 CSR 全字只接受 `0x00000000` 或 `0x00000001`；其它值会拒绝 arm，并拒绝本次 `\Image` launch，随后可能回到既有 BDS/菜单/复位流程，不保证能进入 Linux。未来在根会话协调的单一设备窗口中，必须先有实际有效供电下、同一硬件/boot身份的安全只读全字证据；现在手机由相机会话持有，本线不为补证访问设备。即使静态测试成功，也仍需绑定完整新 firmware 源/产物与独立回退来源后才讨论实装。本项排在 USBIN 单位初始化实体结果之后。

## 固定设计与实际来源

[design-evidence.json](design-evidence.json) 是补丁前封存的 v1 源证据，SHA `ca2c28f5…9e5494`；[design-amendment.json](design-amendment.json) 的 v2 修订是当前 CSR 接受范围依据：**撤回 `0x01010101` 许可**。旧 PlatformBm 注释声称 byte replication，但本次未找到可绑定哈希的 CSR 全字实物原件，不能把注释当硬件证据。补丁将该值也归入 unknown，未修改旧 runtime 冻结组件。

实际当前 boot carrier 原件为私有 `charging-management-20261023/usb-boot/boot-charging-usb-dt.img`，SHA `a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280`。它保留 Image363 SHA `15746aab…d6468`；当前 native DTB 是 `c559d2c4…c4503`，不是旧 FAT DTB `dcdd74ec…b2c8d`。仅改 FAT 里的 DTB 不能据此改变当前 firmware-native 输入。

该 carrier 的 retained `generated-boot-builder-private.py:16–18,51–52` 在构建前后检查 `kernel164/source-validation.json` 中的 PlatformBm SHA `eda995b4…7198a` 和 INF SHA `14ef7691…0ab4`；本次当前源码完全匹配，且 carrier 原件 SHA 已复核。故 **PlatformBm/INF 有实际 source guard → builder → carrier 收据链**。EudLog、SerialPortLib、DSC和EDK2 Core 源码来自当前仓库的只读快照，尚未独立证明每个文件是旧 carrier 当时的链接输入；这个界限保留在设计收据。未来新 firmware 构建必须将全部冻结输入和真实链接产物一起绑定，不以当前 repo 路径代替旧 carrier 源证明。

Image363 的 EUD、earlycon、DWC3、generic PHY 源码复用 `apsd-integration/current-r7` 的固定快照和 Image 源比较收据，见 [inspection.json](inspection.json)。这些相关 C 文件逐字等同原 Image 源；板级 `.dts` 后来已有变动，本候选用当前精确 native **DTB** 为输入，不从旧 DTS 重编全部树。

## 补丁的唯一启动策略

1. 在原 Linux boot-option 路径中新增独立 EUD-off arm/callback/disarm，不改现有 panel 三个函数或其原始调用块。arm 失败直接跳至原有清理路径，不调用 `EfiBootManagerBoot`。
2. `mSamuraiLinuxCmdLine` 的 UTF16 LoadOptions 只移除 `earlycon=eud,mmio,0x88e0000` 和 `console=eud`。`console=tty0`、loglevel、ignore_loglevel、panic及三个 ignore_unused 参数按原顺序保留；不改其它 LoadOptions 构造。
3. 基于当前 `c559…` DTB，只修改 `/soc@0/serial@88e0000/status="disabled"`，同步从 `/chosen/bootargs` 移除上述两 token。全部其它节点、属性原始值及 phandle 逐字一致；当前树只有这一个 EUD compatible 节点，没有另一个启用的完整 EUD 节点。
4. 其它 firmware BDS 的原始 EUD enable/供电过程保留。到 BeforeEBS 时只对固定地址 `0x088e1014` 做 32-bit read、条件 write0、readback；不写 AHB2PHY `0x11`、PHY、SCM、role、PMIC、descriptor、充电电流或预算。AHB wait state 不是路由开关。

`samurai.dsc:20` 的当前 profile 明确同时定义 `SAMURAI_ENABLE_EUD` 与 `SAMURAI_LINUX_KERNEL`。新代码位于 Linux 编译区内并再受 ENABLE_EUD 约束；不是声称任意构建都可访问 EUD。INF 已有 BeforeEBS GUID，未改 INF/DSC 构建选项。

## 交接生命周期、优先级及生产者

实际 EDK2 `CoreExitBootServices` 的顺序是 `DxeMain.c:770` 通知 BeforeEBS → `775` 关全局 timer → `780` 验证 MapKey → `794` 普通 EBS 通知 → 清 boot services。**BeforeEBS 可以在 MapKey 失败前已经执行，EFI 重试会再次通知。** 新上下文是 BDS 库内静态存储，首次 callback 先置 `Attempted`，后续通知不再读写寄存器，不能用 EFI 重试反复清位。

新回调和 EudLog timer 都是 `TPL_CALLBACK`。`CoreRestoreTpl`（Tpl.c:122–133）只在 pending priority 严格大于恢复目标时 dispatch；相同 TPL 的回调不会插入一个正在执行的 callback 中。`CoreDispatchEventNotifies`（Event.c:166–192）按队列串行调用通知。这个实际软件调度依据和 host 定向测试不等于整机多核/固件硬件并发全证明。

固件 register 可访问的范围依据是：原 BDS 在 PlatformBm.c:1082–1089 已经写并读回同一 CSR；当前 EudLog timer 在 BeforeEBS 之前一直读取该 CSR。新 callback 位于普通 EBS driver teardown 和 timer 停止之前，不是从 Linux 未供电状态直接 `devmem`。本候选不新增时钟/供电写，也没有 SoC bus-fault 捕获机制或实物电源测量；它不证明 **post-EBS** PHY、电源或 USB 路由状态，后续 Linux 正常 probe 必须独立核验。

生产者分别处理：

- `EudSerialPortLib::SerialPortWrite` 仅写保留 RAM ring，不碰 FIFO/CSR；callback 的 DEBUG 记录在当前 profile 也走此路径。
- `EudLogDxe::EudLogDrainNotify:190` 在 CSR 低字节不为 1 时不写 FIFO，且自身没有 CSR enable；成功全字0后下一次 drain 会退出。其 timer 在 CoreExitBootServices 775 行被停止。
- `SamuraiEudComPuts` 原来直接写 FIFO，BDS 菜单等待也调用它。因此补丁只新增 `Attempted` 门：任何 EBS 尝试之后，哪怕 loader 返回 BDS，也不再直接触碰 FIFO。正常进入 Linux 时 BDS 的同步 `EfiBootManagerBoot` 调用尚未返回，菜单 wait callback 不是另一个同时运行的线程；这是限定的固件模型，不是任意 runtime owner 保证。
- Linux earlycon 原先在 `eud_setup` 强写 CSR1；Image 的 `CONFIG_CMDLINE=""`，无 FORCE/EXTEND enabled 配置；earlycon 只有参数注册，没有 OF 自动绑定入口。移除两处 token 后不会通过该默认路径启动。COM probe 即使无 console token 仍强写1、安排 RX work，所以还必须 disabled 节点；单删 bootargs 不够。手动重新创建/绑定设备或外部调试器重启 EUD 不在默认启动策略保证内。

## 失败与观察收据

arm 先读取完整 CSR，只接受 0/1；`CreateEventEx` 失败或 unknown 均不写、拒绝本次 kernel launch。callback 再取完整旧值；若它变为 unknown，原样保留并记录 `EFI_COMPROMISED_DATA`。旧值0是零写路径；旧值1最多写一次0。写后必须读回 **完整32位0** 才标 `EFI_SUCCESS`，任何其它读回标 `EFI_DEVICE_ERROR`。不依据低字节掩码消除 unknown，不改白名单来适配测试。

RAM DEBUG receipt 为 `[SAMURAI-EUD-OFF] attempted/write/arm/before/after/status`，所有 raw full words 保留。回调没有分配资源或打印到 Linux console，没有提供能否决 EBS 的返回值。**读回失败仍可能继续启动 Linux**，定向测试直接用真实 `CoreExitBootServices` 证明这点；后续必须检查实际 receipt、Linux中无EUD生产者/CSR状态、host拓扑与新鲜USB预算，缺任一证据均不得验收 EUD-off。

若 loader 在 EBS 前返回，新 disarm 先置 `Cancelled` 再 CloseEvent；关闭失败保留事件引用和静态上下文，未来通知也只能惰性退出，不能留下栈指针或意外在另一镜像 EBS 时写入。成功关闭才清 Event；boot services 已无效时不调用它。任何失败或 BDS 返回均**不自动恢复 CSR1**；已有 `Attempted` 状态也阻止重新 arm。本候选不创建运行期恢复框架。

## Linux后续与回退门槛

实际 Image363 的内嵌 `/init` 先 source `samurai-rootfs`，成功时 `exec switch_root`；内嵌 `samurai-usb start` 只有 rootfs 失败的诊断 fallback 才执行。外部 rootfs 正常 gadget startup 因而存在前置观察点；本候选不改该脚本，不声称已添加 fail-closed Linux gate。DWC3 原 `core_init` 与 generic PHY 正常 probe/init 将自己准备供电、时钟、reset及设备模式，本补丁不替代它们；不执行 PHY 检测模式事务。

未来受控验证前至少需：固定当前上电 CSR 全字证据为0/1；核新 firmware 真实链接到冻结源/正确nativeDTB并实际去除所有eud启动token；确认保留 Image363及相机434所有实际模块/notes；准备可经**实体按键/fastboot**使用的当前 a30 boot 原件与 SHA 回退。恢复旧 boot profile 的下一次 BDS 会按旧实现启用 EUD；本线没有运行恢复、依赖当前 USB/EUD 通路来保证回退，或保证主机必然枚举 fastboot。

新 callback/DTB 未打包成 boot.img，不能直接刷 DTB 文件；实际实验须保持当前 logdump/Image/rootfs/充电包，并先验证 CSR0和真实 host NCM父拓扑变化。只有随后合法 SET_CONFIGURATION/native 预算证据才能回答 SDP500；“EUD hub 未见”或“UDC configured”均不能代替实体通路与授权，当前 hub 是否导致100mA仍是待检假设。

## 定向离线验证

[test-result.json](test-result.json) 记录 12 个新 host cases，执行全部新增 helper、候选 direct FIFO/launch 片段，以及未改的真实 `CoreExitBootServices`、`CoreRestoreTpl` 函数，只有 MMIO/BootServices/OS 边界是假对象。覆盖1→0、0→0、unknown含未证replica、arm失败、callback后unknown/读回失败、CloseEvent失败、loader返回、MapKey失败重试、void callback不能阻止EBS、相同TPL不重入。ASan/UBSan、`-Werror` 通过。

三个原 panel 函数及原调用块逐字比较通过；UTF16/DT bootargs只少两token，FDT只有两项语义差异。没有重跑旧大套件、完整firmware构建或实物试验。[result.json](result.json) 绑定设计修订、具体patch、原/候选DTB、源证据及测试。它是可复审候选，**不是部署或硬件验收收据**。
