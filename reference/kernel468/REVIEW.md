# 468 原厂长焦 mode2 独立离线审查

最终候选 `s5k3m5.c` SHA256 为 `88251268b2c10e15116e717511da206e71da35ab359abb8ca80f747c44f2070b`，header 为 `0336163236832bc9aa51721205c122671e0006940bbb33377d43722d5d22fbd4`。本审查没有修改候选、共享源码或冻结 465/466，没有使用手机、SSH 或绑定 SDK。只编译了私有目录内的有限 host C 检查。

## 原厂输入与最小配置

[mode-review-validation.json](mode-review-validation.json) 记录独立重读原件所得的哈希与结果；可用 [review-mode.py](review-mode.py) 复查。输入是本机已保留的 239 A/B `sensorDriverData.xml`、440 mode3 调校、465 mode2 私有表/调校，以及最终 468 候选。完整寄存器表与调校对象保留在私有目录。

- A/B 原件全部模式的有序寄存器序列一致。mode2 的 **53 条 WRITE16、零延时** 与候选及 465 私有表完全相同，包括重复间接地址写入，未仅比较最终寄存器字典。原厂标签仍为 **HFR，声明 30fps**。
- mode2 输出 4208×2368、LL 4848、FLL 3312；原厂活动首点由参考 mode0 的 `(8,8)` 变为 `(8,384)`，驱动逻辑 CROP 应为 `(0,376)/4208×2368`。该尺寸接近 16:9，并非数学上精确 16:9。
- LSC 沿用 321/323 固定 mode0 参考约定：`source_span=[2103,1559]`、`first_quad=[0,188]`、`quad_step=[1,1]`，末点 `[2103,1371]`。core、golden、unit 和其余 IQ 对象完全复用；原 mode3 的完整 profile 保持一致。精确目标 HAL 的 fullResolution 赋值仍未证明，不能把这个继承约定表述为新取得的 HAL 语义。
- 新 profile 的五项匹配为 `4208×2368 / pixel_rate=481930000 / LL=4848 / FLL=3312`；`sensor_controls` 必须相同。HBLANK=640，VBLANK=944…63167、默认 944，EXPOSURE=1…3308 行、默认 256。

`481930000` 是沿用现有 mode3 的**控制时序**输入，mode2 实际行周期仍须实机确认。466 由同传感器 OP PLL 表支持的 mode2 CSI 候选为 link 723200000 Hz、四 lane RAW10 吞吐 578560000 pixel/s；该吞吐值不可填入曝光控制时钟。原 XML 的 outputPixelClock 也不是独立证明 VT 控制时钟的来源。按控制值计算，行周期为 10.059552 µs，默认帧周期为 33317.237 µs。曝光、增益延迟均暂沿用 2 帧，未取得 mode2 的物理延迟验证。

原 header 的字节前缀完整保留，旧 mode3 写入表及 profile 未变。原 mode3 的 link menu 仍声明 723.2 MHz；466 提出的较低候选尚未部署，本审查不把它改成已验证结果。

## 实际格式选择及调校消费入口

461 `CameraSensorLegacy::getFormat()`（`camera_sensor_legacy.cpp:703`）先排除小于请求的模式，再比较 float 宽高比差，最后比较面积差。按实际两个描述符重现该规则，普通处理流的 1280×720、1920×1080 都选 **4208×2368 mode2**，640×480 仍选 mode3。此结果是按源码 float32 规则的有限计算，没有声称运行了 CameraSensorLegacy 二进制。

实际 pipeline `camss_vfe.cpp:546` 在有显式 SensorConfiguration 时使用其 `outputSize`；因此既有脚本若固定 2104×1560，仍选择 mode3。下一 mode2 的 raw/FULL/PD10 因果捕获必须显式请求 4208×2368；普通 720p/1080p 消费端仍设置目标输出尺寸。不要把直接对 sensor S_FMT 小尺寸所用的最近尺寸规则，与 libcamera 的宽高比选择规则混为一谈。

`sensorInfo()` 从当前 G_FMT/CROP 和真实 V4L2 controls 生成输出尺寸、LL、FLL、pixelRate（`camera_sensor_legacy.cpp:859,924`）。IPA `camss.cpp:265` 精确匹配上述五项；`sensor_controls` 又在 `:339` 核相同输入及延迟。IPA 行周期来自 `LL*1e6/pixelRate`（`:159`），ExposureTime 转行数使用 `llround(time/lineUs_)`（`:438`）。pipeline 在 `camss_vfe.cpp:765` 将 profile 的两项帧延迟交给 DelayedControls，2 帧值只代表当前调度配置。

