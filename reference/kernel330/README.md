# 330：可选个体白平衡与运行中色温控制

2026-10-20。329的通用校准/MWB/CCT数学已接入隔离libcamera候选，四摄内部测试图通过。候选核心库与签名IPA仅由采集进程临时加载，系统仍为r26/config-r21及298/305/318/325内核组件。完整目标保持active。

可选模式配置`white_balance_reference`接收10组MWB RGB增益及可选的同索引factory CCT/golden/unit记录；复用329的unit/golden校准、比值转换和线性Kelvin查表。未配置或disabled时不提供ColourTemperature控制，默认四摄配置没有改变。主摄两供应商配置分别试验，尚未确认本机供应商。

ColourTemperature可在1500～12000 K请求；AWB关闭且未给显式ColourGains时转换为通道增益，沿用现有参数队列、ISP编码及SOF确认。元数据只随已应用的参数历史更新；显式ColourGains优先，单独给增益会清除手动色温标记。AWB开启时维持原自动算法，不伪造测量色温。候选将核心控制方向声明为inout，但任意增益反推色温、自动CCT估计及CCM联动仍未实现，不能称完整标准色温语义或正常照明颜色校准。

变更在[0031补丁](0031-camss-calibrated-white-balance.patch)，涉及通用数学、IPA配置/控制/元数据、框架请求转发及控制声明；无板级DT、SoC、传感器/内核驱动改动。现有CAMSS参数接口承担实际硬件增益，不在应用层对图像做软件补色。候选源为`/home/cy122/x2pro-linux/libcamera214-root/work/libcamera330-wb-built/src/libcamera-v0.7.2`，原SDK工作树已恢复。

核心和签名IPA构建成功；13项真实AArch64 DSO测试覆盖五来源factory/unit、启动/运行中请求、Q10编码、SOF前后与统计元数据、旧AWB、禁用及无效输入，全部通过。DSO/probe以Werror构建；完整libcamera沿用基线Meson werror=false，不能混称全库Werror。[构建](build-validation.json)、[DSO结果](ipa-contract-validation.json)。

手机14组采集共观察95帧，保存24张稳定内部图：四个旧配置unity基线，以及五来源factory/unit各6500/2850 K。四份unity结果与保留基线逐字节一致；20份色温输出元数据增益匹配硬件量化参考，十组unit/factory同色温输出均有差异。独立NV12近似模型平均误差0.316～0.457/255、p99约1.21～1.45/255；模型近似Bayer/缩放/截断，不是RAW光学精度。[采集](probe-r1-validation.json)、[图像分析](image-validation.json)。使用GW1 ShadeColorBars和其余传感器内部灰阶图，不依赖室内灯光。

所有worker终态、媒体/控制恢复、相关故障增量0、taint0，CAMSS与两CCI休眠、九路相机电源关闭且用户0。PipeWire/WirePlumber各一个uid10000进程，最终PID15580/15583。[最终状态](final-state-validation.json)。无软件包/模块安装、重启、刷写或EEPROM/OTP/NV/persist写入。私有配置、校准数值与图像保留在输出目录kernel330，公共镜像不包含这些数据。

下一步推进逆向CCT估计、CCM与动态LSC/lux衔接；供应商绑定、正常照明光学、多摄几何/同步、曝光语义和连续AF仍在目标范围内。发布新包应使用330隔离源及0031，不能由旧321生成器覆盖。当前候选尚未发布/安装。
