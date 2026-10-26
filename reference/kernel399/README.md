# 399：恢复原厂 CST／CV 模式树，接入内核逐帧转换链

**401更正：原HAL提交器证明普通程序类型为20，Gamma为12；本轮0作为generic标签的结论撤回，候选已在[401](../kernel401/README.md)修正。原始模型和400实际像素观察保留，不冒充修正标签后的实机证据。**

原厂转换参数已完成独立二进制读取、原厂XML读取器核对和模式绑定；候选核心新增类型化CST／CC／CV逐帧接口，参数、程序数组及命令均由驱动生成并放在原有IQ页内。实际C编码、DMA生命周期、原厂固件完整帧准备及核心构建均通过。**399未访问手机、未安装；正确RGB域和完整转换组合尚待实机像素验证，多摄／ISP目标继续。**

## 原厂数据与实际字段顺序

复用保留的五份原厂调校文件，以及固定CamxChi提交中的[两份schema](primary-sources.json)。没有重新下载固件、重读NV／OTP或覆盖校准。共恢复17个CST根、71个CV根与1350个CV叶节点；完整树、触发器、enable与reserve均与原厂XML读取器一致。[解码验证](factory-conversion-validation.json)。所有原厂数值、XML与中间文件仍私有。

现有七个物理模式的Preview／Video共14上下文、28次模块选择，与原厂选择管理器一致。[模式绑定](mode-conversion-validation.json)。所选CST包含非单位变换和减偏移，CV包含色度常量偏移及不对称系数；enable来自调校文件，不能等同于已观察到Android运行时开关或已选定运行时叶节点。

本机HAL的真实反序列化器再次解决了字段命名差异：[1350个原厂叶及一个逐字段不同值用例](native-leaf-validation.json)从8字节序列化槽读取，紧凑写入4字节native浮点槽，无字段重排。CV实际native顺序为r_to_y、g_to_y、b_to_y、y_offset、ap、am、bp、bm、cp、cm、dp、dm、kcr、kcb。实际寄存器低槽对应ap／bp／cp／dp，高槽对应am／bm／cm／dm，末两字按KCB／KCR输出。

因此398根据新版寄存器头推测的am/ap语义标签撤回；398按位置比对的数值结果保持。399参数和oracle使用本机反序列化器证明的顺序，不能按新版寄存器字段名交换原厂不对称参数。

## 驱动实现及分层

[补丁](conversion-chain.patch)新增 `camss_a5_ipe_run_colour_chain_status`。类型化输入为模块位掩码、CST Q10系数／减偏移／加偏移／钳位、原CC量化矩阵，以及CV Q8亮度／色度系数和偏移。锁内复制并检查启用模块，分配和任何固件MAP前拒绝非法范围；禁用模块的数据不参与编码。未知模块位、无效钳位顺序、短缓冲、未对齐或溢出IOVA均拒绝。

输入不包含任意CDM、寄存器地址或用户提供的IQ指针。CST固定0x5a68／12字、CC固定0x5e68／9字、CV固定0x6468／8字；开关IQ偏移分别2092、2188、2200。pre-LTM数组只含CST，post-LTM按CC、CV排列。

新IQ区域2860字节：2592共同空数组、2624单项pre数组、2656双项post数组；2720处56字节CST命令、2776处44字节CC命令、2820处40字节CV命令。仍在原4096字节IQ页内，不新增独立DMA分配或释放路径。帧头40为数组基址，44／48为相对偏移32／64，沿用原固件重定位流程。

旧job／frame布局、旁路接口及独立CC接口保持。原free、unknown completion、quiesce、stop与强制复位函数体保持；新增数据随同request映射和保留。板级DT、SID／IOVA域、传感器、主线媒体框架和产品用户空间本轮未改；这仍是内核内部同步接口，尚未建立稳定V4L2媒体请求／libcamera调校接口。

## 验证范围

[完整参数页](parcel-validation.json)使用实际C函数，比对原厂17组CST、737个CC叶、1350个CV叶及128个模块组合／随机边界用例，共2232组／6383520字节零差。CST／CC执行完整本机HAL计算，CV执行本机内联OEM计算片段，三类命令均由完整原厂CDM函数生成；未替换数值或包编码算法。主机ASan／UBSan与实际交叉编译后的QEMU AArch64通过，各2956个非法输入无目的缓冲写入。

[64个传输／生命周期用例](transfer-validation.json)执行实际核心和DMA函数，覆盖旧旁路、独立CC及新转换链，含成功、MAP／FRAME／UNMAP未知完成引用保留、清理失败、参数局部拒绝及分配前拒绝。没有新物理故障注入，不把软件模型外推成所有硬件错误覆盖。

[原厂固件消费与原生条带检查](firmware-parcel-validation.json)覆盖三尺寸、两端口、两核心共12种全模块组合，以及640×480下其余七种模块掩码。实际C参数页交给完整原厂CONFIG_IO与帧准备，pre／post各链接一次。当前生产C条带编码与完整原厂条带算法，在启用转换时仍产生逐字节一致的完整512KiB命令缓冲和32字节job，19组全部零差。停在硬件enqueue前，限定当前1:1线性NV12范围；不宣称NV21转换组合、新缩放或实际像素已经验收。

[正常核心构建](intree-build-validation.json)W=1／Werror成功、诊断0，380760字节，SHA `6927c4c34d40871f420e29dda2f04b0a1722a3ce76007588304243e6f01256ba`。源码branch `samurai-ipe-conversions399`、commit `de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7`，父398 `8b1e8903a550ffc20a2d8f1de574c37f2260fff3`，仅四文件，干净、未部署。[源码状态](source-state.json)。共享构建配置、输出与符号表恢复。

## 下一步与实际部署

下一步临时固定参数实机验证：先CST／CV转换对，再插入单位／零／半幅／非对角和有符号偏移CC，通过合成颜色块核对通道、范围、饱和与舍入，建立真实RGB域。不能仅用成功ACK或近似恒等输出代替像素语义验证。之后接标准媒体请求与libcamera、原厂触发树、Gamma／LTM组合及正常照明画质；所选原厂树不代表已执行原厂完整插值或自动调校。

399没有手机访问、拍摄、模块加载、重启、刷写或永久安装。最后设备证据仍为[397恢复核对](../kernel397/current-state-validation.json)：正式core395／adapter393／CAMSS389、四摄48direct成功及资源释放。这里只复用历史证据，不称作399新复验。Image363／DT389／原固件／r30-r25与回退副本保持。

完整[363剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续：第五2MP／mux、多模式、帧长／防频闪、几何／多摄同步、连续AF与光学。用户现已开灯出门，现场样本重新核实照明与曝光，不默认仍是暗场。访问源码和build先storage284.mounted_build()，原ext4不可重建；私有材料及密钥不公开，公共镜像仅本地提交。
