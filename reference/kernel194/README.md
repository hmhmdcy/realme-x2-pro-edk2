# 阶段194：IMX471 OF接入候选与PM8008复位地址初始化

本轮修复了前摄接入中的一个实际障碍：第二颗PM8008 Q虽然运行在0x04/05，GPIO4复位后却回到0x08/09。新增的普通MFD驱动路径已在真机完成0x08→0x04迁移、绑定和七路LDO注册；已分配地址时也通过正常探测。IMX471新增OF、三路电源和板级pinctrl支持，编译与真机模块加载通过；尚未在本机执行该传感器驱动的实体probe、MIPI配置或取帧。阶段193的实体ID0x0471仍是当前最直接的前摄身份依据。

## 同传感器方案与本机接入

查到2026-08-05针对Nothing Phone (1)的IMX471提交系列：[OF匹配](https://lists.openwall.net/linux-kernel/2026/08/05/2085)、[vdig/vif电源](https://lists.openwall.net/linux-kernel/2026/08/05/2082)。当前本地基线尚无这两部分；本轮采用相同的通用接口方向，没有复制其它手机的接线。绑定参考该系列及[Sakari的评审](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2608.0/10712.html)，允许硬件2/4 lane，不把200MHz写成硬件唯一频率；本地驱动现有模式仍只支持4 lane、200MHz和19.2MHz外部时钟。

修改`drivers/media/i2c/imx471.c`：增加sony,imx471 OF表，vana/vdig/vif bulk supplies，上电前选择default pinctrl，下电后选择sleep；上电失败也撤销pinctrl。若主要操作失败且sleep恢复另失败，保留原始错误并记录恢复错误。未改模式表、RAW格式和曝光配置。ACPI旧平台缺少新电源时仍按现有regulator dummy机制兼容；本机候选DT明确引用真实三路电源，不能把dummy当作本机电源适配。

[IMX471补丁](imx471-of-supplies-and-pinctrl.patch)、[绑定](sony,imx471.yaml)、[实际C电源函数7场景](imx471-power-host-validation.json)。这7个ASan/UBSan场景覆盖电源/时钟错误和pinctrl撤销，未模拟全部V4L2资源绑定与流媒体路径。

## PM8008复位地址实测与驱动修复

最初在所有七路Q LDO关闭、无内核PMIC客户端、P保持复位的条件下，单次GPIO4物理0→1证明：Q@4消失，Q@8返回PM8008身份，SID由1回到2。随后仅写0x08的0x0644=1，Q重新出现在4/5。GPIO1始终物理低，GPIO4恢复高；全部本次采样的七LDO status/VSET/enable/mode/step/pulldown，以及SID/global enable恢复。没有改传感器寄存器、NV或校准。

普通MFD驱动新增可选`qcom,initial-address=<8>`，仅支持本机已验证的运行地址4/SID1组合，要求reset GPIO与普通7位I2C传输。先读运行地址；若已响应则保留电源状态、直接释放复位。只有NACK才进入初始化：保持自身复位并检查地址8未被兄弟PMIC占用，再释放自身、核对身份、单次写SID1并在4验证身份。写入ACK异常但新地址已确认时接受已核实的结果；未盲目重试。若地址8被占用，返回EBUSY并保持自身复位。

所有PM8008 probe的复位/地址设置共用mutex，防止同一驱动中的另一个probe在迁移窗口释放兄弟复位。没有跨GPIO操作保持I2C总线锁，避免GPIO控制器也在I2C上时死锁。无新属性的旧节点仍走原来的释放复位/延时行为。迁移完成后才保留secondary地址、建立regmap和MFD子设备。[源补丁](pm8008-initial-address.patch)、[属性约束](pm8008-initial-address-binding.patch)、[实际C函数35场景](pmic-address-host-validation.json)。

通过默认禁用、可撤销的OF changeset开发模块添加一个Q节点，以正常`pm8008`驱动进行真机测试，未把地址分配代码复制进诊断模块。测试节点仅描述已知S8C输入，没有虚构四路PLDO输入。普通regulator子驱动实际注册七个输出；七路本次采样值在probe前、中、后相同。

| 原生测试 | 结果 |
| --- | --- |
| 复位状态 | 用户态先建立已核实的Q@8/SID2状态；普通MFD自身完成复位、占用检查、SID1写入和Q@4绑定 |
| 已分配状态 | 原Q@4直接绑定，无用户态复位、无SID写入和地址迁移日志 |
| 撤销 | 两次均撤销OF节点、MFD/regulator/fixture模块与4/5客户端；P保持低、Q恢复高；手工SID回退未触发 |

两次均新增WARN/Oops/GPU fault/SLPI fatal/BT重组0，既有taint512保留。[原生收据](pmic-native-validation.json)、[fixture源码](samurai-pmic-fixture.c)。此处“复位状态”是同一运行系统内PMIC复位，不是整机断电或跨boot验收。若未来P已先在8启动，Q会安全拒绝初始化；双PMIC完整启动顺序尚需设计，不能仅凭mutex宣称全部相机冷启动已解决。

## 设备树与构建范围

[前摄开发候选](sm8150-samurai-camera-warm.dts)包含Q reset/initial-address、前摄L2 1.050—1.056V/L5 2.8V、真实VIO1.8V引用、GPIO12 reset/29选择/15 MCLK2、CCI1 master1、DPHY2/CAMSS端点。VDIG上限复现OEM请求1.05V向8mV步进取整后的1.056V，不是凭空提高电压。仅前摄的候选用GPIO1 hog保持P复位；接入P时必须重新设计，不能同时释放P占用8。

GPIO sleep不把RESET12切成输入，避免下一次resume仅set_value却没有输出方向。MCLK/选择线使用正常pinctrl状态。正式编译会为VIO等节点建立phandle，避免阶段193临时名称查找和ldo1重名问题。[DTB构建](camera-dtb-build-validation.json)只生成私人独立候选，没有覆盖canonical DTB、刷写或重启。

独立dtschema 2026.9环境中，Sony绑定与候选sensor节点严格校验通过，7个正反控制符合预期。[Sony校验](imx471-schema-validation.json)。PM8008新属性文档/编译与4个控制通过；**真实候选PMIC节点仍因四路未知PLDO输入缺失而报4项required错误**，没有删除绑定要求或用假BOB/VPH填充。补全数字phandle的schema测试fixture仅验证属性规则，不代表物理接线。[PMIC校验](pmic-schema-validation.json)。因此不是完整合法、可提交上游的板级描述。

IMX471模块62e5f050…、V4L2 CCI库f9c9272a…、PM8008模块9382ba34…及fixture e5b9405e…均通过树内Kbuild、vermagic/导入符号核对和intree元数据核对。V4L2 I2C backend在`v4l2-cci.ko`内，没有独立`v4l2-cci-i2c.ko`。前三个在无匹配OF节点时实机加载/卸载通过；这只证明ABI，不证明IMX471 probe或取帧。[构建](imx471-modules-build-validation.json)、[MFD构建](pmic-module-build-validation.json)、[ABI实机](module-abi-native-validation.json)。

IMX471/CCI目标W=1诊断0；完整模块树另有5条不相关既有告警，未称全树无警告。初次打包错误地寻找独立I2C backend模块，已利用完成的构建纠正，没有为此重复全构建。PMIC初次构建前置检查发现olddefconfig只新增两个default-n注释而停止；确认变化后重建，结束恢复原config字节。fixture的首次格式检查与绑定/代码混合检查告警均保留在私人日志中。

代码与两份绑定分别检查无error/warning/check；仅忽略新文件通用的MAINTAINERS提示。方便复现的[完整集合](camera-integration-development.patch)含三条“绑定应分开提交”告警，它是补丁集合而不是单封上游提交；使用[代码](camera-development-code.patch)、[Sony绑定](imx471-device-tree-binding.patch)、[PMIC绑定](pm8008-initial-address-binding.patch)分开审阅。[最终源码核对](source-final-validation.json)

## 当前状态与下一步

kernel183、boot/DTB172、安装的模块与MM191保持；未重启/刷写。原14个改动源保持，当前另有OF构建文件、IMX471/MFD/PMIC绑定改动，共19个tracked改动，四个相机新文件未暂存；不把存在源码当作启动部署。Image/DTB/config哈希保持，Module.symvers16793行和modules.order770恢复。

15014.14秒仍为189第二个boot：ADSP/SLPI/modem running，SensorProxy加速度/亮度/接近Has均true，MM PowerState3、GPS关闭；WARN1为193时钟失败，BT重组1为189既有故障，Oops/GPU/SLPI fatal0。所有临时PMIC/前摄/CCI模块已卸载，节点及临时适配器移除。[最终健康](native-health-validation.json)

下一步验证正式IMX471 OF probe/运行时PM、板级资源及MIPI真实取帧；不能把当前模块加载当成这些步骤已完成。四路PLDO物理输入、P/Q完整冷启动、其它镜头和高分辨率模式仍开放。GNSS无有效fix、蜂窝卡槽/注册/业务、BT后段重组与传感器长稳等完整goal保持active。

42份手机证据归档0afa8fa2…已在主机逐成员验证；原始身份、日志和完整寄存器快照只在私人目录。[归档收据](evidence-export-validation.json)
