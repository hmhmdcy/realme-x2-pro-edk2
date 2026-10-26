# 396：恢复 IPE CCM 的实际命令编码和固件路由，形成内核候选

**398更正：本轮数值oracle使用type 1，实际IPE调用者使用type 2。下文13位偏移作为IPE契约的结论撤回；[398](../kernel398/README.md)已修正候选为11位并重新验证。原始过程保留。**

完整IQ适配继续推进。本轮把后级CCM从“已提取调校树”推进到可用的受限内核编码器，并以本机原HAL／固件验证计算、打包和帧路由。[1121组对照](colour-validation.json)、[AArch64执行](colour-arm64-validation.json)、[12组固件准备](routing-validation.json)及[内核构建](intree-build-validation.json)通过。**候选尚未接入逐帧运行接口或安装，CCM硬件像素效果尚未验证；完整Gamma／LTM／CCM与多摄校准仍未完成。**

## 现有方案、原厂文件与分层

优先复用351已由本机原厂调校BIN恢复的43个CCM根／737个区域，以及281保留HAL、352固件和350迷你调试符号。没有重读手机vendor、校准分区或个体EEPROM。

补充搜索取得维护者[公共CAMSS参数RFC](https://www.spinics.net/lists/kernel/msg6171146.html)及[OPE接口讨论](https://patchew.org/linux/20260915-camss-isp-ope-v7-0-77b13d131d3d%40oss.qualcomm.com/20260915-camss-isp-ope-v7-4-77b13d131d3d%40oss.qualcomm.com/)，可参考公共参数表示与硬件后端分离。它们属于接口讨论，不能作为SM8150原厂HFI布局或完整可用驱动的证明。

[固定CamxChi来源](primary-sources.json)用于理解模块、寄存器顺序与post-LTM位置；实际目标布局由本机HAL和固件原指令确认。四份CC13源从既有固定本地仓库读取；IPENode文件与350保留版本逐字节相同，本轮又从同一固定仓库读取了一份，没有重新克隆全库。原厂源／反汇编只私存，公开目录只有自有代码、检查程序及摘要。

SoC候选只新增内部[编码器C](colour-codec.c)、[头文件](colour-codec.h)和核心Makefile条目。[源补丁](colour-codec.patch)不改现有帧／adapter ABI，不新增运行调用者、不开放任意用户CDM输入。板级DT、主线媒体框架、传感器驱动和已安装用户空间均保持。

## 原HAL计算与编码对照

完整执行目标`IQInterface::CC13CalculateSetting`的OEM已插值区域输入路径。没有用数值桩替代量化或打包，也没有据此宣称执行了调校插值树、完整IPE Execute或Android覆盖逻辑。然后完整执行目标`PacketBuilder::WriteRegRange`；只将CmdBuffer Begin／Commit的存储分配提供为模型，包头、寄存器地址和全部载荷由原指令产生。

原厂737区域分布为：Qtech长焦5、Qtech主摄36、Sunny广角9、Sunny前摄597、Sunny主摄90。另384组覆盖四种Q因子、独立矩阵元素、独立偏移、符号／端点、半整数舍入和固定种子的合成数据。共49324字节命令与自有编码器完全相同，执行246620条原HAL指令。个体表和实际数值只私存。

确认矩阵为有符号12位，量化Q(7+shift)，shift为2位；IPE偏移为有符号13位。RGB行主序输入转为寄存器的GBR行列顺序，不能将IFE偏移位宽或其打包布局直接套用。输出是固定9寄存器／44字节CDM连续写，从0x5e68开始；没有接受任意寄存器地址、CDM指令或外来包。

72个非法输入用例检查空指针、短输出、非法Q因子及每个矩阵／偏移越界，均返回错误且不修改目的缓冲。超长输出尾部不变。主机ASan／UBSan通过；同一C源静态交叉编译后在QEMU AArch64执行，1121组及72个拒绝用例通过、输出与原HAL仍完全相同。QEMU执行不是硬件图像处理。

[首轮失败](colour-r1-validation.json)保留：293个合成用例不一致，原因是测试夹具把OEM结构的Q因子／enable输入偏移设置错误，原HAL始终读到shift0；全部原厂表shift0，因而原厂区域未暴露该错误。按原指令修正夹具后通过，C编码器没有为匹配错误夹具而改动。首轮输入／期望／实际二进制及模型源私存r1。

## 模块开关、程序数组及固件消费

[HAL／固件ABI检查](enable-abi-validation.json)执行实际IPE模块片段：enabled=false不生成CC命令，true向命令缓冲索引4生成上述44字节，并将模块开关写入IQ偏移2188。原厂固件片段从该偏移取bit0，写向0x5e60。覆盖0、1、2、3和全1值；它是bit0语义，不是任意非零归一化。完整HAL Execute与完整固件硬件引擎未在此检查执行。

进一步执行原厂完整striping创建／执行／销毁和完整固件CONFIG_IO／帧准备，覆盖640×480、1920×1080、4608×3456，端口8／9、核心配置1／2共12组。CC启用与关闭时条带字节及BL容量一致；固件准备的CC开关寄存器为1，外部post-LTM数组被链接一次，44字节命令保持完整。

实际目标帧头偏移40是程序数组基址、48是post-LTM数组相对偏移；数组头8字节，每项24字节。generic类型为0，命令地址／长度字段的高word按`(bytes - 1) << 12`编码。完整原固件分发器还验证了数组cache处理、十个头部偏移重定位，并在重定位后清零基址。帧准备模型使用这一实际重定位结果，不能把较新IPENode的扩展字段布局直接套来。

[调试失败记录](routing-attempt-validation.json)保留了两个模型问题：最初数组地址超出旧夹具映射窗口；随后校验误以为重定位后基址仍保留。均修正模型／校验，没有修改目标固件或放宽硬件错误要求。

模型只提供OS分配／cache／日志／stream查询／命令回收设施；几何、寄存器准备和数组链接执行原指令。执行停在硬件驱动enqueue入口之前，外部CDM是否最终被硬件执行、CCM像素域和量化效果、异步fence及真实缓冲生命周期仍要独立上机验证。未将软件链接数组或固件准备成功当成图像处理完成。

## 候选和当前设备

维护源source354，branch samurai-ipe-colour396，commit46fdb7c96b04825dc1802f8280685a4c4e709615，干净，父为正式395源3a793050。只改Makefile与两个新文件，现有core／帧／adapter实现保持。ARM64 in-tree W=1/-Werror诊断0，模块360096字节，SHA6652bbbc410d3d9c9e8b7a767608a67c6580c664ebb9d3de632e1af950a36c25；符号表确认包含实际编码器。共享构建输出／配置／symvers恢复，构建已终态。

[只读现状](current-state-validation.json)：同一394guard，手机仍正式core395／adapter393／CAMSS389，磁盘和加载note匹配，无测试参数；本轮没有安装、采集、刷写、重启或运行设备worker。计数保持48direct、错误／取消0，CPU／IRQ／PM／映射／导入已释放，ICP／CAMSS／双CCI suspended，taint0。Image363、DT389、FW、r30/r25和个体Preview配置沿用395部署；未重复无关全量检查或宣称SSC／旋转修复。

访问source／build先调用storage284.mounted_build()，保护既有ext4 backing。候选未安装，原395模块与其393回退副本保持；原394重启失败及395首次计数断言失败不被本轮结果覆盖。

## 下一步

接入受驱动管理的逐帧CC参数区域、program array／固定CDM命令与固件地址映射，在提交前完成范围／重叠检查，并纳入未知完成时的DMA保留和复位回收。通过标准媒体请求／参数路径传入量化矩阵，不能让用户空间直接提交任意寄存器包。随后用可预测的合成图像核对实际CC启用／单位及非单位矩阵效果，再接351原厂触发树和libcamera标准ColourCorrectionMatrix。

继续完整Gamma／LTM／CCM组合及[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)：第五2MP身份／mux、多模式、动态帧时长／防频闪、几何／多摄同步、连续AF和光学校准。当前默认仍1:1 NV12/NV21 IQ旁路。关灯黑场／噪点按低照度解释，照明相关校准后做；完整目标active。
