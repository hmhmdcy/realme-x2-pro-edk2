# 264：公共相机缓冲生命周期修复、原生包部署及实际快门

2026-10-18，同260启动、boot235/Image183、961包。已部署 `pipewire-libs` 与 `pipewire-spa-libcamera` **1.6.9-r2**，撤去 Snapshot 的 `SAMURAI_CAMERA_COPY=1`。前摄通过普通系统 PipeWire、GStreamer 和原生 `pw_stream` 取流；实际 Snapshot 窗口预览及快门生成1920×1080 JPEG。应用二进制未改，既有 Cairo/GDK CPU 显示设置保留。完整相机适配仍未完成。

用户要求其它应用不用逐个修改就能工作。修复因此落在共享的 PipeWire 核心与 libcamera SPA 插件：当前证据指向用户态缓冲交付/回收；不能把“公共底层修复”等同于“必须改内核”，也不把应用复制策略作为最终方案。[263故障对照](../kernel263/README.md)中，原共享路径340/340次保留内容变化，复制对照0/673、直连libcamera0/224。

## 最终实现与已部署组合

- SPA 协商 `SPA_META_Busy`，重新排队请求前尊重下游引用；仍被持有时通过一次性5ms定时器重试。释放时移除定时器/事件源并关闭FD，检查缓冲ID，启动时处理保留缓冲。
- SPA 自动声明 `node.reliable=true` 与 `node.reliable.broadcast=true`。核心仅对声明该广播属性的节点使用可靠广播，避免原可靠tee只交付一个客户端导致另一个饥饿；无需额外WirePlumber规则或应用环境变量。
- 客户端退出且仍有消费者时，由远端源代理 `node->remote` 使用标准 Suspend/重协商流程退役旧池；实际导出的SPA节点不重复发起此操作。
- 数据循环锁内、mix重新激活前清空相机mix的两份IO描述；SPA启动前清空输出IO，等待本轮真实完成请求后才交付。**不清零Busy、不丢弃指定数量首帧、不以任意等待隐藏错误、不复制图像作为修复。**

补丁：[核心生命周期](core-binding-reset-candidate.patch)、[SPA生命周期](libcamera-reset-output-io-candidate.patch)。构建：[核心](binding-reset-build-validation.json)、[SPA](reset-output-build-validation.json)。构建收据中的 `no_system_deployment=true` 是编译当时状态，后续安装事务见下文。

| 当前系统组件 | 版本/状态 | SHA256 |
| --- | --- | --- |
| PipeWire核心 | pipewire-libs 1.6.9-r2 | `870b7077747b14c74f15856a20f6ab93d68fde60703e0c116e2a9a38a8f91416` |
| libcamera SPA | pipewire-spa-libcamera 1.6.9-r2 | `0c3471e63587b6e930d712c8962464d636e18f2e36925ce85bb91f7349e8a9a8` |
| GStreamer插件 | 原262安装的gst-plugin-pipewire 1.6.9-r1保持 | `d7a5500688d2881d04bc04c614eb46f00da7070bb96224c7f43f97b3a0e22935` |

现有GStreamer插件仍包含上游延后unref锁顺序修复，以及默认关闭的诊断复制选项；本轮客户端均未启用该复制选项。libcamera r15/config-r10的49项载荷及内核保持。

## 同字节候选回归

先使用隔离PW/WP验证最终核心870/SPA0c组合，GStreamer消费者使用系统插件、共享pool。保留检查对每帧前65536字节作摘要，并检查保留期间PTS；不能扩大为整幅像素逐字节校验或长期无泄漏证明。

