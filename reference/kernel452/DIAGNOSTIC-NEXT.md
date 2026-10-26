# 452 离线 FULL 所有权诊断事务

此处只准备代码和计划，没有访问手机、SDK、编译、remote stage 或正式安装。452 原有 source/header/build/patch 指纹保留。451 比较与此独立：本事务只使用已构建的 452 core e6a90a06…，继续使用旧 444/450 proxy c7887708…、444 IPA 4c90047d…及签名 f5c351bd…、441 三模块、443 原厂配置、449 GST/长 fixture 和原样 450 用户启动器。没有与 451 新 proxy 混用。

## 两段采集

1. 主摄 1920×1080、强制隔离 IPA，默认关闭诊断，实际消费 120 图并正常返回 0。清除继承的全部 LIBCAMERA_/GST_/CAPTURE_ 环境；没有设置 FULL trace 变量，必须没有 CSV 和导出日志。
2. 同一路径和载荷，仅设置 LIBCAMERA_CAMSS_FULL_TRACE_DIR 为 uid10000 拥有的 captures 目录。增量读取 GST_IMAGE，发现第一处实际消费者 sequence 缺口后约 2 秒向 GST 应用发送 SIGINT；没有缺口则在启动后 90 秒取消。10000 图仅为既有 GST 客户端所需的安全目标上限，不是固定帧数长测；不会再采固定 9000 图。

应用及 IPA 的真实 /proc 身份、核心映射、IPA 模块、proxy exe 路径和 SHA 都要见证；两者 UID 均为 10000、CapEff=0。应用 exe 还必须等于本任务用户目录中的 gst-sustained，并匹配既有二进制 SHA。取消前再次核对 PID、start_ticks、exe、UID、能力和 SHA，打开 pidfd 后复查 start_ticks，再通过 pidfd 发送 SIGINT。不会向 fixture、进程组或未知 PID 发信号，不使用 SIGKILL。

正常观测上限为 90 秒，允许停止清理和 fixture 恢复的额外时间。既有 fixture 设置 95 秒作为诊断监视异常时的最后正常取消保障，并沿用其 10 秒清理宽限；这条回退不能冒认为监视成功。若停止失灵，只保留失败和用户目录，不盲杀再声称恢复通过。继承的 434 事务外壳已移除对采集进程组的杀进程分支；本体拥有局部 fixture 句柄。

## 监视和 CSV

监视没有条件观察器。单一文件句柄只向前读，每次至多 256KiB、约每 100ms 一次；未完成行上限 8192 字节，积压上限 4MiB，超过即失败。只保留 PID、上一消费样本和首个缺口，不增长保存日志历史。停止后才完整读取一次日志用于结束检查。首缺口触发要求观察延迟不超过 1 秒，信号距检测在 2–2.5 秒；完整原日志仍在私有目录。

原样 449 客户端在信号处理后走 gst_element_set_state(GST_STATE_NULL)、get_state/unref，再打印 GST_RESULT result=9；fixture 报正常子进程 exit9、signalled=0，fixture 自身为 exit1，恢复为 result0。现有客户端没有独立的 STATE_NULL 成功日志，不能编造这一证据。事务采用精确源文件/二进制收据、CSV StopBegin/StopEnd 和 end 页尾、导出 result0、GST_RESULT 顺序、驱动 idle/资源释放及正常退出共同验证清理路径；不宣称单独测量了 GStreamer 状态转换返回码。

停止后确认应用和 proxy 退出；CSV 必须位于 captures 内、原属 uid10000、0600、普通非符号链接文件。记录其 SHA、长度、权限和导出结果，再复制至事务 case/captures，随后删除用户目录。复制 SHA 在离线审计中再核对。默认关闭段不允许任何 captures 文件；启用段要求恰好一个完整 CSV。地址和完整日志只留 E:\edk2-samurai-out\kernel452，不能镜像原始 CSV 到仓库。

CSV 要求 capacity8192、retained=min(total,8192)、overwritten=total-retained、first=total-retained+1、正文连续编号、23 类累计计数之和等于 total、最后 StopEnd、完整 # end 页尾、clock-errors=0、q-underflows=0。逐条核对保留窗口内成功 QBUF 与 DQ 回调的 outstanding 变化。只能覆盖最后 8192 条事件，实际跨度使用正文首尾 mono_ns；不能声称它覆盖整个 90 秒。缺口相邻 FULL DQ 锚点不在尾窗则诊断覆盖不完整。

