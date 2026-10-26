# 452：有界 FULL 所有权诊断，首次实机定位到成功FULL回调之前

2026-10-23。为449中“33个缺SOF均有PD10和统计、没有IPE_PAIR”准备的诊断，现已由主线完成首轮1080p实机：**诊断可用、严格图像链和正式恢复检查通过，根因仍未证明。**缺SOF168有PD10／统计，没有成功FULL DQ及IPE claim／queue。450回执重入修复、451快编码结果独立保留；本轮只用452 core与旧proxy。详细结果见[实机小结](DIAGNOSTIC-HARDWARE.md)及[脱敏收据](hardware-validation.json)。内核故障结论由后续完整dmesg补读核实，原时钟域错误形成的空日志不被接受为证据。

[补丁](0063-camss-bounded-full-ownership-trace.patch)基于精确450管线；451仅修改worker，管线相同。[生成程序](make-draft.py)先走449存储挂载守卫，校验450管线SHA，将改后源码写到私有kernel452/draft并导出[生成审计](source-draft-validation.json)。[准备脚本](prepare-source.py)另复制完整450源码／构建目录到libcamera452-full-ownership，零fuzz／offset应用；复制前空余12.72GB、原目录约575MB。[源码验证](source-validation.json)通过。

## 实际构建

[构建程序](build-core.py)只请求核心目标。首次计划守卫因额外version.cpp步骤拒绝，在实际编译前退出并释放SDK；[失败计划](build-plan-r1-validation.json)保留。调整守卫后，[r2](build-validation.json)增量123.14秒通过：实际编译camss_vfe.cpp、检查生成version.cpp后链接核心；版本内容相同，Ninja没有重新编译版本对象。没有重建IPA／签名／proxy。

新核心51258432字节，SHA256 e6a90a0699fa62a2c00a03a053bd93d8449450757301bbf7b3804978ceb073d6，私有可复用产物为kernel452/libcamera.so.0.7.2。IPA／签名／proxy继续是450的4c90047d…／f5c351bd…／c7887708…，协议6及原厂参数／AF算法不变；450源码和四个原产物前后哈希一致。SDK bind在finally卸载后实际核对为空，窗口已交还。源码指纹见source-state.json，完整编译日志仅存私有kernel452。

插桩进入共享Camss管线路径，默认关闭。本轮实机范围仅主摄1080p隔离IPA消费者；没有扩大为四摄／RAW-only／多流／其它尺寸诊断验收，亦未与451新proxy组合。

## 记录范围

显式设置LIBCAMERA_CAMSS_FULL_TRACE_DIR为已存在、当前应用可访问的私有目录才启用。默认关闭，无事件堆分配；失败仅禁用诊断并报告，不改变相机开流结果。

[事件环](full_ownership_trace.h)在开流前一次分配并按4KiB及末字节写触页，固定8192条×112字节＝917504字节（896KiB），没有按9000帧扩大。预触页不等于锁内存，不能保证未来永不缺页。热路径只读已有队列大小、写固定记录并取CLOCK_MONOTONIC；不分配、不写文件或逐帧日志。它依赖原有CameraManager单线程契约；同步IPC嵌套回调是同线程顺序执行，记录函数内不调用IPA／用户回调。

23个插桩点覆盖：

- 请求进入管线、缺少空闲FULL、接受、完成；内部FULL借出及归还，含QBUF失败回退。
- FULL QBUF调用前和返回值、DQBUF回调的真实kernel SOF／缓冲时间戳；PIX SOF事件原始时间戳。
- PD10及统计DQ、统计处理完成；等待更早FULL／IPE／PD10、IPE占有、入队及imageProcessed完成。

每条还含epoch、请求／缓冲稳定身份（仅本进程内地址）、请求序号、lastSof、IPE活跃请求和freeFull／requests／waitingFull／coarse／histograms／statistics／associations长度。状态位及事件编号见生成审计中的event_types／flags；不记录照片、直方图内容、曝光值或OEM系数。

FullQbufResult的status是QBUF返回码，IpeQueue是入队结果，ImageProcessed为0／-EIO，FullDq／RequestComplete为FrameMetadata状态，StatsDone为IPA统计状态；其它status通常为0。Unknown＝UINT32_MAX。失败／取消缓冲的SOF及时间戳不可作为有效采样；需要同时检查事件类型、status及BufferSuccess位。hardware_ns保留输入原值，mono_ns是记录时刻，二者用于识别完成时间与回调延迟，不能混成同一个时间。

## 有界导出与证明范围

覆盖后继续覆盖最早记录，仅保留最后8192条；total／各事件累计数覆盖本次启用会话，正文只覆盖尾窗。文件头明确capacity、total、retained、overwritten、first、时钟错误及FULL计数下溢。预计每帧十几至二十余条记录，约覆盖十几秒；实际范围应按首尾mono_ns计算，不能固定声称覆盖多少帧或全程。

