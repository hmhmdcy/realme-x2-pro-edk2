# 428：原厂 Crop 纠正 DS4 色度坐标，四摄完整输出通过实拍

完整多摄／ISP 目标继续 active。本轮修复 427 的 DS4 帧内回压：**主摄、长焦、前摄、广角均完成 FULL 与真实 PD10 同时输出，最终一组取得 144 张同 SOF 配对的 DS4 帧。** 已恢复正式模块与桌面服务；尚未连接 IPE 粗级消费者，本轮 IPE job 为 0，不能称完整自动 TMC／LTM 已完成。

## 原厂几何生产过程与底层修复

427 的模型把 DS4 色度裁剪 X 末端设为 FULL 宽的一半，该值是夹具输入，并非原厂 Crop 生产的结果。本轮直接执行本机 HAL 的完整 FULL Crop Create／Execute，使它生成 preCrop 元数据，再交给原厂 PreCrop、DS410、RoundClamp、R2PD 及节点使能汇总。对于 640×480 FULL，色度裁剪 **X 仍按交织色度分量计数，只有 Y 高度减半**。427 对错误输入的局部寄存器一致性不构成正确几何证明。

[原指令模型](native-geometry.py)、[几何生产检查](native-crop-production-validation.json)覆盖五组源／输出组合，校验原映像内存没有被写坏。FULL Crop 构造路径是 VideoFull；MNDS 输出尺寸与比例仍由上下文提供，尚未执行完整 MNDS／传感器 ROI／striping 推导。不能把该结果扩展成任意输出模式均完成。

[最终内核补丁](precrop-chroma.patch)相对 427 仅修正色度裁剪 X。原厂 precrop 使能已恢复，没有保留绕过裁剪的诊断版本。`precrop-isolation.patch` 仅记录中间隔离实验，不可作为最终安装补丁。维护源码见 [状态](source-state.json)；[补丁复放与构建检查](source-validation.json)、[匹配 10 模块 Werror 构建](intree-build-validation.json)。队列、DMA、FourCC、参数 ABI 和 DT 沿用 427，未改传感器或 NV／OTP／persist。

7 组几何的实际内核 C 与完整 FULL Crop 生产→PreCrop／DS410／Round／R2PD／使能结果逐字一致，宿主 ASAN／UBSAN 与 ARM64 qemu 通过。[结果](runtime-codec-validation.json)。四摄原厂系数和模式选择沿用 [426](../kernel426/README.md)。

## 实机与像素验证

[最终硬件验证](hardware-validation.json)是 r6：四个镜头顺序执行现有板级模式，FULL 640×480 NV12，DS4 160×120 PD10、stride 768、60 packed rows、46080 bytes。

| 项目 | 结果 |
|---|---|
| FULL 单独对照 | 24 帧 |
| 四摄各自色条与现场图 | 每路各 18 张 DS4，共 144；全部有同 SOF FULL 完成帧 |
| 同时输出的 FULL | 共 236 帧；DS4 停流后各继续至少 6 帧 |
| DS4 断粮／恢复 | 每次一处预期 SOF 缺口，FULL 继续，恢复后继续完整交付 |
| 内存边界 | 所有 mmap 尾部与 PD10 行 padding 保持预填值 |
| 时间戳 | 当前驱动记录完成时刻；同序号两端相差最多 154 µs，不要求完成时间相等 |
| 诊断 IRQ | 每流前四个 SOF 共 32 次采样，未命中原厂 CAMIF 错误掩码；不宣称覆盖全部错误注入 |
| 恢复 | worker 均终态，正式模块、媒体图、服务恢复，资源释放，历史 taint 512 不增 |

r1 是探针尺寸替换失误导致前置失败；r2 长焦复现 427 的不完整 DMA；r3 绕过 precrop 的隔离实验成功；r4 恢复 precrop 并修正 X 后成功。r5 四摄也完成 144 张 DS4，但逐帧落盘使主摄现场图中有一张缺少 FULL 伙伴，不能将 r5 说成 144 张完整配对。r6 改用四缓冲、选择性保存 FULL 后通过上述配对检查。未来生产链路仍须丢弃孤立粗级帧，并保持已提交的数学历史。

[像素验证](pixel-layout-validation.json)、[检查器](check-pixels.py)、[诊断解码器](pd10.py)：8 byte 一组保存四亮度与 Cb／Cr，六个高 8 bit 后跟按相同分量顺序排列的低 2 bit；亮度存储顺序为 Y00、Y10、Y01、Y11。三个普通色条传感器的 7904 个恒定邻域与 FULL 差最多 3 个十位单位。主摄使用渐变 Shade Color Bars，不能套恒定色条模型；四路现场图分别比较全部 24 种亮度排列，均确认上述列优先顺序。场景参考是近似 4×4 区域平均，未声称复刻原厂滤波相位。144 帧保留高半字节均为零。

已查看前摄 FULL 与解包后放大的 DS4 现场图，构图／亮度／颜色相符；可见当前上游画面仍偏雾、偏色。这些是无额外调色的诊断图，不能当作完整 IPE 调校画质验收。原始图与原厂数据只保存在私有输出目录。`QP10` 仍是本地实验 FourCC，未上游保留。

## 处理域与下一步

| 层次／域 | 状态 |
|---|---|
| SoC／板级／主线风格驱动 | 沿用 SM8150、既有 DT 与四摄模式；实际 CAMSS DS4 裁剪、队列和像素输出已验证 |
| IFE／BPS GTM | 属于上游域；非零 TMC GTM 份额与实际应用版本的同图像因果绑定仍缺 |
| IPE LTM | 真实 PD10 已可用；需连接 backing 所有权、双遍 striping、scratch／会话／帧端口 1，并证明 DC 写出及 full IP 消费 |
| IPA | 保留 [424](../kernel424/README.md) 的实际触发、同 SOF BHIST／曝光／lux 与最终成功 history；本轮未推进 IPE 或数学历史 |

下一步直接复用本轮真实 PD10 对接 [425 的原厂双遍模型](../kernel425/README.md)，不能再使用单遍固定 48 byte striping。随后完成 GTM 应用因果、自动 TMC／LTM 统计反馈与最终成功提交历史的实拍验证。前摄原厂关闭的 TMC 保持关闭；其它模式、视频、第五 2MP 身份等仍见 [完整未完成范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。
