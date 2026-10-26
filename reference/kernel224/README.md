# 224：RAW自动统计、曝光元数据与停止清理已部署

2026-10-16，手机当前为boot219/Image183、IMX471 e49、CAMSS fae1、完整libcamera 99990.7.2-r11/config 0.1.0-r6。本轮没有刷写或重启；全外设goal继续active。[安装](r11-package-install-validation.json)、[最终健康](final-health-validation.json)、[部署锁](../../linux-port/camera/deployment-lock.json)。

前摄IMX471的约2MP、4MP RAW和CPU RGB已取流。r11安装后普通/隔离IPA共128帧通过；实验4608×3456 RAW和CPU RGB各36帧通过，曝光元数据换算误差均小于1µs。默认cam/GStreamer各6帧通过，实验模块参数与用户态开关已关闭，WP恢复。[128帧](r11-installed-native-validation.json)、[完整RAW](raw-exposure-metadata-system-r11-4608x3456-validation.json)、[完整RGB](exposure-metadata-system-r11-4608x3456-validation.json)、[GStreamer](standard-gstreamer-validation.json)。这些是取流与控制链证据，未验收真实色彩、几何、实时帧率或GUI日用。

原r8的RAW-only绕过软件ISP配置和统计，16帧基线的曝光/增益元数据均缺失；−1只是探针缺失标记。0015让CPU路径只读原RAW缓冲，执行DMA读同步、统计和原软件IPA配置/启动/请求/元数据流程，不分配RGB输出、不修改RAW数据；非CPU旧RAW路径保留。223按真实SOF取得的捕获控制快照继续使用。[基线](baseline-raw-gap-validation.json)、[0015](libcamera-raw-only-statistics.patch)。

有限帧取流之外，同一相机停止/重配测试找出两处错误。r9在重复取消请求时触发断言/SIGABRT；0016改用仍由live frame map持有的请求，先清除所有权、再各取消一次。r10修好RAW退出，但未处理的RGB输出未继承取消状态；0017在completeBuffer前传播捕获状态。r9、r10各128帧普通取流通过仍未获部署，失败日志与产物均保留。[r9失败](lifecycle-r9-cancellation-failure-validation.json)、[0016](libcamera-stop-live-requests.patch)、[r10失败](lifecycle-r10-cancellation-failure-validation.json)、[0017](libcamera-capture-cancel-status.patch)。

r11候选普通/隔离IPA及安装后系统各做一次相同生命周期测试，每次同一Camera对象RAW2M→RGB2M→RAW4M→RGB4M→RAW2M，20请求完成且有曝光/增益、20请求正确取消，无停止卡死或挂起请求。测试二进制与断言未因失败修改。[探针源码](raw-lifecycle-probe.cpp)、[候选普通](lifecycle-r11-candidate-threaded-validation.json)、[候选隔离](lifecycle-r11-candidate-isolated-validation.json)、[安装后](lifecycle-r11-system-threaded-validation.json)。首次包装器晚采样/proc失败单独保留，不当作驱动结论。

三版均用官方abuild完整构建13包；r11保留原14补丁、17补丁完整链、全部管线、子包和tuning。34个ARM64 ELF、5IPA匹配保留核心公钥及Qt/Python入口通过；原214构建树2254文件/链接/模式均已恢复，r9/r10/r11对象树独立保留。外部原IPA214/APK203签名私钥复用，未公开；二次逐字重建未验证。[r11构建](r11-package-build-validation.json)、[产物](r11-forward-package-artifact-validation.json)、[主机QA](r11-host-runtime-qa-validation.json)。

原生签名七包升级已完成，944包中的937无关记录及49相机payload/权限复核通过。仅重载空闲WP，桌面与PipeWire身份保持；完整模式实验结束后当前WP仍映射r11。[重载](wireplumber-reload-validation.json)。r11→r8/r3回退使用实际223七包及224事务前world/repo，保持fae1/e49模块；降级模拟通过，完整回退往返未执行。更早r7/82c是历史配套回退，不能混用。

室内关灯条件保持，没有闪光或外部照明，没有保存场景图像。223暗光4MP RAW/RGB各6帧有非零值和帧间变化，未复现固定全零黑帧；本轮验证元数据与生命周期，没有重新保存或检查场景像素。CPU ISP内部确实读取RAW统计，不能称为“整个CPU未访问像素”。普通客户端报告已更正歧义字段，原输出私人保留。[暗光历史证据](../kernel223/dark-frame-classification-validation.json)、[字段修正](client-reporting-correction-validation.json)。

最终相机/CCI/CAMSS休眠、两前摄电源关闭/用户0、图案0/参数N；三DSP running、BT关闭无连接、GPS引擎关闭/watch空闲、chrony Normal、taint与五类fault均0、NV源保持。Modem仍State−1/原因2/Power1；两槽absent/no-atr是221历史结果，并非本轮查询。[最终健康](final-health-validation.json)。

标准手动曝光/增益独立Auto/Manual、物理2/1帧延迟、真实CFA/几何/颜色/方向/标定、GUI/性能、后置四摄与GPU ISP故障仍开放。16MP为双开关实验，内部TPG普通Bayer不能证明真实Quad颜色。上游CAMSS RFC仍用软件ISP，RAW统计待办可作设计参照，不能据其宣称SM8150硬件ISP已支持。[上游核对](UPSTREAM-NOTES.md)。GNSS真实fix、蜂窝业务、BT phase5、传感器SSR及全部外设继续按[清单](../../linux-port/docs/HARDWARE-STATUS.md)推进。
