329后续已确认：按记录索引配对unit/golden，再按factory CCT分组，payload CCT在该步骤不参与；328尚未确认的对应语义已解决。[329实现](../kernel329/README.md)。下文为328当时记录。

# 328：四摄 WB 标定来源与原厂算法路径

2026-10-20。本轮补齐四摄及主摄两套未绑定调校的AWB参考、golden、手动增益数据，并确定本机HAL向算法传入个体WB的色温/比值语义。部署和327已通过的LSC保持，尚未启用个体WB或动态CCT，完整目标active。

优先复用保留的原厂调校、EEPROM和固定提交源码。按[CamxChi schema](https://github.com/bjzhou/CamxChi/tree/9f17f1b568626b393e785b369c5dc94543774d7a/chi-cdk/api/chromatix/XSD/stats/awb)解码，并由原厂ParameterParser导出独立XML，对照全部字段及模式选择树。保留原始payload/模式树，只在分析副本中关闭无关根的version，未重写数据表。

| 工厂调校 | refPtV1 | MWBGainV1 | sensorCalV1 |
| --- | --- | --- | --- |
| GW1 Qtech | 1 | 1 | 1 |
| GW1 Sunny | 1 | 1 | 1 |
| IMX471 Sunny | 3 | 3 | 1 |
| S5K3M5 Qtech | 5 | 5 | 1 |
| IMX319 Sunny | 9 | 9 | 1 |

共43根全部对应：19组参考点、19组手动WB、5组golden。每参考表15对rg/bg，前10对有效、后5对为零；原值保留，不修补。每手动表10组RGB，各golden声明启用、5个校准因子。[完整结果](factory-wb-validation.json)。

`sensorCalV1`确为320字节：6个8-byte头字段、1个8-byte计数、6个**连续4-byte float** CCT、15个16-byte复合rg/bg记录。最初把固定float数组也按8字节槽估算而得344，是工具字节核算错误，并非已证实的schema版本不兼容；现已纠正且完整XML核对通过。parser初次放错ParameterTuningTypes位置导致Scenario.0重叠，R1/R2输出不能作为场景绑定证据；R4将该文件放在输入schema目录，完整选择树对应，旧输出只留私有排障目录。

四摄个体WB复用299/326读回。结合当前类型描述和本机HAL `FormatWBData`实际指令，确认INDIVIDUAL/LITTLE、qValue=1；R/Gb、B/Gb、Gr/Gb按float32分别除以qValue。qValue零时原厂回退1；Gr/Gb只在mirror非零且invert标志开启时取倒数。本机mirror掩码均0，所以主/前/长焦虽invert=1也不倒置；广角invert=0。五光源枚举依次D65、TL84、A、D50、H，全部分母和输出为正；保留326通道值，未新读EEPROM。[格式语义](unit-wb-format-validation.json)。个体值与组合数据仅保存在私有kernel328。

从本机HAL函数0x405878～0x405d84确认，它按有效记录顺序复制r/g、b/g，并从VA0xdd800常量表赋予以下CCT；这里不是采用其它版本的通用常量：

| 输入光源 | HAL算法payload K | GW1 golden K | 前摄 golden K | 广角/长焦 golden K |
| --- | --- | --- | --- | --- |
| D65 | 6500 | 6500 | 6500 | 6500 |
| TL84 | 3800 | 3900 | 3800 | 4100 |
| A | 2850 | 2800 | 2850 | 2850 |
| D50 | 5000 | 5000 | 5000 | 5000 |
| H | 2300 | 2300 | 2300 | 2300 |

因此把两个数组同索引直接除、把标定点直接当当前测得CCT，都不能声称复现OEM算法。已将两套坐标分开保留，待实际算法的光源分组/标定规则处理。[绑定证据](wb-reference-binding-validation.json)。当前灰世界AWB尚无CCT估计；不能凭这些数据向应用发布伪造色温，也不能把ExposureValue当OEM lux index。

为继续追踪真实标定/色温/lux转换，仅从vendor以ro/noload/noexec补取AWB、AWB wrapper和AEC三个算法组件，已卸载，没有加载或执行原厂代码。无需再次读取HAL或EEPROM。组件指纹、字符串交叉引用与unwind边界见[算法来源](algorithm-source-validation.json)。当前离线定位：

- AWB标定入口0x2ab90～0x2af88；golden/MWB校准0x85b8～0x935c；校准数量与光源分组0x9e30～0xa8fc。
- AWB GetGainFromCCT 0x9bc0～0x9d70；GetCCTFromGain 0x9d70～0x9e30。
- AEC CalculateLuxIndex 0x4b088～0x4b220及0x4b238～0x4b5a8；EstimateLuxIndexForSlave 0x46990～0x46ac4。

这些函数名由自身日志和FDE定位，不能把objdump最近导出符号当真实名称。下一步读取这些已定位的小函数，复现必要数学/输入语义后接入通用libipa/IPA，避免为每颗sensor/板级复制调校算法。四摄光学校准、动态调校、多摄几何/同步仍未完成。

本轮没有新相机采集、模块/包安装、刷写/重启，也未写EEPROM、OTP、NV或persist。相机状态复用[327恢复证据](../kernel327/final-state-validation.json)，无必要重复完整四摄回归。用户关灯不影响上述离线工作。
