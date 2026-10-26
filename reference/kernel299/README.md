# 299：原厂 BLS、本机 EEPROM 与 libcamera 在线候选

2026-10-19。**实际手机仍为 #298**，内核源码 c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117、778 模块、boot276、DTB、原厂固件和产品相机包均沿用298；本阶段没有刷写、重启或更新系统软件包。正式应用仍走 RAW＋软件 ISP。目标继续，完整校准／硬件 IPA 尚未完成。

## 已取得的原厂与本机数据

从原厂 `com.qti.tuned.sunny_imx319.bin`（15389568字节）导出全部16个IFE BLS模式、288区域，均为960 U14、阈值0；原厂解析器与独立二进制解码一致。另独立遍历11个BPS根、198区域。分析副本仅投影未选根的版本元数据，原始数据及模式树保持；没有重建Android的运行时模式选择。[原厂导出](factory-bls-export-validation.json)

原厂BLS参考量不是本机暗场测量，也不能直接用作软件ISP的SensorBlackLevels。归一化减偏移3840映射硬件960；原厂范围伸展截断为2175 Q11，通过用户空间显式共同增益表达，驱动BLS scale继续unity。common gain量化后实际为136 Q7，约0.046%的归一化误差已知。[配置换算](factory-profile-validation.json)、[显式选择的实验配置](manual-sunny-imx319-bls.yaml)

匹配原厂模组描述的EEPROM读取映射由原始BIN和解析结果分别核对：7位地址0x51、16位地址指针、起始0、读取12287字节。普通V4L2流持有相机供电，只读两遍完全一致，传回主机的哈希亦一致。仅发送读取所需地址指针，没有写EEPROM内容、OTP或应用标定值。[读取映射](eeprom-read-plan-validation.json)、[169帧供电与恢复](eeprom-read-validation.json)、[双读与传输](eeprom-transfer-validation.json)

完整EEPROM格式仍未核实：初版原厂解析器被CPU限额终止；移除分析schema中不匹配的signedness字段后可以导出XML，但AF后续字段仍错位。**不能依据该XML的WB／LSC／OIS开关下结论。** AF前缀候选落在10位范围仅是必要条件，原厂校验与完整布局仍待验证。个体数据、校验值、私人图像仅保存在仓库外。Sunny文件的存在不能证明本机个体模组供应商。

## 正常场景与统计域验证

长焦内部图案54图像／54有效统计、6参数完成。独立RAW模型与硬件NV12最大通道误差1.235；5次可观察变化均对应参数报告的首个生效SOF。[独立图案对照](factory-pattern-validation.json)

同一ROI下，改变WB共同／分通道增益时BHIST计数完全相同，改变BLS则计数变化。由此推断本配置统计抽头位于BLS之后、WB之前；不能把gamma编码输出亮度等同线性统计，也不能用此Y直方图替代RGB AWB统计。[统计抽头对照](statistics-tap-validation.json)

广角固定曝光3000、模拟gain code768，六阶段54图像／54统计。原厂60 DN参考与单场景64 DN估计分开对照；减黑后Y122.243，显式归一化后125.736；使用临时场景WB时G/(R+B)/2约0.995，旁路约1.257；重启用参数后Y差0.027。归一化阶段亮部截断约0.58%，AE和多光源色彩验证仍必要。已实际查看私人前后预览。这些是同场景实验，不是色卡准确度、遮光暗场或原厂完整IQ验收。[实景对照](factory-scene-validation.json)

## libcamera 接入状态

实际复用保留r24的libipa V4L2Params和CAMSS公共参数类型，完成56字节编码器：等通道减偏移、显式归一化、WB及BHIST ROI；AArch64 Werror和真实内核解析／WB／BHIST验证器通过，主机测试不声称覆盖BHIST MMIO。[编码器](ipa-encoder-validation.json)、[内核字节协议](encoder-kernel-wire-validation.json)

