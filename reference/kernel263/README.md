# 263：公共相机缓冲生命周期，正常取流进展与断连竞态

2026-10-18，继续用户的 Linux 摄像头适配目标，目标仍 active。用户明确要求其它相机软件无需逐个修改；修复应进入承担责任的公共层。当前实验证据把这一项共享缓冲提前覆盖问题集中到 PipeWire/SPA 的交付和回收路径，不能据此宣称内核或全部 libcamera 功能已无缺陷。

**公共修复尚未部署。** 同260启动，boot235/Image183、libcamera r15/config-r10、961包保持；262的已安装 GStreamer r1 和 Snapshot 临时复制开关保持。所有新增库只用于私人运行目录内的独立 PipeWire/WirePlumber，生产桌面服务未重启。最新候选通过崩溃恢复，但正常断连复测仍出现一次内容变化、一次回收错误和 PTS 回退，因此不能作为完成品安装。

## 已确认的覆盖及隔离

消费者保留 `GstBuffer` 的浅拷贝至少120ms，入队时及释放前分别读取前65536字节计算 SHA256。保留的是共享内存引用，未把像素复制成私有数据。以下均为1920×1080 BGRx、约12秒、前摄真实流：

| 路径 | 收到帧 | 保留内容检查 | 发生变化 | 解释 |
| --- | ---: | ---: | ---: | --- |
| 当前生产 PipeWire，共享 pool | 346 | 340 | 340 | 稳定复现持有期间覆盖 |
| 显式复制对照 | 687 | 673 | 0 | 复制可绕开此故障 |
| 安装的 `libcamerasrc`，绕过 PipeWire | 228 | 224 | 0 | 直连路径未复现；协商30fps，不作等帧率性能比较 |

收据：[共享](immutability-6000000-validation.json)、[复制](immutability-3000000-validation.json)、[直连](immutability-6000007-validation.json)。这是像素采样检查，不是整帧逐字节验收，也没有 GUI 窗口、快门或新照片。原 harness 的 `diagnostic_completed=true` 只表示完成运行和恢复，不能覆盖其 `held_content_changed` 失败字段。

独立 PipeWire 实例使用自己的 socket、配置、registry、状态和 WirePlumber camera-only profile。生产实例未被停止；前后摄图、格式、控制、供电、PM、MCLK均由每轮外层 harness 保存和恢复。

## 分项对照，不能只加 Busy 或可靠属性

| 独立实例变体 | 结果 |
| --- | --- |
| 原库 | 379次检查中351次变化 |
| 仅 `node.reliable=true`，实际属性已确认 | 379次中341次变化 |
| SPA 增加 Busy metadata 和延迟回收 | 只收到12帧即停流；12次中8次变化、8次未回收错误 |
| Busy回收保护＋可靠分发规则 | 408帧，401次检查0变化、0未回收错误 |
| SPA自行声明可靠分发，无规则/应用复制开关 | 448帧，440次检查0变化、0错误 |

