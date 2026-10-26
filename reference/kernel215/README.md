# 215：IMX471 内部测试图寄存器位宽修复并实测

本轮从214的r5完整相机栈继续，修复传感器内部测试图控制读回成功、实际仍输出现场画面的缺陷。只将IMX471_REG_TEST_PATTERN的CCI_REG8(0x0600)改为CCI_REG16(0x0600)，增益上限、模式表、供电/时钟/GPIO和相机软件包均保持。[源差异](test-pattern-source-validation.json)、[canonical补丁](../../linux-port/camera/kernel/0001-imx471-test-pattern-width.patch)。完整画质/16MP、后置四摄及全部外设目标仍开放。

相关原始来源是同款IMX471在ThinkPad X1 Carbon Gen14上的[作者报告](https://cschalle.github.io/mipi-fixes-x1-aura/)和[补丁仓库](https://github.com/cschalle/mipi-fixes-x1-aura/tree/533d995b7acbd6965e5b0b85c97f8bafab9fed4e)。本轮固定仓库提交533d995b，宽度补丁原提交e8c7bce0；8位写入把模式写到高字节，16位写入才能正确更新低字节。自己的原厂sunny_imx471 BIN也记录固色模式向0601写1，与该修复相符。报告中的笔记本镜头校正、色彩标定和增益修改不在本轮套用范围；不能把它们视为本机标定。

新鲜核对仍为214同一启动、内核Image183/boot211、r5数据库原样、相机休眠、taint0，原a28dd67a模块已备份。[基线](baseline-validation.json)。W=1编译无警告，所有导入符号匹配原16798符号表，vermagic不变，新模块25448B、SHA256为6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c；Image/DTB/板级源码/CCI和构建元数据保持。[构建](imx471-module-build-validation.json)、[最终源码核对](source-final-validation.json)。

首次停止空闲WirePlumber后没有用户态camera FD，但modprobe -r仍提示模块在使用，退出前没有替换驱动文件，WirePlumber已恢复，桌面/PipeWire身份和内核健康保持。复查refcnt3、holders空、原模块/绑定原样，把初次marker的泛用failed-restored更正为failed-no-driver-change，原失败保留。[首次尝试](module-reload-validation.json)、[引用检查](reload-ref-validation.json)。

第二次先正常解绑7-0010，释放绑定持有的引用，再卸载旧模块、替换唯一的imx471.ko、depmod并加载新模块，静态绑定成功。只此1个ko变化，771个其它模块保持；WirePlumber恢复，PipeWire/桌面身份不变，未使用强制卸载、未刷机或重启，taint/五fault0。[更新](module-reload-r2-validation.json)。

实际测试使用UID10000、系统r5库和默认CPU配置，没有候选loader/IPA覆盖；RAW读取有DMA READ START/END并排除每行填充。内部彩条模式2的6帧RAW每像素仅0/1023两级，均值819.249、标准差408.562，空间分布非均匀且后5帧逐像素相同；RGB从首帧起非黑。整个测试保留物理传感器CSI输入，未用CSID替代，也未把控制缓存读回当硬件证据。[RAW](system-sensor-raw-validation.json)、[RGB](system-sensor-rgb-validation.json)、[验收](test-pattern-acceptance-validation.json)。

关闭内部图案后，6帧RAW均值63.9824～64.016、标准差0.4405～0.4735，相邻帧32.9%～34.6%像素变化，恢复到真实暗场。所有图案、sensor控制及media graph已恢复，相机设备休眠，未使用闪光灯或外部光源；RGB暗场全零仍不能单独判bug。[图案关闭后的RAW](system-dark-raw-validation.json)。

热更新后默认cam和GStreamer标准API各完成6帧物理前摄取流，无报错、超时、内核fault；普通用户客户端仍使用默认系统路径，未保存场景图。[客户端](default-clients-validation.json)。最终3DSP running、相机休眠/VDIG和VANA释放、MCLK及自身MMCX票0、图案关闭，taint/五fault0，NV与非相机程序保持；GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[健康](final-health-validation.json)。99成员私人原生归档和全部成员核对通过，包括原模块及原元数据，未公开私钥和场景。[归档](final-evidence-validation.json)。

本轮相机包仍为99990.7.2-r5，完整944包数据库不变。模块回退依据为手机k215-baseline/imx471-original.ko、k215-driver-test-r2/before-tree及私人归档，SHA256 a28dd67a…；当前r2 transition-state为verified，初次为failed-no-driver-change。需要回退时先重新核对当前启动和空闲状态，停止相机策略进程，正常解绑后卸载，恢复旧ko、depmod/加载/绑定并重启策略进程；不得重放本轮提交marker。boot211/Image183没有变化，模块回退与214的r5/r4软件包回退分别处理。

下一步核查增益上限/曝光与控制延迟、RAW10白平衡统计位深是否仍有缺陷，先用可控输入证明本机影响；笔记本镜头shading参数不可直接移植。完整16MP和后置四路、GPU ISP、GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、充电/PM及完整rootfs继续按[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)推进。
