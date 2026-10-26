**402更正：401夹具把Gamma源缓冲设为CDMDMI32（type3），错误选中opcode10。实际原厂初始化为CDMDMI（type1），应使用opcode1；修正后Gamma实像素通过。[402证据](../kernel402/README.md)。下文保留401当时结果与范围。**

# 401：原厂 Gamma DMI 契约与 LUT 请求所有权已接入候选

本机原厂HAL的Gamma开关、三通道DMI、地址重定位记录与程序描述符已核实；候选核心新增类型化Gamma接口，将完整LUT放入现有请求中保留。参数页、生命周期、完整原厂固件准备和内核构建通过。**401没有访问手机或安装，新增Gamma和修正后的程序标签仍待实机验证。完整ISP／多摄目标继续。**

## 原厂契约与一次标签纠正

复用保留的HAL／固件、350完整Gamma提取与[固定CamxChi源](primary-sources.json)，没有重新读取固件分区或NV／OTP。[契约检查](contract-validation.json)直接执行原Gamma模块片段、完整`PacketBuilder::WriteDMI`及完整`AddNestedCmdBufferInfo`。仅命令存储的Begin／Commit和设备地址最终物化由模型提供，数值和命令编码不替换。

本机Gamma IQ开关为2192，固件映射0x6060。三条间接DMI命令各12字节：opcode10、地址寄存器0x6008、selector1／2／3，每通道1024字节。原HAL的三个实际嵌套记录分别指向源缓冲0／1024／2048偏移；驱动将它们编码为同请求LUT的可信IOVA。通道顺序沿用350已恢复的G／B／R。97组原数值曲线共99328字节再次与原HAL数值片段一致。

原提交器片段明确：**普通寄存器程序类型20，Gamma类型12，skip类型255**，Gamma描述符长度36字节。此前候选把0当作generic标签，这个命名／标签结论撤回；401修正独立CC和转换链的普通描述符为20。400实际像素结果保留，但不等同于修正标签后的401实机验证。

原命令生成器还区分间接DMI opcode10与仅供软件命令处理器的inline opcode76；本实现使用原厂间接格式，没有将软件inline包直接交给硬件。

## 类型化接口及所有权

[补丁](gamma-ownership.patch)新增 `camss_a5_ipe_run_gamma_status`。输入Gamma为三组256项base10／signed-delta10，分别限制0…1023与−512…511；不接受任意CDM、寄存器或设备地址。原浮点曲线量化继续复用350的通用算法，内核只处理有界整数值。

核心在锁内先将3072字节Gamma输入复制到临时CPU堆内存，校验后才分配coherent请求或MAP，避免把3KiB对象放在内核栈上。编码后固件只引用request中的副本；所有出口释放临时CPU副本，未知完成时整个DMA请求继续保留，包括LUT。没有新增独立coherent缓冲或LUT映射。

Gamma IQ区域6016字节，原IQ页分配由4096增至8192，仍属于同一request parcel：2592为空数组，2624为pre，2656为最多三项post；2752／2808／2852分别为CST／CC／CV固定命令，2896处36字节DMI头，2944处3072字节LUT。普通命令只移动32字节，为第三项post描述符留空间；没有移动图像数据。Gamma程序在普通post程序之后，类型固定12。

旧job／frame／colour结构及接口布局保持，Gamma为NULL时保留旧颜色／旁路行为。free、unknown-completion、quiesce、stop和强制复位函数体保持。板级DT、传感器、主线媒体框架及产品用户空间未改；这是内核内部接口，尚未建立标准媒体请求Gamma参数节点。

## 验证

[完整参数页](parcel-validation.json)由实际C编码函数生成，主机ASan／UBSan和AArch64 QEMU分别通过1121组独立CC、2232组转换链及97组三通道Gamma，共3450组／9993772字节零差。旧区域只按实际提交器修正普通类型20；Gamma期望包使用原HAL DMI和真实嵌套重定位记录，完整6016字节比较。新增6040个非法值／短缓冲／未对齐和溢出IOVA用例不写输出，NULL颜色配置和32位地址上边界通过。

[85个生命周期用例](transfer-validation.json)执行实际核心／DMA函数，涵盖旧接口、转换链与Gamma，以及CPU复制失败、非法LUT在coherent分配前拒绝、未知MAP／FRAME／UNMAP与清理失败保留。模型在复制后故意覆盖调用方输入，仍得到复制时的LUT，且CPU副本没有泄漏；这不替代后续物理故障验证。

[原厂固件消费](firmware-parcel-validation.json)执行完整CONFIG_IO和帧准备：三尺寸、两端口、两核心共12个组合，外加其余七种颜色模块掩码，Gamma均开启。实际C区域被接受，pre／post各链接一次；生产C条带与完整原厂条带产生的整512KiB命令缓冲和32字节job在19组中全部一致。停在硬件enqueue前，范围限定当前1:1 NV12；Gamma实像素和NV21组合未验收。

[构建](intree-build-validation.json)W=1／Werror成功、诊断0。正常核心388520字节，SHA `862c79c94424ba4dedc1936f1394aa9aa992c6f613452e6fe4a1fc3f20eb6f7b`。源码分支 `samurai-ipe-gamma401`，commit `b8ce3ce92745a11b039e1335e87bbb2dd783c2c7`，父399 `de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7`，仅四文件，干净未部署。[源码状态](source-state.json)。共享构建配置、输出和符号表已恢复。

首个Gamma模块夹具把命令数组指针写在2592，实际字段为2600，断言失败；修正夹具后通过。原脚本及失败说明私存401，没有修改HAL指令来绕过问题。

## IFE／IPE分工与接续

[r30调用路径审查](ife-role-audit.json)确认，现有IPA可通过标准IFE参数块发送CCM和IFE64段Gamma；当前IPE用户空间只排队图像缓冲，未携带新类型化颜色／Gamma参数。代码中存在这些路径不等于当前各配置一定启用，401没有把源码支持外推成设备运行开关已核对。

接产品前需明确IFE输入传递函数、CCM处理位置及LTM所需父级Gamma／inverse-Gamma关系，避免重复校正或盲目关闭IFE压扩。不能把IFE64段与IPE256段接口混用，也不能只将两条Gamma直接复合。

下一步临时实机验证类型20修正及Gamma：转换对内先单位／零／半幅或分通道诊断LUT，再原厂曲线，检查实际像素、通道与复位后重载；随后补LTM及完整调校组合，接标准媒体请求／libcamera和原厂触发树。最后设备证据仍为[400恢复核对](../kernel400/current-state-validation.json)：正式395／393、四摄48direct与资源释放。本轮只复用该历史证据，不称作401新复验。

[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续：第五2MP／mux、多模式、帧长／防频闪、几何／多摄同步、连续AF及光学。用户已开灯，现场样本按实际条件判断。source／build先storage284挂原ext4；原厂表、ASM、日志和图像仍私有，公共镜像仅本地提交，保护旧回退副本。
