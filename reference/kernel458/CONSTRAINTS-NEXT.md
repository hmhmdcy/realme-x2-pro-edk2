# 458：第五 OV02A1B 的模式、控制与时钟约束

可继续实现单色 sensor 的模式选择、控制缓存和共享资源骨架；**目前仍不足以填写可信的 HBLANK／PIXEL_RATE／LINK_FREQ 并交付完整可捕获驱动**。本机原厂描述的行计数小于有效图像宽度，没有找到它到像素阵列单位的可靠换算。原厂 outputPixelClock 与曝光时间计算使用的名义 VT 是两条不同消费路径，不能相互替代。

此次只新增458的离线检查与报告，没有手机、SSH、SDK、编译、部署或共享源码修改。[检查脚本](inspect-constraints.py)、[脱敏收据](constraints-validation.json)通过。完整字段值、页序回放、原始结构和算术反例均留在 `E:/edk2-samurai-out/kernel458`；其中 `mode-control-contract-private.json` 是实现约束表，`deployable=false`。

## 来源及实际解析

复用282完整 Shine BIN，SHA256 `63e2122a…b5fa`；115实际 `com.qti.sensor.ov02a1b.so`，SHA256 `47b3c1b8…23e9e`；281实际 `camera.qcom.so`，SHA256 `e2b1b9b6…70dde`。完整指纹在收据。未重新执行454的498组 fill、135组 gain、760字节固件或 C 编译检查，只核对既有通过收据、匹配 SO 与缓存向量。

固定 CHI 仓库提交 `9f17f1b568626b393e785b369c5dc94543774d7a` 的 `camximagesensordata.cpp/.h`、`chi-cdk/api/sensor/camxsensordriver.xsd`提供字段名称和消费公式；本机 schema 存在 OEM 变体，不能直接用旧 XSD 布局或缺省值解释所有字节。458执行281真正的 `SensorDriverDataClass::Parse`，完整消费 sensor root，得到一个模式；序列化字段与实际 native 结构逐项相等，optional 的存在位与空 payload 也相符。原 parser执行420295条指令，未执行设备 I/O。

随后把实际解析对象交给原二进制行时间算术路径，33条原指令返回值与独立公式完全相等。入口使用其实际加载布局与索引；没有把恢复符号名的 C++ 原型当作可调用 ABI。此证据验证 HAL 的名义换算，不是硅片时钟测量。