对应 [mode4](isolation-flow-6000004-validation.json)、[Busy单项失败](isolation-flow-6000005-validation.json)、[组合](isolation-flow-6000006-validation.json)、[自动公共属性](isolation-flow-6000008-validation.json)。第一次可靠规则在 `media.class` 设置之前执行，没有匹配；改按 `node.name` 后才算有效对照，原失败保留。Busy契约来自上游 [SPA metadata](https://pipewire.pages.freedesktop.org/pipewire/meta_8h_source.html)：计数大于0时不应写入缓冲。

自动SPA候选单客户端通过，但双客户端只有406/1帧，第二个被饿死。上游 `tee_process_reliable()` 找到首个可用端口就退出，不能直接将其当作广播路径。[双客户端失败](advanced-6000010-validation.json)

## 公共广播候选及跨框架取流

第一版公共组合：SPA添加 Busy、延迟回收定时器及节点可靠/广播属性；核心只对声明 `node.reliable.broadcast=true` 的节点采用广播，保留已有单端可靠路径。[SPA补丁](libcamera-broadcast-ownership-candidate.patch)、[核心补丁](core-reliable-broadcast-candidate.patch)、[构建哈希](broadcast-candidate-build-validation.json)

这组测试直接使用手机已经安装的 `/usr/lib/gstreamer-1.0/libgstpipewire.so`，没有设置 `SAMURAI_CAMERA_COPY`，共享 pool 保持开启。其它早期诊断轮次使用独立搜索目录的诊断插件；两者不混为同一次验收。

| 广播候选场景 | 收到帧/检查 | 结果 |
| --- | --- | --- |
| 双 GStreamer，分别持有120/180ms | 304/307帧，299/300次检查 | 0变化、0错误，PTS递增 |
| 所有缓冲持有1.2秒，16秒测试 | 96帧，88次检查 | 池耗尽后释放可继续，0变化/错误 |
| 同一后端四次打开/关闭，快/保留交替 | 330/205/333/187帧；保留轮197/179次 | 0变化/错误；首次打开后FD保持64/64/64/64，不能扩大为长期无泄漏结论 |
| 一个客户端正常关闭，另一个继续 | 160/442帧，156/434次检查 | 0变化/错误，剩余客户端持续 |
| 直接 `pw_stream` 消费者＋GStreamer | 341/335帧，341/327次检查 | 两条路径均0变化/错误，PTS递增 |
| 一个客户端被 SIGKILL | 剩余客户端78帧，PTS仅跨3.995秒 | 保留样本未变，但后续停流；失败 |

收据：[双客户端](advanced-6000014-validation.json)、[耗尽](advanced-6000015-validation.json)、[重开](advanced-6000016-validation.json)、[正常退出](advanced-6000017-validation.json)、[跨框架](advanced-6000020-validation.json)、[崩溃失败](advanced-6000018-validation.json)。直接消费者的[源码](native-stream-probe.c)只使用公开 `pw_stream` API，检查前65536字节FNV摘要及保留期间Header PTS；它是测试客户端，不是要求应用采用的新接口。

第一次跨框架运行因手机没有 `pw-dump` 而在取流验证前失败，随后通过标准设备provider读取目标节点属性，使用新上下文完成上述跨框架测试。没有为此额外安装工具包。

## 被否决的记账清零方案

曾尝试在核心按链接记录缓冲ID，所有本地链接返回后清除遗留 Busy 计数。第一版错误假设缓冲由本地 `port->buffers` 持有，取流为0；转为保存实际协商的指针后能运行，但526次检查全部发生变化，498次回收错误。[零帧](advanced-6000022-validation.json)、[内容损坏](advanced-6000028-validation.json)

这些证据说明中间图IO的归还不能直接当作所有下游应用引用已释放，清零绕过了真正的生命周期保护。`core-broadcast-lease*.patch` 以及配套 `libcamera-broadcast-lease-candidate.patch` 是失败实验，**不是待安装补丁**。后续必须保留这个失败对照，不能以“恢复帧数”代替内容所有权验收。

## 标准挂起/重协商候选，仍有退出竞态

回到无计数清零的广播实现，在声明广播的相机输出还有其它使用者时，链接移除触发标准节点 Suspend 和图重协商，让旧缓冲池通过正常流程退役。[补丁](core-broadcast-reconfigure-candidate.patch)、[构建](reconfigure-candidate-build-validation.json)

崩溃轮确实验证了恢复：被杀客户端在退出前收到77帧、0回收错误；后端实际出现2次启动/停止及缓冲重建消息，剩余客户端586帧、578次检查全部不变、错误0，PTS跨17.679秒。[恢复及原始运行](crash-recovery-flow-validation.json)、[完整恢复轮](advanced-6000034-validation.json)

但同版本正常关闭一方的后续回归失败：剩余客户端361帧，356次检查中**1次变化**，**1次未回收错误**，`pts_strictly_increasing=false`。外层完成恢复，但 `diagnostic_completed=false`。[必须继续处理的退出竞态](advanced-6000035-validation.json)

因此当前不能安装公共候选，也不能移除262生产启动开关。下一步要追踪正常关闭时的旧/新缓冲代次、源完成队列、异步IO与客户端pool teardown；区分重协商竞态和已有广播时序窗口。不能通过忽略那一帧、加任意等待或清零Busy来宣布修复。

## 产物、包与继续操作

- 当前生产公共库仍是 `pipewire-libs` / `pipewire-spa-libcamera` 1.6.9-r0；已下载原生回退APK，原包签名在SDK核验通过。[原包与生产哈希](common-package-inputs-validation.json)
- 公共库试打包在PC进行。`pipewire-libs`候选签名包已生成；SPA的严格动态导出集合检查被C++ RTTI符号差异拦下，整套打包脚本未完成、没有安装事务。264复核 `_ZTISt19_Sp_make_shared_tag` 实际为GLOBAL OBJECT，原笔记所称weak不准确。这个差异本身不是已证实的公开SPA ABI破坏；后续按实际工厂入口和依赖验证，不能直接跳过ABI审查。该PC候选对应尚有退出竞态的版本，不能用于生产。
- 最新标准重协商核心 SHA256 `ff2954c1aa1650907f428a5995f02f0fac4bb8a44beb9c2054ccbbec70af206d`，配对SPA `bdd70ab54a9705dbd50329716988f7d4e8908b4759f5f7cb75f4b921c32908c5`。独立shadow目录最后保留此组合，不会被生产实例自动加载。
- SDK `/work/pipewire263-broadcast` 的核心源码已切到标准重协商版本，但其中SPA源码曾用于失败的lease实验；不能仅凭工作目录名称重建配对产物。以公开补丁、构建收据和私人原产物哈希确认组合，换版本后重新回归。
- 每个手机上下文仅执行一次；脚本中的预设但未运行mode不代表通过。新测用新目录/mode，不能覆盖已有失败。`host.py`只包装260严格原密钥运输及当前启动guard；实际连接资料仍只在私人目录。
- 前摄暗/噪声、GUI快门/前后切换、录像、IMX319和其它后摄及GPU问题未在本轮验收。没有新拍照或GUI操作，不能将headless取流称为实际屏幕预览。

[最终健康](final-health-validation.json)确认生产两项公共库、GStreamer与启动覆盖哈希、49项相机框架载荷保持，961包；Phosh/PipeWire/WirePlumber原进程身份保持，22个实验上下文全部终态，PM/MCLK/trace恢复，新增GPU fault0、taint0。原始日志、候选库、原包和归档只在 `E:/edk2-samurai-out/kernel263`；[私人证据导出](evidence-validation.json)逐文件校验，不纳入公开镜像。
