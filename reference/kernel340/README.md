# 340：实时 AEC/CCT 联动 CCM

2026-10-20，候选 IPA 已用实时 lux index 或模拟增益选择完整 CCM 调校树，并与 CCT、白平衡一起排队到硬件。本阶段只修改 CAMSS IPA 的三个源文件，复用 338 SoC CAMSS 后端；没有板级、传感器或内核修改。源码 `/mnt/samurai-full282/libcamera340-runtime-ccm-built/src/libcamera-v0.7.2`，组件补丁 [0035](0035-camss-runtime-aec-colour-correction.patch) 以 339 为基础。

在可选 `colour_correction` 中设置 `aec_source: runtime`，`aec_control` 决定使用本帧 lux index 或实际模拟增益。未设置时仍使用原有显式参考坐标。实时 lux 轴要求启用 `aec_lux`；实时轴不再要求填写无用的参考 `aec_value`。DRC/HDR/LED 坐标继续明确配置，未冒充实时输入。没有可用 AEC 或 CCT 时保持上一次矩阵，开流无历史时用 unity。前摄原厂 CCM 禁用标志继续保留，现场启用只属于具名实验。

每次提交会保存选定的 CCM、AEC 坐标、CCT 和源统计 SOF，再与 WB 作为一个 ISP revision 上传。后续统计不能改写已提出或已准备的包。矩阵元数据按内核确认的 first SOF 选择；手动矩阵优先，零增益导致 CCT 未定义时保留矩阵。硬件编码相同（含偏移和 qfactor）的变化不产生多余上传。新参数确认后清理旧运行坐标，等待当前参数上下文的新统计。

- 候选 core/签名 IPA 构建成功，57.7 秒。实际 AArch64 模块 9 项相关案例通过；66 份 CCM 包及矩阵元数据共 5016 字节，与 335 保留的原厂 CamX 选择/插值/编码源码模型零差。另有两份前摄禁用启动包，未冒称启用。覆盖等待期间输入变化、历史 SOF、手动优先、零增益回退、量化无变化、重新开流；模拟增益轴使用明确的诊断触发域，不宣称对应原厂物理模式。
- 复用 335 未改合同，参考 CCM 及参考 CCM+静态 LSC 两项通过，包仍为 96/1888 字节。没有重跑无关旧组件。
- 现场四摄各三段手动曝光/增益加一段 AWB，共 222 帧、16 张内部图案。73 个已生效运行 revision，222 帧矩阵元数据共 7992 字节与独立模型完全一致。最终三段手动矩阵符合原厂曝光/lux 指令与 CamX 模型预期，10 组不同矩阵的图像对均实际不同；最后 AWB 均锁定。
- 首次分析错误地把公开图像 sequence 当作内核 SOF：前摄相差 1，其余三摄相差 0。已改为使用实际 Pair/恢复事件中的内核 SOF，全部帧重新离线核对通过，未为修正分析假设重复采集。驱动/IPA 原有映射本身正确。
- 初版合同工具被 Werror 拒绝一处误导缩进，已修正后编译/执行通过；功能源码未因此调整。

证据：[构建](build-validation.json)、[AArch64 合同](ipa-contract-validation.json)、[参考兼容](reference-regression-validation.json)、[现场 CCM](runtime-ccm-validation.json)、[采集恢复](probe-r1-validation.json)、[最终状态](final-state-validation.json)。私有表、样本、二进制和源算法仍只留私有目录。

候选尚未安装。现机仍为 Image298/S5K3M5 305/GW1 325/CAMSS338、libcamera r26/config r21。现场没有换模块或写系统配置；控制、媒体和服务已恢复，PW/WP24236/24239 uid10000，故障增量 0、taint 0，CAMSS/两 CCI 休眠、九路相机电源关闭/users0。

下一步从 340 继续动态 LSC、工厂曝光模式/供应商绑定和统一发布。当前运行参考尚未证明物理模式及主摄供应商绑定；内部图案不代表正常照明光学校准。几何同步、连续 AF 等完整目标仍在。使用 `storage.py` 临时 bind E 盘候选进入 SDK；C 盘近满，不建大型副本。
