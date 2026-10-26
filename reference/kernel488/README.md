# 488：识别 DS4 的 0x2027 媒体总线格式

离线候选已准备并通过有限软件验证。`0x2027` 是 `MEDIA_BUS_FMT_UYYVYY10_0_5X30`，属于 YUV，平均 **15 bit/pixel**；当前 libcamera 媒体总线表缺这一项，因而打印 unsupported 和 RGB fallback 两条警告。[最小补丁](0001-v4l2-recognize-uyyvyy10-0-5x30.patch)只在 `v4l2_subdevice.cpp` 增加 7 行：Image、15 bpp、YUV。旧 473 源、441 驱动／头文件、正式已安装 ELF 均保持原字节；未构建完整 libcamera、未使用 SDK、未部署或访问设备。

定义和来源已与本地权威文件交叉核对，完整路径及 SHA256 保留在 [source-validation.json](source-validation.json)：

- libcamera 自带与匹配内核的 `media-bus-format.h:120` 均定义 `UYYVYY10_0_5X30=0x2027`；`YUV10_1X30` 是另一格式 `0x2016`，现有表已支持，不能混用。
- 匹配内核 `Documentation/userspace-api/media/v4l/subdev-formats.rst:8043` 的表列出 10-bit U/Y/Y、V/Y/Y 的两次传输；`camss-vfe-175-ds4.c:59` 明确登记该 code、15 bpp 和本地 PD10 FOURCC。libcamera 对 `bitsPerPixel` 的定义是全图平均有效位数，不是总线宽度。
- 匹配 `camss-vfe.c:2077–2103` 仅在 SM8150 DS4 pad 返回该 code，并沿用 V4L2 SRGB 元数据。441 冻结的内核源哈希和 473 源清单均逐项相符。

这会修正媒体总线信息与颜色空间读回分类，不能据此声称当前 NV12/sYCC 像素颜色已改变。当前 473 的调用链是 `configurePath():476–481` 构造局部 coarse 格式，`pix_->setFormat()` 将返回的颜色空间写入这个局部对象，调用者只检查 code／size；后面的 PD10 wire 是另一个独立格式对象，没有传递 coarse.colorSpace。NV12 配置及 IPE 输出路径也独立，`validate():571` 仍显式设置 `ColorSpace::Sycc`。此补丁没有新增矩阵、范围或像素转换。

转换函数的边界需要分清：V4L2 SRGB 全部使用 DEFAULT 字段时，现有转换即使走 RGB fallback，也可能与 YUV 路径得到同样的 Rec601／Limited 读回值；不能仅由两条警告推断本轮图像色彩错误。若驱动明确提供 YCbCr 601／709 和 Limited 字段，旧 RGB 回退会将读回编码清为 None、范围强制为 Full；新条目会按 YUV 保留这些字段。libcamera sYCC 是 Rec709 primaries／sRGB transfer／Rec601／Full，不能把 V4L2 SRGB 名字直接当作 sYCC。此处只补格式分类，没有改变原转换函数的默认值规则。

15 bpp 同样不能用于替换 PD10 内存 stride／slice／frameSize 计算。该 code 描述媒体总线有效采样，现有 Qualcomm PD10 存储仍使用专用 FOURCC、192 字节行对齐与 slice 布局；这些 helpers、驱动和调校系数完全未改。

[analyse-local.py](analyse-local.py)先调用 461 的 mounted_build guard，只快照受影响的一个源文件到私有 baseline／candidate；补丁在单文件 replay 副本零 fuzz／offset 重放。随后以原头文件、枚举、ColorSpace 常量，以及原样提取的完整格式表、lookup 和两层 `toColorSpace()` 函数体，用本机 `/usr/bin/g++`、C++20、Werror、ASan／UBSan 验证。设备类使用无 I/O 外壳，日志使用计数替身；这不是完整库构建或 ABI 测试。

真实基线 21 项、候选 24 项断言通过，覆盖 0x2027 的识别与警告、邻近 RGB／RAW／YUV 格式不变、DEFAULT 无颜色空间、默认值相同边界、明确 601／709 和量化范围、未知 code 仍告警回退、非法颜色空间／transfer／YCbCr／quantization 仍返回 unset。[软件回执](validation.json)、[断言源码](colour-space-test.cpp)。首轮测试外壳缺 `<cstdint>` 的编译失败及日志保留于私有 `software-r1`；修正的是测试外壳，补丁与候选未变。

484 原实机的 10 对 V4L2 警告原件不变，仍属于旧 ELF 的真实结果。488 尚未证明实机警告消失、颜色／画质变化或新候选兼容全部调用者。后续可将此单文件增量合入独立构建候选；当前不改变正式 r33/r28、包依赖、profile 或已测签名字节。重复软件复审须使用新的 `--run-id` 和 `--output`，保留此前记录。
