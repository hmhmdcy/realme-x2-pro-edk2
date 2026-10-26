# 418：libcamera IPE 请求链路与三方完成回收通过真机验证

候选 `CamssIpe` 已接入417的类型化 Media Request 控制。实际候选库完成16帧非零参数像素验证、4个立即停流取消回调；相机管线完成81帧处理图像请求，包含四摄48帧、主摄RAW＋NV12的6帧和隔离IPA的27帧。**自动调校算法仍未生成非零IPE参数，相机管线本阶段显式提交旁路包；正式软件与驱动已恢复。**

## 分层与现有方案复用

| 层次 | 本阶段范围 |
| --- | --- |
| SoC、板级与传感器 | 未修改；复用417内核候选及既有模式、电源、CCI与DMA所有权 |
| 主线接口 | 复用 libcamera v0.7.2 的 `MediaDevice::allocateRequests`、`V4L2Device::setControls`、`V4L2VideoDevice::queueBuffer`、`V4L2Request::requestDone` |
| 驱动 | 417实验UAPI和匹配模块原样复用，CID仍未获得上游分配 |
| 用户空间 | 新增实际请求池、逐帧参数提交、输入／输出／请求三方完成屏障、失败取消与请求FD回收 |
| 自动调校 | IPA数值算法、接口、原配置不变；407—416恢复的算法尚未通过此接口生成运行参数 |

当前源码及官方说明均已有请求封装，无需另建原始ioctl层。依据：[V4L2Request](https://docs.libcamera.org/master/internal-api/v4l2__request_8h_source.html)、[V4L2VideoDevice](https://docs.libcamera.org/master/internal-api/classlibcamera_1_1V4L2VideoDevice.html)、[Pipeline Handler指南](https://docs.libcamera.org/master/guides/pipeline-handler.html)。实现以当前本地v0.7.2源码和实际ARM64构建为准。

## 实现与生命周期

[公共补丁](0041-camss-ipe-request.patch)修改包装器、管线构造参数，并携带与417完全相同的UAPI头。[源码验证](source-validation.json)确认补丁以零fuzz复现实际候选，维护内核仍为干净的`f0b6ea869e3e748e6c1ccfe06865ac8d02c3ef3a`；[源码状态](source-state.json)记录实际构建文件哈希。

包装器先核对驱动控制的类型、6008字节元素布局与媒体请求能力，再分配与队列深度匹配的请求池。每帧设置独立控制，将请求只附在OUTPUT侧，然后提交媒体请求。显式传入非零参数时，旧驱动返回ENOTSUP，不能悄悄丢弃参数；旧管线无参数调用仍可使用原旁路路径。

输入返回、输出返回、请求完成，三项全部到达才释放关联、归还请求FD并发出成功信号。`requestDone`中立即reinit以禁用电平触发通知，但把可能触发停流／销毁请求池的最终完成延后到该回调栈退出之后；序列号防止延后的旧通知误作用于复用缓冲区的新任务。

参数设置失败发生在任务接管前，错误直接返回；已部分提交后的错误统一停流，通过完成信号返回失败。STREAMOFF失败时仍保留包装缓冲区、图像FD和请求FD至视频设备close／内核工作结束之后，再清理控制请求池。原始IFE缓冲区的SOF序号与时间戳仍通过独立OUTPUT包装器保护。

[ARM64构建](build-validation.json)通过；[37项实际包装器模型检查](ipe-validation.json)在ASan/UBSan下覆盖6种通知顺序、布局与分配失败、控制／QBUF／请求提交／reinit／STREAMOFF失败、超时、停流重入、池耗尽及旧通知。这些模型不替代内核并发证明。

## 真机结果

[运行记录](runtime-validation.json)、[硬件验收](hardware-validation.json)及候选类探针[ipe-smoke.cpp](ipe-smoke.cpp)证明：

- 实际候选动态库提交NV12 640×480和NV21 650×480/stride672各8帧。顺序为旁路、颜色、零Gamma、重复零Gamma、LA2048、LA1024、旁路、颜色。全部有效像素与406固定诊断参考逐字节相同；输入未改、输出尾部和时间戳通过检查。
- 两次重开后立即停流，4个已接管任务均恰好失败返回。内核实际启动18个任务，其中16完成、2取消；其余两个排队缓冲区尚未成为内核任务，不能写成4次内核取消。
- 四摄各12帧GStreamer走`requests=1`，没有多余IPE完成；主摄RAW＋NV12的6对SOF匹配，RAW-only另6对未启动IPE。
- 隔离IPA实际进程与应用不同，5个控制阶段及一次Gamma确认、27帧处理图像请求通过。该Gamma仍属原有IFE控制流程，不代表已接通IPE自动Gamma算法。
- 候选总计99个内核任务，97完成、2取消，failed/first_error为0。97完成=16个合成非零探针帧＋81个相机管线旁路帧；两个范围分别记录。

首轮[r1](runtime-r1-validation.json)失败保留：测试导出器按height482生成逻辑Y/UV平面，却只给第一平面设置整体有效长度，触发libcamera“平面存在空洞”校验。修正探针为同一导出DMA-BUF的连续单平面描述，保留额外尾部空间后，r2通过；生产管线代码未因该测试错误改动。首轮未启动图像DMA，没有新增内核故障。

## 当前设备与剩余工作

已卸载临时候选，恢复正式core395/adapter393/CAMSS389及原r30/r25软件、配置和加载标识。恢复后的四摄各12帧，共48应用帧／48IPE完成。[当前状态](current-state-validation.json)核对资源释放、ICP/CAMSS/双CCI休眠、17时钟0、9路供电disabled/users0，两个桌面服务为uid10000单实例。两个418事务及客户进程、采集器均终止。

本轮无新增内核故障。417-r2遗漏回调产生的taint512仍保留，未清除或为了清标记重启。源于417的历史警告不能误写为418新故障，也不能将当前状态写成taint0。

下一步验证带类型化请求时失ACK／复位／引用回收，再推进可发布参数通道；将IPA参数生成及成功提交／失败丢弃历史接入此接口，并补必要的传感器元数据、IFE/IPE输入域和统计证据。当前IFE已有CC/Gamma，不能未经域核对再次叠加原厂RGB曲线。非零LTM/LCE完整算法、第五摄像头、持续AF、光学及多摄同步仍按[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)推进。

原厂系数、夹具、探针拼接输入、二进制、日志和图像存入私有输出目录。公共补丁不包含原厂表；本阶段未永久安装、未改变产品默认高级IQ。
