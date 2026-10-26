# 350：完整提取原厂 IPE Gamma，复现原 HAL 插值与编码

2026-10-20。遵循用户无色卡、优先反编译原厂包的指示，复用已保留的五份调校BIN和原厂HAL，完成后级Gamma完整树提取及两项数值复现。未重新下载固件、读取EEPROM或操作手机；已部署版本沿用349最后观察的338/r27/r22＋344私有默认。完整多摄/ISP目标继续。

独立读取五份BIN的 `gamma15_ipe` 全部177个根、898条257节点曲线，与原厂ParameterParser输出的完整DRC/HDR/LED/AEC/CCT触发树、通道、控制轴和开关一致。分布为主摄Qtech41根/294曲线、Sunny31/222，前29/87，长焦50/176，广角26/119；全局去重75条。所有通道类型为common RGB，单调且值域有限0～1024。分析副本只修改非选模块的版本元数据，载荷和模式树保持原样。[提取结果](factory-gamma-validation.json)。

解析器新工作目录放既有E盘ext4的`/mnt/samurai-full282/parser350`，没有在近满C盘复制大包。完整曲线、XML、BIN和原厂源只私存kernel350；公共代码不含原厂/个体调校表。复用349已核模式选择，导出14个普通Preview/Video上下文的完整所选根供后续使用；没有给未知前摄裁剪模式强行绑定。

新增通用分段编码器，以模板参数明确区分IFE64段与IPE256段，保持base10bit和有符号delta10bit语义。主机/AArch64各自通过64段41项10660字节（复用347参考）和256段101项103828字节对照；后者包括75条不同原厂曲线、边界、delta限幅及非法输入。原厂GenerateGammaLUT和round/clamp函数仅在私有目录编译作参考。[数值检查](gamma-math-validation.json)。

进一步直接执行保留HAL中IPEGamma15正常编码循环`0x355148..0x35528c`，97组有效曲线共99328字节零差，460071条原始指令，无数学/日志桩。范围是该数值片段，不涵盖整模块运行开关、HDR和手动对比度。[原HAL编码片段](hal-fragment-validation.json)。

新增通用曲线插值函数，并执行HAL完整`Gamma15Interpolation::DoInterpolation`函数`0x483c58..0x4841dc`核对。412次原函数调用覆盖375组不同原厂曲线/权重、18组三通道排列、12组共用/独立通道混合、3组指针相同拷贝及4组非法权重；执行5332702条指令，仅对495次memcpy作内存拷贝桩，无数学桩。主机和AArch64各1240条单通道记录、1279680字节零差，含另4条非法曲线拒绝且不改输出的检查。首次工具构建缺少显式模板参数，已修复；失败编译日志保留。[插值检查](gamma-interpolation-validation.json)。

序列化调校通道是1040字节（enum64、257float、padding），HAL运行时是1032字节（enum32、257float）。HAL统一输出G/B/R三通道；通用插值按已规范化的单通道工作，尚未接到IPA动态触发树。API只接受[0,1]权重，没有照搬原函数在范围外极近端点的容差。

处理链不能直接按两条Gamma复合。固定版本Camx源码表明：IFE输出64个green基值供下游使用，IFE开关还受动态mask和tonemap模式影响；IPE LTM使用该曲线生成inverse Gamma，另有reserve开关和静态设置可覆盖。Titan170和175源码的硬件顺序列表都列出CST→LTM→CCM→Gamma→Chroma Enhancement，但尚未由此确定目标Android运行开关或Titan版本。原HAL内CST/LTM/CCM/Gamma四个构造函数的连续注册槽位已与恢复符号和RELR重定位核对；注册邻接不冒充完整物理执行图。[处理链证据与范围](pipeline-role-validation.json)、[固定源清单](primary-sources.json)。

直接每四点抽样把75条IPE曲线压成65节点，都不能精确表达原曲线。连续分段线性模型最大误差10/1023（约2.493/255），最大RMS1.517个10bit DN；所有段差均可表达。该上界是此抽样策略的曲线域误差，不含硬件整数插值、inverse Gamma、LTM、CCM或ADRC，不作为最终画质或默认方案的验收。[表示能力评估](representation-validation.json)。

本轮只改用户空间通用数值工具和离线提取分析。SoC硬件接口仍是348已测候选；板级DT、传感器、主线框架及手机安装文件均未改。349 IFE Gamma候选仍未安装，也未将IPE256段误交给VFE64段或旧OPE直接表接口。

下一步优先提取LTM reserve/inverse-Gamma设置、IPE CCM13及相关静态覆盖值，继续核清实际输出域；再决定现有VFE的可表达方案或后级支持。之后才组合发布Gamma。曝光表/防频闪/真实传感器限幅、更多模式、正常照明光学、多摄几何同步及连续AF仍待完成。
