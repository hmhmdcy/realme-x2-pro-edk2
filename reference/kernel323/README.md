# 323：长焦原厂LSC、模式映射与实际取流

2026-10-20。复用保留的本机qtech_s5k3m5sx调校和通用工具，完成长焦LSC解码及内部图案实际取流。libcamera r26/config-r21和318 CAMSS保持，默认调校未改变，完整目标active。广角真实个体LSC的322进展继续有效。

本机原厂包已在306只读提取并核对；本轮直接使用该缓存。6个IFE LSC根含94个基础区域、6个golden区域，归并为三套完整配置。复用322的有界类型解码器，再与原厂解析器输出逐项比较所有触发节点、四通道221点网格及golden，全部一致。解析器仅解析离线副本，原数据区与模式树原样。[解码](tele-lsc-decode-validation.json)、[完整交叉核对](tele-trigger-tree-validation.json)。最初交叉脚本缺少channels上下文，解析器本身已成功；补上上下文后收集已有XML，没有重跑解析器。

Default及Sensor.1 Preview/Snapshot配置为UID25/278/488；Sensor.1 Usecase33为625；Sensor.0 Preview/Snapshot为811/951。625另含LED1分支，不能一律假定LED只有一个子节点。组装器增加显式LED索引，缺少选择时拒绝多分支、不存在的索引也拒绝；本轮明确用LED0，未实现闪光混合。396组无闪光AEC/CCT组合及该分支行为通过。

原厂mode0输出4208×3120，mode3输出2104×1560；两者模拟窗口均(0,8)/4216×3120，数字偏移分别8/0与4/0，binning分别1和2，按原厂表关系均从参考(8,8)开始、覆盖相同区域。当前19.2MHz内核模式的相关16个几何寄存器与原厂mode3一致。沿用321固定CamX的mode0输出参考约定，映射为source_span2103/1559、first_quad0/0、quad_step2/2。该约定仍未在本机HAL fullResolution赋值处独立反汇编。[模式与配置](tele-mode-profile-validation.json)。

诊断配置明确选Default、OEM lux index100、6500K、LED0，不将当前曝光或暗室光线伪装成这些测量值；只采用工厂基础表，未使用长焦个体表。几何与调校留在用户空间，不改SoC/板级DT/传感器驱动，也不复制广角个体值。

系统已安装且正常签名的r26 IPA在长焦内部Fade-to-grey图案上运行关闭与factory两种配置，均按实际图像稳定条件得到3帧；105,087/115,200个YUV分量不同，平均绝对变化11.163/255，确认工厂LSC生效。此项仅证明实际链路及作用，不证明正式光学校正精度。[取流](native-r1-validation.json)、[效果](native-r1-image-validation.json)。沿用通用libipa重采样和318硬件参数接口，没有增加新传感器特判。

worker终态、媒体图/控制恢复，PW/WP恢复，CAMSS与两CCI休眠，所有相机供电关闭且用户0，相关故障增量0、taint0。未安装包或替换模块，未写EEPROM/OTP/NV/persist。[服务](restored-services-validation.json)。

下一步继续长焦个体布局与绑定、主摄/前摄对应调校和模式映射，衔接可解释的动态触发。正常光线下的阴影、颜色、黑电平及多摄几何/同步仍待完成；用户已关灯，不阻塞离线、源码和内部图案工作。连续AF及四实体同时取流没有新增验收。