stopDevice停止所有队列、IPA并释放资源后，一次导出CSV至开始时打开的目录。文件使用0600、O_EXCL和O_NOFOLLOW，已有同名文件不覆盖；完成页尾为“# end,records=…”。随后释放事件内存和目录fd，仅输出一条汇总日志。时钟错误、下溢、缺少页尾、导出失败或缺口不在尾窗，都应标为诊断不完整。文件及完整日志留私有目录，不同步原始地址记录到公开仓库。

outstanding_full＝成功QBUF数减DQ回调数，**包含已由硬件完成但尚未DQ回调的缓冲**，不是硬件可写队列深度。库存为正不能排除硬件断供；SOF回调也可能晚于实际SOF。分析时用QBUF前／后时刻和硬件时间，不能直接把回调快照当成物理SOF瞬间的状态。

## 怎样区分现象

| 证据 | 能支持的判断 | 仍不能证明的部分 |
| --- | --- | --- |
| 相邻成功FULL DQ跨过SOF，保留窗内PD10／统计有该SOF，无该FULL DQ | FULL未送达用户态，缺口先于IPE配对 | 硬件从未DMA还是驱动未交付，须必要时补内核完成事件 |
| 没有足够请求、空闲内部FULL充足，完成到下一RequestEnter存在长空档 | 上游提交没有及时到达管线 | 应用消费者、框架前端或调度中具体哪一个延迟，需结合既有GST_IMAGE时间 |
| 内部FULL都被借出，waitingFull或IPE长期占有，归还／下一QBUF推迟 | 管线持有或处理造成供给压力 | 只有与真实SOF时间对应、并排除QBUF调用中的不确定区间，才能确认当时无可写缓冲 |
| 某SOF有FULL DQ，但晚些才IpeClaim／IpeQueue，期间WaitOlder／WaitIpe／WaitPd10可见 | 已捕获，排队迟滞发生在对应阶段 | 不应把这一类写成FULL没有捕获 |

仅库存为正不能清除断供嫌疑；仅有RequestEnter空档也不能把责任归给GStreamer。必须保留边界判断。

## 宿主验证

[测试](trace-ring-test.cpp)、[执行程序](check-ring.py)及[结果](ring-validation.json)通过原生和ASAN／UBSAN：10000次环覆盖、尾部顺序、4次重置、失败QBUF／DQ下溢、非法事件类型、默认关闭、分配失败、9000事件保留8192／覆盖808、时钟与epoch字段、O_EXCL不覆盖及0600导出。热记录窗口实际new调用数为0。权限测试使用私有Linux临时目录，避免把DrvFS忽略Unix模式位误判成实现故障；仅合成CSV留E盘私有输出。

宿主复现：WSL中在kernel452目录执行make-draft.py和check-ring.py。源码变换守卫只允许当前450管线SHA；宿主测试不占SDK。prepare-source.py禁止覆盖已有候选；实际核心已由build-core.py完成，不能为重跑报告重复复制或无故重建。需要新SDK构建时仍应先协调串行窗口。

## 首轮1080p实机结果

[诊断事务](DIAGNOSTIC-NEXT.md)r1先关闭trace消费120图，观测到2个SOF缺口；启用段消费232图、源端成功／物理IPE233次，其中1张完成后未被appsink拉取。两段合计352消费、353物理IPE；启用段230次成功数学提交＋3张bootstrap。严格原始回执、同SOF PD10／GTM／实际WB／历史均通过，没有过滤回执或把未消费图算入消费。

启用段首缺口为SOF168，邻帧167／169，检测约2秒后经应用pidfd发SIGINT正常取消；应用exit9、fixture按既定约定返回1，恢复标记通过。CSV包含3634条事件、9.859346秒trace会话，零覆盖、clock_errors／q_underflows均0，Start／StopEnd及页尾完整。该缺口有PD10和统计，没有成功FULL DQ或IPE claim／queue；相邻FULL回调括窗66.550ms，outstanding为0—2、free FULL为1—2。回调库存不是物理SOF瞬间的硬件可写队列，仍不能区分未DMA、驱动未交付或瞬时断供。

正式440 r32／r27、434模块、CPU选择及r5充电十字段恢复，core资源释放、四设备suspended、P/W各一个uid10000、taint前后0；独立外部检查确认worker退出、无残留进程／用户目录。首次收集器漏传关闭段的空captures目录，导致PC离线审计路径失败；只读核实真实目录为空后，在PC补目录并复审通过，原tar未改、相机未重跑。主线已修后续收集入口传递空目录。

旧434 worker用 `/proc/uptime` 的BOOTTIME筛选MONOTONIC域dmesg，休眠后本轮过滤日志仅1字节；空日志及旧 `new_faults=[]` 不构成零故障证据。主线另补读完整dmesg，按可信恢复snapshot的实际CLOCK_MONOTONIC边界核对，覆盖451／452窗口的1057条新记录，指定故障模式0，边界前消息仍保留且未见丢日志迹象，见[补读审计](kernel-window-validation.json)。本次文档整理没有SSH、构建或重跑审计，也未改冻结脚本／既有收据。下一步应补能区分DMA完成、驱动交付与实际SOF瞬间供给的证据；不把诊断通过写成根因修复、无丢帧或功耗／热验收。
