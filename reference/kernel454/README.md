# 454：复用原厂 OV02A1B 表与曝光控制的离线基础

第五颗 Shine OV02A1B 的本机原厂 BIN 已完整恢复。本轮把它转成私有固件并实现纯整数 C 控制打包／固件解析；实际原厂 AArch64 回调与 C 对照通过。**尚未集成完整 sensor 驱动、DT、共享资源或单色 RAW 管线，也没有实机验证。**未修改共享源码、正式相机栈、手机或 SDK。

优先核对了 [realme 官方单色驱动的固定版本](https://github.com/realme-kernel-opensource/realme8_C25_C25s_Narzo30_Narzo50A_AndroidR_kernel_source/blob/a3e43e3d5cbd14caa5cc1a48561180bfc708dbb4/drivers/misc/mediatek/imgsensor/src/mt6853/camera_project/oppo6853/ov02a1b_mipi_mono/ov02a1bmipimono_Sensor.c)，Git blob dcec8574…、SHA256 79adc42a…。它使用24MHz、不同的时钟／帧长，因此仅作为寄存器协议交叉证据；没有复制其初始化表或时钟值。本机仍使用原厂19.2MHz描述。来源、固定 CHI GetVTPixelClk／API 与 schema 指纹见 [source-validation.json](source-validation.json)。

[固件生成](prepare-firmware.py)从本机原厂 BIN SHA256 63e2122a…逐条取出88 init、1 mode、2 stream-on、2 stream-off，共93条；重复地址、页面、顺序、值及延时完整保留。私有 OV2B v1 为760字节，SHA256 18af819f…，完整值和二进制仅在 E:/edk2-samurai-out/kernel454。[往返检查](firmware-validation.json)通过。格式只保存硬件写表，不包含猜测的调校或默认焦点。

[ov02a1b_firmware.h](ov02a1b_firmware.h)在返回视图前校验完整长度、版本、reserved、四表数量及延时边界；调用方仍须保持 backing firmware 的寿命。[真实 C 检查](firmware-c-validation.json)在 ASAN／UBSAN 下通过有效表、964种非法输入及空输出；失败不改调用方视图。还未接 request_firmware、probe、I2C 或 runtime PM。

[ov02a1b_control.h](ov02a1b_control.h)仅打包原厂七条曝光／帧长／gain／apply 写操作，不做 I/O 或浮点计算。Unicorn 执行原厂 GetSensorLibraryAPIs 返回的真实 calculate／fill 回调：498组 fill 与编译 C 字节相等，135组增益量化与原回调模型相等，另验证空指针和非法输入拒绝；[收据](control-validation.json)。C 接口的整数范围只是编码范围，尚不能代替该模式的曝光 margin、最小帧长或 AE 策略。原厂通用 group-hold 占位字段不可直接拿来写曝光。

模式为1600×1200、单色 RAW10、一条 D-PHY lane，原厂声明30fps。固定 CHI 的 VT 时钟计算是行长×帧长×帧率，本机元数据得到48,698,760Hz；300MHz output pixel clock 字段不能当曝光时钟。这个值只建立名义时间换算依据，真实时钟和帧周期仍待硬件测量。

[共享资源审查](MUX-NEXT.md)定位到前摄／第五共享 GPIO29、MCLK2、reset12 和 PHY2。当前 CAMSS 在 bind 时固定 lane 配置、外部链接 immutable；前摄 probe 和 sleep pinctrl 会改变共享电平。必须同时收敛这些底层所有者和媒体输入选择，不能只加一个 compatible 或复制 OV02A10 的24MHz彩色驱动。单色 RAW 模式选择也未完成。

下一步在独立候选中接入已验证解析器／控制编码与原厂表，配合共享 mux/reset、CAMSS 输入／lane 仲裁和单色 RAW 接口，再协调硬件窗口验证。此次软件契约通过不代表第五摄像头已经可用。
