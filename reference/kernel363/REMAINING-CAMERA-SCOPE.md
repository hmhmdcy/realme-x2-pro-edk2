# 多摄验收范围补核

2026-10-20。当前“4摄通过”限定GW1主摄、IMX319广角、S5K3M5长焦与IMX471前摄，不能外推为全部镜头完成。[realme官方规格](https://www.realme.com/in/realme-x2-pro/specs)列出另外一颗2MP人像镜头。

保留的本机vendor清单含`com.qti.sensor.ov02a1b.so`，但115提取的完整sensormodule路径清单只有六份：Sunny/Qtech GW1、Sunny/Qtech IMX319、Qtech S5K3M5、Sunny IMX471。库文件名不足以证明具体物理器件已检测；116及239原有记录也明确没有验收人像镜头。[115事实](../kernel115/camera-source-validation.json)、[239已有驱动研究](../kernel239/RELATED-LINUX-SOLUTIONS.md)。本轮复用原件，没有重复读取vendor或校准分区。

匹配19781板级源码，固定`23172a1571bd91156032cc9fef16284a82b63d2c`，`arch/arm64/boot/dts/19781/sm8150-camera-sensor-mtp.dtsi`定义`qcom,cam-sensor@4`：CSI PHY2、MCLK2/19.2MHz、reset GPIO12、CAM_MONO_EN GPIO29、CCI设备1/master0、VIO1.8V与P侧L5模拟2.8V。当前已测前摄也使用PHY2/MCLK2/reset12，并通过GPIO29高态选择；这说明后续需核实共享/选择拓扑，不能在保持现前摄独占资源时直接追加另一个设备。

接续顺序：先核对实际模组与原厂描述/初始化资料，再通过标准媒体mux、时钟/供电/复位生命周期协调共享资源，接标准sensor驱动与媒体端点。现有OV02A10上游驱动只作候选框架，不能未经芯片ID、寄存器/时序核对就把OV02A1B当作同一器件。实际器件检测、取流与个体/几何调校仍未完成。

此文件补齐原目标的验收范围，不改变当前已测四摄身份。正在进行的363内核切换及364 ICP/HFI工作仍先完成；未在切换过程中切换GPIO29、探测未知I2C地址或修改板级DT。
