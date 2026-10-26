# DEVICE 同步恢复：原Image363上的独立候选

本候选只改原Image363/`ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 的 `gadget.c` 与 `core.h`，不依赖R2检测窗口。**未部署、未链接Image或ko、未作实体PM验收**；不能据此解释历史r5失联或声称NCM枚举已恢复。旧 `apsd-dwc-resume-error-candidate` 仍为changes-required，被停止的cleanup WIP未采用。

原gadget SHA `9eec86e4…1ff0c5`、core.h `525c1d5d…41373c`、完整core.c `bd8a8aab…d7ffcf` 的来源关联见 `source-result.json` 和既有 `../apsd-integration/current-r7/image-source-linkage.json`。完整候选、差异和收据分别为 `gadget.c`、`core.h`、`sync-recovery.patch`、`result.json`。共享原件没有修改。

原core.c整文件保持逐字：DEVICE init-for-resume成功后仍调用gadget resume并忽略其errno；HOST/OTG分支不改。系统common仍执行SUSPHY恢复、返回原0政策；runtime仍在common后由原尾执行pending引用put、clear、enable_irq及last_busy。gadget首次soft_connect的原errno也照旧返回；即使新增本地恢复为0，也不能擦掉这个primary错误。core init本身失败的原负返回/自身unwind没有变化。

DEVICE且已有gadget_driver/softconnect时，新resume在原 `connect_mutex` 内执行原首次soft_connect；它成功时不增加恢复。它失败时才同步调用一次共用helper。旧UNRECOVERABLE不会使原首次soft_connect被跳过，但新增同步claim不会自行把该旧故障改回RECOVERY。无gadget/无softconnect仍直接返回0，OTG保留原单次connect路径。

共用helper从原gadget.c:4787 worker主体抽取：soft_disconnect、sleepable gadget disconnect；失败时立即结束，仍调用原断开回调，但不增重连count、不继续connect；成功且softconnect仍true时join IRQ、增加原err_recovery_count并检查原MAX3，然后soft_connect。count-limit明确返回 `-EIO`，stage标 `count-limit(policy-EIO)`，不会伪装成硬件返回值。没有清count、新重试循环、额外PM引用、IRQ开关/停车或terminal字段。原真正host RESET在err_state NONE时清count的代码逐字保留。

唯一新增持久字段为受原 `dwc->lock` 保护的u64 `err_event_seq`。原IRQ错误入口每次都递增，与schedule_work是否合并无关；它仍保留原真实新IRQ可写RECOVERY的政策，没有新增全局永久拒绝。helper在connect_mutex内、IRQ锁下保存本轮seq；成功或失败发布均再持同一IRQ锁。seq未变才按本轮结果发布NONE/UNRECOVERABLE；有新事件则保留RECOVERY并单次补排work机会。补排不在本次同步调用中再循环。

这同时修正新worker state gate的适用条件：已被同步恢复完整消费的旧队列可以跳过；恢复期间新到的真实事件不能被无条件NONE覆盖。发布与IRQ用同一锁线性化：IRQ在发布前取得锁，则seq不同；IRQ在发布后取得锁，则它自己递增、改RECOVERY并排work。当前work已RUNNING时pending位已清，允许后续一轮；已有pending时合并请求，但seq仍记住新事件。新失败且有新IRQ同样不能被后写的UNRECOVERABLE吞掉；无新事件的失败才保留原失败政策。seq不是重试额度，也不意味着每个IRQ独立跑一轮。

日志区分原 `primary`、新增 `recovery`、stage、start/end seq、`pending_at_publish`。本地return0加pending=1只表示本次本地操作返回0但有新错误待处理；pending=0也是发布时刻的收据，不承诺之后没有新IRQ。没有“恢复枚举成功”日志。helper的stage/seq/pending放在栈上report，不是新controller终态字段。

`connect_mutex` 仍在整个断开/回调/join/重连/状态发布期间持有；不持DWC spinlock调用可睡眠回调或join IRQ。原选定configfs/NCM链已由既有 `charging-session-20261023/dwc-r2-independent-review` 的固定原始callback缓存独审：gadget4014→configfs1882→composite2305/2288→reset_config928→ncm_disable1375→gether_disconnect1217，未见反向connect_mutex、同步PM-get或断开内flush_work；NCM完成回调亦未见该反锁。gether flush_work在最终cleanup1112，不是disconnect。该结论不认证任意未来gadget function。

runtime恢复回调执行期间，实际RPM源码先置RESUMING、调用callback后才置ACTIVE；同步PM-get会等待当前恢复，因此本候选不取它。core已初始化并保持供电是新增同步路径的前提，normal error worker原有供电约束没有被扩大证明。pending IRQ仍可能由原4686路径禁用，join IRQ只等待已运行handler，不重新启用或证明处理latched event。虽然原core/event setup清旧count，失败connect后仍可能产生新事件并使HALT超时；本候选只能报告这次有界失败，不能靠更改pending/IRQ引用强求成功。原EP0等待500ms及RUN_STOP的2000次1–2ms轮询是已有边界，并非整个PM的硬截止。

实际只读source354 `kernel/workqueue.c` SHA `3a5ec538672d16d4241d161e7ec9e4ea3e6872777727a40ea8a69a7980435cc6`：2499–2502以PENDING决定是否入队；3357在3396调用workfn前清PENDING。这是新事件可与旧running/pending work重叠的原始调度依据；不能把schedule_work返回false当成“无新事件”。本轮未用Git重新取该文件；Image关联的DWC/PM及callback来源仍由既有固定收据限定。

`test-result.json`：11组新增影响范围测试，8个实际函数（新调度/恢复helper/worker/resume、逐字原soft_connect、原common/runtime/system调用者），ASan/UBSan/Werror通过。包含成功/primary失败与恢复成功或断开/重连/cap失败、旧UNRECOVERABLE保留首次行为及真实新IRQ、connect/成功发布前后新错误、失败尾新错误、pending旧worker合并、真实pthread下已RUNNING并阻塞连接mutex的旧worker、running worker再排队，以及原runtime pending尾/系统SUSPHY和供电成功政策。DWC算法直接提取生产函数；硬件、workqueue调度边界为fake，连接/IRQ互斥使用pthread。它不是完整Linux workqueue、硬件时序或所有并发交错的证明。原126断言和独审caller反例仅复用，未重跑。

`build-result.json`：仅私有source-view/O下编译 `gadget.o`，W=1无warning/error；对象SHA `b012a214…4d1b12f`。core.c仍指向逐字原件，只有gadget/header是私有副本；共享source/build/config/Makefile/Module.symvers在检查范围内前后未变，CONFIG赋值无差异。没有SDK、Git、设备、SSH、USB、PM操作或Image/ko链接。

新增struct字段意味着未来采用必须是完整一致的内核构建与审阅，当前对象不是可注入旧Image的替换物。未准备部署或硬件试验；下一步只由根会话审阅此冻结增量及独立审查结果。
