# 334：VFE175硬件颜色矩阵后端实测

2026-10-20。已补齐SM8150/VFE175的CCM参数验证、寄存器编程和生命周期，临时模块实机验证通过。332候选IPA尚未联动CCM，系统安装版本和默认调校不变，完整goal active。

变更仅在SoC专用CAMSS后端和参数容量声明：复用既有`CAMSS_PARAMS_COLOR_CORRECT`结构、参数队列及SOF流程，按G/B/R顺序写9个系数、3个偏移和Q选择；左右字段相同、保留其他位。支持enable、更新时保留enable状态、仅含头部的disable；重新开流复位为关闭的单位矩阵，停流关闭矩阵。参数最大容量增至能容纳WB/BHIST/LSC/CCM的1888字节含头部，旧参数包继续有效。没有板级DT、传感器驱动或应用层软件补色改动。[补丁](ccm-driver.patch)。

系数是12位补码，偏移是Titan175的11位补码，Q选择0～3分别为Q7～Q10。验证拒绝多余标志、越界字段和非零padding，不读取header-only disable后面的内存。主机及AArch64直接编译实际驱动函数，以296保留的原寄存器位域类型作独立参考：各2866组参数、完整模拟MMIO、保留位、保护页、开关和复位全部通过。[结果](register-validation.json)。

内核模块通过W=1/KCFLAGS=-Werror构建，无诊断；只构建CAMSS及其现有依赖闭包，原共享构建输出已恢复。[构建](kernel-build-validation.json)。隔离源码`/home/cy122/x2pro-linux/camera334-ccm-kernel`，分支samurai-ccm334，提交`6c762eae4a4af55d8d9111d3c9fd8c2880f5dad1`，父325已部署GW1提交，tracked clean。[源码状态](source-state.json)。

R1在读取私有矩阵文件时0帧退出：生成文件误把enable位写为disable，工具检查后直接返回，尚未操作图像。已修正文件标志，复用同一工具二进制和内核模块；R1已恢复模块/服务，无相关故障，不能当作硬件矩阵失败或成功。

R2使用主摄ShadeColorBars内部图，8阶段共观察31帧并保存8图：关闭、Q7单位矩阵、非对称通道混合、Q10单位矩阵、正负偏移、关闭、原厂矩阵、关闭。Q7/Q10单位矩阵和三次恢复关闭结果均与初始基线逐字节一致。非对称矩阵、偏移和原厂矩阵均产生图像差异；两项无效参数由实际QBUF拒绝。工厂数据明确为Qtech GW1 Default UID37、DRC1/HDR敏感度比1/LED0/lux100/CCT6500诊断，未绑定本机供应商。[采集](pattern-r2-capture-validation.json)。

独立NV12逆变换/线性RGB模型：非对称混合均值误差0.381、p99 1.216/255；偏移按14位处理域归一化时均值0.261、p99 0.927/255，在所比较的处理域中拟合最好，这支持14位域解释。原厂矩阵均值0.692、p99 5.445、最大14.093/255，远离预测输出截断区的p99仍为3.265/255；保留这些误差，不能把近似模型当逐像素精确验证。图像缩放、Bayer、非线性和截断不完全可从已缩小NV12反推。硬件顺序/位域由独立寄存器参考和非对称图另行证明，不是正常照明光学校准。[图像分析](pattern-r2-image-validation.json)。

临时模块下，安装的r26栈四摄GStreamer各观察12帧，全部无总线错误并恢复媒体状态；这是本次SoC变更的兼容性证据，没有重跑未改软件包全量测试。R2共观察79帧，相关故障delta0/taint0，模块恢复时build-id note与实验前相同，CAMSS/两CCI休眠、九相机电源disabled/users0。PipeWire/WirePlumber恢复为各一个uid10000进程，PID18338/18365。[最终状态](final-state-validation.json)。没有替换已安装模块文件、软件包、Image/DT，也没有刷写、重启或写NV/OTP/EEPROM/persist。私有矩阵、图像和完整日志仅在kernel334输出目录。

下一步335从332候选源将显式ColourCorrectionMatrix、手动CCT/增益和自动WB色温接入333矩阵插值/编码，沿用SOF参数历史报告有效矩阵；必要时临时搭配334模块验证。默认无个体表、主摄供应商未绑定、AEC lux物理语义与动态LSC、正常照明颜色/阴影、多摄几何/同步、连续AF等仍继续，不能以本轮临时硬件支持宣称完整目标完成。