## 锁、缓存和错误语义

候选 `s5k3m5.c:1578` 明确将 `sd.state_lock` 指向 `ctrl_handler.lock`。ACTIVE S_FMT 在共锁下且非 streaming 时先发布 mode 与 active format，再打开 `updating_format` 更新控制缓存。metadata LINK_FREQ/PIXEL_RATE/HBLANK 显式返回成功；VBLANK 仍传播曝光上限，但缓存更新期间在 PM/I2C 前返回。TRY 不改传感器当前 mode/controls，streaming ACTIVE S_FMT 先返回 `-EBUSY`。

开流路径先写选中 mode 的原厂表，再执行 `__v4l2_ctrl_handler_setup()`（候选 `:938,1001`），最后才置 streaming。S_FMT 退出清除 flag，因而 handler_setup 会把新缓存落到硬件。这与 powered-idle 切换时不混写新旧时序的目的相符。

本树 core `v4l2-ctrls-api.c:964` 的 modify_range **先修改范围**，再可能触发 set_ctrl；core `v4l2-ctrls-core.c:2660` 在回调失败时不提交 p_cur。错误通过函数返回值传播，不写入 `ctrl_handler.error`。因此每个实际 API ret 都要检查，且失败不得宣称已回滚。最终候选还修正了 VBLANK 内嵌 exposure modify_range 的返回值：正常 live VBLANK 收回默认 FLL、当前曝光超新上限时，若曝光 I2C 失败，应立即返回该错误，不能继续写短 FLL 并返回成功。

同树 imx319 的模式切换可佐证“先更新当前 mode，再更新相关 controls”的顺序；imx471 的 ACTIVE format 更新可佐证逐项返回 API 真实错误。两者都不构成完整回滚保证。本候选的失败返回也可能留下已改变的 mode/state/部分范围；当前两个 profile 四个静态描述符的正常范围均已核有效。

## 有限 C 检查及边界

[format-control-validation.json](format-control-validation.json) 绑定最终源哈希、提取函数哈希、host 源/二进制哈希和 GCC 版本。运行 [review-control.py](review-control.py) 会把候选与 baseline 的 **真实 `set_ctrl`、`set_pad_format` 及 pad helper 原样提取**到私有 host 检查，使用 [control-harness-prefix.c](control-harness-prefix.c)、[control-harness-tests.c](control-harness-tests.c) 的有限 provider 模型。

GCC 15.2 的 AddressSanitizer / UndefinedBehaviorSanitizer 下 **28 例通过**，包括两 profile 四描述符范围、powered-idle 双向格式切换零 PM/I2C、mode/state/ranges、TRY/streaming 不变、开流 handler_setup 时序控制子集 FLL3312、普通 VBLANK 写入、内嵌曝光 I2C 错误返回、各格式 API 错误注入后的 flag 清理。将同一组候选双模式描述符交给 baseline 的实际两个函数，能复现 HBLANK `-EINVAL` 被忽略，同时写出 FLL2504（应为3312）；baseline 自身原本没有暴露 mode2。

provider 模型仅覆盖已核 numeric range/cache、共锁断言、PM/CCI 桩。它不运行真实 control core、原厂 mode 表硬件写入或完整开流，也不证明内核并发、任意热解绑或实机 CSI/曝光/调校效果。注入错误后断言真实的部分更新边界，没有虚构回滚。

## 363 实际 endpoint 与下一实机边界

对缓存 363 FAT 镜像只读 `mcopy` 提取 `/samurai.dtb`，得到 114556 字节，SHA256 `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`，精确匹配冻结 boot-package-validation。实际 tele endpoint 为 `/soc@0/cci@ac4b000/i2c-bus@0/camera@2d/port/endpoint`，其 `link-frequencies=[723200000]`、`data-lanes=[1,2,3,4]`。当前板 DTS 所含 `s5k3m5-samurai.dtsi` 也保持该值，mode2 可复用原单项菜单。未把后续共享 build 的不同 DTB 冒充 363 冻结件。

主线接下来的实机验证需要首先确认 active sensor format/crop/LL/FLL/profile 确实切到 mode2，再分辨 720p/1080p 输出的同 SOF PD10/FULL 和 LTM 实际消费；467 mode3 的严格同 SOF 结果仍属于 mode3。曝光/增益延迟、真实帧时长、LSC 画幅、链路错误及消费 SOF 缺口都需实际证据，本审查没有把离线通过改写成完成这些硬件结论。
