# USB PM 冷回退：留存来源审核与启动路径适配

本叶补当前PM回退的一个必要依赖：新版采用后，全局 `boot-adoption-private.json` 可以推进；旧502/IRQ及97c热更新的真实性仍应由其留存原件证明。它不要求改回全局指针，也不把历史记录当作当前手机身份或健康证明。没有访问手机、写pointer、创建实际stage/guard/lease或执行重启。

`review_retained_runtime(runtime_pins)` 重用原完整IRQ postboot/adoption审核，只把其中**读取全局pointer的位置**替换为该次采用实际保存的 `adoption-pointer-private.json`。原执行源码、请求、旧pointer、真实child PID/argv/wait、reply、内容和endpoint核对全部保持；再要求保存pointer的原始字节hash等于当初实际记录的hash。只有原来“全局文件当时的位置”这一历史路径允许归一化，其它任何字段或字节改变均拒绝。原97c更新器的完整传输/监督链、备份、INHIBIT/恢复/安全样本审核不改。

输出明确区分历史runtime记录和现在可重读的稳定文件集。稳定 `files` 不再指向可变全局pointer；`current_device_identity_or_health_verified=false`。真实新boot的直接身份、载体、驻留模块、保护与停充仍须另行采集，不能据此请求充电、刷写或省略当前核验。

`review_retained_stage(stage_directory, fetch_directory)` 连接当前stage的原fetch字节审核、进程链及17份设备原件规则，仅将原host.bound中的“全局pointer仍是旧值”重审替换为上述完整历史来源审核。请求须由真实原source identity重新推导且精确相等，原两文件包也重新解码。缺实际stage原件时直接拒绝，不能用过去的runtime成功代替新stage。原root launch-claim未由R2导出；设备仍须独立读取，不补造原件。该返回只证明过去stage的来源，不给新boot验收盖章。

补充接线测试揭示了原stage-proof的一处WSL路径缺口：它把序列化Windows绝对host路径接在REF之后。`current_stage_module()` 只在调用原fetch函数前，将这一**固定、已钉住的host路径**转成当前宿主的绝对路径；hash、remote源码、实际请求、原SSH argv、终态和文件审核保持。其它路径拒绝。原四项历史审核曾通过，缺口此前被模拟fetch边界遮住；失败fixture及原件保留，修正后整条模型接线通过。

**后续正向启动使用本叶 `activation-controller.py` 薄入口。** 它加载已经冻结的当前activation controller，仅替换stage审核回调和来源检查，沿用当前pointer的正向门及上述路径转换；不把历史模式用于正向派发。原controller的HERE、PRIVATE、job源码hash、23个原R2监督/once/EOF/wait函数和实际child路径不改，没有新增Popen。适配器自身三个文件hash进入bound stage review，再次派发时由原bound重审比对；status/fetch仍保留原事务。

四项受影响来源检查通过：真实留存IRQ采用＋97c更新完整重审、全局pointer三种Path读取入口设陷阱且实际访问0次、仅允许保存字节的原路径归一化、旧source/错误请求与缺stage拒绝。另两项用实际stage算法和明确设备/进程/传输模型执行原fetch/chain/17原件检查，篡改终态拒绝；再两项覆盖固定路径转换、正向薄入口及适配器hash。薄入口与reviewer默认检查均过。旧矩阵未重跑；路径修正后仅重跑受影响检查，首fixture路径格式失败和修正前生产路径缺口保留。

当前有审核API和可用的正向调度薄入口，**仍没有完整冷回退执行器和新boot postboot/adoption**。下一步复用原冷回退的source-boot-ended/PID语义、非破坏寄存器读取和原子还原，覆盖同boot旧驻留、新504驻留及回到502后仍驻留新模块三分支。新boot回退不能以整套postboot先成功为前提。完整PM回退仍是USB7cb＋manifest18e8＋logdumpace2，并正常重启；当前未安排实机窗口。
