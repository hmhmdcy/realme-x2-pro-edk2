# 293：VFE175 标准白平衡参数实机闭环与 FULL 回归修复

2026-10-19。实际手机为 **#293 / 7.3.0-rc6-rmx1931-samurai-k293+**，完整 Image 与独立 778 模块已部署、读回核对。S5K3M5 经真实 CSI→CSID175→VFE175 FULL 的标准白平衡参数测试 81 帧通过；IMX319 无内部图案实景 18 帧、四摄 RAW＋CPU ISP 18 段 232 帧通过。**完整多摄和 ISP 目标仍 active。**

另有整机缺陷：本次 SSC 默认启动失败，FastRPC attach 返回 EPERM/exit4，SLPI 已停止，SensorProxy/自动旋转不可用。已一次临时 nodeps 启动恢复桌面，永久依赖配置保持，未重复失败的 SSC 启动。不能称整机健康或自然启动验收通过。[故障](ssc-failure-validation.json)、[桌面恢复](desktop-restore-validation.json)、[最终状态](final-health-validation.json)

## 底层修复与来源

[292](../kernel292/README.md)已实现实际输出 pad 格式门控、VFE175 零 DMA 参数节点、metadata link validator，但遗漏了 FULL 校验器原有 num_outputs == 1 限制，导致真实图像 QBUF 全部 EINVAL。293 提交 **1aa1955077c977b611c722eca0bc467c3bf052ed / samurai-params293** 允许单路 FULL 附带一个标准 params pad、零 write master 的参数输出，同时拒绝其它辅助输出。图像 DMA 地址范围/对齐、NV12 几何、Y/C client 与 plane 限制保持。[补丁](full-with-params.patch)、[函数测试](full-params-host-validation.json)

测试直接提取真实 validate_output/validate_buffer，旧代码对合法 FULL＋params 负对照失败，新代码 ASan/UBSan 通过；额外 DMA、未知 pad、非法输出数、client/plane 和地址越界均拒绝。checkpatch 0 error/warning。修复属于 SoC 驱动，没有设备树、固件、校准或产品用户态改动。

