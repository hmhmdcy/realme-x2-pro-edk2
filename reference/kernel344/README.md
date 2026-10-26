# 344：本机私有校准成为默认配置

2026-10-20。已将 343 按明确模式选择的四份本机私有 Preview 调校安装到 `/etc/libcamera/ipa/camss-vfe/{model}.yaml`。默认应用现在会在五个已对应模式使用个体 WB/CCT、实时 lux 驱动的动态 LSC 和 CCM；前摄原厂 CCM 禁用保持。无需设置临时 profile 环境变量。完整光学与多摄适配目标仍 active。

使用的是既有 libcamera r27/config-r22、Image298/S5K3M5 305/GW1 325/CAMSS338，本轮没有改框架、内核、板级 DT、传感器、APK 载荷或工厂存储。公共包继续只含通用实现及通用配置，本机个体数据不进入公共仓库。

已核实安装版本的 `IPA_CONFIG_DIR` 为 `/etc/libcamera/ipa:/usr/share/libcamera/ipa`，且服务无会覆盖该查找的环境变量。部署前四份私有文件均不存在；正常启动的相机和 GStreamer 日志确认使用 `/etc` 文件。[路径观察](configuration-path-observation.json)。

| 默认校准模式 | 原厂索引 | 本轮结果 |
| --- | --- | --- |
| GW1 4608×3456 | 2 | 47 帧，AWB 锁定 |
| GW1 4608×2592 | 4 | 47 帧，AWB 锁定 |
| IMX471 2304×1728 | 1 | 43 帧，AWB 锁定 |
| IMX319 1632×1224 | 2 | 42 帧，AWB 锁定 |
| S5K3M5 2104×1560 | 3 | 50 帧，AWB 锁定 |

五组均完成三段手动曝光/色温和一段 AWB，共 229 帧、20 张内部图案；102 个 LSC 应用状态的诊断追踪值匹配保留原厂函数加独立重采样模型，186 帧 CCM 元数据共 6696 字节逐字节一致，按真实内核 SOF 配对。主摄 16:9 模式也通过动态网格重采样。前摄/广角使用驱动既有 PN9，不以随机图差异宣称光学精度。[默认参数验证](default-iq-validation.json)。

默认四个硬件相机和四个桌面相机节点正常；系统 GStreamer 广角 640×480 NV12 和 PipeWire 广角各 12 帧通过。实际相机 SPA 在 WirePlumber 进程中：它映射系统 r27 核心、新 CAMSS IPA 及 libspa-libcamera，启动日志也确认私有路径；PipeWire 核心进程自身没有这些映射。[部署与服务](install-r1-validation.json)。初版收集器错误地只检查 PipeWire 进程，报告 false；根据同一次实际 maps 观察修正为检查 SPA 宿主，不重启、不重采，保留[原判断](service-host-assumption-r1.json)。

事务 `/var/lib/samurai/k344-calibration-r1` 已终态成功，四份文件用同目录临时文件替换；若过程中失败，会撤回新增配置并恢复原服务。`backup-state.json` 记录此前各文件是否存在，备份位于同目录 backup。若以后需要回退本轮默认校准，将对应私有文件移出标准查找目录并重启相机服务，即重新使用未改的公共配置；不要重放现有安装事务。两服务最终 PID28486/28492、uid10000，相关故障增量 0、taint 0，CAMSS/两 CCI 休眠，九路相机电源关闭/users0。

范围是普通 Preview、无额外 Feature/Scene/Effect 的已对应模式。343 的 Video 选择数据仍保留，但本轮安装 Preview 版；当前 lux 活跃参数在两用途等价，完整原厂 knee 曝光编程尚未实现。前摄 1928×1088 上游裁剪保持原 generic 配置；广角/长焦全尺寸未新增完整 IQ profile。主摄 Sunny 对应仍以保留清单内的实际马达协议和光学响应为依据，不冒称 manufacturer EEPROM ID 认证或所有场景绑定。

内部图案证明默认加载及硬件参数链路，不能替代正常照明下的颜色、阴影、黑电平、畸变、几何同步和连续 AF 验证。下一步继续恢复原厂 knee 曝光分配及相关模式；无需为这些离线工作开灯，也不重编或重测本轮未改组件。
