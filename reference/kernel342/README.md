# 342：r27/r22 正式包与本机主摄方案对应

2026-10-20。已安装 libcamera `99990.7.2-r27`、config/stack `0.1.0-r22`，合入 330～341 的个体白平衡、手动及自动 CCT、完整树 CCM、实时 lux/AEC 和动态 LSC。内核继续使用 Image298、S5K3M5 305、GW1 325、CAMSS338。本轮是用户空间发布，没有改板级 DT、传感器驱动或 SoC 内核后端。完整适配目标仍为 active。

通用算法留在 libipa，CAMSS IPA 完成模式配置、实时触发、量化与参数排队；硬件执行继续走现有 VFE175 后端。LSC、WB、CCM 按同一 revision 冻结，以内核确认的 SOF 更新生效状态。应用通过标准控制取流。DRC/HDR/LED/lens 参考坐标和工厂曝光表选择没有冒充已恢复的实时语义。

0031～0036 从 r26 源按顺序以零 fuzz 应用，32 个相关源文件与 341 实测源完全一致。完整框架构建成功，用时 828.67 秒，配置包 7.08 秒。13 个签名包、六个 IPA 以及 Python、qcam、GStreamer、V4L2 保留；七个运行包升级。已用打包后的核心验证剥离后的 CAMSS IPA 签名。[源码对应](package-source-validation.json)、[构建](package-build-validation.json)、[产物](package-artifact-validation.json)。

安装后四个硬件相机、四个 PipeWire 节点正常；系统 GStreamer 和 PipeWire 广角各取流 12 帧通过。内核模块保持，相关故障增量 0、taint 0，相机与两 CCI 恢复休眠。离线回退包 r26/r21 和 world/repository 备份保留在 `/var/lib/samurai/k342-install-r1`。[安装结果](install-r1-validation.json)。安装脚本具有旧版本前置，不能在现机重放。

已安装版本的四摄显式 unit profile 完成各四相位动态验证，共 183 帧、80 个 LSC 应用状态；LSC 诊断追踪值与保留原厂函数和独立重采样模型相同，140 帧 CCM 元数据共 5040 字节逐字节一致，均按实际内核 SOF 配对。四摄 AWB 锁定，前摄原厂 CCM 禁用保持。前摄和广角沿用驱动已有 PN9，不把随机图像差异当作校准精度。[安装后参数验证](installed-iq-validation.json)。

默认四摄 YAML 没有加入私有工厂表或个体参数；发布能力可用不等于默认画质已经完成校准。此前 341 的完整参数字节、factory/unit 图像对和未改动的 RAW/双流、主摄单次 AF 结果继续复用，不重复全量采集。测试结束所有相机电源关闭/users0，CAMSS/两 CCI 休眠，相关故障增量 0、taint 0，PipeWire/WirePlumber 各一 uid10000 进程。[最终服务状态](final-state-validation.json)。

本机主摄 `lens-focus` 实际指向 LC898219XI/0x72；结合 274 保留的物理镜头响应以及与 326 库存相同的原厂描述哈希，在 Sunny/Qtech 两份方案内对应 Sunny。另一份 Qtech 描述使用 BU64253/0x0c 和不同协议。这是实际执行器与保留清单的对应，尚未认证 EEPROM manufacturer ID，也没有证明不存在其它库存外模组。[方案证据](module-variant-validation.json)。本轮四摄测试为主摄显式 Sunny、其余显式保留来源，不据此自动选择曝光模式表。

首次动态验证 R1 在采集前被多余的 `apk info` 输出断言阻止，没有停止服务或采集；已删除该断言，安装版本以成功安装事务为依据，失败记录保留为 false。[R1](probe-r1-validation.json)。

正常照明下的颜色、阴影、黑电平、畸变及多摄几何同步、连续 AF 尚未完成；内部图案不能替代这些光学校准。下一步优先恢复物理 Sensor mode/Scenario 到调校根及 AEC 曝光表的选择，继续使用现有源码、原厂库和保留数据。未找到 checksum 不阻塞其它独立、可回退的实验。

正式源码在 E 盘 ext4 的 `/mnt/samurai-full282/libcamera342-r27-built/src/libcamera-v0.7.2`；使用 `storage.py` 临时 bind 到 SDK，不向近满的 C 盘复制大型树。私有调校、个体数据、样本、原厂二进制和密钥不进入公共镜像。
