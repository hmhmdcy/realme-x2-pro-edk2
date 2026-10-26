# 316：默认硬件ISP与产品消费者接入

2026-10-19。已部署libcamera `99990.7.2-r25`、设备配置/stack `0.1.0-r20`和314 CAMSS模块。默认选择camss-vfe，PipeWire识别四摄；安装后的系统GStreamer和公开pw_stream客户端均成功取得广角640×480 NV12。未设置强制管线或实验启用环境变量。完整多摄／骁龙ISP校准目标仍active，未完成。

设备保持298 Image＋305 S5K3M5模块；仅CAMSS换为已验证的314模块，没有改DT、板级接线、供电或V4L2核心，没有刷写或重启。默认产品路径现为硬件NV12＋AE/AWB、RDI直接RAW，主摄对焦沿用CPU对比度算法。PipeWire/SPA/GStreamer版本仍1.6.9-r3。

## 用户空间适配

315的StreamConfiguration没有StreamFormats，普通消费者无法查询支持格式。316按[libcamera handler指南](https://docs.libcamera.org/master/guides/pipeline-handler.html)补标准枚举：RAW由传感器Bayer10模式形成离散集合；NV12结合视频节点范围和PIX的TRY格式／COMPOSE结果得到缩放和对齐边界。多个传感器模式的NV12范围合为一个建议范围，避免StreamFormats拒绝多组连续范围；最终validate仍以所选模式的TRY结果调整实际尺寸，不把VFE175的对齐数值硬编码到板级配置。

libcamera内部V4L2Subdevice新增带Whence参数的setSelection重载，原入口保留。格式查询不修改ACTIVE媒体格式。315的FRAME_SYNC事件时间关联保持；这仍是软件事件关联，不是硬件帧ID或真正的曝光时间。

硬件handler默认匹配具有NV12、参数和统计节点的CAMSS拓扑；LIBCAMERA_CAMSS_VFE_ENABLE=0保留为诊断退出。最终不以CAP_STREAMS为门槛：当前核心的v4l2_subdev_enable_streams_api关闭，会隐藏用户空间路由能力，但314内部的enable_streams和共享输入引用仍工作。单VC通路无需用户空间路由API。新库和314模块作为匹配组合部署，不声称新库在旧309模块上自动退回CPU路径。

## 软件包与实测

完整13包构建成功，保留原子包、原28补丁、auto/virtual管线及GStreamer、Python、qcam、V4L2等构建功能；累计0029补丁加入硬件handler、313 IPA、框架接口及其UAPI依赖。6个IPA模块保留，新IPA签名已对包内core验证。实际升级七个运行包；四个模组YAML放设备配置包，CPU fallback配置保留。[构建](package-build-validation.json)、[产物](package-artifact-validation.json)、[累计补丁](0029-camss-hardware-pipeline.patch)。

| 功能 | 实际结果 |
| --- | --- |
| 四摄分别经GStreamer输出640×480 NV12 | 每摄12帧，尺寸、内容和递增PTS通过 |
| 主摄1920×1080、前摄1280×720 NV12 | 各12帧，无总线错误 |
| 四摄RAW-only | 各34请求，AE/AWB稳定；共136次RAW/内部PIX关联，无错配 |
| 安装后的系统GStreamer广角NV12 | 12帧通过 |
| 安装后的PipeWire广角NV12 | 四摄节点存在，12帧通过；实际接收MemFd |

[r3广角](consumer-r3-validation.json)、[r5多摄／尺寸／RAW](consumer-r5-validation.json)、[安装r2](install-r2-validation.json)。四摄逐一工作，尚未证明四颗实体摄像头同时运行。315的六模式双流、默认AE/AWB、主摄单次AF／取消和缓冲恢复证据按未改动部分沿用：[315](../kernel315/README.md)。这些不是本轮重新完成的全量画质或AF验收。

## 修复过程与边界

首次完整构建缺通用ISP UAPI、params.h、内核帧号写入和Qualcomm元数据FourCC；补齐累计源依赖后成功。一次增量打包因旧pkg子包目录冲突失败，现仅重建生成的pkg暂存目录，复用src/output缓存。

消费者r1错误要求PIX的CAP_STREAMS，r2改为CSID后仍被核心隐藏能力位阻断，均0帧。移除门槛后r3广角通过；r4主摄遇到“Range format is ambiguous”，其余计划未运行；汇总建议范围后r5全组通过。失败记录保留，未计为成功帧。

首次安装r1的系统GStreamer通过、PW识别四摄，但测试客户端拒绝首个缓冲，自动恢复r24/config-r19和309模块。客户端补显式Header元数据协商、DMA-BUF映射及明确的摄像头节点选择后，安装r2成功。本次成功实际收到MemFd，未走新增DMA映射分支，不能把首轮失败归因为已实证的DMA映射故障，也不能声称PipeWire端到端零拷贝。

安装r2的worker已终态；实际加载314，七包版本正确，PW/WP各一个进程，CAMSS和两CCI休眠，相关内核故障增量0、taint0。安装前309模块、七旧包及world/仓库保存在`/var/lib/samurai/k316-install-r2`，本地签名仓库持久可用。无活跃采集或构建。[当前部署锁](../../linux-port/camera/deployment-lock.json)。

## 源码与后续

正式配方已同步到linux-port/packages/libcamera和samurai-camera-config。包内完整源在SDK的`work/libcamera316-r25-built/src/libcamera-v0.7.2`，原`work/libcamera`已恢复；`work/libcamera299-inline`仍是315。最新实现以本目录pipeline/framework、313 IPA和累计0029补丁为准。不要用旧315构建器覆盖316完整包源。

构建和安装均已结束；不重放已有run或一次性prepare生成器。后续源码修改可用refresh-pipeline.py更新当前pipeline及累计补丁，build-packages.py --resume复用编译对象；已部署基线不能再直接套用首次安装脚本所假设的r24/309前置状态。

[原厂个体数据分析](OEM-CALIBRATION.md)已定位广角序列号、畸变块和跨摄曝光参考，并解码部分AE字段；数据和指纹私有，未应用个体值。下一步继续WB／LSC工厂校验与模组绑定、畸变模型／内参、主摄曝光同步参考，以及正式黑电平、CCM／颜色、阴影和多摄几何同步。曝光时间语义、事件丢失恢复、RAW-only内部PIX开销、连续AF仍开放。用户延期的纯色／遮光不阻塞其它工作，旧GPU／modem／SSC问题仍开放。
