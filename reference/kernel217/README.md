# 217：原厂三模式验证、完整分辨率候选与时序差异

本轮为完整16MP适配解码了本机原厂IMX471模式，并构建可审查的驱动/DTB候选。**手机仍运行216模块1388a070…，候选未安装、未刷写/重启；16MP取流和完整图像处理尚未验收。** 全外设目标继续开放。

原厂BIN的Parameter Parser1.3.2符号表有一个ResolutionInformation和3个256字节ResolutionData记录。保留原厂BIN不变，仅在私人分析副本中投影原128字节传感器上下文和resolutionInfo引用，并在分析专用XSD移除BIN中不存在的两个尾部字段。厂商工具最终导出真实3模式XML，独立有界解码器逐项核对所有标量、流尺寸和174条8位寄存器写入；尺寸/裁剪、RAW10/4lane、FLL/LLP均与寄存器一致。[核对](factory-mode-crosscheck-validation.json)、[独立解码器](decode-and-crosscheck-modes.py)。未解码个人EEPROM/NV或公开原厂XML/私有库。

| 模式 | 原厂帧率字段 | LLP/FLL | 输出时钟字段 | 后处理 |
| --- | --- | --- | --- | --- |
| 4608×3456 | 30.01 | 5120/3762 | 599040000 | SWRemosaic |
| 2304×1728 | 30 | 2560/4250 | 320000000 | 2×2 binning |
| 2304×1728 | 60.02 | 2560/2124 | 320000000 | 2×2 binning |

三模式均使用本机19.2MHz外部时钟，模拟窗口0..4655/0..3495；完整输出数字裁剪偏移24/20，binning模式12/10。30/60两组固定寄存器只在FLL与曝光的4个字节不同，可通过相应VBLANK/曝光控件覆盖；这仍需实机验证，不把元数据帧率当实测帧率。OP PLL、4lane/RAW10与输出时钟元数据相互对应：binning候选link400MHz、完整候选748.8MHz。

16MP模式明确需要软件重马赛克。已有发行版quad-Bayer补丁只为IMX371配置2×2 cell collapse，主要用于GPU路径并产生半宽半高输出；不能将其直接用于IMX471并声称获得完整16MP。后续需按模式识别CFA、保持完整原生采样尺寸、实现正确CPU重马赛克，并处理RAW/输出缓冲区预算及COMPOSE几何。完整RGB、方向/颜色/画质、控制延迟和实际灵敏度仍未验收。

候选保留1928×1088旧寄存器表，添加2304×1728和4608×3456原厂表、按固件声明过滤频率、模式切换时更新link/pixel/VBLANK控件，并增加数字COMPOSE/BOUNDS信息。完整未处理RAW还要求unprocessed_fullres显式模块参数；默认不开放，避免当前普通Bayer路径将其作为成片使用。候选DTB只扩充该sensor endpoint的link-frequencies为200/400/748.8MHz；它尚未打入boot.img。[候选补丁](imx471-factory-modes-candidate.patch)、[源记录](factory-mode-candidate-source-validation.json)。

最终候选模块bc4649fb9dbfd42b5b69c4585cf6c62ca9ac8706348b43b1aa0155d85f96ee75、29688B，vermagic保持183；候选DTB a214fd6b2ccb93e5bbb5adc774e7c510398541e8fab286832682cc6bbd76ca42，相比已部署211 DTB仅上述频率属性不同。W=1无诊断、全部导入符号可用，checkpatch0错误/0警告。构建后宿主216源码、sensor/CCI对象及模块、配置/符号/order、Image和旧canonical DTB全部恢复。[构建](factory-mode-candidate-build-validation.json)、[风格](candidate-style-validation.json)、[最终源码](source-final-validation.json)。编译通过不证明物理模式、实际带宽或RGB处理正确。

当前旧预览另做12帧及120帧有限RAW时间戳观察，5次流中采样均为pixel_rate160000000、LLP2328/FLL1308、exposure1270/gain0。控件计算52.5447fps，缓冲区时间戳中位间隔约17.296ms、约57.8168fps，序号连续。cam源码确认其输出来自FrameMetadata时间戳；这个差异保留为待查，尚未区分传感器PLL、输出/阵列时钟定义、IRQ及取流行为，未据此盲改PLL或声称时序标定完成。全部控件恢复、场景未保存、相机休眠、taint/五fault0。[12帧](current-raw-timing-validation.json)、[120帧及活跃控件](active-raw-timing-validation.json)。

保留的失败：第一次厂商工具返回0却无XML；第二次只有传感器上下文XML，因误把重复引用当内联结构而没有模式，均未当成功。第三次错误的minOccurs断言提前终止；按XSD重复引用修正为144字节上下文投影后，第四次才导出3模式。独立解码最初猜错remosaic枚举值，改为按XSD枚举表解释。候选首次仅编sensor导致MODPOST缺CCI符号，恢复后加入CCI目标；风格检查的两个空格缩进及说明换行问题修复，再编译最终候选。所有失败日志和旧候选仍私下保留，手机未受这些离线失败影响。

最终手机仍为216原模块、r5/944包及49条相机payload保持；3DSP running，sensor/CAMSS/CCI休眠、前摄电源/时钟票释放，图案关闭、taint/五fault0，NV与非相机程序核对保持。GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[健康](final-health-validation.json)。22成员私人原生归档全部核对，含原216模块备份和时序采样；未保存场景图或公开私钥。[归档](final-evidence-validation.json)。

续作先完成按模式的完整分辨率重马赛克、COMPOSE到有效物理区域的映射和输入/输出DMABUF预算，再进行隔离候选的物理RAW、已知非黑输入、实际帧率/曝光及默认客户端验证，之后才整合部署。不能把4MP折半/放大结果当16MP，也不能把当前候选DTB当已部署镜像。后置四路、GPU ISP、GNSS真实fix、蜂窝业务、BT phase5、传感器FastRPC/SSR、充电/PM及radio/Mesa/完整rootfs保持[完整目标](../../linux-port/docs/HARDWARE-STATUS.md)。
