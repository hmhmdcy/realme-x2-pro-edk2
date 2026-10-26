# 387：四摄实际 libcamera → IPE 管线，82 帧通过

将原有 CAMSS/IFE 相机管线接入标准 V4L2 m2m IPE 节点。最终候选通过四摄、主摄 RAW 配对及隔离 IPA 验证，IPE 作业 82/82 完成、取消 0、处理错误 0。完整多摄／ISP校准目标仍 active；本轮是私有候选验证，没有永久安装、刷写或重启。

## 分层与复用

沿用 [386 已验证的原生 IPE 核心、V4L2 m2m 和原厂固件](../kernel386/README.md)，复核当前 libcamera 0.7.2 的 V4L2M2MDevice、连续平面合并及缓冲导入实现。没有重复实现 m2m 调度器，没有新增 CPU 图像算法。

SoC 固件、条带、IQ旁路及 DMA/PM 回收逻辑保持386。内核媒体适配层增加固定 driver 名称 qcom-ipe-a5，避免用户空间依赖临时平台驱动名；诊断计数把 ECANCELED 与真正处理错误分开。板级持久 DT、Image、传感器驱动、已安装 r29/r24 和362私有校准配置不变。仍由临时平台所有者和七组 SID 覆盖运行，正式平台驱动及板级启用尚待。

内核维护源 /mnt/samurai-full282/source354，分支 samurai-ipe-pipeline387，HEAD 8003933b7e31e4b5f4d27d21789d42da686831ba；父386 ab58f554a7b9f886bd43b9c3f47d52761d9bf982，中间提交5bd45e8aecb4e978de7400073678abca77bc376a。[媒体标识补丁](media-driver.patch)、[取消计数补丁](cancel-accounting.patch)、[状态](source-state.json)。源码干净。

用户空间候选 /mnt/samurai-full282/libcamera387-ipe-built/src/libcamera-v0.7.2，由已安装r29对应的362源复制。[最终补丁](camss-ipe-pipeline.patch)可直接应用到该r29源；早期 prepare-source.py 与后续修正脚本保留实验过程，不应把最初版本当作最终实现。common dispatcher 和 IPA 源未改，保留362同步隔离 IPA 重入修复。

## 缓冲、时间戳与退出

内部 IFE 缓冲作为 m2m OUTPUT 输入，应用导出的 DMA-BUF 作为 m2m CAPTURE 输出。使用现有 libcamera 连续颜色平面合并能力，没有用户空间像素搬运；核心仍复制到自有 DMA 缓冲，**并非零拷贝**。

[CamssIpe](camss_ipe.cpp)先设置两端格式，再申请任一端缓冲。单侧入队失败会停止整个上下文，避免 FIFO 错配。输入使用共享 FD 包装对象，防止 m2m DQBUF 覆盖原始 IFE 的 SOF、时间戳；两端都归还后才完成请求，应用输出恢复原始 IFE 元数据。RAW配对继续用 IFE SOF，而非m2m局部序号。内部缓冲关联在应用回调前移除，支持请求复用。

本版本 libcamera 通过字符串构造 V4L2M2MDevice 时没有连接 video watchdog 的超时槽，因此管线自有3秒作业超时器，随排队、完成和停止启停。STREAMOFF失败后先关闭FD并等待驱动工作退出，再完成剩余缓冲；该对象随后拒绝重新打开，以免复用库内未清除的旧队列记录。没有修改通用 V4L2 类或 IPA ABI。

IPE媒体设备不存在时保留原有IFE路径；若发现IPE但启动／入队失败，会返回错误而非悄悄旁路。RAW单独输出不启动IPE。

## 验证

[ipe-validation.json](ipe-validation.json)：对实际包装层源码运行ASAN/UBSAN及18个队列provider用例，覆盖两种DQ顺序、启动各阶段失败、单侧QBUF、STREAMOFF失败后等待close及拒绝重开、独立超时器、回调内停止。provider不证明完整内核并发或真实硬件故障。[cancel-validation.json](cancel-validation.json)验证实际计数语句不会把真实错误归到取消。