| mode后六位 | 场景 | 帧数/保留检查 | 结果 |
| --- | --- | --- | --- |
| 000057 | 同一后端3轮正常退出一方 | 75/237、70/217、72/221帧；854检查 | 变化/错误0，剩余客户端继续，最大PTS间隔0.417秒 |
| 000058 | 同一后端3轮SIGKILL一方 | 剩余326/310/317帧；929检查 | 变化/错误0；被杀者每轮已收到>5帧，剩余PTS跨度9.69—9.83秒 |
| 000059 | 双GStreamer | 328/328帧；643检查 | 变化/错误0，两端PTS递增 |
| 000060 | 原生pw_stream＋GStreamer | 316/316帧；624检查 | 变化/错误0，跨框架共用通过 |
| 000061 | 四次开关，快/保留交替 | 334/216/331/219帧；419检查 | 变化/错误0，首次打开后FD保持64 |
| 000062 | 全池持有1.2秒 | 96帧；88检查 | 释放后恢复，变化/错误0 |
| 000063 | 长持有时另一方退出 | 40/104帧；136检查 | 变化/错误0 |

共3693次保留检查无内容或PTS变化。正常退出/崩溃三轮的FD为60→64→64→64；这只证明所测窗口内没有逐轮增长。原始运行收据为 `run-6000057-validation.json` 至 `run-6000063-validation.json`；[正常退出流分析](flow-6000057-validation.json)。

原生测试使用公开 `pw_stream` API，并显式协商MemFd和Header元数据；它是验证客户端，不是要求实际应用采用的新协议。[线性时间戳测试源码](native-linear-probe.c)、[构建](native-linear-build-validation.json)。

## 原生APK部署与生产路径回归

APK使用原已信任项目密钥签名，未增加信任密钥。只替换两个包的指定库，核心包另外42个常规文件及1个符号链接保持；SPA新增严格依赖 `pipewire-libs=1.6.9-r2`。原依赖、provides与license保留。[打包/ABI核验](package-build-validation.json)、[安装模拟](package-simulation-validation.json)、[实际安装及回退模拟](package-install-validation.json)

只有这两个APK数据库记录发生变化，包数仍961；APK自动添加两条checksum world约束。原可信r0包在手机及PC保留，成对降级模拟成功。不要只降级其中一个库，也不能恢复263中已失败的旧候选。

ABI核对未缺少核心动态导出或SPA工厂/函数入口。SPA缺少一个C++分配器RTTI对象 `_ZTISt19_Sp_make_shared_tag`，实际为 **GLOBAL OBJECT**，不是263笔记所称weak；它是偶然导出的标准库实现对象。保留差异记录，并结合工厂入口、依赖和实际实例化/取流/退出验证，不把严格符号集合差异直接等同公开SPA ABI损坏。

正常SIGTERM重启已核身份的桌面PW/WP，未强杀，Phosh保持原身份。最初使用旧测试器的6000070通过，但下一轮6000071在取流前出现媒体链 `EBUSY/-16`：旧测试器在长驻libcamera背后手动恢复媒体链接和格式，实际内核图与libcamera缓存的链接标志不一致。保留失败收据：[失败](system-6000071-validation.json)。

随后修正生产测试器：**由libcamera正常释放相机，不再外部写回媒体图/格式/AE控件**，观测它实际控制的状态。只在这次旧测试器破坏缓存后正常刷新一次WP重新枚举；这不是每次关闭重启服务的方案。[刷新记录](policy-refresh-validation.json)、[生产测试器](native-system-natural.py)

以下五轮和随后真实GUI使用同一个PipeWire PID29640/start4321604、WirePlumber PID30425/start4360372。默认pipewire-0、系统库映射，无私有remote/配置/插件路径或复制开关：

| 系统mode | 场景 | 帧数 | 保留检查 |
| --- | --- | --- | --- |
| 6000080 | 20秒默认共享取流 | 643 | 635 |
| 6000081 | 一方正常退出 | 152/404 | 542 |
| 6000082 | 一方崩溃 | 剩余511 | 503 |
| 6000083 | 原生pw_stream＋GStreamer | 308/306 | 608 |
| 6000084 | camerabin标准拍照 | 424 | 416 |

共2704次保留检查，内容/PTS变化及回收错误均0，PTS严格递增；每轮正常恢复PM/MCLK、无新增故障。6000084实际收到image-done，保存677358字节JPEG。[80](system-6000080-validation.json)、[81](system-6000081-validation.json)、[82](system-6000082-validation.json)、[83](system-6000083-validation.json)、[84实际拍照](system-6000084-validation.json)

