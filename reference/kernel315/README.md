# 315：libcamera RAW 与硬件处理流接入

2026-10-19。硬件 CAMSS handler 已支持 RAW-only、NV12-only 和同一请求 RAW＋NV12。六种现有板级模式的双流默认 AE/AWB、四颗摄像头的 RAW-only、主摄双流／RAW-only 单次 AF 及取消、一次双流缓冲暂停恢复均已实机通过。候选没有安装，设备已恢复309 CAMSS，完整多摄／骁龙ISP适配目标继续 active。

## 分层与复用

沿用[314公共 CAMSS streams 驱动](../kernel314/README.md)，内核提交 afad7bde625bbf7bf58c145bde1f977b806da986。315最终不改内核、SoC资源、DT、传感器或板级电源；不增加私有 ioctl 或用户空间寄存器操作。图结构发现同一 CSID 的 PIX 与可输出 packed RAW10 的 RDI，不在 handler 中硬编码摄像头地址或视频节点名称。

沿用313 IPA、四个模组调校目录和 ContrastAf。标准 StreamRole::Raw 与 Viewfinder、Bayer格式转换、sensorConfig、FrameBufferAllocator／DMABUF导入、请求／缓冲完成接口用于新路径。应用RAW缓冲直接交给RDI DMA，没有逐帧复制RAW图像。RAW-only暂时仍分配四个内部640×480 NV12缓冲，为硬件统计和已有CPU对焦评分保留处理流；这部分内部带宽／内存以后还可优化。

两个VFE队列的内核帧号分别起算，不能仅按相等数值配对。复用标准[V4L2_EVENT_FRAME_SYNC](https://www.kernel.org/doc/html/next/userspace-api/media/v4l/vidioc-dqevent.html)，在libcamera内部V4L2Device新增带原事件CLOCK_MONOTONIC时间的信号，保留旧frameStart信号。分别保存RAW／PIX的帧号→SOF事件时间，待两路缓冲和统计／控制元数据完成后才归还请求。时间差须不超过min(1ms,实测帧周期/8)；事件缺失或不匹配时返回错误帧，不能交付为成功配对。

这属于软件中断事件时间关联，不是硬件帧ID或曝光开始时间。最初SOF缓冲时间原型错误使用SOE语义，在构建／上机前已撤回；[缓冲时间规范](https://docs.kernel.org/5.15/userspace-api/media/v4l/buffer.html)区分帧结束与曝光开始。原型差异仅留私有诊断，prepare-sof.py／build-kernel.py已退出禁用。最终保留原缓冲EOF时间，SensorTimestamp也仍沿用已有完成时间语义，尚未完成真正曝光时间标定。

## 实测结果

[r1](raw-r1-validation.json)先验证广角；[r2](raw-r2-validation.json)扩到其余三摄双流、四摄RAW-only和广角NV12-only；[r3](raw-r3-validation.json)验证两种新增模式、暂停恢复及主摄AF。应用等待AE／AWB稳定或AF完成后结束，记录帧数不是固定验收规模。检查实际DMABUF内容覆盖预填数据、有效长度、时间递增、标准控制元数据和SOF配对。

| 模组／输入模式 | RAW＋640×480 NV12请求 | RAW-only请求 |
| --- | ---: | ---: |
| 主摄 S5KGW1 4608×3456 GBRG10 | 35 | 35 |
| 主摄 S5KGW1 4608×2592 GBRG10 | 35 | 本轮未单独覆盖 |
| 前摄 IMX471 2304×1728 RGGB10 | 30 | 36 |
| 前摄 IMX471 1928×1088 RGGB10 | 32 | 本轮未单独覆盖 |
| 广角 IMX319 1632×1224 RGGB10 | 34 | 34 |
| 长焦 S5K3M5 2104×1560 GRBG10 | 36 | 36 |

六模式双流共202请求／404个应用缓冲，默认AE/AWB均稳定；四摄RAW-only共141请求。广角NV12-only另34请求通过。全部实验累计902个完成请求／1405个应用输出缓冲，包含下面的恢复和AF；其中868请求进行了RAW与可见或内部PIX关联，均通过，最大SOF事件差61,511ns。所有本轮普通流的两路帧号恰好相同，因此未声称已覆盖故意错位／单路独立重开后帧号不同的libcamera场景；代码仍以事件时间判定。

广角双流暂停归还四个请求缓冲120ms，实际出现4个未输出帧槽；重新归还后完成33请求／66缓冲，AE/AWB恢复稳定，无错误配对。没有声称暂停期间无损，或单路长期饥饿／事件丢失已覆盖。

主摄4608×3456：双流AF扫描224请求／448缓冲，23次镜头命令全部成功，最终Focused；双流取消另44请求／88缓冲，实际进入Scanning后取消并回Idle；RAW-only依靠内部NV12完成224请求、23次镜头命令并Focused。仍是同一场景／模式的CPU对比度AF，不是连续AF、VFE BAF、PDAF或距离标定。

相关候选库Werror构建第2次通过：[构建](build-validation.json)、[增量补丁](hardware-raw.patch)、[源码状态](source-state.json)。应用编译中修正了const Stream指针和DMA标志初始化的编译错误，没有放宽警告；三轮实际设备采集均通过。没有重建Image或全量内核模块。

## 当前状态与后续

所有315 worker、fixture、应用及其IPA子进程已终态。临时314模块卸载，实际加载恢复309；PW/WP恢复，CAMSS及两CCI休眠，九路相机电源关闭、用户0，相关内核故障增量0、taint0：[收尾](final-health-validation.json)。设备仍298 Image＋305长焦模块＋309 CAMSS，产品r24/config-r19仍RAW＋CPU ISP。

SDK `/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline` 现在是315。使用本目录build-candidate.py；它取315 pipeline与framework、313 IPA／mojom／YAML。旧313及更早构建入口会覆盖当前实现，不要重跑。build-runtime.py构建当前应用；prepare-probe.py只包装匹配产物，launch-probe.py必须使用新run名称。k315-raw-r1～r3不可重放。生成脚本保留过程，最终来源以当前源文件／补丁为准。

下一步接入产品包和PipeWire／GStreamer等消费者，完善帧时间语义、错位／事件丢失恢复及RAW-only内部处理流开销，再推进正式黑电平、CCM／颜色、镜头阴影和个体EEPROM校验／绑定、多摄几何与同步。304已解码的个体值仍未应用。四颗实体摄像头同时工作、其它OEM模式、连续AF和完整画质校准均未完成；用户延期的纯色／遮光不阻塞其它工作。旧GPU／modem／SSC问题仍开放。
