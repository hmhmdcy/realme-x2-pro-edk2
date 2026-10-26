# 内核日志边界：唤醒后必须使用同一时钟域

451／452 r1完成后，主线发现继承434的worker把 `/proc/uptime` 作为dmesg筛选边界。该值包含整机睡眠时间，printk时间戳使用MONOTONIC；r5已有3396秒睡眠，两者不再可比。两份r1的 `kernel-log-private.txt` 均仅1字节，**不构成无新增故障的证据**。原件和图像审计保留，不能改写成有效日志。

主线随后只读补取完整dmesg和充电健康，以充电会话交接恢复snapshot的真实MONOTONIC为边界。当前日志仍保留原snapshot最后一行和边界前记录，故覆盖两次相机事务；1057条新记录无指定fault或丢日志迹象，taint0、两样本健康。独立[重算程序](../kernel452/check-kernel-window.py)及[补充收据](../kernel452/kernel-window-validation.json)通过。451／452的故障结论应引用此补充来源；严格图像链、CSV、实际proxy身份及恢复另有独立证据。没有为补日志重新运行相机。

后续新尝试使用 [prepare-with-monotonic.py](prepare-with-monotonic.py)，明确传 `comparison` 或 `diagnostic` 和新的 `--attempt r2`（或后续编号），再传同次可信handoff／baseline。该入口只对旧prepare加载worker正文时加入精确变换，把边界赋值改为 `time.monotonic()`；原434正文、451／452冻结prepare／body、历史worker和收据不变，不重建核心或IPA。它仍只准备载荷，不stage或launch。stage-prepared.py对r2及后续拒绝旧时钟worker，r1已结束不可重放。

[原赋值契约](log-clock-validation.json)执行从真实worker抽出的旧／新赋值：无睡眠时两者都保留随后故障；模拟3396.19秒和500秒睡眠时旧边界漏掉、新边界保留。两种prepare的变换源码语法检查通过。这是宿主时钟契约，尚未把新wrapper跑成新硬件事务；以后仍须验证当前dmesg时钟格式和实际保留范围，不能由空结果推断完整覆盖。

[暂存入口](stage-prepared.py)只在新preflight和完整逐文件SHA成立时，独立显式执行stage或launch；拒绝已有根目录／启动记录和不安全tar成员。[收集器](collect-prepared.py)已补充只传递固定captures目录的元数据，避免漏空目录；完整日志／CSV只留私有输出。它们不改正式包或充电设置。
