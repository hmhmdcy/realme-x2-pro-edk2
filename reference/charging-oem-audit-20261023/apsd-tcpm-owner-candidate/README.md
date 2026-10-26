# 真实 Type-C/TCPM owner：最小 gate/cancel 接入调查

**现固定源有BC1.2启动等待点，但没有完整安全的状态/取消租约可直接复用。** 本叶已经把具体接口缺项缩到TCPM真实协议状态、qcom输入事件和取消join顺序；没有写只返回false的占位消费者、把缺owner当PD inactive，或生成可部署硬件写patch。现Image363/EUD启动实验不混入新代码。

## 固定来源与本机连接

`source-manifest.json` 固定12个实际source354文件。TCPM core SHA `e7e8b9c692e64782e3422ba8e1f79b21072ed89e1dce8751d53f4b197762c0ab`；qcom总驱动 `02d6faab…747cd`、port `5d3fa92d…af1d`、PDPHY `d8a0e073…0cf6`。后三者与此前current-r7保存的Image363/ba61原始字节关联逐件相等；TCPM core本次固定了实际文件，**没有新查Git或冒称其独立ba61源字节关联已完成**。原配置有TCPM/QCOM_PMIC模块，配置存在不证明正在绑定。

复用原FDT reader，只解析现有缓存：native DTB `c559d2c4…c4503` 与本次EUD boot policy DTB `9271d9cc…4358` 的Type-C/VBUS子树逐字相同。`typec@1500` disabled，**没有connector子节点**，VBUS regulator也disabled；详见board-linkage。这只证明当前Linux没有这个owner实例，不证明引导遗留PD协议inactive。

qcom_pmic_typec.c 87–124行先找connector/注册TCPM，随后port_start，再pdphy_start；port_probe 729–739行要求connector及VBUS regulator，PDphy_probe576行要求vdd-pdphy。因此不是简单把status改okay就得到观察器。port_start631–683行会写中断配置、**EN_TRY_SNK**、VCONN/CC参数并开IRQ；PDphy_start510–528会供电、reset并开IRQ。TCPM register8957又会运行init，init7866起会reset port及进入PORT_RESET。不能在本轮把这些控制动作伪装成只读“接上owner”，也不在本叶强制角色。

## 可复用的真实函数与不够用的回调

| 当前函数/行号 | 真实状态/锁 | 能做什么及准确限制 |
|---|---|---|
| tcpm_port459–560 | `port->lock`保护attached/pwr_role/state、pd_capable/explicit_contract、swap_pending/AMS；`pd_event_lock`保护事件位 | 这是协议事实的正确来源，不能从PHY enable、DT peripheral或PMIC APSD结果替代。state/AMS和pending必须一起读。 |
| SNK_ATTACHED 5765–5777，fw timing8161 | attach成功后用`sink-bc12-completion-time-ms`延迟SNK_STARTUP | 现有上游BC1.2等待点可作为未来初始窗口位置；只是timer，没有完成/取消token、没有等待精确PHY恢复，不能把delay返回当检测窗口成立。默认未配置值0。 |
| tcpm_snk_attach5213、SNK_WAIT_CAPABILITIES5838 | attach时pd_capable=false；set_pd_rx(true)失败也会转SNK_READY | **SNK_READY且pd_capable=false不是已知PD inactive证明**。还需TCPC I/O成功、无遗留合同/活动、事件及当前协议phase。 |
| tcpm_set_roles1315/1374、qcom set_roles426 | TCPM持port锁，qcom短持PDPHY spinlock写MSG_CONFIG角色位 | role回调只有attached/power/data参数，不能补出PD active/PR swap/hard reset。qcom实现本身不消费attached，也不查询合同。 |
| tcpm_pr_set7501 | `swap_lock→port->lock`；AMS/upcoming_state/swap_pending后解port锁等completion | 需在本地请求入口失效gate，不能等角色位实际改变。远端PR/FRS走RX/event路径，同样不能只看swap_pending。 |
| tcpm_pd_receive4224 / rx_handler4151 | 每条消息独立GFP_ATOMIC事件和kthread work，handler才拿port锁 | 排队RX不进入`pd_events`，分配失败直接丢回。只查事件位会漏真实协议输入；失效须在分配前发布。 |
| tcpm_pd_event_handler7071、cc/vbus/reset7188等 | handler先port锁再短pd_event_lock，取事件后放spinlock；原位会合并 | 事件位不是单调代号，重复/合并不等于同一事件。未知排队期不能发安全许可。 |
| qcom SIG_RX isr374 / reset_work139 | threaded IRQ(ONESHOT)，先schedule普通work；work在PDPHY spinlock内reset_on/off，解锁后才tcpm_pd_hard_reset | **只在TCPM hard-reset入口取消已晚于实际PDPHY reset**。必须在qcom真实输入入口先发布失效，并在硬件动作前于内部锁外完成join。 |
| qcom set_pd_rx407 | 只写RX_ACK 0x4b，未改变TCPM合同 | RX关闭不是PD inactive，也不是模块掉电或源电压证明。 |
| qcom get_vbus324 / detect276 | vbus_lock下返回cached source-enable OR detect；detect读错置misc0 | 现回调会把真实读取errno压成0；不能用它单独把“读错”当真detach或known sink。新gate需要保留I/O未知旁路，不能仅把负errno直接塞回bool调用者。 |
| tcpm_tcpc_reset8062、qcom remove132、unregister8975 | reset在port锁下init；remove先stop两硬件再unregister/work销毁 | 生命周期也需要先失效、锁外cancel+join；单有device引用不保证硬件仍可借用。 |

