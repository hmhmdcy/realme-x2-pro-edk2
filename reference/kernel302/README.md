# 302：硬件 IPA 的曝光／增益控制与有效帧上下文

2026-10-19。实际设备仍 **#298**，内核、778模块、DT与固件未改，正式相机包仍为RAW＋CPU ISP。本阶段在隔离候选中接入现有CameraSensorHelper／DelayedControls，以及标准手动模式和有效曝光／增益元数据；硬件AE／AWB、其它摄像头／模式及完整校准仍未完成。

## 分层实现

IPA使用既有CameraSensorHelperFactory按sensor型号取得增益模型，不复制Sony或Samsung的公式到handler／板级DT；曝光时间按IPACameraSensorInfo行长与像素速率换算。公开ExposureTime／AnalogueGain及两者的Mode控制，当前只声明Manual、拒绝Auto，不宣称已实现AE。5000μs量化为503行；本模式返回的实际曝光元数据为5004μs，模拟增益由硬件码值反算。

handler使用既有DelayedControls，按SOF推进控制与来源cookie，立即保存该SOF的控制快照，之后将快照随对应统计交给标准IPA／IPC。异步统计不再读取可能已被覆盖的16槽历史。元数据来自实际生效快照，不直接回填用户请求值；摄像头初始化时通过IPA取得控制范围，停流重开不重复init同一proxy。

每次写入后核对V4L2控制框架读回与计划值；SOF不连续、读回不符或接近DelayedControls的有符号序号边界时，停止推进控制并将上下文失效，直到重开。此项不等于读取传感器嵌入式寄存器，也未完成所有I/O失败／晚IRQ／取消／worker故障注入验收。

[显式配置](imx319-manual.yaml) 使用301已测的两帧延迟，检查1632×1224、209066666像素／秒、2080行长、3350最小帧长；当前只支持已验证的等延迟配置。通用BLS参考仍来自299原厂解析，临时场景WB由测试应用提供。没有把模组参数写进SoC驱动或DT，也未改通用DelayedControls／SensorHelper的实现。

## 验证

[构建](build-validation.json)、[真实DSO契约](ipa-contract-validation.json) Werror通过；模式时钟不匹配被拒绝，5000μs→503行／4×→768码独立数值通过，转换错误不会部分覆盖输出。未知／越界上下文不输出曝光／增益元数据；Manual模式声明／回报、Auto拒绝已在实际模块测试。沿用56字节包逐字节对照、错误统计、停流／重开与统计SOF回绕测试；后者不代表整个延迟控制队列支持长时间序号回绕。

[最终独立核对](runtime-association-validation.json) 仅汇总补齐Manual接口后的最终候选包：

| 执行模式 | 真实图像／统计／曝光增益及Mode元数据 | 标准控制变化 | 图像四分区亮度变化 | 收尾 |
| --- | --- | --- | --- | --- |
| 强制隔离 R3 | 两轮各240帧，共480 | 18 | 72 | 媒体图／控制恢复，1294ms自然休眠 |
| 默认签名线程 R4 | 两轮各240帧，共480 | 18 | 72 | 媒体图／控制恢复，1299ms自然休眠 |

每帧独立关联请求、来源cookie、原始SOF、量化后曝光／增益及Manual元数据。36次变化的线性BHIST、NV12 Y四个垂直分区均满足响应条件，并与有效元数据同帧变化；DelayedControls真实写入日志逐项对应SOF＋2。手机上8个包文件全部读回核对SHA。私有场景亮度和曲线不公开。[R3关联](control-association-r3-validation.json)、[R4关联](control-association-r4-validation.json)

对变化前第6—3帧及变化后第6—13帧取中位数，变化须超过两平台MAD的10倍及相对3%；连续3帧达到变化量15%识别首变化，连续3帧处于85%—115%识别平台。全部36次BHIST变化和144个输出分区变化均从有效元数据SOF开始。此为正常场景控制响应验证，不是暗场、逐像素曝光锁存、色卡准确度或完整画质校准。

隔离模式部分请求的控制到其后一个图像帧才生效，默认线程本轮均在对应请求帧生效；均按真实有效值报告，不能承诺发起控制的request就是生效图像。不能将硬件SOF＋2延迟与应用／IPC队列延迟混为一谈。

两次最终运行未新增WARNING／Oops／GPU fault／DSP fatal；5个传感器／镜头、两CCI、CAMSS均休眠，9供电关闭／用户0、taint0，无匹配活worker。[R3恢复](controls-capture-r3-validation.json)、[R4恢复](controls-capture-r4-validation.json) 本阶段没有重跑961包／778模块全量校验或四摄产品回归；引用300最后全量记录，既有GPU／modem／SSC问题未关闭。

## 保留的中间状态

首次模块可编译但真实加载缺少uint64 YAML accessor符号；改用框架已有的unsigned int读取像素速率。测试程序生成器首次匹配到两处reuse而停止，改为完整语句锚点。Manual模式补齐时Werror发现两个enum类型混用，显式转int32修复；所有失败发生在新版本上机前，日志保留。

补齐Mode接口前R1／R2各480帧的控制关联也通过，保留原包及源码，但不计入最终接口验收。最终包为[ipa-bundle-r2](ipa-bundle-r2-validation.json)，R3／R4均已核对实际加载它；R3启动请求发出时打包工具的终态尚未读回，随后已取得工具正常退出，并以实际8文件哈希及480帧Mode元数据消除版本歧义，没有重放该启动。

旧301九入口、已测300源码与候选、302补Mode前源码／包均保留。[基线](baseline-preservation-validation.json) SDK历史名`libcamera299-inline`内现为**302源码**；使用302构建脚本，勿重放299／300源码安装器覆盖。R1—R4均终态，不盲目重放归档、打包或采集。

## 继续目标

下一步复用libipa AgcMeanLuminance，将本模式的线性BHIST及有效曝光／增益上下文接入硬件AE；继续补有效颜色统计与AWB、多摄／模式和完整IQ。Y BHIST不是RGB AWB。晚启统计、丢失SOF、错误取消与worker故障矩阵、S5K3M5属性缺口仍开放。

原厂IMX319 BLS已解析，本机EEPROM双读一致但完整布局／校验未确认、个体值未应用，见[299](../kernel299/README.md)。用户暂不遮光，正常场景不替代暗场标定。私人根`E:/edk2-samurai-out/kernel302`，当前guard298、稳定回退290；没有上游接受或跨版本零补丁升级证明。完整多摄／ISP校准目标继续。
