# 371：持有模式仍在probe返回前重启，设备基线已恢复

本轮完成新收集器、一次真实A5持有实验和恢复。**实验失败：仍是HFI响应3／约2.502ms，块复位完成日志之后进入新启动，probe没有正常返回；没有取到标准dump或固件RAM异常页。** 不能把370的软件状态和夹具通过等同为实机可用的故障窗口。整体多摄／骁龙ISP目标继续active。

## 实现与离线检查

沿用370的start失败保留RAM／映射／PM语义，SoC核心仅增加DMA开始／完成和PM引用释放的三个阶段日志，便于区分何时进入资源清理；没有改变CPU／复位顺序。维护源分支`samurai-a5-held-snapshot371`，commit `f41d5f828e047b57c61a0e1a3b4dcde3fca96671`。[源码](source-state.json)、[补丁](a5-teardown-observations.patch)。两个实际k363配置in-tree W=1/-Werror候选模块构建通过，无诊断；test模块与370逐字节相同，core232856字节。配置及原CAMSS输出恢复。[构建](intree-build-validation.json)。实际start／quiesce／stop函数体22例模型通过，平台提供者仍为桩。[生命周期](lifecycle-validation.json)。

独立collector先落盘ready并确认进程存活，worker才以明确`hold_start_failure=1`加载诊断模块。collector核对临时设备／OF归属、启动guard、held状态及完整固件映射；先读首4KiB代码页并与原厂ELF对应LOAD内容哈希比较，匹配才读109000异常页、340000 L1以及必要且在界内的L2表。临时接口与固件特有偏移分离：偏移只在本轮诊断工具，SoC核心没有加入原厂符号地址。原始内容只私存。

标准devcoredump只处理本轮新增、failing_device及OF同时匹配的对象；先持久化raw和解码，再等待固件窗口检查完成或有界超时，之后确认消费，避免保留引用妨碍overlay移除。5个实际独立进程夹具覆盖成功、代码页不匹配、guard变化、未held和OF不符，无关dump未消费。[收集器](collector-validation.json)。7个实际worker判断／错误清理语句模型覆盖成功保留、代码不符、ACK失败、清理失败、未知归属、握手成功和CPU释放前失败；每次清理尝试先保存状态，已开始的写操作不自动重试。[worker](worker-validation.json)。这些不能代替硬件现场。

板级静态DT／固件物理区、主线公共框架、CAMSS/VFE／传感器和libcamera／IPA均未更改；本轮用户空间代码只是诊断收集和恢复工具，没有绕过HFI错误或改变正常相机流程。

## 真实结果与边界

执行前核对369当前guard、taint0、CAMSS休眠、临时模块／固件／事务不存在。新事务`/var/lib/samurai/k371-boot-r1`，worker8617，collector已就绪后仅启动一次。加载之后原Wi-Fi不可达，USB从EUD重新枚举为NCM，经原密钥严格USB SSH确认已经新启动；旧worker与collector均不存在，旧state仍terminal=false／load-boot-test，未补写成功。

ramoops记录CPU release至响应3为2.502ms、版本0x01000100、expired0，随后记录块复位断言成功。未观察到DMA开始、DMA完成或PM释放日志，亦没有worker发出cleanup的状态。本次源码在start失败后先保留资源，明确的hold参数用于跳过自动stop，仍无法避免重启。因此现有证据不支持把异常只归因于DMA／PM释放；也不能仅凭没有阶段日志证明真实硬件DMA静止或排除其它损坏。**精确复位原因仍未知，收集到的末尾没有modem watchdog记录。** [真实失败](boot-runtime-r1-validation.json)。

只取回collector-ready与两个空日志，没有collector-result、raw标准dump或firmware快照。不能称标准dump未曾发布，也不能把未读到的异常字段当零；本轮没有再读取重启后的DDR来推断旧现场。下一次需要将有界固件RAM复制提前到内核失败路径、块复位之前，独立于probe返回和用户空间调度。

复位后的末尾再次有4条fw_devlink代理链接失败。核对实际Image363同一`drivers/base/core.c`，该分支记录错误并返回EINVAL；现有LKML[SYNC_STATE_ONLY代理链接讨论](https://lists.openwall.net/linux-kernel/2026/09/29/1980)也展示了别的平台在consumer已probe后拒绝此类链接。它只能说明0x180日志有常见代理路径，不能证明本机UAF、SoC复位或提供ICP修复。没有移植其它SoC补丁或关闭fw_devlink。[源码审计](framework-audit-validation.json)。

## 恢复

新启动仍为Image363／boot366／DT365，模块和临时DT节点已不存在，17路ICP/BPS/IPE时钟归零、taint0。boot及logdump读回保持；只在临时firmware副本与原厂及事务副本哈希一致后删除该临时副本，旧事务和原件完整保留。新guard为`/var/lib/samurai/k371-recovered/boot-id-private.txt`，后续用host371，严格原密钥USB。[恢复](recovered-boot-validation.json)、[清理](recovery-cleanup-validation.json)。本轮未发送主机复位、未刷写分区、未写NV／OTP／校准。

SSC、SensorProxy、greetd、Phoc/Phosh、PW/WP和adsp/slpi/modem均健康，无额外正常重启。[健康](current-health-validation.json)。四颗传感器各12帧硬件采集通过，主摄实际隔离IPA另28帧／5阶段及Gamma ACK通过，相关新增故障0，九相机电源均disabled/users0，CAMSS/双CCI休眠。[采集](camera-runtime-validation.json)。十个相关模块loaded note与磁盘一致，无活动worker／ICP模块／临时固件或节点，PW/WP各一个uid10000、taint0。[终态](final-state-validation.json)。

## 后续

不要重放371用户空间held窗口。下一步在仍拥有的固件映射中、CPU复位前完成有界内核快照，再离线核验代码页／异常字段／动态页表；通用SoC驱动按加载布局保存固件范围，原厂特有解析留在诊断工具，避免把符号偏移散入板级或正常用户空间。还应在复位前向已经有效工作的printk／ramoops写入受界字段和代码校验摘要：只复制到普通RAM的devcoredump仍可能来不及被用户空间持久化。需同时继续对照原厂错误停机及MMU／共享区访问，不预先认定fw_devlink或DMA清理就是根因。

完整SYS_INIT/PING/PC_ACK、IPE会话及IO/IQ、第五颗2MP身份、更多模式、光学／几何同步／连续AF等均未完成，见[完整剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。
