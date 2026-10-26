# 472：mode2 控制阶跃的最小准备方案

**306 的控制工具和响应分析可复用；旧包不能原样重跑。** 本轮只完成源码阅读和差异候选，未构建、上传、执行硬件或修改共享源码。延迟结果保持未测。

[306-mode2-tools.patch](306-mode2-tools.patch) 仅用于 **472 私有目录内的 306 源码副本**，不要应用到冻结 306。两份未编译候选保存在 `E:/edk2-samurai-out/kernel472/candidate-control-stepper.c`、`candidate-delay-capture.cpp`；[preparation-validation.json](preparation-validation.json) 固定源及补丁哈希。

## 已有机制与必要修改

| 项目 | 306 原工具 | 472 最小处理 |
|---|---|---|
| 物理模式 | capture 请求 NV12 320×240，会选 mode3 | 候选沿用已有 441/442 的 SensorConfiguration 写法，显式 pin RAW10 4208×2368；NV12 仅用 320×180 作存活见证 |
| 控制写入 | 同一 VFE SOF 上标准 S_CTRL，记录 event/begin/end_ns、ret/errno，并 G_CTRL 回读 | 原写入代码及 9 步 schedule 保留；不设置目标生效 SOF |
| 模式守卫 | 仅验控制范围，硬编码 k298 | 候选在配置后及 SOF0 核 active format/CROP、HBLANK640、VBLANK944、pixelRate481930000、test-pattern0；release/version 改为必须由冻结前置收据提供的精确输入 |
| 图像／统计关联 | Pair 的 epoch/物理 sof/request，统计与图像按同一 kernelSequence 配对 | 保留这条关联；不可把当前应用 buffer 的连续 sequence 直接当作物理 SOF |
| AE／延迟 | 测量用 300 IPA 没有 AE、DelayedControls；只有固定 WB/BLS 和 BHIST | 使用当前成套 461 runtime，配下述精简测量 profile；不填 sensor_controls、AGC 或任何 delay |
| 分析 | 首变化、三帧平台从真实均值响应计算，无“必须等于2”的断言 | 复用纯计算段；取本地日志，不调用旧 analyse-delay.py 的 SSH 顶层 |

原阶跃可保留：初值曝光500行、gain code64；SOF12/36/60 曝光1200/500/1200，84/108/132/156 增益128/64/128/64，180/204 曝光800/500。240帧、233个 SOF 事件和原18秒 deadline 足够容纳各24帧间隔；这些值均在 mode2 的 1…3308 行、32…512 gain code 范围内。是否有足够信噪比仍须从本轮数据判定，不能继承306“7个有效样本”的数量或结果。

## 统计 ROI 与运行输入

原测量没有保存 RAW 帧或独立 RAW ROI；应用只校验 NV12 DMA 访问、哈希及最小／最大值。实际响应域是 **全幅线性 BHIST**：300 IPA 将 `Rectangle(input_)` 交给 encoder，population 必须等于 `(input.width/2)*(input.height/2)`。mode2 对应 ROI `(0,0)/4208×2368`、population **2491136**，与320×180输出尺寸无关。最小方案继续用这个既有域，无须新增 ROI 或 RAW 解包。

均值与 MAD 门槛不能单独证明局部未饱和。场景须稳定、有足够亮度且不饱和；若全幅受遮挡、运动或强饱和影响而不能满足原响应条件，应将样本记为无效，再决定是否另做 RAW／直方图端点检查，不通过插值或改写阈值制造延迟结论。

不能复用旧300 lib/IPA/proxy整包：旧 IPA 严格要求统计 bytesused 为单 BHIST 包，而当前175内核序列化还追加 AWB_BG（及可选GTM）块。应复用 **469 已核的461完整 library／IPA／签名／proxy配套文件**，只换测量 profile；不混搭旧接口或471正在比较的单变量产物。现有461即使 sensorControlsKnown 为假，也仍可输出有效同 SOF Pair 直方图。

精简 profile 可只保留原厂 BLS 参考和模式匹配：

```yaml
version: 2
sensor_model: s5k3m5
modes:
- match:
    width: 4208
    height: 2368
    pixel_rate: 481930000
    line_length: 4848
    frame_length: 3312
  residual_black_subtraction: 3840
  range_normalization: 1.06201171875
```

这个测量 profile 不启用 sensor_controls、AGC、AWB、动态调校或 IPE/PD10。原 capture 仅发送固定逻辑 ColourGains=[1,1]；应确认启动配置日志 `delayed-controls=0`，并且没有自动控制写入。481930000 只用于控制时序／模式匹配，实际帧间隔继续从 SOF event_ns 求中位数，不以理论30fps代替。

后续运行输入还必须来自本轮冻结前置记录：mode2模块文件及加载note、461成套文件哈希、boot-id、`MEASURE_KERNEL_RELEASE`、`MEASURE_KERNEL_VERSION`，以及469既有恢复包装器的原模块／图／controls快照。不要使用306绑定305 boot的旧 native/launch/poll 脚本，也不要从运行时即时 uname 自证 expected 值。本轮未生成执行包装器或触发这些操作。

## 分析移植仅需的变化

1. 将306 `analyse-delay.py` 中 Pair／events／writes 的解析和 median/MAD／归一化响应计算放入本地文件分析入口，去除 host 导入、SSH读取／回读及旧 stage/boot 固定值。
2. 当前461 Pair 末字段为 `parameter-buffer-submitted`，替换旧 `parameters-acknowledged` 正则；输出仍称 submitted，不将其当作硬件锁存确认。依靠 Pair 的物理 SOF 与写入记录相减，独立计算曝光和增益的观测偏移。
3. 保留原前窗 `[n-6,n)`、后窗 `[n+6,n+14)`、0…7响应及原信噪比／平台门槛。先验证所需 SOF 完整、唯一，写入成功且无 pending／迟到；缺失样本判无效，不补帧、不预设2。报告 mode2 实际 format/crop/LL/FLL、两类有效样本数、每次首变化与平台偏移及时间戳。

源码依据：306 `control-stepper.c`、`delay-capture.cpp`、`analyse-delay.py`；300 `ipa/camss.cpp` 的严格单BHIST检查与 `pipeline/camss_vfe.cpp` 的同SOF配对；299 `ipa/parameter_encoder.cpp` 的 ROI；当前461 `camss.cpp`／`camss_vfe.cpp`，及guarded source354的 `camss-vfe-175-stats.c`。本轮未重做469原厂逆向，未改变曝光／增益延迟配置。
