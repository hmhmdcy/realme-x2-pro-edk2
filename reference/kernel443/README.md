# 443：主摄 16:9 模式补齐原厂 DS4，正常 GStreamer 两尺寸双遍通过

2026-10-23。正常消费者与 [442 探针](../kernel442/README.md)的模式选择不同：`libcamerasrc` 为 720p／1080p 选择 4608×2592，而此前探针固定 4608×3456。本轮补齐该 16:9 模式缺失的原厂 DS4 绑定，四条普通／隔离 IPA 路径各收到 120 帧并通过同 SOF／实际版本／成功历史审计。**没有修改核心、IPA 数学或内核模块，也未永久安装；旧积压根因、持续录像和绝对画质仍未全部验收。**

手机已恢复正式 440 r32／r27、434 三模块和原来的四份私有配置；epoch 作业 0、taint 0、四设备 suspended、PipeWire／WirePlumber 各一个 uid10000。[最终状态](current-state-validation.json)。本轮未刷写、触发重启、写 EEPROM／NV 或 push。

## 复用原厂模式资料补缺

正式主摄配置已有 3456／2592 两种高度对应的 tone、LSC、色彩与控制时序，但 431 只给 3456 模式接入了 `ife_ds4`。实际未修改的 ARM64 IPA5 在旧配置下报告 2592 模式 `pd10=false`，因而不能直接把此前固定模式的结论外推给正常 16:9 消费者。

复用 [426](../kernel426/README.md)保留的 Sunny GW1 原厂 DS4 reserves 和原始模式管理器选择结果，明确选择 sensor mode 4 的 `ds4to1v10_ife_full_dc4`、PASS_FULL 三项系数。Preview／Video 选定值相同，已有独立 BIN／原厂 XML 与管理器对照直接复用，未重新 dump 固件或从另一个模式复制系数。

[配置导出](export-profile.py)只在私有候选 4608×2592 节点添加 `ife_ds4`，其余数据保留；源配置 SHA `b4b6daa2…`，候选 `b5669d84…`。[导出验证](profile-export-validation.json)。实际 IPA5 的四组配置／参数上传检查表明：旧 2592 无 PD10，新 2592 有 PD10 且 typed DS4 字节等于原厂 mode4 PASS_FULL；3456 参数包逐字节相同，2592 其它 typed 块逐字节相同。[真实模块检查](profile-module-validation.json)。这证明配置与上传正确，硬件证据另见下文。

## 正常消费者实机结果

复用现有 316 `libcamerasrc → capsfilter → appsink`，仅给探针增加受限帧数、真实 GstBuffer offset、单调时间、错误标志／长度检查和首帧传感器 G_FMT 查询。没有启用丢帧选项，没有把图像处理放到 CameraManager 完成回调内。每张 NV12 检查长度、PTS、内核序号、DMA 同步与非零像素采样哈希；本轮不保存全部像素，完整像素及 LTM 因果证明沿用 442 的对应组件证据。

实机四路均确认传感器实际 4608×2592，进程映射 442 核心 `f7c25ff3…`，使用正式 r32 GStreamer 插件；IPA 进程关系符合普通／隔离选择。每个消费者帧的 offset 都对应真实 PD10 SOF、已实际生效的 GTM cookie／generation、WB context revision 和成功 IPE receipt；所有观察、停止取消与历史分别记账。[逐帧验收](hardware-validation.json)、[原始事务摘要](runtime-r1-validation.json)。

| 路径 | 消费帧 | 成功数学／bootstrap | 物理 IPE | PTS fps¹ | 前 8 样本后跳过 SOF |
| --- | ---: | ---: | ---: | ---: | ---: |
| 720p 普通 IPA | 120 | 117／3 | 120 | 30.056 | 0 |
| 720p 隔离 IPA | 120 | 117／3 | 120 | 29.787 | 1 |
| 1080p 普通 IPA | 120 | 117／3 | 121 | 30.056 | 0 |
| 1080p 隔离 IPA | 120 | 117／3 | 120 | 29.524 | 2 |

¹仅按本轮去掉前 8 个消费者样本后的时间戳间隔计算，不是长稳、固定帧率控制或录像编码验收。实际 wall fps 分别 30.078／29.861／30.009／29.354。全部期间 SOF 跳过数为 1／5／1／4，包含启动边界；隔离路径仍有约 66.54 ms 的双帧间隔，因此没有把结果标为无丢帧 30fps。

总计 480 张成功消费者帧、468 次数学提交、12 张 bootstrap、481 次物理 IPE 完成。1080p 普通路径多出的一个作业完成后在停流取消，没有提交成功历史。GStreamer 源端可能接受但 appsink 未消费的缓冲与已消费帧分开审计，本轮四路该差值均为 0。每路有 3 个明确停止取消请求；未见新内核故障／配对超时，最终 pending／superseded 为 0。

GStreamer 不提供本探针原有的 AWB 元数据字段或策略锁定结束条件；审计没有制造这些字段，改用实际源端 WB context／AWB_STATE revision 与同 SOF 观察核对。其它 typed GTM、上次成功 lux、物理完成与失败不提交规则沿用 441。正常结果标记使用 `GST_RESULT … bus-errors=0 result=0`，不再误要求采图探针的 `ADAPT_RESULT`。

## 剩余瓶颈与后续

[缓存时延分析](latency-validation.json)显示，普通路径 Pair→IPE queue 中位约 11 ms，隔离路径约 21—25 ms；queue→成功 receipt 则分别约 7 ms（720p）／10.6 ms（1080p）。隔离路径增量主要位于入队前，但这些区间包含多个同步调用与调度，不能直接当作某个函数的独立耗时，也不能据此宣称旧 441 长积压根因关闭。

下一步细分 `frameMetadata`／`processFocus`／`prepareIpeParameters` 的同步调用及队列等待，检查是否能在现有请求／epoch／成功历史边界内合并调用或收敛调度；先用当前源码和缓存证据设计最小底层改动。保留 442 固定模式及本轮正常消费者结果，按改动选择验证，不扩大统计池或放宽 SOF 审计。其它模组、完整模式／HDR、长录像、连续 AF、绝对画质及第五 2MP 等完整范围继续。

原件、系数、typed 包及完整日志仅在 `E:/edk2-samurai-out/kernel443` 和手机 `/var/lib/samurai/k443-gst-consumer-r1`；该事务已终态，不重启。与充电会话已确认独立源码／输出、公共 build／SDK bind 串行，不卸载共享 ext4；本轮手机实验已结束，下次手机验证或刷写窗口再协调。
