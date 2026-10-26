# 212：同一boot镜像第二次启动与默认CPU ISP

boot211未修改、未刷写。以当前211身份完成分区/产品程序/786文件模块树核对、正常停用相机和三个DSP、关闭显示音频后，执行一次restart2和一次经新fastboot身份核对的reboot；两个请求marker均闭环。旧GPU告警及全部失败证据已保留，不能重放切换。[停用](quiesce-validation.json)、[停用归档](prewarmboot-archive-validation.json)、[新启动](runtime-validation.json)。

旧启动printk环形缓冲区从保存的349条变为可见348条，首轮严格总数检查在任何停用动作前拒绝。逐条带时间戳比较证明只是旧行被淘汰、没有新告警，修正检查后才继续；不是放宽到允许新增告警。所有原始日志保留。

新启动自动绑定IMX471/PM8008，加载新sensor模块及heap，CROP/TRY/ACTIVE均正确，sensor供电域存在，三个DSP running，taint/五类fault0。首轮普通用户取流发现`/etc/libcamera`目录被部署umask变成0700，CPU配置不可读，再次落入GPU的CMA不足；未取流、无新增fault。修复目录0755/文件0644并保留原失败。[首次失败](default-cpu-capture-validation.json)、[目录修复](config-directory-fix-validation.json)。

随后以真实桌面UID10000、不设置`LIBCAMERA_SOFTISP_MODE`，运行系统默认配置取得6帧1920×1088 RGB888。strace证明读取系统CPU配置且未打开DRM节点；日志没有EGL renderer。首帧全黑，随后5帧非全黑，后四帧预热窗口通过；没有超时、强杀或新增五类fault，测试图案均0。**不是六帧全通过，也不代表拍照质量已验收。** [6帧证据](default-cpu-capture-r2-validation.json)。

226秒最终健康：sensor/CAMSS/CCI休眠，VDIG/VANA disabled/users0、MCLK0、自身MMCX vote0；桌面相机监视进程未暂停。三个DSP running、taint和五类fault均0。GPS0/Signalsfalse/rate30，BT关闭无连接，NV及产品程序核对保持。GNSS自动UTC第8次准备成功、chrony Normal，没有人为补时或新增收星实验。[健康](final-health-validation.json)。

96份原生文件已私下快照归档并逐成员核对；原始场景图像、端点、私人标识与归档指纹不公开。未新增kernel源码变更，语法/diff检查通过，没有暂存或提交。[归档](final-evidence-archive-validation.json)、[源码](source-final-validation.json)。

当前运输`reference/kernel212/host.py`，guard为`/var/lib/samurai/k212-runtime/boot-id-private.txt`；boot211 c3bf043f…/DTB6f9f5b0f…/Image183、logdump183保持。CPU配置为当前兼容路径，GPU ISP的CMA不足/黑帧/IOMMU unmap仍需修复；首帧黑、IMX471增益helper/延迟/静态属性、方向/tuning、完整16MP及后置四颗摄像头均未完成。完整外设goal继续active。
