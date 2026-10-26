# 327：四摄个体 LSC 链路补齐

2026-10-20。326取得的主摄GW1、前摄IMX471、长焦S5K3M5主表已与对应工厂golden合成，通过现有r26 IPA送入318 CAMSS硬件。结合322广角实测，四摄均已有真实个体LSC临时应用证据。默认调校仍未启用个体表，完整适配目标保持active。

全部采用内部测试图，不依赖室内光照。仅临时运行配置，没有新内核/驱动/包安装，不把个体数据放进SoC代码、板级DT或公共仓库。主摄两份不同工厂配置分别测试，尚未确定本机供应商；不能因其中一份能出图而自动绑定。

使用明确的Default根UID25、OEM lux index=100、CCT=6500、LED=0与EEPROM光源0主表，作为诊断坐标，并非测得当前环境或完成OEM动态场景选择。长焦光源2原描述GR低字节地址异常保持原样，本轮不选择或修补它。全部正值输入有效；未知工厂checksum不阻断本次可回退试验，也不宣称校验完成。[组装配置](profile-assembly-validation.json)。数字表与配置仅在私有kernel327目录。

| 相机/工厂分支 | 实际传感器输出 | 成对配置 |
| --- | --- | --- |
| GW1 Qtech、Sunny，各自测试 | 4608×3456、4608×2592 | 各模式factory/unit，共8次 |
| IMX471 Sunny | 2304×1728、1928×1088 | 各模式factory/unit，共4次 |
| S5K3M5 Qtech | 2104×1560 | factory/unit，共2次 |

复用325模式选择/标准TEST_PATTERN采集工具和313媒体恢复fixture，正常系统libcamera/IPA加载；GW1选择Shade Color Bars，Sony/长焦选择淡灰图。每例实际ACTIVE尺寸读回匹配，测试图流中切换成功，获取稳定帧后立即停止，最终45帧是观察数量，没有固定帧数验收门槛。14例均成功并恢复媒体/控制。[设备结果](probe-r1-validation.json)。

用真实AArch64 r26 IPA DSO导出14份1792字节LSC块，与独立Python Hermite重采样/float32校准/GR-GB均衡/Q10模型核对，12,376个通道值完全相同；此项针对新配置，不重跑未改组件的全量回归。[编码核对](ipa-mesh-validation.json)。

7组unit图像均不同于对应factory；7份factory与323/324/325保留的相同配置结果逐字节一致，因此复用原关闭LSC基线。原基线梯度确定彩条边缘和灰阶重置行的排除区，未依据unit差异挑选像素。近似独立图像模型的unit p99误差约GW1 1.68～1.80、前摄1.49～1.54、长焦1.17/255；最大约3.45、8.95、2.25。这里存在Bayer/缩放/空间插值近似及NV12反推/裁剪误差，不能当作RAW光学精度或均匀照明效果。[成对图像分析](unit-image-validation.json)。

采集worker终态，PW/WP恢复各一个uid10000进程；CAMSS/两CCI休眠、九相机电源关闭用户0，相关故障增量0、taint0。[恢复状态](final-state-validation.json)。部署保持298 Image＋305长焦＋318 CAMSS＋325 GW1，libcamera r26/config-r21；未刷写、重启、写EEPROM/OTP/NV/persist。

下一步继续可解释的动态AEC/CCT触发、供应商与光源绑定，以及WB个体数据/原厂参考。不能直接把ExposureValue冒充OEM lux index。正常光线下的阴影/颜色/黑电平、畸变内参、多摄几何与同步、曝光语义和连续AF仍未完成，需与当前已通过的配置链路区分。
