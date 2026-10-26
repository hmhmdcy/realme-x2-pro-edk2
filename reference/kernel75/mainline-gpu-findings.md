# 主线 GPU 支持核对（2026-10-10）

SM8150 / Adreno 640 已有主线 SoC 设备树和驱动，本轮直接复用它们。

| 层级 | 官方源文件 | 已核对内容 |
|---|---|---|
| SoC 设备树 | [sm8150.dtsi](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/sm8150.dtsi) | `gpu@2c00000`、`qcom,adreno-640.1`；`gmu@2c6a000`、`qcom,adreno-gmu-640.1`；GPU/GMU 时钟、GDSC、IOMMU、OPP、speed_bin、ZAP 保留内存引用 |
| GPU 型号支持 | [a6xx_catalog.c](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/adreno/a6xx_catalog.c) | A640 `0x06040001`、1 MiB GMEM、`a630_sqe.fw`、`a640_gmu.bin`、ZAP 名称与 A6xx 函数表 |
| GPU 执行 | [a6xx_gpu.c](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/adreno/a6xx_gpu.c) | MSM DRM 的 A6xx 硬件初始化、命令提交与恢复实现 |
| GMU | [a6xx_gmu.c](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/msm/adreno/a6xx_gmu.c) | GMU 初始化、固件加载、HFI 与电源管理实现 |
| 用户态 | [Mesa Freedreno/Turnip](https://docs.mesa3d.org/drivers/freedreno.html) | A6xx 可用 Freedreno OpenGL ES 和 Turnip Vulkan；当前临时测试只选择 Turnip |

本机实际源码 v7.3-rc6 中这些节点、A640 条目和依赖均存在，所需 DRM_MSM、GPUCC、SCM/MDT loader、SMMU、LLCC、RPMh 和 SM8150 interconnect 已内建。没有另写 A640 驱动或套用 Android KGSL 驱动。

本机板级 DTS 的增量只有 GPU/GMU 改为 `okay`、ZAP 固件路径改为本机专用路径；三个固件均来自本手机 vendor 的只读提取。SoC DTS 的默认 `disabled` 是供具体板子决定启用，不能解释为主线不支持。

本轮 GPU 接入首先暴露 DPU 旧帧排空超时和既有清理双释放；这是实际日志显示的失败位置。消除 Oops 不等于 GPU 渲染已经通过。最终状态以新的启动、固件认证、真实渲染回读和显示回归结果为准。
