# 322：原厂触发选择与广角真实个体LSC试验

2026-10-20。IMX319原厂LSC完整触发树已独立解码，并将320修正的真实个体表经已安装r26 IPA应用到318 ISP，内部灰阶图试验通过。正式包仍321的r26/config-r21，默认四摄调校保持；完整多摄校准目标active。用户已关灯，内部图案不依赖房间照明。

原厂二进制七个根与原厂解析器七个XML入口逐项对应，比较包括所有触发节点、基础表和golden。实际上只有三套完整配置：Default/Sensor.1为UID25/130，Sensor.0/Usecase.33为1262，四个Sensor的Preview/Feature1.12为186/456/710/989。后两组中的多个UID分别完全相同。此前只比较增益集合的报告无法区分AEC阈值，已明确标注其局限；以[完整树结果](trigger-tree-validation.json)为准。

固定版本[IQSettingUtils::GetIndexPtTrigger](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/hwl/iqsetting/iqsettingutil.cpp#L257)确认：触发值落在某个区间内时保持本表，只在前一区间end至下一区间start的间隙插值。原厂使用lux index与CCT，不能把当前ExposureValue直接当作OEM lux index。本轮显式选择Default、lux index 100、6500K；它们是诊断坐标，并非测得的当前暗室参数，也不代表复现了Android场景/Feature选择。

[配置组装器](assemble-profile.py)支持AEC/CCT两级插值，父级lens/DRC/HDR/LED在现存表均单分支；若将来遇到多分支则要求补充真实选择参数。生成关闭、factory、factory+golden/unit三份私有配置，实际几何沿用321确认的约定。10个边界向量、非有限值拒绝，以及七根504组实际触发组合通过。[结果](profile-assembly-validation.json)。个体值保留在私有目录，不进入公开调校包。

实际AArch64 IPA DSO生成的两份LSC块与独立Python Hermite重采样、单精度golden/unit合成及Q10量化比较，每份884个编码字全部一致。网格为52×52 quad、起点8/6、细分1。[网格结果](ipa-mesh-validation.json)。本轮只增加离线配置组装和分析工具，通用数学仍在libipa，调校仍在用户空间，不向板级DT或传感器驱动塞入模组表。

设备使用系统已安装、正常签名的r26 IPA，没有候选DSO覆盖。三个内部图案配置各在实际稳定条件下得到3帧，媒体图/控制恢复成功，PW/WP恢复，CAMSS与两CCI休眠，所有相机电源无用户并关闭，相关故障增量0、taint0，worker终态。[设备结果](native-r1-validation.json)。本轮未改软件包、内核模块或工厂存储。

图像中factory和unit都区别于关闭，unit也区别于factory，确认真实个体补偿产生效果。43,008个彩条内部像素的近似模型：双线性p99误差分别1.954和1.874/255，双三次分别1.757和1.687/255；平均误差0.38～0.41/255，最大约10.8～11.1/255。模型由NV12基准反推线性RGB，并近似Bayer重建与缩放，不能据此确定硬件插值实现或宣称完成光学校准。[图像分析](native-r1-image-validation.json)。

322完成后，真实个体LSC从“尚未应用”推进到“临时实际链路通过”，默认仍未启用。工厂checksum未确认，仍不宣称验证完成；它不阻塞这些可回退的运行配置试验。下一步继续其它三摄调校/个体布局与模式映射、通用动态触发衔接，以及正常照明的阴影/颜色/黑电平、畸变、多摄几何与同步。不得将正常光照项目延期扩大成全部工作暂停。已有四摄NV12、RAW/双流、单次AF和消费者证据沿用315/316/321，连续AF及四实体同时流仍未完成。
