# 397：逐帧 CCM 参数归入驱动请求，固定矩阵已作用于硬件像素

**398更正：复用396的数值oracle选错分支；实际IPE偏移为11位，已在[398候选](../kernel398/README.md)修正。本轮零偏移固定矩阵的硬件观察仍有效，不能外推为负偏移验收。原始过程保留。**

在396原厂编码与路由证据基础上，新增类型化逐帧CC接口，将IQ、程序数组和固定寄存器命令放进现有请求的同一个IQ页，沿用原DMA保留与复位回收。临时实机验证四个固定模式通过：单位矩阵全帧等于旁路，零矩阵全帧归零，半幅矩阵亮度精确减半。[像素证据](pixels-validation.json)。随后恢复正式395核心／393 adapter，四摄各12帧、共48direct回归通过。**候选未永久安装，完整IQ和多摄校准仍active。**

## 分层及接口

继续复用既有仓库与[396原厂HAL／固件来源](../kernel396/primary-sources.json)，没有重读vendor、NV、OTP或个体校准。SoC核心增加`camss_a5_ipe_run_colour_status`，输入为量化RGB行主序矩阵、整数偏移和Q因子；旧job／frame／session布局与旧接口保持。旧调用传入NULL，仍走原旁路。

[补丁](per-frame-colour.patch)在锁内复制并验证参数，发生任何固件MAP前拒绝非法矩阵。固件仍只收到驱动生成的固定9寄存器命令，用户不能传入任意CDM、寄存器地址或外部IQ指针。原未知完成分类、释放、强制复位和stop函数体保持。

原IQ2584字节，32字节对齐后的2592偏移放共同空程序数组；2624偏移为单项post-LTM数组，2656偏移为44字节命令，总2700字节。仍位于原本已分配、映射并保留的4096字节IQ页内；没有新增独立DMA分配或生命周期。帧头40填数组基址、48填post相对偏移32，沿用原厂分发器重定位流程。板级DT、SID／IOVA域、主线媒体框架、传感器和产品用户空间均未改。

本轮没有建立标准V4L2请求参数或libcamera矩阵接口。硬件测试通过[临时编译宏适配器](temporary-colour-adapter.patch)从私有路径加载：仅有0旁路、1单位、2零、3半幅四种固定选择，正常adapter不含开关；核心本身与正常候选构建逐字节相同。不是把临时模块参数作为产品调校接口。

## 软件与固件验证

[39个实际传输／DMA函数用例](transfer-validation.json)ASan／UBSan通过，覆盖旧接口和新CC接口、指针夹具／DMA-BUF、MAP／FRAME／UNMAP未知完成引用保留、清理失败及非法CC在分配／MAP前局部拒绝。额外CC数据与整个request一并保持，不绕过393局部拒绝和395强制复位保证。没有重新注入395已验证的相同ACK丢失故障，也不宣称CC路径的每种物理错误均已上机覆盖。

[完整参数区域检查](parcel-validation.json)使用实际CC编码与原旁路IQ函数，复用396的1121组真实HAL命令，每组比对全部2700字节，共3026700字节零差；2730个非法输入／短缓冲／未对齐和溢出IOVA用例不写目的缓冲。主机ASan／UBSan与实际交叉编译后的QEMU AArch64均通过。[原固件消费](firmware-parcel-validation.json)在三尺寸、两端口、两核心共12组中接受实际C函数生成的同页区域，并链接post-LTM程序一次；停在硬件enqueue之前，软件证据与下述硬件像素证据分开。

正常核心ARM64 in-tree W=1/-Werror构建通过，370160字节，SHA2a2aa6b57050cd4fda82fa849bff6924061b6b3600287a0541c3664846f254e6。[正常构建](intree-build-validation.json)、[临时适配器构建](test-intree-build-validation.json)。临时adapter122160字节，SHAa56989f098212ccca4ba084b5c6aee80d8ec04970aee431660bb3cbc030d0e01。标准媒体／SG帮助模块只用于链接符号核对，未安装；与393已有产物摘要相同。

[前两次构建失败](build-attempts-validation.json)保留：第一次没有把配套媒体／SG帮助模块列入目标，modpost报未解析符号；第二次准备尚未终态就过早启动，仍使用旧列表。检查准备终态和生成脚本后，第三次完整目标构建通过，诊断0。没有为消除错误修改驱动、忽略modpost或将失败记录改成成功。