继续复用作者的 [IFE 标准测试](https://github.com/0xB0D/ife-tests)及[公共 typed 参数节点方案](https://lists.openwall.net/linux-kernel/2026/10/05/1605)。本机后端使用已核对原厂协议，标准参数结构不新增私有接口。该公开补丁及本地在树内实现均不等于主线上游已经接受。

## 实际参数与颜色验证

通过实体发现 msm_vfe0_params=/dev/video4、msm_vfe1_params=/dev/video9；FULL=/dev/video3。只声明 sink/FULL/params 的格式，不存在的 DS4/DS16/stats 格式返回 EINVAL。本轮验证 VFE0；不能推广为双 IFE 同时工作。

S5K3M5 原模式 GRBG10 2104×1560，传感器图案 2、CSID 图案 0，经真实 CSI 输出 320×240 NV12。工具只用标准 MC/V4L2，无用户态 MMIO 或 CPU ISP。参数节点为 META_OUTPUT，QCIP 容量 56 字节。[81 帧及清理](wb-params-capture-validation.json)

- 10 类非法参数 QBUF 均 EINVAL：版本/大小、非支持类型、冲突或未知 flags、非法 gain、非零 offset、padding、截断块和短头。
- 九阶段：预队列 unity；分别 R/B/G 四分之一增益；header-only DISABLE；bypass 中更新值；重新 ENABLE；停参数流继续图像；停开图像流恢复默认值。7 个参数缓冲完成，81 帧、9 张阶段末图。
- 每次合法 QBUF 后，用户态保留合法包头、把 gain 载荷清零；实际图像仍符合 QBUF 时参数，验证内核快照不受后写影响。
- 独立 291 RAW 色块参考，按线性 gain→sRGB→601 full-range 预测，九阶段最大 Y/U/V 误差均小于 1.235；RGB 独立方向、禁用、重启及状态清理符合预期。私人预览已核看。[像素对照](wb-params-pixel-validation.json)
- 可观察切换的实际首帧为 10/19/28/37/55，与 PARAM_DQ sequence 完全相同，之后本阶段保持一致。phase0/5 颜色不变，不能从像素确定首次生效，明确排除在帧切换证明之外。[帧级核对](frame-association-validation.json)

范围是单个队列更新、一个模式/输出尺寸、测试图案下的 WB gains。尚无统计闭环、请求 API、自动白平衡、offset/BLC、复杂参数组合、长稳或完整 libcamera hardware pipeline 验收。

## 实景、回归与启动缺陷

用户确认后摄正常照明、无遮挡后，IMX319 同模式无 sensor/CSID 图案，gain512，曝光500→3000→500行，18帧通过。阶段末 Y 均值74.230→89.303→74.230，标准差2.688→12.216→2.688；私人预览已看到可辨识边缘/结构，仍偏暗偏绿。证明光学输入和可逆曝光响应，不证明完整画质调校。[像素](optical-pixel-validation.json)、[核看](optical-review.json)

普通 libcamera cam 四摄独立进程18段232帧全部通过，主摄SIGINT28帧后重开12帧；每段供电/时钟回收，无强杀或测试期间服务重启。仍为 RAW＋CPU SoftwareIsp，不能称相机应用已使用硬件 ISP。[回归](four-camera-regression-validation.json)

最终核对778模块、50载荷、961包，旧292/290/288各778、旧k132776和未启动292 R1的778模块完整保留；五sensor/lens、双CCI、CAMSS suspended，九rails/共享IO disabled/0，四MCLK/双CCI clocks0，CCI错误列表空、fault0/taint0/pstore空。Phoc5644、Phosh5714、PW7087、WP7089；详细start_ticks见最终收据及手机k293-services-verified-private.json。

SSC失败上下文在私人目录保留：默认服务确实 attempted→exit4→stopped，FastRPC node attach EPERM，SLPI offline，modem/adsp running。不是仅启动慢，也未证明由相机修复引起。临时 `rc-service --nodeps greetd start` 一次成功，greetd依赖配置SHA不变；本轮不盲目重试共享池/SLPI停启。原273同现象仍需定位根因。

## 当前部署及升级依赖

完整构建152.74秒，五阶段W=1诊断0，39个CAMSS组件Werror；三个嵌入BT模块与新安装树匹配，depmod无未解析符号。只刷logdump，boot276与DT保持；源码、镜像、模块一致。[构建](boot-candidate-build-validation.json)、[打包](boot-package-validation.json)、[启动读回](postboot-identity-validation.json)

准备中的复制路径、宿主工具参数、报告目录及BusyBox诊断选项错误已单独记入[准备记录](preparation-notes.json)；都在相应检查点停止并修正，没有把失败检查写成成功。最终SSC默认启动失败保持为实际缺陷。

| 层 | 当前达到 | 仍缺 |
| --- | --- | --- |
| 引导 | 原厂XBL/ABL→BootShim→EDK2→EFI stub→Linux已运行 | 仍有本机专用链和打包，发行版标准内核安装/更新未闭环 |
| 固件 | modem/adsp/Wi-Fi等原厂二进制继续使用 | 完整ACPI/持久变量、固件/系统整套独立更新验收；本次SLPI启动失败 |
| 硬件描述/板级 | SM8150公共DTS＋本机DTS；供电、接线、lens/模组属性逐步归标准描述 | 仍有bring-up资源保留策略，不能称全树标准化完成 |
| 主线及SoC/驱动 | 固定7.3-rc6基础，通用CCI PM、PM8008、sensor/lens、VFE175 FULL/WB有实际实现及测试 | 当前维护树相对base有48本地提交/175改动文件，尚未证明上游接受 |
| 用户空间 | 标准MC/V4L2、libcamera/PW/GStreamer，四摄CPU成像，历史主摄单次AF | libcamera配方28补丁（含发行版既有补丁）、PW另6项目补丁；硬件pipeline/统计/IPA和完整调校未接入 |

[本轮分层审计](layering-validation.json)重新读取实际启动：EFI/DT存在、/boot为空，clk_ignore_unused、pd_ignore_unused、regulator_ignore_unused仍在。**有底层收敛，但不能承诺主线内核和关键软件包更新时零补丁或最小补丁自动适配。** 需要公共功能进入对应上游，设备差异留标准DT/固件/调校包，并做跨内核/关键包、冷启/PM/整机回归。源码树内的intree=Y不是上游接收证明。

原厂DTS/kernel可给接线、时序、模式和协议；vendor BIN/XML/EEPROM可给部分模组参数，不能直接把CamX调校搬给libcamera，开源内核也不等于完整Chromatix算法开源。板级接线归DT、公共协议归驱动、成像策略/校准归IPA/数据包。[调校来源与边界](../kernel276/OEM-TUNING.md)

后续优先SSC启动故障、统计/BLC及硬件pipeline/IPA，补主/前摄硬件路径、模组校准、AF加速/Continuous/距离映射、Shine OV02A1B、四摄GUI/录像及长稳。完整rootfs、GPU默认故障/CPU回退和旧modem watchdog仍开放。回退首选已保留#290镜像/独立778模块，未做回退往返；#292保留用于失败复核，不作为稳定FULL基线。所有一次性事务已结束，不重放终态切换或采集。
