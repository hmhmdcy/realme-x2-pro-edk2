# 406：LTM 实像素通过，修正单全帧 IP 启用策略

405类型化LTM接口首次物理验证发现：mask开启而DC关闭时后续条带水平错位2像素，LA表也没有预期效果。定位到原厂多级处理策略与当前显式单全帧接口的差异后，修正实际IP启用字段。第二次52个固定诊断请求全部完成：错位消失，LA／逆Gamma／组合Gamma符合控制预期，NV12／NV21归一化一致；随后恢复正式395／393，四摄48帧及资源释放通过。**这是固定640／650×480诊断的LTM硬件证据，不是完整自动调校、DC统计或全部镜头／模式已经完成。目标保持active。**

## 首轮失败与实际控制位

复用400已物理验证的CST／CV转换对，CC为单位矩阵，准备13种固定模式：原旁路、转换对、LTM子模块关闭、IP／mask开关、LA零／2048／1024、逆Gamma零／线性、DC＋IP，以及LTM＋Gamma线性／零。[诊断代码](ltm-adapter-tail.c)只暴露固定选择，没有任意寄存器或CDM输入。新客户端覆盖640和650宽、NV12／NV21，共52请求；650双核的mask路径会由两条变四条，检查实际条带边界。

第一次事务`k406-ltm-r1`使用405核心。52个请求传输完成，随后正式四摄48帧及恢复通过，但[首轮像素](pixels-validation-r1.json)未通过：mask-only在640宽差5736字节、650宽差10703字节。逐区域对齐发现首条带正常，后续条带Y／UV恰好对应输入向左2像素的位置；DC＋IP配置没有该位移。LA零／1024／2048也都仍输出转换对图像。不能以请求完成或与原HAL命令相同，宣布IP处理已正确启用。

[原厂完整命令定位脚本](probe-dc-commands.py)执行实际C IQ与原HAL／原固件准备。DC0和DC1时几何仅条带偏移416不同，整512KiB命令也仅`0x5c60`的bit10不同：`0x2001`与`0x2401`。该位是实际IP_EN。原HAL分配器将全帧IP字段绑定DC和有效四分之一尺寸，固件又从该条带字段生成IP_EN，而不直接采用IQ2184。因此，旧实现虽保持原HAL策略，却在当前DC0／显式IP1请求中让硬件IP关闭，同时按IP＋mask扩展了处理区域。

这是移植原HAL策略到当前单全帧接口时的适配错误；不据此断言原厂完整多pass相机流程也存在同一缺陷。403／404对原规则和字节一致性的记录作为历史事实保留，不能继续把DC／quarter条件当成当前显式IP接口的正确语义。

## 底层修正

[唯一驱动修正](ltm-ip-enable.patch)让full-pass条带字段416直接服从检查后的`image_processing`请求。DC／粗级处理策略留给上层流程；分区、处理裁剪、网格、输出裁剪、IQ／LUT布局、请求所有权和复位清理均未改变。IP＋mask仍用324步长／6像素halo及左右扩2的处理区域；其它情况328／4。旧旁路传入关闭标志，行为保留。

[32组实际C验证](ip-enable-validation.json)在主机ASan／UBSan和AArch64 QEMU一致，覆盖128／282／640／650、两种格式、单／双核与全部DC／IP／mask组合。完整原固件生成的IP_EN与显式请求一致；与旧实现相比，至多仅该bit改变，其余命令位及job保持。小尺寸仅有离线证据，不能外推为本轮已物理验收。

候选branch `samurai-ipe-full-pass-ip406`，commit `b4f382affa9a8be089ccec6170c34d74005103ce`，父405 `3b65d2989ca8d71b658f8a859e8784be3e6bb965`，一个SoC编码文件，干净未永久安装。[源码状态](source-state.json)。[构建](intree-build-validation.json)W=1／Werror诊断0，核心415720字节、SHA `b0fbf678b045aa52f9db1eb54b6bfecce6fa5c10c76bb1dadbea5329d4dd28b4`，共享配置／输出／symvers恢复。板级DT、主线框架、传感器及产品用户空间未改。

## 第二次实像素

确认首轮worker／client／collector终态并恢复正常后，才启动独立`k406-ltm-r2`。两轮测试adapter和client的字节完全相同，仅替换上述核心。52个请求、52次start／stop，error／cancel／first_error为0，其中44个使用LTM、8个组合Gamma。[像素验证](pixels-validation.json)：

- 两尺寸中，LTM子模块关闭、零scale的IP／mask、线性逆Gamma、DC＋IP配置均与转换对全图零差；原先2像素位移消失。
- LA零、逆Gamma零和组合Gamma零分别产生全图Y=0／UV=128，证明实际表值能够改变硬件输出。
- LA2048／1024在每尺寸／格式各八个灰阶色块的全部内部像素分别为128／64，误差0。彩色色块包含比例和裁剪效应，没有把整张彩色图误称为常量。
- LTM＋线性Gamma与对应LTM结果最大字节差1：640宽100字节不同，650宽160字节不同；组合零Gamma为精确黑场。
- 两尺寸全部13模式的NV12／NV21归一化全字节一致；640转换对与402保存的460800字节完全一致。未受修正影响的首轮控制图像也逐字节一致。

主机重算CRC、检查合成输入生成器；客户端确认输入未改、输出尾canary、sequence和timestamp。合成像素与环境照明无关，本轮黑场来自明确的零表控制。普通相机回归按当前开灯环境执行。

本轮未验证非零LTM scale／LCE的完整局部对比度公式、DC统计读回、完整factory动态插值、所有尺寸、连续多帧参数变化，或带LTM的强制丢ACK／故障复位。尤其不能把设置DC标志等同于已经验收完整粗级统计流程。

## 正式恢复与接续

[第二次事务](runtime-validation-r2.json)和[最终状态](current-state-validation.json)证明：正式core395／adapter393恢复，四摄各12共48direct，error0／extra0；CPU／IRQ／PM／映射／导入释放，ICP／CAMSS／双CCI suspended，17时钟0、9电源disabled／users0，taint0，PW／WP各一实例，无残留测试参数、dump、timeout、重启或新增相关fault。所有实验进程终态。两轮各52诊断＋48正式恢复，共200direct属于不同模块epoch，首轮像素失败保留，不能写成200帧全像素通过；最后正常epoch只计48。

原厂固件／HAL／OEM片段／表、命令、日志和样本仅私存406及前序，没有访问或改写NV／OTP或个体校准备份。候选和检查点只作本地提交，不push／PR。

下一步接原厂完整LTM数值／动态触发、非零scale／LCE与统计流程，完成IFE／IPE输入域和CST／CCM／Gamma职责核对，再接标准media request／libcamera及多摄校准。正式默认仍旁路高级IPE IQ。[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续，包括第五2MP／mux、多模式、帧长／防频闪、连续AF／光学、几何和多摄同步。