另TCPM普通power_supply属性只给usb_type/电压电流/online，没有PR swap/hard reset/pending RX字段；其变化通知不是可靠取消握手。init7880的VBUS已高会记录vbus_never_low，5838之后还专门对可能的boot合同做soft-reset路径。这正说明软件初始pd_capable=false不代表遗留合同不存在。

## 与原厂/官方既有方案的关系

本机原厂SMB5已恢复源的 `smblib_set_prop_pd_active` 原4320（本地oem-functions.inc637）先接真实协议控制端传入的PD状态，再令APSD=!pd_active，后续管理PD电流；request_dpdm也显式避PR swap，plugin/source处理hard-reset。原厂没有靠USB PHY off或peripheral角色自行推断pd_active。这里只复用该所有权原则，不移植它的内置充电器、PD电流投票、角色或高压控制。

现上游TCPM的BC1.2 completion-time正是可用的最小**位置**，但没有safe lease hook；现qcom回调也没有提供完整protocol snapshot或同步取消完成。因此本轮不提交一份“编译通过却没有真实owner授权”的gate patch，不为不存在的生产patch做对象编译。五组真实旧函数边界编译/执行在下节，不能被称为新接口实现。

## 最小可实施的新接口形状（设计，尚未实现）

`interface-contract.json` 明确implemented=false，供session协调，不可链接或视作已接通API。拟由实际qcom设备/父PMIC regmap/TCPM port/connector fwnode绑定，禁止全局找第一个port或参数自报。`tcpm_bc12_owner_snapshot`在port锁下读取真实协议字段，并与输入generation、queued RX/CC/VBUS/reset及I/O validity组合，返回后不持任何组件锁。PD事实必须含valid/UNKNOWN，不用默认false；缺owner=-ENODEV、错PMIC=-EXDEV、未知/输入pending=-EAGAIN、source/PD/swap/reset busy=-EBUSY，实际I/O errno保留。

成功候选只允许已完成port_start+pdphy_start的owner、已处理引导遗留状态且实际物理epoch建立、attached sink、明确已知PD inactive、无PR/FRS/HR/待处理协议输入及I/O未知。最短初始window在现SNK_ATTACHED等待点，但要新增完成/取消ack，不可仅加长timer。若考虑已稳定non-PD的后续window，同样需要真实owner的协议activity与当前phase证明；不能靠某一个false字段。

取消要分两段：在真实输入/请求到来时先无睡眠发布monotonic event generation/abort，随后**在TCPM port锁、qcom spin/vbus锁之外**调用session cancel+join。PD RX分配前、SIG_RX安排reset前、本地swap、离开可借用phase的timer、TCPC reset、remove/PM均要覆盖。join必须让已开始的唯一总线操作及精确PHY恢复完成，再让冲突的controller动作继续；不能从持port锁的回调直接反向join一个正在查询TCPM的session。join失败/超时的PD时限和恢复失败政策尚需作为新hook的一部分明确，不能声称此处已有安全闭环。

物理attach epoch由真detach建立，DWC rebind不重新武装；binding generation与event generation独立。session在唯一写之前核同绑定/epoch/generation，取消join接住已开始动作。这个gate不提供七字段stable两读、0x1341写通道、EUD电气route许可或PHY/DWC资源，它们不能用stub顶替。已通过消息与session候选对齐：缺任一前提保持明确拒绝，不把设计API当已实现。

## 本轮实际验证及交付

`actual-functions.inc` 从固定源抽取9个完整原函数，行号/hash见function-manifest。5组-Werror/ASan/UBSan通过，fake仅限OS/regmap：PD RX独立排队/分配失败无事件位；SIG_RX pending与先reset后TCPM通知；RX disable/role写不清合同；VBUS读取errno与cached source-enable；CC位合并不是generation。它们是当前API限制的真实可执行反例，不是新“safe gate”模型。

仅新增本叶与私有小C测试输出；未修改共享source/build/config、旧候选或收据，未重跑APSD/充电/保护旧套，没有手机/SSH/USB/SDK/Git动作。下一可接入小块已具体到真实TCPM snapshot/ingress invalidate及qcom pre-reset join；这需要新增内核owner接口和有效板级owner实例，当前源码不存在足以直接复用的完整hook，故本轮停在准确可实施规范，不能宣称PD前提已解决。
