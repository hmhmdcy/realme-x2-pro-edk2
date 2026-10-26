# 332：个体参考点驱动的逐帧色温估计

2026-10-20。331反向色温模型已接入候选IPA，手动通道增益与自动白平衡均可报告由已应用增益推导的色温。四摄内部测试图、15项真实AArch64 DSO测试通过。候选只由实验进程临时加载，系统仍为r26/config-r21和298/305/318/325组件，完整目标active。

在330的可选`white_balance_reference`中增加10组`reference_points`，由选定refPtV1根提供，按同一组unit/golden因子逐通道校准，再配置331二维轨迹模型。反向参考点与正向MWB表分开；本次明确选择refPt UID79、MWB UID117作为诊断配置，主摄两供应商分支分别测试，未绑定本机供应商，默认配置不变。

每次编码ISP参数时，从硬件量化后的有效ColourGains倒数得到R/G、B/G，计算估计色温并存入该revision的参数上下文。启动、手动增益变化、AWB反馈都走现有参数队列，只有收到SOF确认后相应帧才报告该估计。显式手动ColourTemperature标签仍优先；无反向参考点的330配置继续保留原行为，未配置WB参考的旧配置不产生占位色温。

这项自动色温是**已有灰世界AWB增益结合个体参考点得到的估计**，没有移植整套原厂AWB场景分类，也没有正常照明光学精度结论。CCM联动仍未实现，因此不能把候选称为ColourTemperature全部标准语义完成；动态LSC/lux也尚未联动。核心库和内核沿用330/318接口，本轮仅改IPA与通用数学，[0032增量补丁](0032-camss-calibrated-cct-estimation.patch)，无SoC、板级DT或传感器驱动改动。

候选签名IPA构建成功，SDK原工作树已恢复。15项实际AArch64 DSO检查全过：十个factory/unit配置的手动CCT/增益反推与SOF/统计元数据、330无反向表配置、旧配置、新配置拒绝/禁用，以及真实合成RGB统计驱动的AWB反馈与延迟确认。后者确认估计色温随已应用增益更新。[构建](build-validation.json)、[DSO结果](ipa-contract-validation.json)。完整IPA沿用基线werror=false，合同与采集工具以Werror构建。

手机五个unit参考配置覆盖四颗传感器：GW1两供应商分支、IMX471、S5K3M5和IMX319。内部图从手动增益1.25/0.75切换AWB，按实际锁定和稳定图像结束；共观察153帧、保存10张图，五组均锁定且自动图与手动图不同。所有153帧估计色温与独立原厂指令包装函数结果一致，整数K舍入误差0；不以固定帧数作门槛。[采集](probe-r1-validation.json)、[独立元数据核对](cct-metadata-validation.json)。不需要室内灯光。

手机`/var/lib/samurai/k332-cct-r1` worker16581终态，媒体/控制恢复，相关故障delta0/taint0，CAMSS/两CCI休眠、九路相机电源disabled/users0。PipeWire/WirePlumber各一个uid10000进程，最终PID16618/16621。[最终状态](final-state-validation.json)。没有包/模块安装、重启、刷写或EEPROM/OTP/NV/persist写入。私有配置、参考点、推导色温期望、完整日志和图像留在kernel332输出目录，公共镜像仅含通用代码及汇总。

候选源`/home/cy122/x2pro-linux/libcamera214-root/work/libcamera332-cct-built/src/libcamera-v0.7.2`是后续集成基线，累积330的0031和本轮0032；发布时不要由旧321生成器覆盖。下一步优先提取原厂CCM参考和触发规则，复用现有CAMSS_PARAMS_COLOR_CORRECT接口实现温度/手动矩阵联动，再推进动态LSC及AEC lux语义。正常照明光学、供应商绑定、多摄几何/同步和连续AF等仍在完整目标内。
