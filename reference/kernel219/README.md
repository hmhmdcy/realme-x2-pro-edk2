# 阶段219：原厂模式实机取流与时序修复

2026-10-16。已部署boot219与新的IMX471模块，内核仍为183。设备树仅为前摄增加400/748.8MHz链路频率，原200MHz保留；启动镜像其它代码保持。[镜像核对](build-package-validation.json)、[刷写](flash-validation.json)、[新启动](runtime-validation.json)。当前身份依据为新启动的`k219-runtime/boot-id-private.txt`，不可继续用218或219旧启动的guard。

前摄真实传感器→CAMSS的2304×1728和4608×3456 RAW10均已取到六帧，完整尺寸并非合成输入或放大。16MP CPU Quad Bayer路径也输出了六帧4608×3456 RGB；仍为显式实验选项，默认关闭，未验收正常光照颜色、标定、标准CFA/几何和日用画质。后置四摄仍待接入。

新增[测试图案相位核对](test-pattern-layout-notes.md)：完整模式的内部TPG仍按普通Bayer周期生成，不能据其RGB色条验收真实Quad场景颜色。此前完整RGB正对照只证明完整尺寸传输、内存与非黑输出。

房间关灯、室内窗边；没有闪光灯、外部照明或场景图片保存。真实[4MP暗场RAW](2304x1728-raw-pattern0-system-validation.json)噪声约0.47，帧间变化约35%；[16MP暗场RAW](4608x3456-raw-pattern0-system-validation.json)噪声约0.60，变化约51%。均在DMA READ START/END内解包全部有效像素并排除行填充。真实传感器[完整RAW测试图案](4608x3456-raw-pattern2-system-validation.json)及[完整RGB测试图案](4608x3456-rgb-pattern2-candidate-validation.json)提供正对照。[暗场RGB](4608x3456-rgb-pattern0-candidate-validation.json)校正后接近黑且有稀疏变化，不以处理后的黑色单独判故障。

## 帧率与元数据

直接只读活动PLL/FLL/LLP，并各取120帧硬件时间戳，定位旧模式实际行长5120而驱动报2328；旧PIXEL_RATE还混用了链路吞吐值。修复为显式写入原已观察到的行长、按像素阵列时钟报告速率，不修改PLL或链路频率。[增量补丁](imx471-pixel-array-timing.patch)、[隔离构建](timing-candidate-build-validation.json)、[正常解绑重载](timing-module-reload-validation.json)。修复后：

| 模式 | 硬件时间戳fps | 控件计算fps |
| --- | ---: | ---: |
| 1928×1088 | 57.82018 | 57.81728 |
| 2304×1728 | 30.00030 | 30.00000 |
| 2304×1728/VBLANK396 | 60.03122 | 60.02825 |
| 4608×3456 | 30.01381 | 30.01506 |

[旧模式](1928x1088-timing-vblank-1-after-timing-fix-validation.json)、[4MP30](2304x1728-timing-vblank-1-after-timing-fix-validation.json)、[4MP60](2304x1728-timing-vblank396-after-timing-fix-validation.json)、[16MP](4608x3456-timing-vblank-1-after-timing-fix-validation.json)。这些时序试验只读帧元数据，没有读取像素；不作为噪声或CPU DMA同步验收。早期旧模式报告曾继承错误的方法字段，已明确更正并保留私人原始输出。各次格式、媒体图和控制恢复，内核taint/五类fault增量均0。完整模式试验结束恢复参数N及WirePlumber。

表中是RAW传感器出帧速率；尚未证明完整16MP CPU RGB能实时达到30fps。此前218三帧合成输入的四线程处理时间约136–139ms，也不能代替真实取流吞吐测量。

