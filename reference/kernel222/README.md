# 222：请求间断错配复现与SM8150帧同步候选

2026-10-16。**实机复现采集帧号与请求号分离，补上并临时验证标准FRAME_SYNC事件；手动曝光接口尚未完成。** 当前已恢复原CAMSS82cbc052模块，保持boot219/Image183/IMX471-e49及完整libcamera r7/config-r2，未刷写或重启。[最终健康](final-health-validation.json)

## 先验证真实采集帧

本次重新认证USB邻居、原公钥和当前启动，建立`k222-baseline`。当前49条相机payload准确，标准客户端仍只列Contrast/Gamma，媒体图/三DSP/休眠、taint和五fault检查通过。[基线](baseline-validation.json)

v0.7.2的[曝光控制设计](https://docs.libcamera.org/master/internal-api/namespacelibcamera_1_1controls.html)要求独立的ExposureTimeMode、AnalogueGainMode，手动值只在对应Manual模式生效；AeEnable可同时设两项，显式模式优先。不能仅添加控件名字或在元数据中立即回显请求模式。

源码中，simple管线以请求号查询DelayedControls；RGB缓冲保留真实采集序号。220连续36帧的两种模式中，两类序号恰好都为0–35，没有复现间断条件。[旧证据复核](sequence-history-validation.json)。这不否定220模式行时长修复，但其原验收只证明换算，不能扩大成真实逐帧延迟标定。

新增[标准API探针](request-gap-probe.cpp)：四缓冲、每组四请求，共16请求，组间暂停提交500ms但保持流运行。只读元数据，不映射或保存客户端像素。[构建](gap-probe-build-validation.json)

| 请求序号 | 采集缓冲序号 | 旧曝光历史索引 |
| ---: | ---: | ---: |
| 0–3 | 0–3 | 0/0/0/1 |
| 4–7 | 33–36 | 2–5 |
| 8–11 | 66–69 | 6–9 |
| 12–15 | 99–102 | 10–13 |

这是新的真实间断复现：不能把请求号当作采集帧号。当前CAMSS也没有可用帧开始事件，曝光/增益延迟配置为2/1帧；缺少实际同步与捕获快照时，单独改查询索引仍不能保证正确。[原生结果](request-gap-r7-validation.json)。本轮三个采集会话共48个RGB请求只记录元数据，没有保存场景；关灯条件不影响这项序号判断。

## 帧同步候选

[三文件候选补丁](camss-sm8150-sof-candidate.patch)仅给SM8150开放标准V4L2_EVENT_FRAME_SYNC订阅，在现有RDI SOF中断中发事件，独立SOF计数并在stream start复位。未修改IRQ掩码、频率、MMCX策略或寄存器地址。其它平台保持原行为。当前buffer.sequence仍按BUF_DONE计数，SOF与缓冲的完整配对继续开放。

公开QTI [VFE170](https://android.googlesource.com/kernel/msm/+/1f626a61841c7474c4baa02e5e6f4260c0622bdd/drivers/media/platform/msm/ais/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe170.h)与[VFE175](https://android.googlesource.com/kernel/msm/+/1f626a61841c7474c4baa02e5e6f4260c0622bdd/drivers/media/platform/msm/ais/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe175.h)的RDI0/1/2 SOF掩码与现有BIT27/28/29一致。两个头文件固定提交/哈希；同目录lite头请求404也保留，不将它当作已取得依据。[来源](sof-public-source-validation.json)

首次构建C编译完成，modpost因未包含vb2依赖目标退出；118份原文件恢复，未操作手机。随后加入四个依赖目标并保护其对象，W=1无诊断、全部导入符号存在、intree/vermagic正确；180份受保护源/对象/元数据恢复。checkpatch仅提交描述换行警告，修正后通过，C源码和已编译模块不变。[首失败](sof-initial-build-failure-validation.json)、[最终构建](sof-candidate-build-validation.json)

最终对照时发现NTFS快照显示的Unix权限不是原文件权限，内容180份均相同。构建finally已在内存中逐项核对原权限；恢复后补存带模式的JSON清单，最终验证按该清单复核。构建脚本也补上构建前模式清单，避免将NTFS模拟的0777当作原值。[源码核对](source-final-validation.json)

候选模块SHA256 `9c3b9db6b2933ebf5f1c01deea9fca7bb823fb2a745cd7f3a1d88e3ccc54e83e`，776664字节，只存私人试验目录。安装的原模块没有覆盖；通过正常unbind/rmmod/insmod临时加载，停止并按实际环境恢复WirePlumber，桌面与PipeWire进程身份保持。

第一轮16请求完成，libcamera已识别frameStart；事件读取器在第一条后把空队列ENOENT当成错误。当前内核v4l2-event.c明确返回该值，修正观测器后重新试验；没有把首轮改记通过。首轮清理已恢复原模块、图/格式与策略。[首轮失败及恢复](sof-first-native-failure-validation.json)

第二轮收到105条事件，帧序号0–104及事件队列序号均连续。间隔中位17.2961365ms、范围16.342829–18.213091ms，没有超过25ms，吻合此前该模式约57.82fps的采集速率。请求间断时事件继续推进，16个请求完成，libcamera实际选择该帧开始源。[原生候选](sof-candidate-native-validation.json)、[事件分析](sof-event-analysis-validation.json)。这不证明曝光物理延迟、无抖动时序或缓冲号已经与SOF准确对应。

## 当前部署与接续

两次试验均正常恢复原CAMSS，ELF loaded build-id与82cbc052文件核对，原驱动再次拒绝候选事件订阅。r7/r2的49条payload、e49模块、实验参数N、相机休眠、两前摄电源关闭/用户0与测试图案0保持；三DSP running、GPS空闲/刷新30、BT关闭无连接、chrony正常、NV源保持，taint及五fault0。[最终健康](final-health-validation.json)。首次健康报告沿用了221的“未拍摄”标记，已更正为本轮进行了元数据采集，并把UIM槽位记录明确标成221历史；原报告及更正保留。

[71成员私人原生归档](final-evidence-validation.json)逐一核对，包含原/候选模块与两轮记录；原图、身份、密钥和归档指纹不公开。宿主kernel canonical仍216传感器源/旧DTB，不能当当前boot219部署树刷写。

下一步先核对并标记每个捕获缓冲对应的SOF；在捕获回调保存相应控制快照，防止软件ISP处理延后及环形历史回绕，再接独立自动/手动模式、AeEnable优先级、忽略Auto期间手动值、模式切换冻结和Camera::start控制。完整r7配置/功能、隔离IPA和回退输入应保留，候选尚未写入产品部署锁。

真实几何/CFA/颜色/延迟、后置四摄及GPU ISP继续；GNSS真实fix、蜂窝业务和其余[全外设目标](../../linux-port/docs/HARDWARE-STATUS.md)仍active。维持关灯/室内窗边、不闪光或外部照明，以RAW噪声/帧变化/TPG区分暗场与故障。
