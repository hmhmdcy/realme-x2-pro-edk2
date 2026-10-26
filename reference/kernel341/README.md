# 341：动态 LSC、个体校准与统一 ISP revision

2026-10-20，候选 IPA 已将 LSC 从开流静态网格扩展为实时 AEC/CCT 触发的完整核心树选择，并和 WB/CCM 在同一 revision 内排队、生效。源码 `/mnt/samurai-full282/libcamera341-dynamic-lsc-built/src/libcamera-v0.7.2`，补丁 [0036](0036-camss-dynamic-lens-shading.patch) 以 340 为基础。仍未装包，没有更改内核、板级或传感器。

可选 `lens_shading.mode: dynamic` 使用 `aec_control` 的 lux index 或模拟增益，完整保留 lens/DRC/HDR/LED/AEC/CCT 树。lens/DRC/HDR/LED 仍为显式参考坐标，不冒充实时输入。所有五份选定 Default 根的原厂控制方法均确认为 lux index/曝光灵敏度比，rolloff enabled；每根恰有一个 golden 区域。使用一个明确选定的 golden/unit 主表对，沿用已验证的合成、绿色均衡、模式重采样与 Q10 编码，不自动混用未知光源或供应商。

缺省模式仍走原静态路径。动态模式无 AEC/CCT 时保持上一次网格，无历史时从 unity 开始。提议时冻结网格与来源坐标；后续统计不改变已排队的包，硬件编码相同则不重传 LSC。现有 1848/1888 字节容量和 1792 字节 LSC 块足够，无 UAPI 变更。CCM 与 LSC 复用同一个固定版本的浮点插值原语，避免两份数值规则漂移。

- core/签名 IPA 构建成功，83.29 秒。实际 AArch64 模块十份工厂/个体配置、143 份提交中，105 个 LSC 块及 125 个 CCM 块共 193160 字节与独立模型一致；38 次不重复上传未变化的 LSC。模型编译保留的原厂 LSC 插值/单表校准函数，重采样采用独立 Hermite 表达。原工具的私有编译封装最初缺 cstddef，补齐后成功，不改原厂函数或功能数学。
- 原参考 CCM/静态 LSC 两项合同以及三项新配置错误处理通过。实际 Default 轴与保留原厂 XML 的核对也通过。
- 四摄工厂/个体各四阶段，最终选定 369 帧、32 张图，163 个已生效 LSC 状态的诊断追踪值匹配独立模型，并按实际内核 SOF 核对。283 帧 CCM 矩阵元数据共 10188 字节也一致；前摄原厂 CCM 禁用保持。四摄八组最后均 AWB 锁定。
- 工厂/个体图像比较使用可重复图案，四摄合计 14 个阶段图像对不同。PN9 的随机图像差异不用于证明个体校准效果。诊断网格追踪值不是工厂 checksum，也不替代 AArch64 包的完整字节比较。

R1/R2 的高亮渐灰图案经 LSC 后使前摄、广角可用 AWB 区域不足，算法没有锁定；失败记录保持 false。R2 保存已完成手动阶段并继续独立案例。R3/R4 改用驱动已有的 PN9 控件，保留原 AWB 筛选条件，两摄均锁定。PN9 本身随帧变化，工具以实际控制与 AWB 锁定检查，不要求重复帧字节相同；手动阶段是已生效参数快照，不宣称所有浮点滤波已完全收敛。

R4 首次发送早于压缩包写完，远端只部分解包，没有 state/worker。已确认未启动，保留为 `/var/lib/samurai/k341-dynamic-lsc-r4-incomplete-transfer`，再用完整包成功运行。后续打包先写临时文件再替换，仍须等准备工具完成才启动。没有因观测超时重复执行相机切换。

证据：[ARM 参数](ipa-contract-validation.json)、[原路径兼容](reference-regression-validation.json)、[原厂控制方法](control-method-validation.json)、[现场 LSC](runtime-lsc-validation.json)、[最终状态](final-state-validation.json)。R1/R2 的失败与 R3/R4 补测分开保存，已通过的主摄和长焦采集复用。

现机仍为 Image298/S5K3M5 305/GW1 325/CAMSS338，libcamera r26/config r21；默认没有新个体绑定。PW/WP25981/25984 uid10000，所有 worker 终态，相关故障增量 0、taint 0，CAMSS/两 CCI 休眠、九路电源关闭/users0。私有调校、个体表、样本与算法库不进入公共镜像。

下一步是实际工厂曝光模式/主摄供应商绑定与统一发布。正常照明光学校准、几何同步、连续 AF 等完整范围仍未完成。保持 E 盘 ext4 候选和临时 SDK bind 工作方式，勿在近满的 C 盘建立大型源码副本。
