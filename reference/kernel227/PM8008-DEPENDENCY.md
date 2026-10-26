# 后摄P/Q依赖：只读设计，未实现或上电

当前地址锁只串行化访问，不能保证Q从默认8迁至4后P才释放至8。用户已授权的后摄子代理核对了当前MFD、device core及DTS。标准managed device link可以约束驱动绑定和解绑，**不能替代冷启动复位保持**。

建议P新增拟议phandle`qcom,address-setup-supplier = <&pm8008_q>`，并保留自己的reset GPIO；这不是现有上游binding。schema限制P为reg8、有reset、无initial-address；驱动检查Q同adapter、reg4、initial-address8，拒绝自身、反向、跨总线和禁用目标。不能借用假supply/reset或`post-init-providers`表达地址依赖。

P probe先取得并保持自身reset，再找Q。Q设备未创建/尚未完整绑定时返回EPROBE_DEFER。持Q的device_lock核查`device_is_bound()`及正确驱动后，以`DL_FLAG_AUTOPROBE_CONSUMER`建立持久managed link；不加STATELESS、AUTOREMOVE或PM_RUNTIME。随后平衡引用，才进入现有地址锁下的P初始化。Q解绑时core先解绑P，Q重绑后可自动重试P。[device-link规范](https://docs.kernel.org/driver-api/device_link.html)

P应在注册MFD子设备以前登记reset devm action，令子regulator先移除、P后保持复位、最后释放GPIO。195的Q迁址失败重assert必须保留。最小设计中Q remove保持已分配地址4；以后若要复位Q，必须晚于P及Q子设备清理，不能在remove入口抢先复位。

启动前置仍未闭合：现在P的gpio-hog能保持低，但会阻止P驱动取得同一GPIO；删hog后，Q先probe而P状态未知时，一条device link不会自动把P拉低。需要经核实的早期reset保持与GPIO所有权移交；当前默认地址占用检查只能安全失败，不能证明冷启动可成功。这一问题应先于启用P的LDO消费者处理。

修改范围将限定`drivers/mfd/qcom-pm8008.c`、对应schema和板级DTS。PLDO VIN仍未知，未添加猜测电源、未提高电压、未操作P/Q或后摄电源。IMX319资源/驱动候选继续沿用[226研究](../kernel226/RESEARCH-FOLLOWUP.md)。
