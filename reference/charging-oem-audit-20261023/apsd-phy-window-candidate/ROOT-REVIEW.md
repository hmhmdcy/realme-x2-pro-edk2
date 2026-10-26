# 根会话的限定复审

复审固定 `phy-window.patch` SHA256 `5228605bac9450af97e41cb45daa7a3bc24e8f81909ba46a9b7c65c967003990`、candidate C `cc8e7f3292792f1f921db090384202fcf8ebb426f5a782f976b5f4614ba6b6dc` 和原 Image 关联的 generic phy-core。8组实际函数测试和私有对象编译复用作者收据，没有为了复审重跑。

本次查看 begin 的 active-only PM get、generic mutex/initialized/mode 检查，三组原值保存后按原厂顺序写入，逐步错误及部分恢复，end 的逆序 masked 恢复、独立错误与准确 PM ref 释放，以及实际 generic init/exit/set_mode 和 runtime callback 调用顺序。在这个范围内未发现新增可证实问题；这不是全并发、link或硬件验证。

一个容易误报的边界已核实：generic phy_init 先在锁外获取 PM，然后锁内只在count=0调用ops；额外引用可1→2。generic exit只在最终count=1调用ops，因此2→1合法，最终可能断电的exit才会被owned guard拒绝。set_mode_ext直接在generic mutex下调用ops，callback不得再次拿同锁。候选和最终README已按这些真实路径描述，未改phy-core来施加不必要的全局限制。

provider probe 的初始PM引用和创建PHY/driverdata后才put属于固定baseline，不是本候选新增；它满足新增runtime mutex对phy指针已存在的要求。PM get/put均在generic mutex之外；end成功清state后释放的是本次自己的引用，未替其它组件释放引用。

仍依赖未来同Image owner：绑定对象生命期与remove前cancel/join、成功DWC HALT及系统PM栅栏、独立PD/route前提、PHY end成功才DWC end。get_device、provider ref、HIGH_Z数字位或cookie单独存在均不能替代这些条件。代码没有自动消费者，当前手机未部署本补丁。
