# 336：原厂曝光索引与lux触发语义

2026-10-20。已从保留的原厂AEC库恢复曝光索引/lux函数身份，提取五份调校的曝光表及关键lux字段，并完成通用数学实现。主机和AArch64各2554组结果与原厂指令参考逐字节一致。尚未接入实时IPA：当前Bayer统计到原厂lux亮度的等价转换、物理模式到曝光表的绑定仍待完成。手机本轮没有操作，仍为335恢复后的安装状态，完整goal active。

原厂AEC库沿用328已匹配当前vendor的副本，未重新挂载或读取手机。解压其`.gnu_debugdata`恢复实际符号，确认`CLuxLumaCalculator::CalculateLuxIndex`、`CLuxLumaCalculator::calculateLuma`、`CExpTable::CalculateExposureIndexForManualMode`和`CAECModArbitration::QuerySensitivity2ExpIndex`，不再只按日志字符串猜函数名称。原始库、符号和反汇编留在私有目录。[工具](inspect-aec.py)、[原始文件来源](../kernel328/algorithm-source-validation.json)。

普通lux计算是曝光索引加上亮度修正，修正使用原库存储的双精度常量77.898529052734375乘`log10(50/luma8)`，各指定位置按float32舍入。该常量是`1/log10(1.03)`的float32近似，不能重新计算一个更高精度常量替换。可选跨模式补偿再加`log10(tableZeroSensitivity/referenceZeroSensitivity)`的同尺度项；随后下限0，并按原规则执行时间滤波。滤波因子0表示直接采用新值；初始化及显式重置也采用新值。它是调校使用的lux指数，不能当作物理照度lux、曝光时间或EV。

手动曝光索引由已知曝光表锚点的增益、纳秒时间和索引，加上时间比×增益比的上述对数项得到。灵敏度路径则先按曝光表修正因子、锚点增益和纳秒时间组成分母。两条路径保持原厂float32运算顺序；手动索引本身允许负数，lux阶段才截为0。原厂普通lux亮度计算对已经处理好的256个亮度单元求平均并设置0.1下限。新`aecUniformLuxLuma`的输入明确要求是这些原厂等价的8位处理单元，不能直接把现有14位RGB均值当作已验证输入。[通用代码](libipa/aec_lux.cpp)。

固定版本公开XSD和统计接口来自已使用的CamxChi仓库，只取相关六份文件；广泛lazy对象搜索发现需要大量远程对象后已停止，改为精确取文件。[来源](primary-sources.json)。原厂Arbitration为1.0.0/176字节，公开XSD为1.0.1，末尾多`disableBandingGainCapping`。第一次解析只导出Metering；后续使用明确标记的推导兼容schema：删除该末尾字段并把schema修订号设为0，原BIN载荷未改。它不是找到的原厂完整schema；独立解码另行检查全部旧版Arbitration运行字段及动态曝光表。

五份原厂数据共89个Metering根、164个Arbitration根、224张曝光表和1140个曝光拐点。Metering的lux补偿开关、零索引参考灵敏度、滤波、采样、RGB亮度权重及参考增益，与原厂解析器XML对应；Arbitration的曝光表、修正因子、全部增益/纳秒时间/优先级/索引、ISO及其它旧版运行字段均对应。保留完整选择路径。`default_field_matches`仅表示与Default XML已解码字段相同的根，不能据此断言其它未解码Metering字段也相同或完成物理模式绑定。[解码证据](factory-aec-validation.json)。

两张主摄分支中的非默认曝光表含原始零修正因子，六个相关灵敏度路径会产生0/0，原值保持不修补。通用接口拒绝这类无效输入；原厂指令正常数值比对不包括这六项未定义除法，手动路径仍检查。没有把它变成其它有效配置的阻塞条件。

离线参考运行选定原厂指令，手动曝光索引为完整函数，灵敏度转索引为原函数数学片段，lux为完整函数，256单元亮度为完整包装函数加一个提供输入单元的虚拟回调。`log10`是主机数学库桩，日志也是桩，没有启动Android加载器或原厂算法服务。主机/AArch64以默认编译器FMA设置、Werror构建，各2554组/30648字节差异0：1212手动、1134有效灵敏度、32配置、140滤波/补偿lux、36完整亮度包装。还检查非法输入；保留独立float乘加避免FMA改变边界。[结果](math-validation.json)。

本轮没有改板级DT、SoC驱动、传感器、已安装组件或335候选IPA，也没有新增设备实验。下一步从335候选接入这些通用原语前，优先恢复`CStatsProcessor::ProcessBGStatsRegion`到`GetLegacyYRegionStats`的亮度转换，并核对曝光表模式选择；之后再让真实lux参与LSC/CCM。不要用假定的EV或固定参考值冒充该链路。335/334已有实机结果继续复用，无需因本轮离线代码重跑全量采集。
