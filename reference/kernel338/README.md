# 338：部署兼容原厂亮度链的 CAMSS 统计网格

2026-10-20，已安装并加载 CAMSS 338。默认 BG 网格从 32×24 改为 32×16，满足已恢复原厂普通 Bayer→16×16 亮度池化的几何要求。仅修改 SoC VFE175 统计后端一个文件；板级 DT、传感器、UAPI 最大容量均不变。338 同时包含 334 的 CCM 硬件后端，候选 335 IPA 尚未安装。

源码 `/mnt/samurai-full282/source338`，分支 `samurai-lux-grid338`，干净提交 `e3aa81b109e44735161036a2adede105e437ed01`，父提交 334 `6c762eae4a4af55d8d9111d3c9fd8c2880f5dad1`。使用现有 E 盘 ext4 构建镜像，先调用 `reference/kernel284/storage.py` 的 `mounted_build()`；C 盘空间不足，不再向其复制大型源码树。

- 相关模块及依赖闭包 W=1/KCFLAGS=-Werror 构建通过，37.32 秒，无诊断。没有重建或更换整套 Image。
- 四摄内部图案实际统计均为 32×16、16424 字节，最大容量仍为 22568 字节。2048 个真实 Bayer 区域经原厂指令与独立 C++ 主机/ARM 比较，各 8224 字节零差。
- 新网格下，已安装 r26 IPA 的四摄 AWB 全部收敛并取得稳定图像，共观察 95 帧；主摄、前摄、广角、长焦均通过。
- 持久安装后四个硬件相机及四个 PipeWire 节点可见，GStreamer/PipeWire 取流通过。相关故障增量 0、taint 0，CAMSS/两 CCI 休眠，九路相机电源关闭且用户数 0。PW/WP 为 uid10000 的 22627/22630。

当前 CAMSS SHA256 `c7ebd3b6d4e288530d88455e3a2504b23f627fa12bb34efeac6659365c6f256f`，已加载 note SHA256 `0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297`。原 318 模块保留在手机 `/var/lib/samurai/k338-install-r1/qcom-camss-before.ko`。libcamera r26、config/stack r21、Image298、S5K3M5 305、GW1 325 不变。

证据：[构建](kernel-build-validation.json)、[真实统计](hardware-statistics-validation.json)、[四摄 AWB](awb-grid-validation.json)、[安装](install-r1-validation.json)、[最终状态](final-state-validation.json)。R1/R2 记录中的 `installed:false` 描述当时的临时试验；持久部署以安装记录为准。

亮度比较采用显式 Default Metering 权重及参考 exposureIndex=200，仅验证数值链；并未证明物理曝光表/传感器模式绑定或主摄 Qtech/Sunny 供应商。内部图案不代表正常照明光学校准，lux index 也不是物理照度。接下来将 337 原语接入 335 候选 IPA，再推进真实模式绑定、动态 LSC/CCM 和统一发布。完整多摄适配目标仍在进行。
