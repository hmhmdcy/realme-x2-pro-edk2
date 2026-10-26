# 当前 IRQ／97c 基线的 USB 冷启动暂存入口

本叶仅连接已经完成的设备端暂存工具：当前 #502、USB7cb／charger97c／保护7848、manifest18e8 → 磁盘 USBd046／manifest34ead。原 bootedd、logdumpace2 和所有驻留模块保持；设备端同步停充后保持 INHIBIT，结果只能是 `staged/runtime_pending`。它不会热卸 USB、加载新模块、切 AUTO、刷载体或重启。

绑定同时重审原 IRQ 启动采用材料和已完成的 charger97c 热更新原件，包括原传输、worker／supervisor 的实际终态、完整安全样本和保留的保护实例。旧 boot pointer5fca 保持原义，不能冒作当前磁盘清单；当前18e8由成功热更新证明。绑定失败先于创建任何事务目录。实际身份不来自测试数据、uname 单字段或未来启动的猜测。

主机 `host.py` 默认 `check-local`，不读运行身份或访问手机。显式 `bind --transaction <新事务> --runtime-pins <实际overlay>` 只生成本地请求。`preflight` 经原 strict key 和固定压缩 SSH 执行只读检查；健康 Full 可用于冷启动暂存，预检不会创建设备目录、租约或停止充电。`launch --window-confirmed` 会先预检，再由原 R2 传输创建一次性启动意图；设备仍独立检查新鲜窗口、锁、身份和保护状态。

`status`／`fetch` 使用原事务，不因超时、断线、新 pointer 或后来的启动重新绑定。原 R2 的 Popen／stdin EOF／finally wait、设备 supervisor 及其 worker 所有权保持；仅传输 argv 增加固定 `-C`。remote 仅改事务前缀和请求 schema，输出仍为 `device-stage`；取回保持原 `fetch-*/raw` 布局。root 目录的 launch-claim 由原 remote 核对，原实现不单独导出它；后续审核不能要求不存在的取回文件或补造原件。

六项受影响检查通过：真实缓存 adoption＋热更新与当前两文件包相接、伪造 overlay 在创建目录前拒绝、健康 Full／故障／现场窗口分支、原启动 claim／EOF／wait、只读预检及请求对应、后续 fetch 保留原事务而变更原件阻止新 launch。设备边界在模型中替代，只有缓存文件审核使用真实原件；没有实际 SSH、设备暂存、租约、刷写或重启。旧测试矩阵直接复用。

**尚不能部署整套 PM 候选。** 还需完成 logdump-only 的504／4453启动与 ace2 回退入口、新启动完整核验及独立 adopted guard，再安排实机窗口。完整 PM 回退为 USB7cb＋manifest18e8＋logdumpace2，并正常重启；不能只退载体或仅退 charger。该暂存工具的离线通过不是待机、USB枚举或500mA恢复验收。