现有CAMSS参考分支基于RAW＋离线OPE／软件ISP，不能直接当成在线VFE后端。本阶段新增可选的在线handler候选，使用MediaDevice／CameraSensor／V4L2VideoDevice／MappedFrameBuffer和公共编码器管理图像、参数、统计及应用请求；按能力匹配节点，未写入机型或CCI总线号。只支持单NV12流、已实现的Bayer10范围以及启动时手动WB；逐请求控制、自动AE／AWB与IPA IPC尚未实现。

发现公共V4L2层会把每个采集队列首帧独立归零，候选在FrameBuffer私有数据中保留原始kernel sequence，公共metadata序号行为保持；图像／统计按同一epoch的原始SOF配对。统计缺失超时释放请求，不向算法提供错误配对。停流清上下文、重开重发参数、恢复路由。已在IMX319完成三轮真实请求，每轮24帧，72帧均完成CPU DMA同步读取且亮度非恒定；72组图像／统计与观测SOF事件及应用序号独立交叉核对，参数均从SOF0生效。每轮停流后不重新配置即可启动。该验收不覆盖逐请求控制、错误取消、晚启动统计、严重IRQ延迟或其它传感器／模式。[实机](inline-capture-r3-validation.json)、[独立关联及包读回](inline-request-association-validation.json)

候选树 `/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline`，保留r24源码／产品库不改；默认不匹配，需显式启用环境变量。完整候选库和测试程序Werror构建通过；状态见[构建结果](inline-build-validation.json)、[测试工具](inline-smoke-tools-validation.json)、[实机记录](inline-capture-r3-validation.json)。首次构建发现SDK缺少当前内核两个元数据FourCC，已同步已有定义；O2构建明确中断后改用O0候选，不把中断当成功。

## 分层与续作

- SoC驱动／板级／内核：沿用298已部署BLS、参数与共享SOF实现，本阶段不加DT调校属性或私有ioctl。
- 用户空间：模组参考配置、个体EEPROM及算法分开；编码器可移入正式IPA，当前handler只是显式启用的候选。
- 下一步：补晚启动统计／取消／丢失SOF／逐请求参数及更多模式验收，再接IPA、sensor helper和DelayedControls，实测曝光／增益延迟；补有效颜色统计、AE、AWB及多摄／多模式校准，核对EEPROM布局与原厂校验。
- 用户选择正常场景、暂不遮光；不把场景拟合替代暗场标定。严重IRQ延迟、多丢失SOF及多参数在途仍待验收。
- 既有GPU／SSC／modem问题未关闭，whole_system_healthy=false。没有上游接受或跨新版本迁移证明，不能承诺零补丁升级。

私人产物 `E:/edk2-samurai-out/kernel299`；操作前确认进程／状态和当前#298 guard，勿盲目重放已执行采集。稳定回退仍为#290，详情见[298检查点](../kernel298/README.md)。


## 实机收尾与保留的失败

R1仅枚举传感器，测试应用按设备树camera ID寻找型号而未进入采集；原始私有报告中硬编码的actual_libcamera_requests标志已在公开派生报告纠正为false，原始记录保留。改用Model属性后R2三轮72图像／72配对成功，但固定1秒采样仍看到CCI活跃，总验收未通过。读取该设备1000ms自动休眠配置并确认随后休眠后，R3改为5秒以内的纯观察轮询，在1305ms取得前后完全相同的休眠状态；没有强制挂起或更改延迟。R1／R2失败报告与包均保留。

最终核对：5传感器／镜头、两CCI及CAMSS休眠，9相机供电与共享IO关闭、用户0，MCLK／CCI时钟0，fault／taint／pstore／CCI错误0；961包、50相机载荷和778模块校验一致。桌面／PipeWire／WirePlumber进程未替换，SensorProxy、Wi-Fi、HCI和三个DSP维持正常。[最终检查](final-health-validation.json) 四摄RAW＋CPU产品回归引用先前298的18段233帧结果，本阶段没有重跑，也没有把候选采集等同四摄产品验收。

所有本轮构建与采集已核终态；R3 worker与fixture均无匹配活进程。只同步脱敏源码／证据，不提交或推送、不安装候选库。正式目标仍未完成。
