# 335：色温、白平衡与硬件色彩矩阵联动

2026-10-20。332候选IPA已接入333原厂CCM触发树和334硬件后端，显式矩阵、手动色温、通道增益及自动白平衡可通过同一参数revision联动。20项真实AArch64 IPA检查、四摄内部测试图五组配置六阶段采集通过。候选临时运行后已恢复原模块和服务，安装版本仍为r26/config-r21及298/305/318/325；完整目标active。

改动集中在用户空间通用矩阵数学、可选配置解析、参数编码和CAMSS管线控制分发。没有新增板级DT、传感器驱动或内核改动，实机临时复用334 CAMSS。新增可选`colour_correction`，保留DRC→HDR AEC→显式LED分支→AEC→CCT完整树，按原区间内保持、间隙插值及逐层舍入规则处理。矩阵依赖本revision的显式手动色温或硬件量化后WB增益推导的色温。AEC/lux、DRC、HDR、LED坐标目前明确来自`reference_triggers`诊断值，不能称为完整场景动态调校。[增量补丁](0033-camss-colour-correction-coupling.patch)。

只在启用CCM配置时公开`ColourCorrectionMatrix`。手动矩阵优先；随后仅发送色温或增益可恢复表驱动矩阵。AWB开启会清除手动矩阵和手动色温标签，矩阵跟随实际有效WB估计色温。零通道增益无法估计色温时保留上一矩阵，启动时使用单位矩阵，不编造色温。矩阵先按12位有符号系数和Q7～Q10量化，元数据报告有效3×3 RGB矩阵；只在SOF确认后应用对应帧历史。旧配置不添加矩阵块或控制。WB/BHIST/LSC/CCM启动包1888字节，普通CCM更新96字节，无CCM旧更新56字节。

诊断表明确选择五份调校文件的Default UID37，WB仍为MWB UID117/refPtV1 UID79。发现前摄原厂CCM根`enabled=0`，两个正常factory/unit配置保留关闭；另加两个明确标识的前摄实验启用配置验证链路，不能当作原厂默认。主摄Qtech/Sunny两分支分别测试，尚未绑定本机供应商。所有原厂表、参考点和个体数据均留在私有输出目录，没有写入公共源码或默认配置。[配置范围](profile-validation.json)。

独立参考直接编译保留的固定版本CamX `GetIndexPtTrigger`、`CalculateInterpolationRatio`、`InterpolationData`、`CalculateHWSetting`与原舍入助手，为每配置生成1500～12000K整数温度对应的期望矩阵。参考不是本次通用实现，也不是原厂HAL整段指令执行。335复用333原始来源记录，不再下载或核验未改文件。[原始来源](../kernel333/primary-sources.json)。

核心库和签名IPA增量构建119.46秒成功，原SDK工作目录恢复。完整库沿用基线werror=false；合同与采集工具使用Werror。20项实际AArch64 DSO检查包括十个factory/unit、两个前摄显式实验配置、合并LSC启动包及不足容量拒绝、五项新配置错误、真实RGB统计驱动AWB反馈、旧无表配置。矩阵包与独立参考一致，延迟SOF前后及统计元数据、矩阵覆盖/清除、相同增益但矩阵策略改变、零增益回退均通过。[构建](build-validation.json)、[IPA检查](ipa-contract-validation.json)。准备时修正了Meson源列表匹配；测试工具的76字节文件记录不能按带尾部对齐的80字节C结构整读，已改为分别读取40+36字节，失败日志保留私有目录。

手机R1 worker19479终态完成。临时334 CAMSS搭配335核心库和签名IPA，GW1 Qtech/Sunny两分支、IMX319、S5K3M5及前摄显式启用实验共五组，均运行6500K→2850K→手动非对称矩阵→6500K恢复→手动增益1.25/0.75→AWB。253帧、30张内部图，按参数确认后图像稳定结束。253帧矩阵元数据与独立表结果或已请求手动矩阵一致，147帧增益估计色温另对原厂指令包装函数检查，整数K误差0；五组AWB均锁定。五组手动矩阵均有真实图像变化，恢复6500K图像均与初始逐字节相同，手动增益与自动AWB图像也不同。[采集](probe-r1-validation.json)、[元数据与图像](ccm-metadata-image-validation.json)。这是内部图案和参数链路证据，不是正常照明光学校准。

原模块note与实验前相同，未替换安装文件、包、Image或DT。媒体/控制恢复，相关故障delta0、taint0，CAMSS/两CCI休眠，九相机电源disabled/users0。PipeWire19667、WirePlumber19708各一个uid10000进程。[最终状态](final-state-validation.json)。没有刷写、重启或写EEPROM/OTP/NV/persist。R1摘要沿用334的`temporary_module_only`字段名称；实际同时临时使用候选核心库与IPA，运行构建记录明确列出这点，后续worker字段改为`temporary_userspace_and_module_only`。

后续候选基线为`/home/cy122/x2pro-linux/libcamera214-root/work/libcamera335-ccm-built/src/libcamera-v0.7.2`，累积330/332/335用户空间修改；内核基线为334已验证提交。继续优先确认AEC lux实际语义和动态LSC/CCM触发、模组供应商绑定及统一发布；正常照明颜色/阴影、多摄几何/同步和连续AF仍未完成。关灯不妨碍继续源码和内部图工作。
