# 339：每帧 Bayer 亮度与 lux index 接入候选 IPA

2026-10-20，已在 335 候选 IPA 上接入 337 恢复的原厂普通 RGB Bayer→16×16 亮度池化→曝光 index→lux index 数值链。源码在 `/mnt/samurai-full282/libcamera339-lux-built/src/libcamera-v0.7.2`，组件补丁 [0034](0034-camss-runtime-reference-lux.patch) 以 335 为基础。候选 core 与签名 IPA 编译成功，尚未替换系统 r26/r21。

新增的是通用 libipa 数学和 CAMSS IPA 可选模式配置。内核、板级、传感器本阶段均未修改，现场复用已部署的 338 CAMSS。物理模式与工厂曝光表、主摄模组供应商仍未证明绑定；运行配置明确指定参考值，不自动选择来源。

`aec_lux` 可选节点包含 `exposure_anchor`（`analogue_gain`、64 位 `exposure_time_ns`、`index`）、RGB `weights`、`reference_gains`、`compensate_colour`、`normalization`，以及 `lux` 的灵敏度补偿、参考/表零点灵敏度和滤波因子。缺省或 `enabled:false` 不计算；不会写入标准物理照度 `Lux` 控制。

计算使用统计对应 SOF 已生效的 ISP 参数上下文，以及实际传感器曝光行数/增益码；纳秒曝光由真实行时长换算，颜色补偿使用硬件量化后的有效增益。未知上下文、缺 BG、不兼容网格或重复/损坏统计不推进滤波。开流、停流重置滤波。结果以私有 IPA Statistics 的 `luxValid/exposureIndex/luxLuma/luxIndex` 返回，当前用于诊断及后续动态调校接入；没有把未标定值发布成物理 lux。

- 实际 AArch64 IPA DSO：11 项相关检查通过。7 组配置共 63 条有效结果、756 字节，与原厂曝光/Bayer/池化/lux 指令逐字节一致；另覆盖禁用、错误配置、延迟 SOF、生效前后 WB、重复/缺失/损坏统计和重新开流。颜色补偿亮度最高 359.018，不错误截为 255。
- 手机内部图案：四摄加广角颜色补偿共 5 次采集，122 帧均产生有效实时结果，AWB 收敛且图像稳定。原厂指令核对实际曝光 index/滤波；120 帧的亮度还与 338 稳定内部图案原始统计模型对应。INFO 日志仅六位有效数字，最大对比误差 0.000507，小于明确的 0.003 日志容差；这不替代上述 DSO 精确字节比较。
- 前摄 SOF0/1 的亮度为 0.1，随后出现稳定图案。两帧保留在曝光和滤波检查中，不拿 338 稳定图案包替代其输入。首次分析假定所有启动帧都与稳定参考相同而报错，已修正分析范围并记录启动帧。
- 首次 DSO 加载发现 ValueNode 没有 uint64_t accessor；已改为原始标量字符串加 `from_chars` 的 64 位整数解析，重新编译/签名并通过实际加载。未降为浮点时间或缩窄时间域。

证据：[构建](build-validation.json)、[AArch64 合同](ipa-contract-validation.json)、[现场数值](runtime-lux-validation.json)、[采集恢复](probe-r1-validation.json)、[最终状态](final-state-validation.json)。现场未装包或更换模块；媒体和控制恢复，相关故障增量 0、taint 0，CAMSS/两 CCI 休眠，九路相机电源关闭/users0。PW/WP 为 uid10000 的 23394/23397。

当前安装仍为 Image298/S5K3M5 305/GW1 325/CAMSS338、libcamera r26/config r21。默认无个体 LSC/WB/CCM 绑定。下一步从 339 候选继续模式/供应商绑定、lux→动态 LSC/CCM 与统一发布；正常光学校准、几何同步、连续 AF 等完整目标仍未完成。继续内部图案和源码工作无需室内光亮。

候选放在 E 盘既有 ext4 构建镜像；用 [storage.py](storage.py) 先挂载镜像，再在构建/合同期间临时 bind 到 SDK `/work/libcamera`，结束后卸载 bind。原 SDK 工作树和 335 候选保留；不要在近满的 C 盘建立大型副本。原厂表、个体值、样本、算法库、仿真环境和构建二进制均只保留私有输出目录。