公开交叉来源仍为 [realme 官方 mono 驱动固定版本](https://github.com/realme-kernel-opensource/realme8_C25_C25s_Narzo30_Narzo50A_AndroidR_kernel_source/blob/a3e43e3d5cbd14caa5cc1a48561180bfc708dbb4/drivers/misc/mediatek/imgsensor/src/mt6853/camera_project/oppo6853/ov02a1b_mipi_mono/ov02a1bmipimono_Sensor.c)，blob `dcec8574…2bf112`、SHA256 `79adc42a…3b448`。它也区分 timing pclk 和 mipi_pixel_rate，且行计数同样小于图宽；但使用另一 MCLK、帧长和控制边界。只用它交叉确认协议，未搬用其表、时钟比、margin、最小 shutter、gain step 或最大 frame。

## 可供实现的控制契约

模式保持原厂1600×1200、单色 RAW10、一条 D-PHY lane、声明30fps；没有新增裁切、binning、HDR 或更高帧率模式。

| 项目 | 本机已有依据 | 驱动约束与尚缺内容 |
| --- | --- | --- |
| 名义帧长 | ResolutionData 的 frameLengthLines、frameRate，native 解析一致 | 第一候选可固定名义帧长及只读 VBLANK。它是限制在声明模式内的保守软件策略，不是已经证明的硅片最小帧长。minVerticalBlanking 字段存在，但不能单凭它缩短名义帧长、扩展最大帧率。 |
| 帧长上限 | 固定 CHI `GetMaxFrameLengthLines` 依赖模式 AE/tuning 的最小 FPS | 目前未恢复这次实际选择的完整策略。454打包器的整数边界、帧编码基数、曝光上限都不能单独充当正式 VBLANK 最大值。 |
| 曝光最小／最大 | exposureControlInfo 的 minLineCount、maxLineCount 及 verticalOffset 均实际存在 | 以整数积分行缓存曝光；给定帧长时，上限取描述最大积分行数与 `frame_length - verticalOffset` 的较小者。变更 VBLANK 时先更新曝光范围并处理已有曝光，再统一写入。 |
| exposure step | integrationInfo 实际 absent、对应 payload 为空；fill 接受整数行并按字节编码 | 可实现一行的编码粒度，但不能声称找到了独立的原厂 integrationTimeStep。实际曝光响应、最小端点及余量仍须硬件核对。 |
| 模拟 gain | 描述有最大值；minAnalogGain absent，parser 的零存储不是合法最小 gain。真实 calculate 回调有下限夹紧与分段量化 | 复用回调已验证模型；原厂可生成 gain code 为非等距集合。不要把打包器允许的全部原始整数码都宣称为原厂增益步距。私有表给出完整模型集合。 |
| V4L2 gain 单位 | `V4L2_CID_ANALOGUE_GAIN` 是整数，单位可由驱动定义 | 可将原厂集合编码为递增整数索引，再在驱动中查表；必须同步明确用户态 gain-code/real-gain 换算，不能直接套其它 sensor helper。此处仅给接口方案，没有生成驱动或 IPA 配置。 |
| sensor digital gain | 描述与原回调一致为固定量 | 不暴露可调 sensor digital gain；原回调的 ISP residual 是后级补偿，不能当作传感器数字增益写入。 |
| 初始控制 | 454原表按页面、顺序回放可恢复曝光／gain／帧编码 | **原表初始帧编码与模式声明帧长不同。**须在 init/mode 后、真正 stream-on 前，统一应用选定帧长及合法曝光／gain／apply。不能仅发完原表就声称已经运行声明帧率。这里是表重建，未作寄存器实机读回。 |

私有约束表包含来源 root/UID、native offset、原表初值、原厂 gain 模型集合和固定名义帧策略。离线正／反例只检查该软件约束的自洽性，不代表曝光端点或长帧硬件已经通过。

## HTS、VT 与输出接口频率

固定 CHI `camximagesensordata.cpp` 的 `GetVTPixelClk`（约462行）返回 `lineLengthPixelClock * frameLengthLines * frameRate`；`GetLineReadoutTime`（约978行）再用行计数除以该名义 VT。`ExposureToLineCount`／`LineCountToExposure`用此行时间换算积分行数。这个流程没有从 sensor PLL 寄存器恢复真实频率。

`PopulateSensorModeData`（约1827行）分别发布 outPixelClock 与 vtPixelClock。`CreateCSIPHYConfig` 对应代码（约2673行起）取 outputPixelClock，可能应用 `overrideOPPCLOCK` 百分比，再以 bitWidth／laneCount 形成接收端 dataRate。它提供的是该实现的配置预算路径；未恢复当前实际 override，也没有证明字段等于物理像素阵列频率、MIPI symbol frequency 或 UI。不能把300MHz字段直接填成 V4L2 的任何一种时钟，也不能仅除以二得到已验证的 LINK_FREQ。

source354实际 UAPI文档要求 HBLANK 为像素、VBLANK 为行、PIXEL_RATE 为像素阵列采样率，帧周期由这些量共同计算；LINK_FREQ 对 D-PHY 表示 `1/(2*UI)`。本机 HTS934 小于有效宽度1600，因此 `HBLANK=934-1600`不成立。将负值夹成零、用 minHorizontalBlanking 替代再反算 pixel rate，也没有恢复真实单位。

现有 API可以表达这种硬件：保留 raw HTS/HMAX 为驱动私有值，只有在已证明换算后，才把换算后的整行像素数减去 analogue crop width 形成 HBLANK，并暴露对应 PIXEL_RATE。当前 `drivers/media/i2c/imx415.c` 的 HMAX_MULTIPLIER 及 HBLANK 读写就是已有接口例子；它自己的倍率不能移给 OV02。本次还构造了两个仅在代数上满足相同名义行时间的表示，证明仅凭帧率／帧长甚至 SOF 周期也无法唯一确定像素单位；这些反例不构成候选时钟。

当前 CAMSS 明确区分阵列速率和 CSI-2 接收吞吐。`get_mbus_config.link_freq` 优先，其后为 LINK_FREQ control，最后才可能从 PIXEL_RATE 估算。缺少可信 LINK_FREQ 时随意填一个 timing rate，仍可能让 PHY 消费到错误频率。应先补本机 MCLK／PLL／HTS 单位及 D-PHY UI 的可靠依据，再独立发布阵列 timing 与链路频率；不要为使图能够启动而采用这个估算兜底。

Linux来源为保留 `source354`，HEAD与14份实际文件 SHA在收据；它们可能包含本机已有移植修改，不能仅以 HEAD 代替文件指纹。另有两份固定 CHI sensor-node/utils blob在本地缺失，本轮未联网或猜测其实现；这也是实际 AE 帧长策略尚未闭合的边界。

## runtime PM 与共享资源的实现顺序

沿用[454共享资源审查](../kernel454/MUX-NEXT.md)：前摄与第五共用 route、reset、MCLK引脚和 PHY，且 lane 配置不同。资源独占必须早于 probe/default pinctrl、reset 或电源操作，维持到完全断电及失败收尾之后。GPIO mux provider、reset provider、时钟引脚应各有单一所有者；不能让新 sensor probe 在前摄运行时改变这些电平，也不能让旧 IMX471 继续直接驱动已交给 provider 的 GPIO。

正式 sensor 的 runtime resume/suspend负责电源／时钟／reset引用；start-stream先取得运行引用，在模式写入后应用控制，最后 stream-on；stop-stream及失败路径只回收本次成功获取的引用。关电状态的 s_ctrl 只缓存，不能访问 I2C；恢复后由 start-stream应用。不要在 runtime_resume 内调用 `v4l2_ctrl_handler_setup`，因为 PM状态此时尚未标为 active。共享 CAMSS 的输入/lane选择也必须在空闲时完成并保持互斥。454所列前摄 probe、sleep pinctrl 与 immutable link冲突仍未集成解决。

最小下一步是先离线取得**同一本机时钟版本**的 PLL／行计数单位／MIPI率来源，将其与完整原表逐字段对照；无法取得时需要安排有明确观测手段的时钟窗口，不能用另一24MHz表或试猜 PHY寄存器代替。完成时钟来源及共享资源候选后，最小硬件验证依次检查：前摄独用与冲突拒绝；第五独占时的标识／MCLK／初始化及控制应用；原始单色RAW的格式、行宽、连续SOF和声明周期；固定模式内的曝光最小／最大、gain分段及停流／错误恢复。若扩展 VBLANK，再单独验证帧长上下限、曝光依赖和更新生效帧。当前没有获得这些硬件结论。

离线复核入口（不会访问手机、调用编译器或 SDK）：

```text
wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel458/inspect-constraints.py' --all
```

该入口首先执行449的 mounted_build守卫，复核原件及缓存收据，执行原 parser／有限行时间路径，并生成458私有约束与公开脱敏收据；不会重跑454控制／固件测试，也不会改453／454。