依据：[V4L2 PIXEL_RATE定义](https://docs.kernel.org/userspace-api/media/v4l/ext-ctrls-image-process.html)、[像素阵列与总线速率区别](https://docs.kernel.org/6.8/driver-api/media/tx-rx.html)。四lane VT关系是由源表、活动寄存器和时间戳共同支持的推断，未声称取得IMX471完整数据手册。

后续补查的[上游9月/10月时序讨论](upstream-timing-crosscheck.md)提供了不同硬件上的独立佐证；没有照搬其它机型的供电、镜头或标定。

## 默认RGB的真实分配失败

[已装r5的4MP RGB](2296x1728-rgb-pattern2-system-validation.json)在第三个输出缓冲分配时失败，未开始取流；日志明确为dma-heap allocation failure，不能当作暗场或通过。同样尺寸、四个缓冲使用system heap的[候选库](2296x1728-rgb-pattern2-candidate-validation.json)通过。完整16MP CPU路径也观察到system和videobuf2_dma_sg导出器。

完整r6配方保留原11子包、全部管线及5个IPA，增加可配置`software_isp.dma_heap`，产品配置选择system；原生Quad选项仍默认关闭。原签名输入继续使用。[13包验签/架构](forward-package-artifact-validation.json)、[5个IPA与核心公钥](host-runtime-qa-validation.json)、[完整r6 CPU类50组测试](r6-cpu-isp-tests-validation.json)通过。七组件已原生统一升级为r6/config-r1，944包中的937无关记录保持，49条payload核对通过，[七包r5降级模拟](r6-package-install-validation.json)通过。

初次完整模式预检因CCI尚未自动休眠退出，已正常恢复并保留[失败记录](full-initial-preflight-validation.json)；加入有界等待后实测通过。新启动早期SLPI/BlueZ/ModemManager就绪延迟，之后原服务自动启动，不能称为新的SSC修复。

## 当前源码与回退

当前模块`e49dab26…`，私人`kernel219/timing-build/imx471-factory-modes.ko`；时序回退为设备`k219-timing-baseline/imx471-original.ko`（d82c941d…）。模块树772项、其余771模块保持。更早驱动回退见`k219-baseline`。启动回退是私人211镜像`c3bf043f…`，当前219镜像为`156f0370…`；模块与启动回退分别核对。

宿主canonical内核源/对象仍恢复到216状态，canonical DTB也仍是旧树，不能当当前部署树刷写。产品相机配方现为完整r6/config-r1；内核补丁链已保存，宿主canonical内核及完整rootfs整合仍待完成。全外设目标active，GNSS真实fix、蜂窝业务、GPU ISP退出告警、后置四摄及其它开放项见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。

## 完整包实机回归与当前状态

隔离r6与已安装r6各完成八组取流，每组六帧：4MP真实暗场RAW/RAW图案、2296×1728 RGB图案/暗场及实验完整16MP的对应四组。[安装后4MP RGB](installed-r6-2296x1728-rgb-pattern2-default-validation.json)、[完整16MP RGB](installed-r6-4608x3456-rgb-pattern2-full-validation.json)。r5原第三缓冲失败保留，r6同尺寸/四缓冲使用system heap通过。

普通用户使用默认系统库及CPU配置、显式请求4MP，[cam](standard-cam-validation.json)与[标准GStreamer API](standard-gstreamer-validation.json)各六帧通过，全部格式/图/控制恢复。GStreamer只核对流元数据，不宣称未同步的像素统计；其短FD采样窗没有观察到导出器，system分配依据为独立同步取流收据。

[最终健康](final-health-validation.json)：相机休眠、前摄两电源零用户/关闭、MCLK与本域票释放，实验参数N、两个测试图案关闭；三个DSP运行、GNSS空闲、BT关闭无连接、taint/五类fault0，NV与非相机程序保持。初次最终检查把合法升级的配置与旧212指纹比较而失败，已按签名包归属核对新配置并保留[原失败](final-health-initial-failure-validation.json)，没有重放安装或硬件操作。

产品配方、配置与部署锁已整合，[内核四补丁链](kernel-patch-integration-validation.json)重放一致。完整r6构建后abuild按常规清理了src/pkg目录；配方、13个签名包和独立解包QA前缀保留。IPA验证使用保留的上游验证程序，已核对其实际加载新r6核心/基础库，从新核心获取公钥。尚未证明二次构建逐字一致。

私人原生归档逐成员核对通过，[归档收据](final-evidence-validation.json)不公开归档指纹、密钥、场景或坐标。全外设goal继续active。
