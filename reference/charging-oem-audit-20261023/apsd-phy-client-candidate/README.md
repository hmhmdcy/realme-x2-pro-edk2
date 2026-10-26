# APSD：DWC检测任务接入PHY撤销接口

2026-10-25，离线接线、十二组组合测试和真实对象编译通过，未安装、未链接Image或模块、未访问手机。原[PD5V bridge](../apsd-pd5v-client-bridge-candidate/README.md)和[PHY provider](../apsd-phy-withdrawal-candidate/README.md)保持原件。本目录的owner替代旧owner，并要求配套新PHY实现和本目录相同的头文件；不能和旧裸PHY接口混编。

worker在读取PD/接线状态前，按DWC实际`usb2_generic_phy[0]`注册真实client。未发布或已被其它client占用时等待，不先执行PD接管；注册通过已有owner kref的get/put保持回调上下文。注册本身不执行PHY MMIO、PM恢复或检测。begin/end只接收该client句柄，无裸指针后备路径；普通PM保留注册和物理attempted历史，DWC解绑在join后显式unregister，busy时保留引用与故障状态。

provider调用真实`owner_phy_cancel_join`时，先发布永久PHY fence、abort/retiring/quarantine，再取得原owner_registry并join工作。清理使用retiring路径：先精确恢复PHY，再cancel DWC，不用正常end短暂重连。已有DWC quiet token由原stop_post在window_shutdown之后消费，再清理EUD/额外PM引用。普通SYSTEM/PD/UDC resume不能解除PHY撤销后的quarantine。

worker若先观察到revoked状态、而撤销回调尚未取得生命周期串行权，也立即建立同一retiring fence。新provider不会自动清除此状态。DWC先解绑时，provider已持有的client引用保证后到回调不会使用已释放owner；回调看到`dwc=NULL`只join、不访问旧DWC MMIO。恢复失败继续保留独立错误/quiet，provider最终释放资源后旧PHY handle只能读保留结果；DWC后续解绑可释放该handle，但不能冒报恢复或重试MMIO。原有故障孤立状态仍可阻止自动替换控制器。

[组合测试](test-result.json)执行**完整实际owner、PD5V及PHY provider实现，以及四个实际PHY窗口函数**。十二组ASan/UBSan/Werror通过，覆盖provider缺席后绑定、剩余attempt gate、PM引用/attempt历史、PHY撤销、PD/PHY两种取消顺序、待发回调的revoked cut、DWC先解绑、正常/失败精确恢复、busy unregister、shutdown及UDC重绑。kernel work/PM/MMIO是模型；回调待发cut是显式调度模型，不冒称穷尽并发。前轮十组PHY真实pthread证明直接复用；未重跑旧14组PD bridge或其它无关套件。失败孤立场景的fixture销毁只释放模型资源，不是生产恢复路径。

[实际编译](build-result.json)复用原284存储检查和既存W1命令，仅编译两个私有owner对象：当前TYPEC=m拒绝路径214b197f…efbe15，以及仅命令预处理为未来builtin的路径f0f305c2…60459；均Werror/零诊断。共享源码、config/命令保持。已有PD对象和PHY对象按准确哈希复用。真实当前配置没有因此变为builtin，也没有部署。

[内部接口检查](interface-result.json)只将未来owner、新PHY对象及原PD对象做私有relocatable link：九个所需内部接口均有定义，相关未解析符号为0；剩余kernel导入正常保留。不是vmlinux/Image或可加载模块，不证明整套内核配置或运行通过。patch对原三个叶文件fuzz0应用后字节一致。

初次测试先因fixture缺BIT声明拒绝，随后解绑断言误把独立存活PD provider的Type-C引用也要求归零；已修正fixture，保留真实owner释放要求。首次真实编译因旧core.h优先引用旧owner头、缺PHY fence而失败，原结果保存在`history/build-include-precedence-failed.json`。最终私有include视图使用原core.h字节及新owner头，未修改共享源码或放宽告警。构建器第一次锚点计数拒绝发生在创建输出/调用编译器之前。

无条件EOPNOTSUPP检测门继续保留：**EUD-off路由授权、最终一次PMIC传输重验证仍缺**。正常worker测试保持零1341/模拟窗口操作；主动窗口清理案例仅在fixture直接调用内部函数以检查错误顺序，不代表生产入口已放行。没有改变原厂三组PHY控制位、PD四次禁用操作、保护分类、输入帽、CC/CV、桌面或相机。完整APSD/Type-C/PD/快充、真实待机USB唤醒及计时修正的实机验证仍待完成。
