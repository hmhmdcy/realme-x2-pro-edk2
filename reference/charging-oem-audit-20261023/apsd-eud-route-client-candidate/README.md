# APSD任务接入真实EUD-off路由

2026-10-25。沿[最终传输边界](../apsd-final-transfer-candidate/README.md)接入[实际producer仲裁](../eud-route-provider-candidate/README.md)。默认关闭、未装机；显式配置下的真实client/lease路径已经接通，继续保留原PD禁用、PHY撤销、物理连接历史、七字段重读和单次命令限制。当前手机原USB13f及普通500mA充电不变。

worker先解析真实路由provider并注册绑定DWC设备和owner引用的client，再解析PHY及观察PD。缺少provider会等待；关闭配置、缺少节点、撤销或身份不匹配不能授权。进入检测前必须具有实际PD sink lease；持runtime PM引用后，依次取得EUD-off路由lease、DWC halt窗口和PHY high-Z窗口。最终传输回调再次验证原路由lease地址/代际及新鲜EFI证据，保留原PD代际、PHY撤销、来源/时限与一次epoch检查。此profile完全删除旧`eud_com_quiet_*`调用，不以COM未绑定作为关闭证明。

正常退出按PHY→DWC→route→runtime PM恢复。路由撤销先永久封住worker，再锁外join；DWC仍正常时恢复原gadget，已进入UDC退出流程时保持cancel/shutdown顺序。取消返回0但尚有shutdown所有的窗口，不会冒作全部释放：provider保留排他，等真实stop_post/end和后续unregister确认。恢复失败仍保留路由及owner引用，调试producer不能提前接管。PM使用provider既有的本boot证据过期策略，普通resume不能重新启用APSD；完整路由待机重建仍待实现。

组合测试发现旧owner恢复路径会在另一supplier的后续join中再次尝试已失败的PHY恢复，实测模型写计数4→7。现先检查首次`phy_error`，保留原错误和quiet窗口，后续独立join不再重写。原失败源码、私有运行和首次七组结果保留；此修正尚未安装手机。初次组合fixture声明/宏错误、后续仅fixture销毁遗漏PD引用的错误也保留，没有把失败写成通过。

[九组完整C测试](test-r2-result.json)运行真实owner、PD、PHY及route provider，包括正常单次传输/逆序恢复、最终证据失效、正常路由撤销、UDC退出、失败恢复、回调前DWC解绑及PM过期。内核工作调度、DWC MMIO、EFI copy及总线命令是模型；真实pthread/worker join并发另复用已通过的provider测试，不能把本套确定性交错叫实机或完整并发证明。失败孤儿的销毁仅为fixture释放模型资源，不是生产清理路径。

[两个受影响对象](build-result.json)沿原ABI/命令W1/Werror零诊断，当前关闭配置无route或COM导入；未来builtin配置具有真实route导入、无COM依赖。复用当前USB IRQ/PM input、PHY、PD和route/receiver五个原对象，私有relocatable检查十八个内部API均解析。共享源码/配置保持TYPEC=m，未链接最终Image、固件或模块。[源码审查](source-review.json)核二十三个原函数逐字保持、四个新增/十个改动函数、完整C/h patch零fuzz及进入/恢复顺序。

下一步需把固件交接、真实producer钩子、内核provider和本client成套加入同一启动组合，并绑定实际DT/Type-C配置后启动检查。实际首次物理断源/新连接周期、FLOAT/APSD结果、路由跨待机重建和完整PD/快充仍未验；软件重连不能代替VBUS断开。
