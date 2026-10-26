# APSD：USB2 PHY provider撤销与消费者寿命

2026-10-24，离线实现与真实单对象编译通过，未接入消费者、未链接Image、未安装；手机仍为504/USB13f41/charger97c/保护f6bef/服务83469，未访问手机。该组件补[APSD下一步](../apsd-next-eud-off-closure/README.md)列出的provider撤销接口，尚不代表完整APSD、PD或快充完成。

沿用[原PHY窗口](../apsd-phy-window-candidate/README.md)，保留原厂三组masked高阻进入及精确旧值恢复。两个原window函数仅改为内部bound函数，实际硬件动作/错误/PM规则不变；新的外部接口必须传入注册后的client句柄，不能再用裸`struct phy *`调用begin/end。API仍只供同Image内部使用，无EXPORT/UAPI或自动消费者。

provider在generic PHY、OF provider及PM资源建立之后发布，最后注册devm撤销action。因此probe回滚时也先撤销，再释放PHY/MMIO。remove/shutdown显式调用同一撤销函数：先从注册表移除并拒绝新begin及普通init/exit/mode/runtime动作，额外pin住client，再在registry/provider/generic PHY锁外调用真实`cancel_join`。回调须停止并等待所有检测工作结束，可在资源仍有效时调用end或成功unregister。

client注册需要真实get/put，持有owner回调代码/数据的寿命；注册表按实际PHY实例匹配，不靠名字。begin/end在单独provider锁内串行，防止devres与已开始的硬件访问并行释放。unregister要求调用者已join全部API使用者；尚有window时返回EBUSY，保留句柄和上下文。回调自己的client引用允许回调中unregister，最后put在锁外执行。每个并发withdraw还有独立provider引用，不能在另一个devres回收发布引用后，让completion等待者读到已释放内存。

join之后将provider的bound指针清空，另存结果供尚存client读取。成功恢复保留restored事实；失败/遗漏恢复则记录独立withdraw_error、清除high_z许可、释放本窗口仍持有的PM引用（put_noidle），不重复MMIO恢复、不重连DWC/EUD。资源销毁后旧句柄的begin/end返回ESHUTDOWN，status仅返回保留结果，不再访问PHY/PM/MMIO。恢复错误不因撤销被改成成功。

[十组定向测试](test-result.json)执行完整provider实现及十二个实际窗口/生命周期函数，ASan/UBSan/Werror通过。使用真实pthread mutex、原线程join和completion等待；PM、MMIO和driver core边界为模型。覆盖实例/引用/单client、原masked恢复、busy unregister、remove后结果、恢复失败/未完成进入、回调内unregister、实际begin与remove并发、devres与撤销等待者并发、shutdown普通入口及probe action失败。没有穷尽所有内核调度，也没有physical/lockdep证明。

[实际单对象编译](build-result.json)沿原PHY私有构建器及kernel284存储入口，只构建`phy-qcom-snps-femto-v2.o`；W1/Werror零诊断，146064字节、SHA3518d8e6…ef571c。共享PHY源码及config保持，未用SDK、未构建Image/包。首次测试因fixture缺dev_vdbg声明拒绝；首次对象虽生成，但kernel-doc三条警告使检查失败。`history/`保留当时测试/构建结果；已修正注释位置/函数名，并补并发撤销引用后重新测试和编译，未放宽告警。

下一步须在现有DWC检测任务中注册真实client并接cancel/join、替换begin/end调用，连同其PM/UDC/unbind路径编译验证。原[PD5V bridge](../apsd-pd5v-client-bridge-candidate/README.md)仍使用旧API，不可直接和本头文件混编；其无条件EOPNOTSUPP入口继续保留。EUD-off路由授权及PMIC最终单次传输重验证也仍未实现，本组件不解除1341禁入、不提高任何预算。普通5V实机与待机USB唤醒仍按原窗口另测，桌面未改，无子代理。
