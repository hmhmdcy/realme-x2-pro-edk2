# 阶段193：前摄IMX471实体识别与CCI/MCLK电源域验证

**本机前摄通过CCI1 master1，在7位地址0x10、寄存器0x0016实际读到0x0471，确认IMX471。** 这次是实体传感器应答；阶段192只解码原厂候选BIN。尚未配置传感器输出、启动MIPI或取得图像，完整摄像头适配仍未完成。

## 真机路径

当前DTB的CCI1原先disabled。临时模块仅对`/soc@0/cci@ac4b000/status`建立可撤销changeset，使用已有`i2c-qcom-cci`驱动，实际注册master0/1为i2c-6/7；[changeset接口文档](https://docs.kernel.org/devicetree/changesets.html)。CCI单独启用没有新增所列故障。[CCI源码](samurai-cci-bringup.c)、[实机](cci-native-validation.json)

前摄执行已与原厂工具交叉核对的供电流程：TLMM29选择、TLMM12复位、PM8150L L1 VIO 1.8V、PM8008 Q的L5 VANA 2.8V、L2 VDIG 1.056V、MCLK2 19.2MHz、释放复位后读取ID。1.056V复现原厂1.05V请求向8mV网格取整的编程值，并非另行提高输出；[192电压依据](../kernel192/pmic-voltage-contract-validation.json)。L5/L2均读取到VREG_READY，随后一次两消息CCI事务返回正确ID。[完整原生结果](front-native-validation.json)

PMIC P@0x08/09、两根PMIC复位线、SID/全局使能及MAX98937没有改动。Q@0x04/05在测试时被临时I2C客户端保留，只有L5/L2 VSET和enable被写入；结束后七个LDO的本次全部采样值，包括VSET/enable/status，与测试前一致。没有单独复位共享QUP总线，也没有编程sensor模式或曝光寄存器。

临时资源使用正常regulator/GPIO/clk/pinctrl API。S8C保持1.352V、最终用户数3，没有改变其电压；另一颗名为ldo1的0.752V电源保持用户数1。VIO结束后用户数0、state disabled；此前state unknown，因此不能说VIO状态字符串逐字未变。GPIO12/15/29恢复输入、物理低；MCLK引脚GPIO15_CTL前后整值一致。只读映射此一个TLMM寄存器用于取得原配置及比较，所有引脚写入经过pinctrl/GPIO接口。

阶段196勘误：按当前DT的reg-names与SM8150 group映射，GPIO15的north地址为0x0390f000。193 helper只读的0x0310f000位于west，因此上述整值比较不能证明GPIO15恢复。正常pinctrl/clk/GPIO/CCI路径取得实体ID的证据保留；196另按实际资源核对三处CTL与方向/电平并恢复，见[196报告](../kernel196/README.md)。

当前VIO节点没有phandle，且两个PMIC都存在名为ldo1的regulator。诊断使用临时名称查找后先校验1.8V，取得0.752V对象会在上电前退出；这是本机受限诊断方法，正式设备树必须建立明确供电引用，不能照搬名称查找。[诊断源码](samurai-front-identify.c)

## 两个失败与电源域修正

| 尝试 | 真实结果 | 退出后的状态 |
| --- | --- | --- |
| first | pin级pinctrl getter返回-ENOTSUPP(-524)；Qualcomm驱动仅实现group配置，ready0/ID0 | 未进入传感器上电，PMIC采样与GPIO恢复 |
| r2 | 改为group状态后两电源ready，但MCLK2报stuck off，返回-EBUSY(-16) | 电源/GPIO/PMIC恢复；新增一次WARN，内核taint变512 |
| r3 | 保持CCI父设备运行时PM引用后，result0、ID0x0471、ready2、restore0 | 采样/GPIO恢复，新增故障0；已有taint512保留 |

r2的实际调用栈在`clk_branch_toggle`，源于独立诊断消费者启动MCLK时TITAN_TOP_GDSC已关闭。r3在所有时钟读取/设频/启用之前`pm_runtime_resume_and_get(cci_parent)`，关钟并恢复原频率后再`pm_runtime_put_sync`。依赖已有CCI的标准genpd管理，不直接操作GDSC寄存器；接口语义见[内核运行时PM文档](https://docs.kernel.org/power/runtime_pm.html)。修复的是这个独立诊断流程；还不能据此断言已有正式IMX471 I2C驱动存在同样的缺陷。正式设备层次和PM关系仍需原生验证。

没有抹去r2告警、清taint或通过重启把它改成无故障结果。r3没有新增告警，结束仍为taint512。三个版本源/模块、原始日志和前后快照全部保留在私人归档中。

## 构建与检查范围

新增两个默认禁用的开发模块及Kconfig/Makefile入口。[完整补丁](samurai-camera-bringup.patch)、[最终源核对](source-final-validation.json) CCI模块SHA d3b4610d…；最终前摄模块c9856835…，源47ec57a2…。通过树内Kbuild正常生成模块元数据，没有手写intree标记、强制加载或掩盖taint。两个目标W=1告警0，vermagic及所有导入符号匹配当前kernel183。[CCI构建](cci-helper-build-validation.json)、[前摄构建](front-helper-build-validation.json)

原14个改动源码、Image/DTB保持；`.config`恢复原字节SHA55f1f0a3…，完整Module.symvers16793行/modules.order770恢复。首次构建自动添加“新选项未启用”注释，被不变检查检出并恢复；后续临时预置新选项n，退出后仍恢复原文件。前摄第一次编译的camcc头文件名称错误在加载前修正。完整组合补丁checkpatch无error/warning/check。

实际CCI init/exit函数在主机16个场景覆盖既有设备、属性/通知失败、回退和引用平衡。实际电源/下电及PM引用函数在49个场景覆盖每一步失败、错误/部分ID读取和7种撤销错误，ASan/UBSan通过；模型要求MCLK启用时电源域活跃。资源查找和pinmux创建没有被这49个测试全部仿真，三个原生尝试提供该部分证据。[CCI测试](cci-helper-host-validation.json)、[电源测试](front-sequence-host-validation.json)

## 最终状态与续作

前摄诊断模块、CCI changeset模块及原先未加载的i2c-qcom-cci均已正常卸载；CCI1恢复disabled、两个临时适配器和PMIC客户端移除。没有刷写分区或重启，也没有把诊断模块安装成启动项。[最终健康](native-health-validation.json)

11872.27秒仍为189第二个boot；MM191/PowerState3、GPS关闭、三个DSP running、SensorProxy加速度/亮度/接近均true。全boot保留warning1（本次r2时钟）和BT重组1；Oops/GPU fault/SLPI fatal均0。不能再用旧taint0收据描述当前启动。

下一步把已确认的前摄接入正式IMX471驱动：OF匹配、VIO/VANA/VDIG和选择GPIO、正确的PM父设备关系、CCI/DPHY2/CAMSS端点及真实取帧。主线现有驱动仅ACPI/vana，尚未修改或部署。Q的L5在本次条件下可达ready，仍不等于已确定四组PLDO的物理父供电，或冷启动地址/复位已通过。其余相机、GNSS有效fix、蜂窝业务和BT后段故障保持完整目标范围。

手机67份证据归档及每成员哈希通过：[归档收据](evidence-export-validation.json)。原始日志、身份与寄存器快照只保存在私人目录。完整goal active。
