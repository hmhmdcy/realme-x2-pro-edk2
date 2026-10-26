# 461：同步 IPA 回执期间保留请求所有权

修复一个实际可复现的停流重入问题：原452 `tryComplete()` 在同步 `frameProcessed()` 前就将请求移出集合。同步IPC会处理事件；若其中重入stop，原stop drain找不到该请求，FULL池随后被释放，而外层仍访问FULL并完成请求。宿主从实际完整函数与实际stop drain提取代码，原版正常场景通过、stop场景由ASAN报heap-use-after-free。

[0065补丁](0065-camss-retain-request-through-ipa-completion.patch)只改一个管线文件。回执期间保留请求并设置 `ipaCompleting`，嵌套的普通完成／timeout不重复发回执；stop仍能走原取消drain一次。同步返回后重新检查running、epoch、请求sequence和FULL身份，旧外层不得再处理已取消／重启复用的对象。正常路径仍先确认成功历史，再归还内部FULL、完成应用请求，未把FULL提前复用于IPE仍在读取的阶段。

[实际函数检查](check-completion.py)的[10例ASAN／UBSAN收据](completion-validation.json)通过，覆盖normal、stop、epoch restart、同request复用、嵌套完成／timeout、live failure、零token、RAW等待／超时及stopped entry。它证明该有限重入与所有权修正，不代替完整CameraManager／代理故障／实机停流验收。

## 已编出单库候选

[准备](prepare-source.py)从冻结452私有树复制，零fuzz／offset应用补丁，只修改 `camss_vfe.cpp`。保留452 source／产物、IPA6、旧444 proxy、签名、原厂配置、参数数学、buffer数量与正常排队顺序。副本约575MB，准备后ext4仍余6.86GB。

[构建](build-core.py)由主线接手：子代理被系统中断后，先查实际进程与SDK挂载，确认构建未启动、SDK空闲，才执行一次独立目标。dry-run限定管线对象、版本生成／对象、core链接4步；实际因版本内容未变而跳过其对象，只执行3步，j2、109.498秒、exit0，SDK已卸载。

- 新core 51259240B，SHA256 `9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af`。
- IPA仍 `4c90047d…`、签名 `f5c351bd…`、proxy `c7887708…`，逐字节原hash保持；生成版本内容保持。
- [构建收据](build-validation.json)通过；二进制及完整日志只在PC私有 `kernel461/`。后续r2已临时上机并恢复正式，未永久安装。

## 与FULL缺帧问题的关系

这次是停流可靠性修正，**不是已证的偶发缺帧根因修复**。源码确认FULL出队后还需供IPE读取，不能直接回收；现有 `completeRequest()`也已立即排入prepared等待请求，简单defer下一次finish或把QBUF跨过历史回执并没有确定改善依据。459的90秒无gap与546条正常尾链不改变452已捕获的旧缺口。

新boot的[实机小结](HARDWARE-SUMMARY.md)和[逐帧收据](lifecycle-r2-validation.json)已完成：两种IPA模式各720p→1080p→720p，285消费／286IPE，同SOF严格回执通过；真实FULL FD及303 qbuf／286 dqbuf、跟踪无覆盖、正式恢复。native 1080p仍缺SOF4、7；[缓存关联](full-gap-validation.json)见软件队列零快照，但根因未证。未混新proxy、调校或第五DT，未宣称长期无丢帧或完整画质／AF完成。

[新启动预检](preflight-handoff.py)复用固定451只读查询及正式440校验，改为绑定充电线程已采用的guard／manifest，旧k449 guard被明确拒绝。工具只有生成查询和检查缓存观察两种入口，没有SSH、写手机或采用guard入口；没有有效owner return时仍可生成占位查询，但它在读设备前退出。交接后由原key传输以stdin执行，检查同次nonce／boot／guard／正式文件／模块／服务／资源和充电快照，再生成一次性handoff。

[宿主检查](preflight-validation.json)保留8个拒绝用例及占位查询的提前退出；它本身不是硬件证据，后续r1/r2各自的新启动实读预检已保存在私有原件。[运行体](capture-body-lifecycle.py)复用冻结459跟踪生命周期及463角色检查。r1工具失败、修正constructor的[检查](lifecycle-tool-validation.json)与r2独立终态均保留，终态不可重放。

镜像器会脱敏UUID文本，当前测试改用UUID构造器生成假身份。复用的451只允许两份精确文件hash，其差异已核为未调用的旧self-test假UUID被替换；设备校验函数逐字相同，旧guard仍被拒绝。没有修改冻结451或实机载荷。
