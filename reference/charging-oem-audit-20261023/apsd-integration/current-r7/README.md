# 当前 R7 USB / PHY 的具体集成边界

本轮继续记录在新 `current-r7/`，原 `../inspection-result.json` 挂载缺失记录保留。根会话允许后使用原 kernel461→kernel284 storage helper，只读取选定源码与原件；未调用SDK、手机、SSH、构建内核或修改共享源码。

## 已固定实际源码及原 Image 关联

`source-manifest.json`：原 helper 返回 `/mnt/samurai-full282/build`，build/source 与生成 Makefile 均指 `/mnt/samurai-full282/source354`，当前 HEAD `5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d`。快照含 PHY、core、两版QCOM glue、DWC gadget/DRD、UDC、role、Type-C/PD、两版EUD、DTS、当前config；每件有路径、长度及SHA。

`image-source-linkage.json` 将19个驱动/header文件逐个与原 kernel363 Image 提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 的 git 对象比较，全部逐字相同。原 Image SHA为 `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468`，由既有363与native USB boot收据关联。当前两份DTS源码已变化，**没有拿它们当部署DTB**；实际角色判断改用现有 native DTB原件 `c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503` 的完整解析。它只新增原生usb-psy-name，既有收据证明其它属性逐字保留。此为本地原Image/DTB来源关联，不是新设备读取。

## 当前可以复用什么

| 入口 | 当前真实行为 | 用途和边界 |
|---|---|---|
| `phy_set_mode_ext()` / femto `.set_mode` | phy-core持`phy->mutex`；femto只保存`hsphy->mode`，忽略submode，无MMIO | 可复用短操作互斥；当前没有DPDM/BC1.2进入、退出功能。返回0不能当high-Z。没有为产出patch而修改它。 |
| `usb_role_switch_set_role()` | NULL switch直接返回0；DWC NONE映射default设备/主机 | 当前没有可用role switch；这个API不能当暂停、失败检测或PD inactive证据。 |
| `usb_gadget_disconnect()` | 持UDC connect_lock调用`.pullup(0)`，通知function driver断开 | 可复用设备协议断开；不独占后续重连、不保证PHY高阻。 |
| `usb_gadget_deactivate()/activate()` | connect_lock下保存connected意图并置共享deactivated，之后恢复 | 可复用禁止function连接的机制；不是租约或引用计数。必须保留原状态，不能把别人的deactivated借来再activate。 |
| DWC `.pullup` / `soft_disconnect` | 正常路径synchronize_irq→connect_mutex→停transfers/EP0→DEVCTRLHLT轮询 | 可复用真正controller停止序列，但必须处理下面的PM快速返回与timeout。 |
| DWC `soft_connect` | DWC core soft reset、event setup、gadget start、run/stop | 可复用协议恢复；不是整PHY reset，但可能失败。返回与硬件/USB重新配置证据必须分别保留。 |
| femto write-mask helper | RMW后读回用于完成写入 | 可复用保留其它bit的写法；现有读回没有核对预期值，不能直接充当检测进入/恢复验收。 |

精确DTB中的父节点兼容为 `qcom,sm8150-dwc3` / `qcom,dwc3`，匹配 **dwc3-qcom-legacy.c**；新 dwc3-qcom.c只匹配`qcom,snps-dwc3`，其pre_set_role notifier不是本机路径。legacy probe对非host永久打开VBUS/session override；无extcon属性时`register_extcon()`直接返回，没有物理拔插notifier。因此configured/逻辑VBUS无法替代PMIC/ACOK的物理边沿。

当前配置 `CONFIG_USB_DWC3_GADGET=y`、DUAL_ROLE未启；Makefile只有DUAL_ROLE才链接drd.o。精确DTB的DWC节点`dr_mode=peripheral`且无usb-role-switch/connector graph。即使以后另行接role switch：drd中的NONE转换为默认DEVICE/HOST，core `dwc3_set_mode()` 对非OTG直接返回；OTG才排异步work。故当前不能用 `USB_ROLE_NONE` 获得quiesce。

## gadget / PM 的实际完成边界

UDC层当前顺序为 `udc.connect_lock → gadget.ops.pullup`。DWC pullup在拿connect_mutex之前先改变softconnect意图。停止时先做runtime-PM barrier；已runtime-suspended则直接返回0。`pm_runtime_get_sync()` 返回0（刚恢复、由resume回调执行run/stop）时也直接返回；负值透传并标suspended。**这些0返回均不是新的DEVCTRLHLT或PHY high-Z收据。**

只有正常已active路径才先synchronize_irq，持`dwc.connect_mutex`进入`soft_disconnect`。它结束活动transfer、处理/等EP0，再清RUN_STOP、轮询DSTS.DEVCTRLHLT，timeout透传，之后停gadget IRQ并置NOTATTACHED。`run_stop()` 本身仍有runtime-suspended快捷成功。未来检测入口须持明确runtime引用并核实实际停止完成，不能拿pullups_connected或UDC枚举字符串替代。

