# IMX319 近黑数据后的控制链核对

2026-10-16，已授权只读子代理审查实际r13保留源及235传感器源。以下是源码差异，不是光学根因已验。

## 已确认的增益单位缺口

实际r13源在`/home/cy122/x2pro-linux/libcamera214-root/work/libcamera225-r13-built/src/libcamera-v0.7.2`。其`camera_sensor_helper.cpp`和`camera_sensor_properties.cpp`均没有IMX319注册。`soft_simple.cpp`无helper的回退将V4L2 gain code直接当倍率；IMX319 code为0..960，默认0。

[IMX319驱动](../kernel235/imx319.c)第2180行明确公式`gain = 1024 / (1024 - code)`，所以请求2.0若被直接取整为code2，只有约1.002倍。真实2/4/8倍分别是code512/768/896，最大code960是16倍。下一步应加入最小`imx319` helper，使用`AnalogueGainLinear{0,1024,-1,1024}`；此换算可与IMX471共享，型号的其它属性不能复制。

不复制IMX471的blackLevel4096、1µm unitCellSize或delay2。237的约64DN只是这一轮近黑基线，尚不是IMX319黑电平标定。仅注册gain helper后仍需验证RAW控制/元数据确实经过该helper，不能把类型存在当实际生效。

## 启动曝光与原厂表不同

[OEM表](../kernel235/imx319-oem-tables.h)第250–251行的0x0202/0x0203为0x0d04，即3332行；驱动第38/2583行默认0x04f6，即1270行。开流第2406行写mode后，第2419行的`ctrl_handler_setup`会用控制默认值覆盖模式中的曝光。

按当前推导VT209066666Hz、LLP2080计算，这分别约33.150ms与12.635ms，相差2.624倍。计算依赖尚未物理校准的VT，不能以此解释全部近黑，也不应盲目把驱动默认改满帧。

## 下一项验收

先加入最小helper并保持其它传感器/软件ISP全部能力，再扩展237 exact physical探针：显式关闭AE并分别设置曝光/增益，记录采集时控制元数据和恢复后V4L2值；仅RAM统计亮度/噪声响应。避免把`AnalogueGain=2`无变化当作光学失败，避免重放相同默认六帧。完成响应验证后再验IMX319 CPU RGB、颜色和3A；无需用户准备纯色物体或新增照明。
