# 361：请求链实测、公共分发器修复与交接

2026-10-20，按用户要求收尾、提交和交接。四摄、五个物理模式的十个原厂用途上下文，均完成 r28 曝光／手动防频闪／IFE Gamma 的线程模式请求检查；隔离进程模式仍失败，新候选未安装。完整多摄／骁龙 ISP 校准目标尚未完成。

实机沿用恢复后的 k298 启动和严格原密钥 USB SSH。临时加载已测 348 Gamma 参数模块，使用 360 的 r28 核心库、签名 IPA 和代理。五段请求依次覆盖 EV 0、+1、-1、0、0，频闪 Off／10000µs／8333µs／Off／10000µs，合并手动白平衡并重新开启 AWB。检查真实采集帧、请求元数据、AE 更新、Gamma ACK、实际动态库映射及线程／隔离 PID；每轮恢复媒体图、控制、原 338 模块和桌面服务。[运行汇总](runtime-validation.json)。

| 事务 | 结果与适用范围 |
| --- | --- |
| r1／r2 | 临时包遗漏 SONAME 相对链接，实际回退到系统 r27，零帧；修正临时打包后再测，不归因于控制映射实现。 |
| r3 | IMX319 Preview 完成五段、28 帧，Gamma ACK 一次、AE 更新三次。 |
| r4 | 其余九个原厂线程上下文各完成五段，共 246 帧；随后主摄隔离模式在第 11 帧后触发公共分发器断言。整轮结果保持失败。 |
| r5 | 加入公共分发器修复后，隔离主摄同样运行 11 帧，暴露 CAMSS `IspControls` 队列重复处理／空队列 `pop_front()`。整轮失败，后续广角实景及线程检查未执行。 |

十个通过上下文分别为 GW1 两个模式的 Preview／Video、IMX471 Preview／Video、IMX319 Preview／Video、S5K3M5 Preview／Video，共 274 帧。每组五段请求完成、Gamma 只上传一次，存在实际 AE 更新。它们使用未修改的 r28 公共 base；不能把这一结果写成 361 修复后的全套回归。r4／r5 的隔离应用均失败，Linux 及相机资源恢复成功，相关新增内核故障均为 0、taint 0。

传感器测试图案用于验证请求链，不能证明曝光对实景亮度的物理响应、防频闪消除效果或绝对色彩校准。元数据按实际 SensorContext／SOF 解释；回调时读取的当前 V4L2 控制可能已领先，不能机械按“回调读数加两帧”推断锁存。广角正常光照用例尚未执行，没有保存场景图像。

## 公共层修复

隔离 IPA 的同步 IPC 会从 notifier 回调递归进入 `processEvents()`。旧 `EventDispatcherPoll` 的内层分发会删除外层仍引用的 map 条目，并提前清除 `processingEvents_`，导致断言或悬空引用。

[补丁](event-dispatcher-reentrancy.patch)保存并恢复外层处理状态，将空条目回收推迟至最外层退出。保留原断言，接口及类布局不变，没有禁用隔离或在 CAMSS 中吞错。修改位于 `src/libcamera/base/event_dispatcher_poll.cpp`，当前完整候选在 `/mnt/samurai-full282/libcamera361-event-dispatch-built/src/libcamera-v0.7.2`。[源码身份](dispatcher-source-state.json)。

真实 ARM64 公共库构建通过，29.87 秒。独立回归使用相同头文件，分别装载旧／新实际共享库：普通一级分发均通过；旧版在二级、三级和定时器注销的嵌套场景均复现 SIGSEGV；新版均通过，并验证回收后重新注册。八组预期全部匹配。[构建](dispatcher-build-validation.json)、[回归](dispatcher-regression-validation.json)。实机 r5 已越过原 notifier 断言，但整条隔离路径未通过，不能据此宣称全部问题已修复。

参考过[上游相关断言讨论](https://lists.libcamera.org/pipermail/libcamera-devel/2024-August/044453.html)，其触发场景不同；本补丁是本地修复，未声称是上游回移或已提交上游。

## 续作的首个具体问题

r5 的 `Algorithm request epoch=1 source=12 revision=0` 连续打印两次，随后 `std::deque<CamssVfeData::IspControls>::pop_front()` 断言。应先检查 `CamssVfeData` 的待处理 ISP 控制队列，在调用同步 `applyIspControls()` 前处理所有权／重入，避免递归处理同一项。不能简单删除断言、空队列跳过或禁用隔离。原始日志保存在私有 `kernel361/probe-r5-observation.json` 和手机 `/var/lib/samurai/k361-request-r5`，不要重放旧事务。

修复后先验证隔离主摄、一个线程上下文和未执行的广角实景；只有相关检查通过，才生成包含公共修复的下一版完整包并决定安装。360 的 r28／配置 r23 APK 仍含旧 base，不能视为隔离模式合格包；361 只重建了公共 base，没有制作 r29 或永久安装。临时打包脚本已补齐 `.so.0.7` SONAME 相对链接，不能只复制 `.so.0.7.2` 文件。

## 交接时的设备及资料

[最终只读观察](closeout-device-validation.json)确认：原严格密钥 USB SSH 可用；k298／CAMSS338，taint 0；五个 libcamera 运行包 r27，配置／stack r22；PipeWire 和 WirePlumber 各一个、uid 10000；CAMSS 与两个 CCI 均休眠，无活动 361 worker，无 ICP 实验模块和孤儿临时固件。r5 清理记录中九路相机电源全部 disabled、users 0。没有永久更换内核或包，没有重启、刷写、分区／NV／OTP 操作。

9008 的进入过程、板级错误及恢复边界分别保留在 [357](../kernel357/README.md)和 [360](../kernel360/README.md)。本阶段没有再次启动 ICP；不能将旧 R5 的非终态改写为成功，也不能把后来 USB 恢复归因于未确认的操作。继续使用 360 独立启动记录，旧 305／356 记录不变。

原厂镜像、固件、个体表、密钥和可能包含认证输入的原始日志留在私有输出目录；提交仅包含通用实现、补丁、脚本及脱敏结果。8 份原厂完整 Preview／Video 配置和 r28／回退签名仓库见私有 360；公共默认 YAML 没有原厂或个体表。执行脚本前按 [当前检查点](../../NEXT-SESSION.md)定位 SDK 和 E 盘 ext4，避免并发占用 SDK bind。

完整目标剩余：隔离请求队列修复与新包；正确板级内存后的 ICP／HFI 握手及真实 IPE 图像会话；后级 Gamma／LTM／CCM；动态帧长、更多模式、绝对光学／几何标定、多摄同步和连续 AF。IFE Gamma 不代表原厂最终显示色调。
