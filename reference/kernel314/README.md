# 314：公共 CAMSS 共享流与 RAW／PIX 并行

2026-10-19。通过标准V4L2 streams API管理共享CSI输入；四颗摄像头各自完成RAW RDI＋640×480硬件NV12 PIX并行、分别停流和重开，并连续切换摄像头。最终259路输出帧通过，未出现停流超时、缺SOF标签或新增相关内核故障。候选仅临时加载，已恢复309模块；libcamera双流请求及产品接入仍待完成，目标active。

## 复用来源与分层

优先采用Gjorgji Rosikopulos的[CAMSS streams系列](https://lore.kernel.org/all/20260911062213.195007-1-gjorgji.rosikopulos@oss.qualcomm.com/)，保存[原始补丁及来源](upstream/manifest.json)。使用CSID路由引用关系，仅在首个消费者启动、最后一个消费者退出时传播共享输入启停；CSIPHY和VFE接标准enable_streams／disable_streams。上游曾提出的video层共享计数方案已撤回，未采用。[后续讨论](https://lkml.iu.edu/2609.1/18354.html)。

原始系列针对RDI和SM8250，不能直接替代本机175 PIX实现。本轮保留既有PIX／统计／参数节点，补独立IPP端口和错误传播；按后续上游思路把启用标志放在SoC资源，只启用SM8150。当前7.3-rc6的set_fmt仍是原三参数，较新linux-next的client-info签名补丁不适用。原有VFE IRQ、固定RDI写通道和最后一路才复位等修复已在基线，未重复改写。[相关上游修复系列](https://lkml.rescloud.iu.edu/2609.3/08841.html)。

改动均在公共SoC驱动，不增加模组私有启停或用户空间MMIO。DT、板级电源、传感器驱动、V4L2核心、Image和系统库未改。原厂175停流状态定义复用[280固定OEM源码证据](../kernel280/oem-version-sources.json)：RDI状态寄存器0x350＋端口×0x100，bit0表示停止确认；Lite对应基址0x250。

## 实际修复与失败记录

原CAMSS视频节点会分别走legacy s_stream上游遍历。共享CSID／PHY／传感器面对第二个消费者时存在重复启停，不能直接加一条RAW队列来解决。

首次临时运行r1因fixture只接受绝对可执行路径，python3相对名称导致exit127、0帧；修为/usr/bin/python3。r2广角及r3前摄虽完成双路出帧，但后来完整日志发现最后停流的IPP超时，继而r3主摄启动EALREADY。旧worker没有计入这些具体停流错误；补充分析将r2／r3明确保留为失败，不能以原worker的通过字段验收。[r1](dual-r1-validation.json)、[r2](dual-r2-validation.json)、[r3](dual-r3-validation.json)。

原因是CSID先释放传感器，再要求IPP按帧边界停流；此时已无输入时钟，超时后V4L2核心保留启用状态。改为先停本地CSI端口，再释放共享输入。r4退出超时已消失，但主摄RAW独立重开时出现缺SOF标签的错误帧，仍保持失败。[r4](dual-r4-validation.json)。

进一步按原厂定义等待RDI在帧边界停止，并在VFE释放／回收对应DMA前完成CSI端口停流，避免截断在途帧或将旧完成事件带到重开之后。所有停止侧仍尝试本地及远端清理，真实失败继续上报。单VC传感器可缺省frame descriptor，安静回退到VC0＋总线格式，避免把可用回退打印成错误。

## 最终实测范围

[r5四摄证据](dual-r5-validation.json)使用最终第4次构建的模块。每颗依次完成：双路采集→停RAW而PIX继续→重开RAW→停PIX而RAW继续→重开PIX。广角／前摄从RAW先启动，主摄／长焦从PIX先启动。

| 摄像头 | RAW输入 | RAW＋PIX输出帧合计 |
| --- | --- | ---: |
| S5KGW1主摄，C-PHY | 4608×3456，GBRG10 | 66 |
| IMX471前摄 | 2304×1728，RGGB10 | 64 |
| IMX319广角 | 1632×1224，RGGB10 | 64 |
| S5K3M5长焦 | 2104×1560，GRBG10 | 65 |

每一路尺寸／bytesused有效，输出覆盖预填数据，序列及时间递增；四颗依次复用同一CSID／VFE，停流返回成功且无相关内核错误。不同步轮询会多取得少量帧，因此以功能阶段完成为准，不要求固定总帧数。

这里只证明每颗摄像头的RDI／PIX双路生命周期，**未证明四颗实体摄像头同时工作，也未证明两个独立队列属于libcamera同一请求／同一物理帧**。两路线上的帧计数在重开后分别从头开始；不能仅靠相同数值配对。本轮没有开启AE/AWB统计IPA，亦不作为光学画质或新的校准证据。

CAMSS相关Werror构建通过，无诊断；没有全量Image／模块／包重扫。[构建](kernel-build-validation.json)、[聚合补丁](shared-streams.patch)、[当前源码](source-state.json)。新树/home/cy122/x2pro-linux/camera314-streams-kernel，samurai-raw314／afad7bde625bbf7bf58c145bde1f977b806da986；309树保持。导入的两个.rej仅为未跟踪诊断，不属于构建输入；后续修正以聚合补丁／已提交源码为准，生成脚本不重放。

最终已确认所有实验进程结束，同一启动，加载恢复为309；桌面PW/WP已恢复，CAMSS／两CCI休眠，九路相机供电关闭用户0，taint0、相关故障增量0。[收尾](final-health-validation.json)。旧GPU／modem／SSC问题仍开放。

## 当前产品状态与下一步

设备仍为298 Image＋305长焦模块＋309 CAMSS。314模块仅临时加载，安装文件未替换。用户空间SDK仍是313，使用[313构建入口](../kernel313/build-candidate.py)；312六模式默认AE/AWB、缓冲恢复和313主摄单次AF证据沿用原模块组合，尚未与314模块联合复测。产品r24／config-r19继续RAW＋CPU ISP。

下一步把RDI接入libcamera候选，完成RAW-only／RAW＋处理流的请求、缓冲和物理帧关联，验证314下参数／统计／AF兼容，再接产品包和消费者。完整黑电平、颜色／CCM、阴影、模组绑定仍未完成；304 EEPROM完整校验／绑定／几何未齐、未应用个体值。用户延期的纯色／遮光测试不阻塞其它工作。
