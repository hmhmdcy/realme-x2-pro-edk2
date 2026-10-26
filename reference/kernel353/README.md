# 353：实现并构建 A5 ICP 队列和 ELF 内核核心

2026-10-20。上一轮352已取得原厂固件并核实队列ABI，属于实质进展。本轮开始实际内核代码：新增A5 HFI队列表、环形传输和ELF内存加载核心，编成`qcom-camss-icp-a5-core.ko`。这是后续设备驱动要调用的核心库，尚无平台probe、IOMMU映射、时钟/电源启动、HFI握手或V4L2会话；完整目标继续，不能当成ICP/IPE已可用。

代码位于[kernel](kernel)，使用现有内核DMA屏障、mutex和LE字段类型。队列头956字节，live字段保持原厂64字节间距；队列表3848字节，预留4槽、3槽激活，前三槽为CMD/MSG/DBG。中断模式全部3848字节与私有编译的原厂初始化代码一致，含debug TX watermark1024。初版只分配3槽，在原厂结构比较时失败，已修正；[失败记录](core-r1-failure.json)保留，早期模块未部署。

主机写命令保留一个空word，处理连续、跨尾和满队列，完整payload发布后才更新write，再发布索引供调用者敲门铃。helper本身不做MMIO。接收按包长逐包读取，不沿用原厂一次取走全部可见word的上层接口；后续包保留。短输出、未完整输入、空队列和无效字段不推进read，也不覆盖调用者输出。主机调用由mutex串行，要求在进程或workqueue上下文运行。

共享数据必须来自一致性DMA内存。代码使用dma_rmb/dma_wmb，完成接收拷贝后以dma_mb发布read；实际内核AArch64对象中有oshld/oshst/osh屏障。此处的测试不证明真实ICP缓存一致性、IRQ或停机并发；这些由后续拥有设备生命周期的驱动实测。DBG通道按原厂协议属于尽力而为的日志路径，不宣称有MSG通道同等的防覆盖保证。

ELF核心识别原厂ARM32 little-endian/ET_EXEC/entry0格式，检查全部LOAD段的文件边界、内存窗口、大小和对齐后才修改调用者拥有的RAM；按段复制，并清零BSS及段间空洞。未把固件文件直接送MDT/PAS，也没有往固定物理地址写内存。入口、span和段数仅在检查成功后返回。[代码](kernel/camss-icp-a5-fw.c)。

真实内核函数体以主机/AArch64两种架构编译执行，每种1584组写队列与原厂`hfi_write_cmd`的完整缓冲和header逐字节一致；16组单消息读取与原厂`hfi_read_message`一致。另核对多包跨尾保留、短输出、不完整包、错误长度/队列状态；两个生产线程加一个消费者处理2000包，没有重复或次序丢失。此为主机mutex模型，不冒充与真实固件并发。[核心检查](core-validation.json)。

原厂ICP固件加载结果与独立Python按ELF段生成的5MiB参考缓冲逐字节一致：加载区及BSS/空洞正确，span外保持原值，两侧guard未改。每种架构17类损坏ELF拒绝，目标RAM和输出layout均保持原样。原厂源码、固件及生成参考只私存，不镜像。测试临时将E盘小工作目录绑定到SDK，结束已卸载，没有在近满C盘复制内核/固件树。

外部模块在准备好的实际内核`7.3.0-rc6-rmx1931-samurai-k298+`上以W=1/-Werror构建成功；最终r2为1.98秒、无诊断，88408字节，私有模块SHA`d6ccd241513a718d88a3d460ba7ea468b7312d712e8d896071f02cdcb6b3cf8f`。仅构建新组件，没有重编已有CAMSS/传感器/Image或安装。[构建记录](kernel-build-validation.json)。r1是修正4槽前的可编译版本，不作为最终语义通过依据。

继续核对实际内核IOMMU实现，为下一步选择映射方法：OF的`memory-region`/`iommu-addresses`节点在没有物理`reg`时可表示纯IOVA保留；核心→ARM SMMU→DMA helper→OF取得该保留，DMA的IOVA allocator会跳过它。因此可提议保留A5的0..5MiB虚拟窗口，在别处分配一致性RAM后逐页映射到该窗口，不必先假设必须存在固定物理camera carveout。尚未修改DT或实际映射，设备分组、域及撤销路径仍需验证。[源码与导出依据](iommu-planning-evidence.json)。

当前内核没有向模块导出`iommu_get_dma_domain`，后续需用已导出的`iommu_get_domain_for_dev`并核对域类型；map/unmap/iova_to_phys及保留区查询/释放已导出。没有为此盲加框架导出或改全局DMA策略。所有访问E ext4的后续脚本都先调用284 storage helper；一次临时读取未挂载的Module.symvers失败，随后已改成可复用脚本，未重复切换设备状态。

层次划分：本轮实现SoC A5传输/固件核心；板级DT、传感器驱动、主线IOMMU框架和用户空间IPA都未改。当前手机仍沿用349最后观察的338/r27/r22＋344私有默认，353无手机操作。没有活动构建、SDK bind或相机worker。下一步354实现保留窗口、一致性RAM分配、逐页别名映射和回滚/释放，再接A5平台资源与启动握手；继而实现IPE会话/IQ与libcamera m2m。350～352曲线数学和前摄矩阵尚未作为新默认部署，AE/防频闪、更多模式、光学、几何同步和连续AF也仍待完成。
