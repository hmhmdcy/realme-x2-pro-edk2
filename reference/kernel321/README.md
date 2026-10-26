# 321：LSC用户空间闭环与r26正式包

2026-10-20。已部署libcamera `99990.7.2-r26`、config/stack `0.1.0-r21`。318 CAMSS、298 Image及305 S5K3M5模块保持。LSC的调校读取、golden/unit合成、模式网格重采样和参数序列化已接入实际IPA，并经过传感器内部图案的完整取流链路验证；默认四摄调校尚未添加真实个体LSC。完整目标active，正式光学及多摄校准仍未完成。

## 分层与实现

通用合成／重采样在libipa，源自317／319；CAMSS IPA只读取模式调校、量化并编码LSC参数。内核继续由318处理硬件几何与DMI，不增加板级DT或传感器私有调校。沿用现有IPC、帧参数队列、AE/AWB及AF；本轮未改V4L2核心、传感器驱动或硬件寄存器序列。

可选`lens_shading`模式字典接受`source_span`、`first_quad`、`quad_step`三对源Bayer格坐标，以及`gains`的r/gr/gb/b四组221点。可同时提供`golden`和`unit`，按golden/unit合成并均衡GR/GB；缺省不校正，`enabled: false`显式关闭。配置沿用已有模式尺寸／时序选择。静态网格只在启动revision0发出，后续AWB增益更新仍是原56字节包，不反复上传DMI。

[IPA](ipa/lens_shading.cpp)、[参数编码](ipa/parameter_encoder.cpp)、[通用重采样](libipa/lsc_resample.cpp)、[增量补丁0030](0030-camss-lens-shading.patch)。补丁已在实际r25源上dry-run通过；默认设备YAML内容保持，包内不含个体校准值。

## 几何依据

IMX319当前原厂mode2为模拟窗口3280×2448、2×2 binning、数字裁剪左4／上0，再输出1632×1224；mode0为数字裁剪左8后输出3264×2448。两者在物理阵列均从(8,8)取样，覆盖同一视野，不能以3280/1632猜测binning。

[固定CamX IFENode源码](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/hwl/ife/camxifenode.cpp)用mode0输出作为LSC全尺寸参考。结合原厂XML及当前驱动相同的几何寄存器，该约定下的源跨度为1631/1223、首quad为0/0、步长2/2。[记录](imx319-mode-mapping-validation.json)。这是固定源码约定与本机寄存器的对应；尚未反汇编本机HAL里fullResolution赋值，不能声称所有版本完全一致。模拟裁剪／binning／数字裁剪的分层符合[libcamera传感器模型](https://docs.libcamera.org/master/camera-sensor-model.html)及[Linux传感器接口](https://docs.kernel.org/userspace-api/media/drivers/camera-sensor.html)。

## 验证和部署

实际AArch64 IPA DSO完成缺省、LSC合成／仿射映射、显式关闭和无效单位表的测试，保留AE/AWB及参数历史行为。[契约](ipa-contract-validation.json)。首次LSC断言错误地把ENABLE写成数值1，已改为UAPI宏；产品编码本身一直使用正确宏。

新IPA经系统r25核心加载后，在IMX319内部灰阶彩条上测试关闭、单位、统一1.5倍、二维渐变及合成后的R2.5/G1.25/B3.375。每种按实际图像稳定条件在3帧收敛；单位与关闭逐字相同。对43,008个彩条内部像素，独立线性RGB模型的99百分位误差不超过1.929/255，最大误差8.875/255，均值不超过0.404/255。模型从基准NV12反推线性RGB，不是独立RAW或光学校准。[采集](native-r2-validation.json)、[模型](native-r2-image-validation.json)。首次r1工具只接受单平面NV12，取首帧后失败；支持完整多平面后r2通过，失败时媒体状态和服务均恢复。

完整13个签名包、6个IPA保留，升级七个运行包。打包后的r26四摄分别GStreamer640×480 NV12通过；安装后的系统GStreamer与PipeWire广角各12帧通过，四摄节点正常。[构建](package-build-validation.json)、[产物与签名](package-artifact-validation.json)、[四摄](product-r1-validation.json)、[安装](install-r1-validation.json)。六模式RAW／双流、主摄单次AF和高分辨率的未改部分沿用315／316证据，没有冒充本轮全量重测。

安装后PW/WP各一个进程，相机和两CCI休眠，相关故障增量0、taint0。所有本轮worker结束。回退包、world及仓库配置保存在`/var/lib/samurai/k321-install-r1`；安装事务假设r25/r20前置，不能在当前r26/r21上重放。未刷写或重启，未写EEPROM／OTP／NV／persist。

## 后续

最新完整包源为SDK `work/libcamera321-lsc-built/src/libcamera-v0.7.2`；316源保留，原`work/libcamera`已恢复。不要用旧316/315生成器覆盖321源。正式配方见linux-port/packages。

320已解决原个体表的4个零节点：每51点跳过一个0xff字节，原始值无需修复。下一步确定原厂基础表／golden的模式与触发选择，使用已保留数据进行可回退的真实校准配置试验；同时继续核查原厂有效性约定。未找到checksum算法不应成为所有只读分析或可回退实验的新硬门槛，也不等于校验已完成。还需其它三摄的对应调校、正常照明下的阴影／颜色／黑电平、畸变内参、多摄几何同步、真实曝光时间及连续AF。用户已关灯，继续可独立完成的源码、原厂数据和内部图案工作。