## Snapshot实际窗口及快门

两份用户启动覆盖仅移除 `SAMURAI_CAMERA_COPY=1`，Cairo/GDK既有显示设置保持，D-Bus ReloadConfig通过；应用二进制未修改。[启动项变更](launcher-update-validation.json)、[实际文件](../../linux-port/camera/snapshot-launcher/org.gnome.Snapshot.desktop)

使用实际新桌面启动命令创建窗口，通过AT-SPI再次核对拥有者PID、窗口名及 `win.take-picture` 动作后触发快门。实际新JPEG **1759945字节、1920×1080**，私有导出SHA256与原件一致，Pillow完整解码成功。随后发送应用正常quit，退出码0，无强杀或超时。[GUI与快门](snapshot-gui-validation.json)、[解码](snapshot-photo-0-validation.json)

日志包含2254个新缓冲、2246次sink render，源PTS持续递增跨 **38.984785秒**，回收错误及paintable bus错误均0。没有新的GPU FD、内核或GPU故障。[预览流核验](snapshot-flow-validation.json)。这是实际窗口渲染和快门验收；无人工屏幕观感确认，不代替光学画质验收。截图、照片与私人场景文件不进入公开镜像。

## 失败候选及验收边界

- 仅实际源触发重协商的6000041：无覆盖但剩余客户端停止，失败。[收据](run-6000041-validation.json)
- 仅代理触发但未完整重置IO的6000047正常退出通过，6000048崩溃出现1次变化/1次回收错误及PTS下溢，失败。[正常退出](run-6000047-validation.json)、[崩溃失败](run-6000048-validation.json)
- 6000053原生诊断未显式协商Header/可映射内存，重协商后276个错误，不构成有效成功或故障根因证明。修正测试器后的6000054通过。[无效诊断](run-6000053-validation.json)、[修正后](run-6000054-validation.json)
- SPA输出IO重置、尚无核心绑定重置的6000055/56各自通过；观测到重启前IO为NEED_DATA/INVALID，未直接抓到旧HAVE_DATA。因此单次通过不能证明某条陈旧描述恰为全部故障原因。最终组合使用核心绑定时与SPA启动时两处明确重置，并重新跑上表。[55](run-6000055-validation.json)、[56](run-6000056-validation.json)
- 263的Busy记账清零方案仍明确否决；不能恢复到该工作树的SPA文件进行打包。

## 源码配方、证据与下一步

[完整公共配方](../../linux-port/packages/pipewire-common/README.md)基于固定Alpine提交，保留官方配方/辅助文件，追加4个项目补丁。已核验精确源tar、10项SHA512、官方recipe SHA256；官方systemd补丁＋4个项目补丁对原始tar无fuzz应用成功，得到与已编译部署核心/SPA一致的源码。[配方准备核验](recipe-prepare-validation.json)

本轮实际APK由隔离ARM64 SDK增量源码编译后装入原可信包的保留载荷生成，**没有执行完整abuild全子包重建**。完整源构建、全新rootfs、跨启动与更长稳定性仍待后续，不能把配方应用通过写成完整构建通过。

[最终健康](final-health-validation.json)：已安装公共库/启动项/49项框架验证，961包，25个有状态上下文均终态，PM休眠/MCLK关闭/图案和翻转0/trace移除，本轮新增WARN/Oops/GPU/fatal/蓝牙重组故障均0、taint0。健康脚本首次把上下文数误写24，读阶段断言失败；核实实际25后修正并复查，没有重复安装或重启。[私人证据归档](evidence-validation.json)逐成员SHA256核验；原包、二进制、日志、快门图片在 `E:/edk2-samurai-out/kernel264`，不公开。

下一步继续IMX319近黑、曝光/增益/裁剪及前后摄切换，随后S5K3M5/GW1等其余后摄、画质/录像/长稳；Snapshot默认Vulkan历史480条fault及GPU ISP退出IOMMU告警仍单独待修。本轮未修改锁屏设置；验证时screensaver GetActive已为false。无需为了此轮相机测试永久关闭锁屏。目标仍active。
