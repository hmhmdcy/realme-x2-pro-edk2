# 347：从原厂调校包提取完整 IFE Gamma

2026-10-20。按用户“没有色卡，反编译原厂刷机包获取校准数据”的要求，复用已从原厂包及本机vendor保留的调校BIN，继续提取未接入的Gamma。没有重复下载刷机包、读取EEPROM或运行原厂相机服务。此前四摄WB/CCT、LSC和CCM已在344默认私有配置中启用；本轮新增Gamma提取、模式对应及通用编码，尚未安装。

五份调校的全部IFE Gamma共17个根、51条65点通道曲线。独立二进制解码保留DRC/HDR/LED/AEC/CCT完整树、开关和控制轴，全部与保留原厂解析器XML一致。分析副本只屏蔽其它模块的版本元数据，原始BIN、载荷和模式树未改。[提取结果](factory-gamma-validation.json)、[解码工具](decode-gamma.py)。

原厂通用模式管理器继续复用343，新增Gamma标签的511个上下文查询与独立ModeTree零差。已有几何依据的七模式、Preview/Video共14上下文均选根36、开启Gamma；前摄1928裁剪仍无原厂模式对应。本机主摄沿用已确认的Sunny执行器方案，其它来源不据文件名重新猜供应商。[模式结果](gamma-mode-validation.json)。

这五份BIN的51条曲线实际上完全相同，跨触发区和通道也相同，因此这些来源的IFE Gamma可先用静态曲线表达，无需凭空增加动态Gamma算法。这只是所保留IFE数据的结论，不能扩展为BPS/IPE、HDR合成或整套Android画质链等价。曲线、解析XML及原始数据仅保存在仓库外。

通用 [编码器](libipa/gamma_curve.cpp) 把65个浮点节点编码为64个VFE175原生字：低10位base和有符号10位delta，末端节点用于最后一段斜率。半值按roundf规则、base/末节点和斜率按原规则限幅。输入仅接受有限的0～1024值，非法值拒绝；不复制原厂代码到公共实现。原厂公开来源例程和相应round/clamp辅助函数仅在私有目录编译作参考；主机及AArch64各41项、10660字节零差。51条相同工厂曲线只测一次，并补端点、半值、反向斜率及无效输入。[数学结果](gamma-math-validation.json)。这是固定来源代码参考，不是目标HAL逐指令仿真。

硬件现有Gamma初始化仍来自输出传递函数。既有公共 `CAMSS_PARAMS_GAMMA` 描述的是OPE的256项直接表，不能把本机64段原生表填进去冒充已接通。下一步应在通用typed params框架补IFE原生Gamma语义、VFE175后端及DMI/生效帧管理，再由IPA按模组配置提交；不把原厂曲线硬编码进SoC驱动或板级DT。Gamma接入前手机仍为344默认基线，r27/r22及Image298、传感器305/325、CAMSS338不变。

固定来源的 [Gamma schema](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/api/chromatix/XSD/isp/gamma_1_6_0.xsd) 和 [Gamma16 setting](https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/camx/src/hwl/iqsetting/gamma16setting.cpp) 的精确路径及指纹见 [来源清单](primary-sources.json)，下载仅涉及五个缺少文件。通用原厂IQ不替代EEPROM/OTP个体值；本机个体WB/LSC此前已只读提取并接入。没有色卡仍能推进这些工作，但不能据调校解包宣称绝对色彩精度或完整适配完成。完整goal active。
