# 377：还原目标 IPE CONFIG_IO ABI；首次映射失败

优先检查了已有 CAMSS 原型、Realme GPL HFI/ICP 管理器和固定 CamxChi 源，再执行本机原厂 HAL 与 CAMERA_ICP 固件指令。公开旧头文件的 848 字节 IO 结构与目标固件不符；本机实际 payload 为 1216 字节，image descriptor 为 84 字节。来源见 [primary-sources.json](primary-sources.json)，相关既有源见 350/352/355。

完整原厂 `SetConfigIOData` 对输入 0、显示输出 8、视频输出 9 的 NV12/NV21 共 18 次执行，无外部提供者桩。自写序列化器的 12 组完整输出共 14592 字节与原厂输出一致；13 个无效布局在写入前拒绝。完整 setup 未执行，其保留指令片段用于确认 maxBatch、secureMode、userArg 等字段位置。原始 HAL、汇编与二进制结果只存私人目录。

新增 SoC 驱动 API `camss_a5_ipe_configure_nv12`：在生命周期锁内写入配置、MAP、间接 CONFIG_IO、UNMAP，逐会话保存布局与 scratch 大小；超时、未知回复、映射与缓冲区寿命均纳入错误处理。沿用原有 IOMMU/DMA API 与保留窗口，未改板级 DT、传感器、主线框架或用户空间。此时 parser 错误地把 MAP/UNMAP 的尾部也视作状态；[379](../kernel379/README.md) 已修正。

首次实机 INIT/PING/RT create 成功，首次 MAP 返回错误，CONFIG_IO 未到达。驱动走强制复位、DMA/PM 释放日志后系统自动重启，worker 未保存终态。不能把内核清理日志当作正常事务终态，也不能混入 pstore 中早先 376 的成功 PC/销毁记录。见 [本次窗口审计](attempt-audit-validation.json)。本轮未主动重启或刷写。

原始固件队列查找函数证明：102400 字节 debug 队列被映射为从 `0x07403000` 起的 1 MiB 区域，377 的配置别名 `0x07420000` 落入其中。原始重叠检查可复现拒绝；实机未记录原始 HFI 错误码，因此不能宣称错误码已直接对上。见 [重叠模型](queue-overlap-validation.json)。[378](../kernel378/README.md) 将别名移至 `0x07600000`。

恢复启动已核对 boot366/logdump365，移除哈希一致的临时固件，保留原 ELF 与失败事务。被动 EUD 采集仅捕获恢复后启动日志，不能证明旧启动停在哪条指令；EUD 已关闭。完整恢复日志、固件、回包和个体校准均仅私存。当前状态与续作以 [379](../kernel379/README.md) 为准。
