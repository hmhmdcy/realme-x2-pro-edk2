# IRQ native USB PM：仅冷启动前两文件 stage

当前真实输入为 #502、boot `eddade…6e06`、logdump `ace2e2…3ed1`、manifest `18e8a1…3b4e5`、USB7cb/charger97c/protection7848。只写磁盘 USB `d04608…67037` 与 manifest `34ead4…8a39b`，其余文件和**全部live notes**保持。真实forward `f1162d…230bc`（27,163B）及cohort delivery `89349f…da01`已经物化并重读绑定；不是future hash。该cohort后续要求Image504/4453载体，但此worker不写载体、不重启、不热卸、不加载、不AUTO、不查询新MAC。

`stage-worker.py`是实际冻结原件的薄组合：原4779 stage的 `atomic_replace/read_owned/lease`与509c更新器实际97c snapshot、健康、身份、held MAC fd等方法逐段提取，`source-reuse.json`列原件SHA和逐字部分。没有带入R8卸载/加载/恢复AUTO路径，没有新Popen监督器。原supervisor `b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc`继续以regular request fd启动唯一 `python3 -B <root>/stage-worker.py --execute-stage` 并finally wait。root host另行绑定实际18e8 runtime overlay/原key/-C/原child，不能仅相信本叶的结果标签。

精确请求在 `contract.json`：schema `samurai-irq-native-usb-pm-stage-request-v1`，transaction `irq-native-usb-pm-stage-[a-z0-9-]{8,48}`，identity五项、adoption三项（原IRQ adopted guard）、worker/source、cohort/payload和lease token。输出 `<root>/device-stage/`独占新建，已存在不重放。执行需原charging flock及新的root:0600 `/run/<tx>-window-private.json`，原stage精确lease字段/摄像头蓝牙交回/issued≤now<expires≤issued+120s；没有真实request/lease在本轮生成。

默认入口只输出source-only。`--preflight`接同stdin；也可加载后调用 `preflight(request, Device(raw), raw)`。它复用509c的existing O_RDONLY+SH service lock、current502/18e8/notes/完整carrier/guard/原02c MAC实例夹读；不创建目录或lease，不stop/control。schema `samurai-irq-native-usb-pm-preflight-v1`，含request SHA、identity双夹、snapshot、healthy_state、eligible。健康Full或Managed均可 `eligible=true`，此许可仅是冷stage预检，不能当已停充或已stage。

执行前fresh完整安全NORMAL sample、独立保护/pack/cell/原预算/限额、所有notes、相机idle和四服务都核对。原manager614直接同步stop并核REG08 INHIBIT。Full前的logical_full/cause/session0保持；stop后holding/hold_requested/desired_enable必须清0，不能要求它还处在健康Full holding。若stop后已见Full事实丢失，替换前拒绝。只对既有目标原子备份→USB→manifest，逐项fsync/readback；live匹配使用旧USB备份，不能让新磁盘冒充已运行新模块。最后仍INHIBIT，状态仅 `staged/runtime_pending`。

失败时无启充或模块动作。若已尝试写文件且身份/原notes/原MAC实例及实际INHIBIT仍可证明，使用同atomic函数、独立`-restore`临时名恢复精确旧两个文件并读回；原file已旧则保留并记录。恢复可以在本次forward因lease到期失败后完成，只还原该持锁事务的原磁盘，不延展forward窗口。若identity/实例变化、无法证明INHIBIT、对象不是已知old/new、原进程/module未知则停止，记录recovery_error/partial或unknown，不猜写、不重放。原failed temp保留并列在结果中。Full保持只证明至本事务最后snapshot；后续真实物理detach按原内核语义重置Full，不伪造跨事件/跨boot延续。

设备原件固定：原stdin `request-private.json`；`process-private.json`为tx/boot/pid/start_ticks/argv（没有额外伪造的requestsha）；两个`.before`和`files-before-private.json`；`before-private.json`、`stopped-private.json`、`after-private.json`均为直接完整snapshot；events/jsonl和result。result schema `samurai-irq-native-usb-pm-stage-result-v1`，request/cohort/payload与old/new hashes、stop_verified、staged/status/runtime_pending/terminal、primary/recovery错误、final_files/temporary_files、Full事实均保留。成功必须原worker/supervisor真实wait0、最终两文件和snapshot共同认证；`staged`单标签不够，不能当新boot通过。

11个新组合只运行实际stage/health/Full门和原atomic函数（私有temp文件）：Managed/Full成功、Full事实丢失、stop失败、USB与manifest各rename后失败恢复、unknown不再动作、保护实例/cache变化停止、独占事务不重放、只读Full可stage预检以及旧kernel请求预检零设备边界。硬件/manager为明确模型；冻结真实forward包实际解码。旧矩阵未跑。没有手机/SSH/USB/SDK/284/storage或内核构建、payload再制作、当前pointer改变；主机传输及后续冷启动由root另接。
