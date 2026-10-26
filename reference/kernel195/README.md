# 阶段195：PM8008失败复位回退与前摄VIO精确OF引用

本轮补齐阶段194的地址迁移失败回退，并验证了一条无需重启的前摄供电引用方法：临时给现有、关闭的VIO节点建立phandle，标准`of_regulator_get()`能精确取得真实1.8V电源，撤销后原节点属性、regulator对象和电源状态均恢复。IMX471实体probe和取帧仍待完成；本轮没有启动传感器数据流。

## 地址迁移失败后保持自身复位

194的成功路径通过了真机验证，但代码审查发现：释放Q复位后，若身份读取、SID传输或新地址验证失败，旧函数会直接退出，可能将Q留在共享出厂地址8。后续若P释放复位，便可能产生地址冲突。这是代码与故障模型发现的缺陷，未声称在真机制造过地址冲突。

新增`release_attempted`状态；只有进入本次冷初始化的释放阶段后出错，才额外请求自身复位。第一次真实错误仍返回调用者；若复位回退也失败，则记录其错误，不覆盖主错误。地址已分配的warm路径、成功冷初始化、属性拒绝和兄弟地址已占用时保持自身复位的行为保留。[增量补丁](pm8008-error-reset-recovery.patch)、[完整MFD补丁](pm8008-initial-address.patch)

实际C helper的37个ASan/UBSan场景通过。新增检查不仅看返回码，还检查每个释放后失败的最终复位状态；另有两个用例验证复位回退自身失败时的日志和主错误保持。**旧194实际函数无法通过这个加强后的回归检查**，原SIGABRT断言日志保留。[主机验证](pmic-address-host-validation.json)

GPIO方向设置本身失败时，软件只能记录/返回失败，不能保证物理复位已成功；本轮没有把模拟中的可恢复错误扩大成全部硬件失败均能恢复。普通成功路径又用新MFD模块在真机分别复测：Q复位状态8→4、Q已在4时直接probe，均完成七路LDO注册，七路采样前中后相同，P保持物理低、Q恢复高，临时节点/模块全部移除。[原生验证](pmic-native-validation.json)

## 现有VIO节点的可撤销OF引用

当前运行DT中`/soc@0/rsc@18200000/regulators-1/ldo1`没有phandle，同时另一PMIC也有名为ldo1的输出。193诊断通过查找后校验1.8V识别了目标；正式sensor驱动应使用明确的OF supply引用。完整DT候选在编译时可建立引用，本轮验证的是当前运行系统内的开发接入方法。

默认禁用的`samurai-vio-phandle`开发模块，仅接受没有子节点、没有compatible及原phandle的已知VIO叶节点。用标准OF changeset执行detach、添加新phandle、reattach，使OF缓存也能识别；随后临时创建一个vif-supply消费者，通过标准`of_regulator_get()`核对电压1.8V且供电关闭。没有启用regulator或调用设压接口。[源码](samurai-vio-phandle.c)

真机当前最大phandle300，模块分配301，精确OF查找成功；标准regulator句柄在模块init中释放。加载前、加载后、卸载后的state disabled、microvolts1800000、num_users0一致。卸载后目标节点所有原属性逐字恢复，临时消费者消失，原regulator对象路径保持，没有重绑其RPMH provider。[原生收据](vio-native-validation.json)

这是开发用changeset模块，后续可与CCI/前摄资源fixture组合，以验证真正的IMX471 OF probe；正常启动仍应使用编译后的板级DT。没有把新增phandle留在当前运行树中，也没有直接改OF私有缓存或硬件寄存器。

## 同平台仓库与运行时PM方向

找到[OnePlus 7T Pro公开适配仓库](https://github.com/Sr-0w/hotdog-linux-bringup)，固定到`47087509c4289c2580c54f5433e55366b2e00445`，以无checkout的只读克隆提取代码。该项目[前摄记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-10-mainline616-camera-imx471-popup.md)报告了同SM8150平台IMX471、MCLK2、DPHY2与libcamera取帧；这属于对方设备的证据，不是本机验收。

其[IMX471补丁](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0102-media-add-OnePlus-hotdog-IMX471-front-camera.patch)含1748×1748 RAW10、525262500Hz链路及明确分步供电；可用于后续模式/时序比较。Hotdog使用PM8009、BOB和外部VANA gate、CCI1 master0及弹出机构；本机已验证的是PM8008 Q、2.8V VANA、CCI1 master1，没有复制这些板级资源或动作。对方CAMNOC/带宽/桥接时钟和失败stream撤销补丁也已固定保存用于比较；先与本机126已通过的真实TPG/DMA路径核对，再决定缺少哪些通用改动。[来源及哈希](hotdog-reference-validation.json)

另核对了[移除CCI sensor重复power-domains的主线评审](https://marc.info/?l=devicetree&m=165954133922137&w=4)：CCI父设备已描述TITAN域，sensor按正常层次管理。当前I2C core会在driver probe前处理时钟默认值和PM域；本机下一步需要实测正常I2C子设备层次的probe/resume。193独立诊断的外部PM引用仍仅证明该诊断所需条件，不能据此宣称标准IMX471驱动也有同一缺陷。

## 构建、失败保留与最终现场

MFD源057ccd62…，模块d1ff82c0…；VIO helper源868c9b2a…，模块9e83668e…。两者树内Kbuild、vermagic、全部导入符号和intree元数据核对通过，最终目标W=1无诊断。[MFD构建](pmic-module-build-validation.json)、[VIO构建](vio-helper-build-validation.json)

最初MFD格式检查因一行102列停止，加载前已缩短日志文本。VIO第一次编译缺少OF内部常量头文件，第二次modpost发现allnodes迭代器未导出；改用已导出的property迭代接口后构建通过。两个失败源码/日志均在私人目录，没有强制加载或补写intree标记。

原14个改动源、194 IMX471与绑定保持；当前仍19个tracked改动，相机新文件共5个。Image183、canonical DTB172及config字节保持，Module.symvers16793行/modules.order770恢复。[当前源码及开发代码补丁](source-final-validation.json)；未部署新启动DTB或替换安装模块。

16368.69秒仍为189第二个boot：taint512、WARN1为193时钟旧事件，BT重组1为189旧事件，Oops/GPU/SLPI fatal0。ADSP/SLPI/modem running，SensorProxy加速度/亮度/接近Has true，MM191/PowerState3、GPS关闭。S8C1.352V/用户3、VIO1.8V关闭/用户0、另一ldo1 0.752V/用户1保持；本轮临时模块、CCI/PMIC/消费者节点已撤销。[最终健康](native-health-validation.json)

手机37份证据归档10c5f4aa…已下载并逐成员验证；原始身份/日志/外部参考原文保留私人目录。[归档收据](evidence-export-validation.json)

下一步：组合精确VIO引用、Q LDO约束、pinctrl和CCI资源，让普通IMX471驱动执行实体probe及运行时PM，然后验证CAMSS真实取帧。四路PLDO输入、P/Q完整冷启动、其它镜头、GNSS有效fix、蜂窝业务、BT后段重组及传感器完整验收仍属active goal。
