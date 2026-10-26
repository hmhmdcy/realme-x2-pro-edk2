# 482：481 安装事务的有限默认路径 probe

已实现离线准备，未 SSH、绑定 SDK、上传、编译或执行 target。入口为 `default-probe.py` 的 `run(root, state, *, phase, expected)`；481负责新鲜窗口、包／模块切换、PW/WP停止及最终恢复，482只启动自己的用户客户端并返回 idle。`phase` 为 `forward-first`／`forward-final`，日志分别写入481目录的 `default-probe-<phase>/`；异常抛给481，保留失败原件。

每段7例：四摄正常默认 NV12 640×480，各32帧；主摄原生 RAW4608×3456、长焦原生 RAW2104×1560，各6帧；主摄 dual6帧。最后6帧增量用于核同一请求的 RDI RAW／processed 同SOF及 RAW-only 条件分支，覆盖本次 core 所有权和 RAW 策略相关变更；不扩展成光学、AF、录像或480帧矩阵。复用440现成 `pipeline-smoke` 及449现成 `gst-sustained`／fixture／launcher，无需构建。

expected包含：`packages`（7名称→版本）、`runtime_files`（实际绝对路径→SHA）、`modules`（4个name/path/sha256/note_sha256）、`profiles`（4个model/path/sha256）、`probe_tools`（四名称→{path,sha256}，path位于481 root内）、`deadline_monotonic`（481 promotion截止）。工具列表与精确来源见准备收据。四个工具需已具可执行权限；同时将两个482脚本放在481 root，`probe-log-audit.py`由callback加载。

每例前后核真实安装文件、四模块loaded note、四profile和七包；仅把两个probe可执行文件复制到临时UID10000目录。清全部LD／LIBCAMERA实验项，保留本次日志级别与现成probe帧数／只读sensor节点参数。没有私有lib/IPA/proxy/profile目录，没有设置force-isolation、pipeline选择或profile覆盖。475保留的 `/etc/libcamera/configuration.yaml` 精确SHA `078d4021…a81a04` 无IPA强制隔离，因此要求现场signature valid且app／IPA同PID；not-valid回退隔离是部署失败，不能绿。

现场保存PID/start ticks、UID／CapEff、完整maps及对应已安装文件SHA、实际签名分支、Manager租约及live affinity。按同一PID/start证明退出，额外扫描实际 `/usr` proxy，失败路径也保留进程身份；不能因删除用户目录就宣称proxy退出。启动新case至少余45秒，fork前余40秒；停止／fixture恢复清理不会因promotion期限已过而跳过。482不启动／恢复PW/WP。

日志审计核实际Gst尺寸、NV12字节／时间戳／sequence、完整成功回执、PD10及IPE队列、数学revision／token／SOF关联、停止分类及idle恢复。计数取原件，不固定bootstrap／数学帧数。显式失败receipt计discarded、stop时未resolve观察计aborted，分别保留queued／unqueued；RAW-only单独要求零IPE／PD10作业，lens的既有Manager租约可存在。warning／ERROR原行保留，不因默认配置或profile缺IPE字段推断零IPE。

本地验证仅含AST／导入与真实旧440缓存的history协议有限回归。旧缓存不是475安装或本轮probe的硬件结果；最终须由481新鲜事务及483缓存审计共同确认。