维护源source354，branch samurai-ipe-frame-colour397，commit6a6451dd1fa14534e5c805d8ca8e9a588b42016d，父39646fdb7c9；正常源干净，临时adapter源与共享构建配置／输出恢复。构建已终态，不重启旧handle。

## 实机像素与颜色域边界

一次事务`k397-colour-r1`／worker10439。停止桌面相机消费者并等owner0后，临时加载候选核心和固定模式adapter，正常静态ICP设备及CAMSS模块保持所有权。正式磁盘模块、固件、板级及个体配置没有替换。

四个模式均使用相同640×480 NV12合成输入，各自完成一帧，保留输入／输出私有文件，独立重算CRC与客户端一致。时间戳／序号、输入未改、输出尾部canary、完整完成及资源回收通过。原生epoch jobs/completed/direct4、starts/stops4，failed/cancel/first_error0，图像通路没有核心CPU复制。

|模式|实测|
|---|---|
|旁路|307200个Y字节与生成输入一致；UV保留既有滤波／舍入行为|
|单位矩阵|460800个输出字节全部等于旁路|
|零矩阵|460800个Y／UV字节全部为0|
|半幅单位矩阵|307200个Y字节精确等于输入的一半；UV相对于旁路逐字节向下除2有5280字节高1，其余相同|

这证明CC模块开关、程序数组、外部固定CDM以及逐帧请求已实际影响硬件像素，而非只收到固件成功ACK。UV差异原因尚未单独隔离，不宣称一般舍入、饱和或滤波公式。非对角元素、负偏移、所有模式和性能仍需独立实测。

**还不能直接应用原厂RGB调校矩阵。**当前输入输出是NV12，测试只启用CC，原先旁路配置中的前后颜色转换仍关闭。零矩阵连UV也归零、半幅矩阵改变UV，是当前像素通路的观察，不证明CC所在处理域已经建立为正确RGB。下一步必须从原HAL核实pre-LTM color transform与post-LTM chroma enhancement等转换及其范围／顺序，再验证组合后的RGB矩阵语义；不能把原厂前摄CCM直接乘到当前Y／UV通路，或通过CPU变换掩盖此差异。

## 恢复、当前状态及接续

[事务结果](runtime-validation.json)passed且全部进程终态。原生四帧后卸载临时模块，从原磁盘恢复正式core395／adapter393；默认r30四摄各12帧、48direct，额外完成0、starts/stops4，错误／取消0，fixture恢复，无私有库／调校覆盖。原生4与恢复48来自不同module epoch，不跨epoch混计；实验前正常48也单独保留。

collector10536在原生首帧前就绪，最终无新dump／timeout。没有新相关内核故障或重启；同一394guard。最终[只读核对](current-state-validation.json)：正式磁盘／加载note与四私有配置匹配，两个测试参数不存在，CPU／IRQ／PM／backing／映射／导入全释放，ICP／CAMSS／双CCI suspended，17时钟0、九路电源disabled/users0、taint0。PW10681／WP10684各一uid10000；worker／client／collector无活动实例。

Image363、boot389／DT389、SG owner API、原FW及r30/r25保持；本轮没有刷写、重启或永久安装，395／393和前序回退副本仍保持。当前host397委托396／395／394，guard仍`/var/lib/samurai/k394-recovered/boot-id-private.txt`，原USB密钥／known_hosts不变。source／build访问先storage284.mounted_build()，保护既有ext4 backing。

接续先核实颜色域转换与实际通道、非对角／偏移效果，再把类型化参数接到标准媒体请求及libcamera、351原厂触发树。完整Gamma／LTM／CCM组合和[363全部范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续：第五2MP、多模式、动态帧长／防频闪、几何／多摄同步、连续AF及光学画质。默认产品仍1:1 NV12/NV21 IQ旁路。关灯黑场／噪点按低照度解释，照明相关校准后做；SSC／旋转未全面重验，不宣称旧间歇故障修复。

FW／HAL／原厂源／ASM／CDM／完整日志／图像／个体表只留private397及前序；公开镜像仅本地提交，保留其它改动，不push／PR。
