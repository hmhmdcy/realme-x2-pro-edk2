# 422：原厂 LTM 标量、LA／mask 与完整类型化帧组装

继续用户要求的原厂调校复用和自动TMC／LTM接入。新增两个公共数值接口，复用352／403逆Gamma、407强度／衰减、408时域、409 ADRC、412 TMC11采样和413生成结果。**目前是已核对的数值及2800字节类型化帧组装，不是自动实机链路完成；本检查点尚未访问手机或安装候选。** 正式系统继续421最后验证的419生产驱动及r31/r26。

`prepareLtm13Static()`接受已选reserve和已插值LA，输出RGB2Y、亮度比、权重、mask核与归一化、LA／mask表。原厂系数不嵌入公共代码。[静态对照](static-validation.json)：6份所选模式去重叶输入，加24组边界及7项非法输入；主机ASan／UBSan和ARM64各23680字节零差。实际原HAL标量、权重、unsigned pack片段共60150指令，只替代30次memcpy。DC/IP两布尔字段不冒充完整多pass状态证明。

目标对mask第六项归一化贡献固定加4，包括输出指数为0的边界；公共参考C++含负数移位未定义行为，不能直接逐式翻译。新实现以实际ARM64结果为准，并用无符号移位明确其它零指数行为。

`prepareLtm13Frame()`组合强度→平滑→保存候选历史→衰减→TMC11归一化/PCHIP/对比度→ADRC→打包，输出与既有内核payload同尺寸的2800字节类型化字段及13组LUT。输入包括真实IFE green节点和forward节点，TMC结果及对应axis由调用方显式给出；没有自行伪造DRC／HDR／未知AEC字段。无ADRC明确走非ADRC分支；输出与下一份历史均在全部成功后才写出，历史保留衰减和ADRC之前的值。

[组合对照](frame-validation.json)：四个供应商物理变体各有/无ADRC，共8组，加5项非法输入；主机ASan／UBSan和ARM64各41704字节零差。核对原厂temporal、逆Gamma、TMC11采样及ADRC片段，并复用413已保存的生成结果，没有重跑全部算法矩阵。各变体共用保存的主摄forward表只是数值夹具，**不声称完成各模式的forward绑定**。前摄原厂TMC关闭；有ADRC前摄用例只是显式算法夹具，不能用于启用前摄默认TMC。

组合检查最初给旧16段packer发送短记录，旧工具按固定268字节输入协议未产生输出；在候选构建前断言退出。[首次失败](frame-check-r1-failure.json)保留。改正记录尺寸并选16段packer后通过，没有设备影响。

[内核载荷检查](kernel-payload-validation.json)使用当前维护树实际colour编码器及6008字节media-request验证器，8份类型化帧全部接受；每份92字节IQ、2736字节LUT和尾部逐字节一致。第一次来源检查发现405旧文件不等于当前文件，在执行编码器前退出：[保留失败](kernel-payload-r1-failure.json)。差异是后加的逐帧验证器及includes；最终重新编译实际当前源和UAPI，没有沿用旧共享对象冒充当前实现。

[数值历史策略](numeric-history-validation.json)另有12个ASan／UBSan场景：每摄像头最多一份未完成数学提案，显式绑定epoch、SOF、token和基础版本；失败不更新状态，其它重叠观测不能替它提交，停流／旧epoch拒绝。该策略目前是通用组件，尚未接入IPA回调。

[候选源码](candidate-source-state.json)已加入`libcamera422-tmc-ltm`公共libipa及独立数值历史头，24文件[补丁](0043-camss-tmc-ltm-numeric-assembly.patch)零fuzz复现；[真实SDK构建](build-validation.json)成功。**新增数学对象还未被IPA调用，静态链接剔除了未引用对象，库／IPA／代理字节与421完全相同**；不把“公共数学库构建通过”写成“IPA已经自动调参”。配套签名证据按相同字节复用421，没有重拍未改变的运行路径。

[设备只读检查](device-read-validation.json)确认guard394保持、239作业仍全完成／失败取消0，四设备suspended，历史taint512保留。本轮没有新硬件帧或服务／软件切换，不宣称新增相关故障增量或完整资源回归。

下一步仍需把选根／触发树、TMC生命周期、实际统计与传递域接到候选IPA及同帧media request，再进行非零参数实拍。不得把单曝光观测直接伪装成原厂双槽HDR／DRC或408未定名字段。前摄普通根的TMC10／11关闭，应保留，不能照搬主摄启用策略。还需核实局部数据收集／IP实际依赖，不能以DC位已设置代替粗级统计验收。421统计发布重入修复及真实观测/回执候选继续保留。

SoC驱动、板级DT、主线框架、传感器、固件、正式用户空间及个体校准未修改。原表、目标汇编、原始输入输出仅存`/mnt/e/edk2-samurai-out/kernel422`及前序；公共代码只包含通用实现和脱敏结果。
