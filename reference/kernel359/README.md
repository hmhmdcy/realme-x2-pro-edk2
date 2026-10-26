# 359：原厂曝光程序接入实际 CAMSS IPA（主机候选）

2026-10-20。基于342 r27完整候选，将345／346的原厂曝光分配与358防频闪接入实际 `HardwareAgc`。核心库、签名IPA和匹配的隔离代理已构建，实际ARM64 IPA及公共AGC回归通过；尚未安装或验证实机画质，当前接口的独立进程IPC仍待验证。手机最后确认仍为9008，恢复原因与操作见[357记录](../kernel357/README.md)。完整多摄／ISP目标继续进行。

实现按以下层次收敛：

| 层次 | 本轮变化 |
| --- | --- |
| 通用用户空间算法 | `AgcMeanLuminance` 提供拆分前的滤波目标；旧 `calculateNewEv()` 继续通过原分配器处理。`libipa` 接入通用曝光表与防频闪算法。 |
| CAMSS IPA | 新 `ExposureProgram` 读取已选择模式的曝光表、EV政策及防频闪参数，使用拆分前目标分配时间与模拟增益。 |
| 传感器约束 | 从实际 V4L2 曝光／增益控制范围和默认 VBLANK 取得约束。使用现有传感器辅助类与行时间量化，不把原厂表的 knee 当硬件上限。 |
| 请求与元数据 | 标准 `ExposureValue`、`AeFlickerMode=Off/Manual`、`AeFlickerPeriod`；按 SOF 保留策略，延迟统计和旧帧元数据使用对应历史。AE控制单独变化不增加ISP参数版本。 |
| 内部 IPC | `applyIspControls` 新增策略起始SOF，CAMSS pipeline版本升为1；核心、IPA和worker必须配套。 |
| 板级／内核 | 本轮不修改手机内核或板级资源。356已修正的ICP固件地址和357引用修正仍未安装。 |

私有8份完整Preview／Video配置保持原WB、CCM、LSC及lux内容，新增已有5个物理模式／10个用途上下文的曝光程序。其它4个高分辨率上下文缺完整IQ配置，本轮未拼造；未知前摄裁剪模式继续原行为。[配置准备结果](profile-validation.json)。原厂参数、校准内容和原库保持私存。

明确的适用范围：当前使用配置时固定帧预算，未实现动态 `FrameDurationLimits`、自动频率检测或数字增益补偿。最终行／增益量化和限幅可能破坏严格周期对齐，不能据此宣称消除实机频闪。AE亮度目标及滤波继续采用现有控制器，原厂分配政策接入不等于移植完整原厂AE状态机。349 Gamma候选尚待合并；ICP／IPE实际握手、图像会话、更多模式、光学、几何同步和连续AF等仍待推进。

构建记录见[build-validation.json](build-validation.json)。生产候选沿用Meson的 `werror=false` 配置，不能称为全库Werror构建；合同测试程序单独以 `-Wall -Wextra -Werror` 编译。

独立原厂指令组合生成60组参考，执行47,086条原指令。[原指令参考](native-reference-validation.json)。实际ARM64 DSO在四颗传感器／10个模式用途上下文逐位核对全部60组分配；主摄另通过线程代理重复6组。控制历史、延迟统计、EV／手动防频闪元数据、非法输入原子拒绝、验证不提交状态、AE单独变更不产生ISP版本、WB合并确认及重启复位均通过。[IPA结果](ipa-contract-validation.json)。统计缓冲和V4L2控制由夹具提供，范围依据当前驱动源码；这些检查不访问实机，也不验证画质或硬件帧时序。

公共 `calculateNewEv()` 使用各自匹配的342／359头文件及静态库分别构建ARM64程序，10个上下文共480帧／15,360字节零差，包括零曝光回退、滤波／重置、不同EV目标和饱和。传感器量化辅助类源码保持一致。[回归结果](agc-regression-validation.json)。

独立进程代理实际尝试仍因当前QEMU不实现 `clone3` 而无法启动worker，记录为未通过；没有更改生产进程隔离代码绕过它。[环境限制](isolated-transport-validation.json)。线程路径遵循异步 `parametersApplied`，通过后续统计回执确认完成后再查询元数据，不把排队发送当作已生效。

通用源码差异保存在[补丁](exposure-program-integration.patch)，文件清单及哈希见[source-state.json](source-state.json)。主机曾在两个调用同时首次挂载时重复挂载同一构建镜像；两调用都在修改前被检查中止，确认无工作进程后卸载恢复。`kernel284/storage.py` 现串行化发现与挂载，后续构建和测试正常；没有格式化或重建镜像。
