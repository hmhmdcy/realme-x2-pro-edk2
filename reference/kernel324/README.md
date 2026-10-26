# 324：主摄/前摄原厂LSC与前摄两模式实机

2026-10-20。已解码主摄两套及前摄原厂LSC，前摄2304×1728、1928×1088两模式经系统r26 IPA→318 ISP→NV12内部图案验证。主摄LSC实际取流尚未完成；当前GW1驱动缺少标准测试图案控制，已取得厂商同传感器实现依据用于继续补齐。完整目标active，默认包/调校和内核保持。

本轮从本机原厂vendor只读取得qtech_s5kgw1、sunny_s5kgw1、sunny_imx471三份调校，来源与298留存指纹一致，合计约96.6MB。挂载使用ro/noload/noexec并正常卸载，没有执行厂商代码或写工厂存储。[来源](factory-source-validation.json)。复用322完整类型解码器和原厂数据解析器，六个IFE LSC根的所有触发节点、基础表及golden逐项一致：Qtech命名的主摄2根/5区域，Sunny主摄2根/18区域，前摄2根/22区域；三文件各2个golden。[完整树](factory-lsc-validation.json)。

主摄Default与Sensor.9分别独立，前摄Default与Sensor.1 Preview/Feature1.12也不同。诊断配置显式用Default、OEM lux index100、CCT6500K、LED0，不当作当前场景测量。主摄两文件差异显著，尚未绑定本机个体，不把一套命名文件直接当作正确供应商。模组描述中qtech_s5kgw1的EEPROMName甚至写Sunny_19696，进一步说明名字不足以确定实际供应商/项目。

按原厂模式寄存器及321固定CamX的mode0输出参考约定，四种模式的映射如下；不是以输出尺寸猜测binning。当前主摄和前摄原厂模式相关几何寄存器与已有驱动一致；前摄旧裁剪模式直接解码实际CCI宏。

| 模式 | 源跨度quad | 首quad | 步长 |
| --- | --- | --- | --- |
| GW1 4608×3456 | 4639/3471 | 16/8 | 2/2 |
| GW1 4608×2592 | 4639/3471 | 16/440 | 2/2 |
| IMX471 2304×1728 | 2303/1727 | 0/0 | 2/2 |
| IMX471 1928×1088 | 2303/1727 | 200/302 | 2/2 |

主摄mode0为9280×6944；当前两模式裁剪与数字偏移决定起点。前摄mode0为4608×3456，物理起点24/20；2304模式起点相同，1928模式为424/624，不能复用0/0。IMX471全分辨率仍需软件remosaic，没有启用。本机HAL fullResolution赋值仍未独立反汇编，映射参考约定的版本边界保持。[模式与私有配置生成](mode-profile-validation.json)。

只扩展采集工具的公共SensorConfiguration模式选择和ACTIVE格式读回，没有修改产品库。前摄两模式各比较off/factory，实际传感器尺寸均确认，每项按稳定条件得到3帧，内核参数/媒体恢复成功。[R3取流](native-r3-validation.json)。图像由基准梯度排除彩条边缘后，独立重采样与近似RGB模型的p99误差分别1.478/255、1.541/255，最大4.127/255、8.851/255，平均约0.34/255；不是独立RAW、正常光线或正式光学精度证明。[图像](native-r3-image-validation.json)。

R1首先在GW1读取TEST_PATTERN控制处返回6，没有取到主摄帧；媒体图/控制和服务已恢复。R2前摄off通过，factory因生成YAML复用同一gain对象产生anchor/alias，被libcamera解析器拒绝。配置生成改为每模式独立对象，复用未改采集二进制重新打包，R3通过。没有为原厂调校添加专用YAML语法，也未把失败记录改成通过。[R1](native-r1-validation.json)、[R2](native-r2-validation.json)。

GW1本机模组描述只声明关闭测试图案（0x0600=0）；[真我官方同GW1源](https://github.com/realme-kernel-opensource/realme6-kernel-source/blob/0933e0e5b2fd30faa7857f5024a86f3759713374/drivers/misc/mediatek/imgsensor/src/common/v1_1/s5kgw1_mipi_raw/s5kgw1mipiraw_Sensor.c#L16376)明确Color Bars为16-bit 0x0600=2，关闭为0。这是同传感器另一板型的来源，本机启用尚未实测，不据此把CSID图案冒充GW1内部图案。[固定来源](gw1-pattern-primary-source.json)。GitHub搜索/API没有直接返回可用内容/触发限流后，用官方仓库浅克隆固定提交取得原文件，未下载其它整套厂商载荷。

另从已有原厂模组类型表核出EEPROM读取前缀：主摄7位0x50/9984字节，前摄0x54/5682字节，长焦0x50/12272字节，均16-bit地址/8-bit数据、READ操作。本轮只核布局，没有重新读这些个体EEPROM；完整WB/LSC、有效性、绑定仍须继续，不能沿用旧错位XML。[前缀](module-calibration-prefix-validation.json)。

所有R1/R2/R3 worker均终态，最终PW/WP各一个，CAMSS/两CCI休眠，全部相机供电关闭用户0，相关故障增量0、taint0。libcamera r26/config-r21、298 Image/305长焦/318 CAMSS保持，未替换模块或包，未刷写/重启/写EEPROM/OTP/NV/persist。[服务](restored-services-validation.json)。

下一步补GW1标准TEST_PATTERN控制、实测同传感器原厂Color Bars并完成主摄LSC链路；随后继续主/前/长焦个体数据与动态触发，推进正常光线的阴影、颜色、黑电平和多摄几何/同步、连续AF。源码/图案工作不需要房间亮灯。内核只承担标准控制和SoC执行，模组表/重采样/算法继续放用户空间。