[build-validation.json](build-validation.json)：实际AArch64 libcamera构建通过。[intree-build-validation.json](intree-build-validation.json)：k363配置in-tree/W1/-Werror通过，无诊断；共享CAMSS/V4L2/vb2输出及config/symvers已恢复。核心、标准m2m helper、临时平台模块二进制与386相同；仅适配器变化，115544B，SHA256 a7fd24755c2aaa667a1591fdd44778aa6dd0d69fcc61213589bff40ca6604546。未替换设备已有vb2模块。

[pipeline-validation.json](pipeline-validation.json)、[实机r5](pipeline-runtime-r5-validation.json)：唯一 /var/lib/samurai/k387-pipeline-r5，worker21629，实际节点video12/media1为动态分配，不应硬编码。候选库SHA256 60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d；上传清单校验与主机最终产物一致，隔离应用映射中确认实际加载该库。

|用例|应用结果|IPE完成|
|---|---|---:|
|imx471 / imx319 / s5k3m5 / s5kgw1|各12帧640×480 NV12，GStreamer无bus错误|各12|
|主摄RAW＋NV12|6请求；NV12时间戳等于原始SensorTimestamp；6组SOF配对，最大差15885ns|6|
|主摄RAW单独输出|6请求、6组SOF配对，最大差23854ns|0|
|主摄强制隔离IPA|28帧、5控制阶段、Gamma ACK1；IPA统计来自不同进程|28|

合计82个IPE作业、82完成、0取消、0真正处理错误、6次FW运行。最后一次运行是隔离主摄：单会话create/destroy/peak1，28帧MAP/FRAME/UNMAP，91消息／92中断／debug1，watchdog和protocol错误均0，正常PC/WFI退出。未发送PING，ping_done=false不是失败；旧synthetic字段scratch数组和image_bytes不用作m2m像素证明。完整像素／UV误差复用386证据，本轮没有重做全图identity对照。

## 失败审计与当前状态

[attempts-validation.json](attempts-validation.json)保留r1～r4，均已清理并恢复服务。r1误用model匹配driver，12帧实际仍走IFE，IPE0；r2先申请OUTPUT缓冲再设置CAPTURE格式，EBUSY、IPE0；r3四摄输出均成功，但旧计数jobs49/completed48/failed1无法区分取消与错误，具体返回码未记录，**不事后改称已证明取消**；r4四摄及RAW两种模式通过，私有库触发未安装路径判定，隔离IPA找不到代理。最终设置已安装IPA/代理搜索路径。r3旧collector窗口10秒超时但无dump／相关fault；最终窗口330秒，每个用例前检查collector活跃，r5全程有效且正常退出。

[current-state-validation.json](current-state-validation.json)：同一378恢复启动，五次worker/client/collector均不活跃；taint0、CAMSS和双CCI休眠，九路相机电源disabled/users0，17相关时钟归零。临时模块、节点、FW均移除，PipeWire/WirePlumber各一实例恢复。Image363/DT365/boot366、已安装r29/r24保持；静态ICP仍disabled，SSC旧问题未修。本轮没有证明整个平台全部健康。

## 接续范围

先复用现有驱动／仓库与原厂固件证据，推进SG/DMABUF直接DMA以去掉核心CPU复制、正式平台所有者和板级部署；补显式在途取消／错误并发实测，再接原厂Gamma/LTM/CCM完整IQ和全部[剩余校准](../kernel363/REMAINING-CAMERA-SCOPE.md)。r5取消0，模型与r3旧混合计数不能替代实际取消分支验证。第五2MP身份、更多模式、动态帧时长／防频闪、几何／多摄同步与连续AF仍待。

现场按用户关灯条件解释，黑场／噪点不单独判链路失败；需要照明的光学／颜色校准后做。原厂FW、HAL、反汇编、CDM、完整日志、图像与个体校准仅私存 /mnt/e/edk2-samurai-out/kernel387；公共镜像仅自有源码、工具及脱敏证据，本地提交，不push／PR。