outstanding_full 是成功 QBUF 减 DQ 用户态回调，包含硬件已完成但回调尚未到达的缓冲；正值不能证明硬件仍有可写缓冲，也不能直接解释为 FD 或缓冲泄漏。free_full 等字段是回调时队列库存。实际进程 fd 数仅在一次活见证中计数，不构成泄漏趋势测试；诊断目录 fd 在启动打开、停止导出后关闭的实现边界由已有宿主环测试覆盖。

hardware_ns 是驱动提供的输入时间戳，mono_ns 是用户态记录时刻。只有验证相应时钟标志和语义后才能进一步比较；本检查不把两者直接相减。消费 wall-ns 与监视单调时钟只用于触发延迟。某 SOF 有成功 FULL DQ 才能说 FULL 回调已捕获并分析到 IPE 占有/排队的 mono 间隔；有 PD10/统计但无 FULL DQ，只能定位到 FULL 未交付该用户态回调，不能证明硬件从未 DMA。库存为正同样不能排除断供。

缺口摘要还保留相邻成功 FULL 回调之间的 QBUF、内部借还、请求进入/接受/完成、缺库存及等待事件计数，和各队列库存的最小/最大值。无新 RequestEnter、内部 FULL 被持有、已有 FULL 等待 IPE 可以据此分开检查；摘要仍是回调括窗，不能直接充当物理 SOF 时刻的缓冲供给证明，也不会把“无请求进入”归因到特定消费者。

## 离线入口和新交接

在 WSL 对此目录运行：

~~~sh
python3 -B check-diagnostic.py --self-check
python3 -B prepare-diagnostic.py
~~~

自检覆盖有界分片尾读、首缺口、2 秒/90 秒边界、pidfd 信号身份拒绝的宿主 mock、8192 条尾窗/808 条覆盖、坏页尾/编号/时钟/下溢拒绝，以及 450 的原始 94 图正常取消和 9000 图正常缓存严格审计。没有回执过滤；重复成功回执必须拒绝。它只证明脚本与旧缓存可用，不是 452 实机证据。

prepare 首先执行 mounted_build 守卫，再核对精确 452 源码收据和所有实际载荷 SHA，不占 SDK。它从冻结的 451 指定 SHA 提取通用 handoff/charging/proc/finalize 定义到私有 capture-common-private.py；没有改 451。只向私有 diagnostic-prepared-r1 渲染 worker、计划、清单、终态检查器及收集器。收集器白名单显式允许 .csv/.json/.log/.txt，不收照片或原厂系数；各文件最大 64MiB。镜像目录中只有本次五个公开文件。

缺少新的可信 handoff/preflight 时，fresh_handoff_received、ready_for_manual_stage、payload_generated 和 hardware_validation_passed 均为 false，不能 stage 半成品代码。后续由主线提供同次 --handoff / --baseline；handoff 沿用 451 描述的 samurai-camera-handoff-v1 字段，但 window_id 必须为 k452-full-diagnostic-r1。必须包含当次实际 boot guard、baseline SHA、正式库 SHA 和完整现状充电快照，禁止沿用 450/451 过期断言。只在新交接和与当前脚本 SHA 绑定的离线自检均通过时才可生成包；prepare 永远不 stage 或启动。

主线决定部署时须复用一次性、安全暂存规则：新事务根目录不存在、完整逐文件 SHA、0700 根、fixture/launcher 可执行、不可重放已结束事务。正式恢复后，通过渲染的 inspect-terminal-private.py 独立见证 worker 已退出、无本任务进程/目录、正式库/包和服务恢复、四设备 suspended、充电前后完全相等，再将该外部 JSON 作为 --residual 交给 check-diagnostic.py --root 收集目录。

最终审计复用 443 原始同 SOF PD10/GTM/WB/成功历史/回执契约，只参数化消费数量和正常取消结果码；消费、源完成未拉取、停止放弃的入队请求分别计数，驱动物理完成计数单独对齐。无缺口只能验收诊断可用；有缺口也先报告尾窗覆盖与用户态交付/排队证据，始终保留 root_cause_proven=false，不宣称丢帧根因已证或已修。
