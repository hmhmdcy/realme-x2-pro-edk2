# 216：补齐 IMX471 原厂模拟增益范围并验证 RAW 响应

本轮将前摄模拟增益寄存器上限从800改为960，名义范围从1～4.57倍扩展至1～16倍。只改这一个常量，215测试图位宽、模式/曝光、供电/时钟/GPIO和r5相机软件包保持。已部署并观察实际RAW噪声响应；未把它写成实际光照灵敏度标定、完整暗光画质或标准手动增益API验收。

本机原厂com.qti.sensor.imx471.so重新反汇编，指令102c加载16倍上限、1058加载960、1078比较960，与1024/(1024-code)换算一致；原库未修改，未读写校准或NV。该事实与同款传感器[上游作者的增益补丁](https://github.com/cschalle/mipi-fixes-x1-aura/blob/533d995b7acbd6965e5b0b85c97f8bafab9fed4e/kernel/patches/0003-media-i2c-imx471-Raise-the-analogue-gain-limit-to-th.patch)相符；固定仓库提交533d995b、补丁原提交5cf84f3e，不套用其笔记本镜头标定。[原厂依据](factory-gain-contract-validation.json)、[源变更](gain-source-validation.json)、[canonical补丁](../../linux-port/camera/kernel/0002-imx471-analogue-gain-limit.patch)。

新鲜基线确认同215启动、旧模块6b2bb0b4、原r5数据库和相机休眠、taint0，保存旧模块；实际V4L2控件上限仍800。[基线](baseline-validation.json)。W=1模块编译无诊断、导入符号和vermagic匹配，Image183/boot211及DTB/其它源码/构建元数据保持，新模块1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b、25448B。[构建](imx471-module-build-validation.json)、[源码核对](source-final-validation.json)。

按215验证的流程暂时停止空闲WirePlumber，正常解绑前摄释放引用，卸载/更换唯一imx471.ko、depmod/加载和静态绑定，再恢复策略进程。771个其它模块及PipeWire/桌面身份保持，未强卸、未刷机/重启，r2 transition-state为verified。[部署](module-reload-validation.json)。原215模块及全部原元数据已私下保留。

有限RAW测试先启动流，再用普通V4L2控件写0/800/960，写入及缓存读回成功后排队6帧；使用UID10000、系统r5库、DMA READ START/END并排除行填充，图案关闭，无外部光源。独立测试依次为0、800、960、0；稳定部分最后4帧的RAW标准差中位数分别0.47435、0.94529、2.34678、0.44158。噪声随增益上升，回到低增益后下降，表明960确实影响了传感器输出，不只是扩大控件元数据。[0-a](system-gain-raw-0-a-validation.json)、[800](system-gain-raw-800-a-validation.json)、[960](system-gain-raw-960-a-validation.json)、[0-b](system-gain-raw-0-b-validation.json)、[验收](gain-acceptance-validation.json)。

全部24帧与首帧保留。800/960的首帧标准差约0.48，随后约0.95/2.35，说明首帧可能保留切换前的响应；统计比较排除前两帧，但未把它推广成所有模式/曝光/增益的确定控制延迟。暗噪声不是受控光照响应，不能由这些数字宣称实测灵敏度恰为16倍或提高1.8档；均值仍约64符合暗场黑电平，RGB全零也不能单独判bug。

首次默认客户端预检中，我错误假设配置前cam --list-controls会列出AnalogueGain；它实际只列Contrast/Gamma，预检在采集前StopIteration退出，未改驱动状态。保留该记录，第二次仅核对实际内核上限960，并如实标注标准手动增益API未验收。随后默认cam和GStreamer各取6帧通过、无报错/超时/新增内核故障。[客户端](default-clients-validation.json)。仍需检查配置后的控制映射、IPA曝光/增益和用户态手动控制能力。

最终sensor/CAMSS/CCI suspended，VDIG/VANA disabled/users0、MCLK及自身MMCX票0、图案关闭；三个DSP running、taint/五fault0，NV与非相机程序核对保持，GPS0/Signalsfalse/rate30、蓝牙关闭无连接。[最终健康](final-health-validation.json)。原模块/元数据、首帧和初次预检失败等86成员私人归档完整核对通过；无私钥、无场景图。[归档](final-evidence-validation.json)。

回退为k216-baseline/imx471-original.ko及k216-driver-test-r2/before-tree，原215模块SHA256为6b2bb0b4…，已导出。必须重新核对当前启动和空闲状态，再停止策略进程、正常解绑/卸载、更换旧ko、depmod/加载/绑定和恢复策略；不能重放已完成marker。它保留215已验证的TPG修复。r5软件包未变化，与214的软件包回退分别处理。

下一步继续完整16MP模式、曝光/控制延迟和标准控制API，并逐路接入后置四摄。RAW10 AWB线索需要先核对实际输入格式：0.7.2的packed10P路径已经读8位值，同款补丁只给unpacked10/12的和做缩放，不能未经检查便称其修复本机白平衡。笔记本shading/色彩矩阵不套用。GNSS真实fix/正CNR、蜂窝真实业务、BT phase5、传感器FastRPC/SSR、GPU ISP、充电/PM及完整rootfs继续开放。[全硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