`err_recovery_work` 与pullup共用connect_mutex；但 `dwc3_gadget_suspend()/resume()` **不持它**。core的DEVICE suspend路径在gadget suspend后会`dwc3_core_exit → phy_power_off/phy_exit`；femto `.exit` 会assert PHY reset、关时钟、关电源。system sleep不会因一般runtime使用引用自动被禁止。因此只持connect_mutex、只加generic PHY引用，均不是完整APSD事务锁。

femto电源与时钟在 `.init` 启用，在`.exit`关闭；`.power_on/.power_off`没有实现，不能把`phy_power_on()`成功当作供电已准备。`phy_set_mode_ext()`也不自动取runtime PM引用。若init_count降到0后重新`phy_init()`，现有`.init`必做整个PHY reset；这不是允许的检测准备捷径。

restore还存在具体错误边界：UDC activate先清deactivated、清connected再调用connect，失败不会自动还原这两个字段；DWC软重连失败需要独立终态。当前core DEVICE resume调用`dwc3_gadget_resume()`时未传播其返回值，故不能只依靠PM resume成功认定数据已恢复。任何将来BC1.2专用完成接口必须直接保留恢复错误。

## EUD 与 PD owner 的真实状态

精确DTB只有`qcom,sm8150-eud-com`串口节点，未实例化完整`qcom,eud`。当前完整qcom_eud模块所需SCM mode-manager资源与USB role switch不能冒用到COM driver。COM probe会打开CSR_EUD_EN；其停RX/TX、注销console、恢复AHB2PHY、关CSR的完整路径是 `eud_reboot_cmd()`，随后不可返回地kernel_restart。普通UART shutdown/remove不等价于可恢复的数据路径借用；当前无专门运行期quiesce/restore API。根会话的EUD常态off工作保持独立，未合并到这里。

PM8150B Type-C/PD节点在精确DTB中disabled；虽然相关驱动模块配置存在，当前没有该节点的Linux TCPM/PD角色所有者和connector graph。**这表示Linux缺owner，不能证明bootloader遗留PD协议inactive。** 原7个输入字段、peripheral角色和BC1.2 DONE也不能补足PD/PR-swap/hard-reset的独立状态。

## 最小实际驱动变更边界

当前可将实现收敛到三个具体位置，不需要移入整个SMB5内置充电器：

1. **DWC3拥有的检测窗口**：在gadget.c/core.c建立明确begin/end/cancel状态，让pullup、err_recovery、runtime/system suspend、remove都遵守同一窗口。复用soft_disconnect/run_stop和UDC连接意图保存，进入前取实际active PM引用，避免持connect_mutex等待会反向拿锁的恢复；返回独立halt收据。真正detach与系统PM要取消/拒绝检测，不能让phy_exit发生在检测中。单独调用公共deactivate/activate不能完成这个排他协议。
2. **femto专用检测模式**：由这个窗口调用，要求PHY已经initialized、regulator/clock受窗口保护，不能通过init去reset它。在phy mutex下保存原`+0x64`的0x0c、`+0x3c`的0x18、`+0x94`的bit0，按原厂顺序设high-Z并逐步读回。退出恢复原masked bits并读回，不能硬写“normal默认值”；任一步失败保留quiesced/错误终态，不允许自动接回DWC。现有mode_ext可作为将来明确submode的运输接口，但没有owner证明之前不加硬件写实现。
3. **输入session owner**：只有独立证明sink/PD inactive且EUD数据已交还时，才请求上述窗口，按原厂一次APSD复测/真detach重置，并等待新的完成。必须将PHY退出、DWC数据恢复与APSD检测成功分开记录，保持R7 native授权与MP2650保护帽。缺PD状态或EUD交接时拒绝，不默认false。

目前1与EUD/PD独立前提尚未实现，无法证明2的供电、时钟、旧寄存器恢复和退出错误在真实并发下闭合。因此本轮停在已定位的跨驱动缺口，**没有占位补丁，也没有可运行硬件写候选**。下一步应优先为DWC/COM明确排他窗口与独立PD状态，而非在provider getter里加regmap写或复位整个PHY。

## 定向验证

`actual-functions.inc` 从固定快照抽取10个完整现有函数，来源行号/SHA在`function-manifest.json`。`test-result.json` 的6组测试以真实函数、fake OS对象执行：PHY mode静默不做检测、NONE/default与非OTG无操作、pullup PM快速成功/错误/timeout、deactivate意图保留、共享停用没有lease、activate失败与延迟connect不代表物理恢复。ASan/UBSan与-Werror全部通过。

这些测试固定真实API限制，不宣称证明整个内核锁图或硬件安全。未重跑原厂7组、FLOAT12768+14、图标32+13或PM旧套件；未生成或构建新驱动。
