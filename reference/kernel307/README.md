# 307：VFE175硬件RGB网格统计

2026-10-19。公共CAMSS候选已在IMX319广角和S5K3M5长焦各采集36组RGB统计与图像，同SOF对应、计数／求和范围和包边界通过。候选仅临时加载，实验后恢复已部署CAMSS；产品仍为RAW＋CPU ISP。AWB算法、IPA解析／参数回写、主前摄硬件成像及完整校准继续推进。

源码树/home/cy122/x2pro-linux/camera307-rgb-kernel，分支samurai-rgb307，提交ba9b36e8f872017ad2a39480a223a3afb76e1488。[补丁](vfe175-rgb.patch)、[源码状态](source-state.json)、[实测结果](rgb-capture-validation.json)。

## 来源与分层

复用[306固定的CamX和Realme原厂内核主来源](../kernel306/awb-primary-source-validation.json)，并静态分析原厂刷机包lib64/hw/camera.qcom.so。未加载或执行厂商库。[寄存器分析快照](oem-register-analysis.json)保留当时尚未实现／实测的状态，不替代本阶段实测结果。

原厂ARM64指令确认AWB BG配置0xbc8～0xbe0、Y配置0xc14、采样／移位配置0xcb0、enable bit3；BHIST仍bit4。全局0xaac的quad-sync bit6由原厂OR 0x40、对应CamX逻辑与旧寄存器头交叉支持，本次置位后正常采集；未单独切换该位证明其功能，也未完成整个原厂output-port结构的恢复。旧VFE4.8头中的0xab0地址没有移植过来。[固定单体CamX实现](https://github.com/tadiphone-caf/vendor_qcom_proprietary/blob/9a79e3c6b709ced2c53befa46628395989d8892b/camx/src/hwl/ispiqmodule/camxifeawbbgstats14.cpp)

改动落在SoC公共参数／统计与DMA层：BG client15和BHIST client16共用现有统计输出、完成组1及SOF标记。两个DMA地址独立且256字节对齐，停流停止两个WM后返回缓冲。未改DT、供电接线、传感器寄存器或个体调校。

新RGB块包含网格几何、U14阈值和逐区域R／B／Gr／Gb求和及有效样本数。常规硬件区域为6个32位字，内核去掉保留位，输出4个32位和4个16位值。当前驱动自动选择至多32×24的居中偶数网格，几何随输入模式返回，不提供动态BG区域配置。BHIST区域仍可独立更新。

通用层增加可选统计序列化回调和每输出的缓冲尺寸；未实现该回调的后端保留原BHIST布局。本候选VFE175统计包增至22568字节，303硬件IPA的固定4112字节检查尚未适配，**不能将本模块单独装成产品部署**。下一步让IPA按块解析、保持旧BHIST输入兼容，再接AWB。

## 实测

| 输入 | RGB网格 | 每区域尺寸 | 偏移 | 每色有效样本数 |
| --- | --- | --- | --- | --- |
| IMX319 RGGB10 1632×1224 | 32×24 | 50×50 | 16,12 | 480000 |
| S5K3M5 GRBG10 2104×1560 | 32×24 | 64×64 | 28,12 | 786432 |

共72张硬件NV12图像／72份统计。每份RGB与图像SOF一致；所有768区域的每色计数均不超过区域Bayer样本数，求和不超过计数×16383，元数据末尾未越界。使用普通实景，未启用sensor／CSID图案。

四阶段为默认减黑／WB unity、加入减黑、改变WB、再提高模拟增益。广角减黑4096 U16对应1024 U14，各色均值约下降1023.9；长焦3840 U16对应960 U14，均值约下降960。随后改变WB时RGB均值基本保持，支持RGB统计位于BLS之后、WB之前；广角再提高模拟增益，RGB均值约翻倍。长焦低照度下有残余底座，不能把其均值直接当作去偏后的光信号，也不据此声称完成暗场或AWB标定。

临时参数只用于观察硬件响应，不是正式调校。初始采集和停止路径已实测；BG双WM的长时运行、饥饿恢复、元数据晚启动与跨图像重开仍需在IPA接入时覆盖。

只构建CAMSS及链接所需的六个既有依赖模块，最终W=1／Werror诊断0。前两次在单模块modpost缺少模块导出符号时失败；最终将实际依赖闭包放进同一次树内构建后通过。只取CAMSS候选，构建输出恢复，依赖模块未部署。[构建结果](kernel-build-validation.json)

两次手机worker均终态；原CAMSS加载note与磁盘模块一致，PipeWire／WirePlumber各一进程，CAMSS／两CCI休眠，九相机供电关闭且用户0，taint0，无新增所检查内核故障。图、格式、控制通过既有fixture恢复。没有刷写、重启或更换系统库；私人原始包、图像及8份统计样本保留在私人目录。

## 后续

下一步将RGB块解析接入硬件IPA，输出区域有效性和通道均值，再实现AWB增益提议、参数完成SOF与实际生效元数据关联。结合原厂模组资料和个体校准确认黑电平、颜色、阴影及模式绑定；低照度、饱和和单色场景不能直接套全图灰世界。继续主／前摄、其它模式及产品硬件路径接入，目标仍active、未完成。
