# 268：公共相机切换修复与前后摄应用实测

后续[269收尾](../kernel269/README.md)：已完整构建新Image/773模块但未部署，并修复板级整屏旋转。用户打开Snapshot发生意外重启，末尾modem watchdog，稳定性原因未明；原267/268启动guard和PID已失效，现用269guard。下文GUI通过与最终健康只对应268原启动，不覆盖新故障。

2026-10-18。沿主线 Linux＋SM8150 公共支持＋RMX1931 设备树方向继续收敛。[267](../kernel267/README.md)已把双 PM8008 供电及 IMX319 接入公共驱动和设备树。本阶段修复跨进程使用时公共 libcamera 的链路状态缓存问题，原生安装 r19/r14，并在手机完成未改 Snapshot 的前后摄预览、界面切换和拍照。**当前阶段通过不代表完整摄像头画质、所有镜头或整机适配完成。**

## 修复所在层次

`SimpleCameraData::setupLinks()`原先根据本进程缓存的 ENABLED 位决定是否发送 MC link ioctl。标准 cam 改变图后，长期运行的 PipeWire 内仍保留旧值，切换到另一传感器可能跳过冲突链路禁用，最终 EBUSY。现在对可变冲突链路发送幂等 disable，对目标链路发送 enable；不可变链路、路由限制和 ioctl 错误仍保留。没有加入机型、应用名或外部 media-ctl 恢复逻辑。[补丁](0023-simple-link-state-after-external-client.patch)、[源码锁](source-validation.json)。

实际方法提取后完成 70 个 ASan/UBSan 案例，缓存与内核状态独立变化，错误传播和旧源码负对照通过。这是函数模型，不是内核并发验证。[模型](link-test-validation.json)。

以完整 r15 构建树为基础，保留既有 22 补丁、调校文件、auto/virtual 管线、Qt/Python/GStreamer/V4L2 和五个 IPA。通过原生 abuild build/rootpkg/index 构建 13 个签名包；SDK 原目录 2254 项与原缓存 2270 项恢复/保持。签名、34 个 AArch64 ELF、五个 IPA 签名、cam/lc-compliance/qcam 帮助及 Python 导入通过。[构建](r19-package-build-validation.json)、[完整功能](r19-full-feature-configuration-validation.json)、[运行 QA](r19-host-runtime-qa-validation.json)。这是使用已构建完整源码树的构建，未声称全新解包 SDK 或完整 rootfs 重建。

系统只升级五个 libcamera 组件至 `99990.7.2-r19`、config/stack 至 `0.1.0-r14`，仍 961 包，其余 954 个记录不变。49 项载荷的内容、符号链接和模式均核对。CPU ISP/system heap、已有公共 PipeWire/SPA/GStreamer `1.6.9-r3` 保持。[原生事务](native-install-validation.json)。当前公开构建入口为 [libcamera 配方](../../linux-port/packages/libcamera/APKBUILD)与[配置配方](../../linux-port/packages/samurai-camera-config/APKBUILD)。

## 手机验证

| 路径 | 实际结果 |
| --- | --- |
| 标准 cam 与常驻 PipeWire 交替 | 三次各 12 帧，共 36 帧；同一组服务跨进程切换，无需逐次重启 |
| GStreamer camerabin / pipewiresrc | 后、前、后三轮共 1097 帧，1081 次保留缓冲检查、9 次 JPEG；PTS 递增、内容变化和回收错误均零 |
| Snapshot r3 | 前摄窗口 847 缓冲/835 渲染，界面快门取得 1920×1080 JPEG |
| Snapshot r5 | 从桌面激活同一窗口，前摄快门→实际“Switch Camera”按钮→后摄预览和快门；应用与控制器均 exit0 |
| JPEG 解码 | 三张 GUI 照片全部成功解码；前摄两张 1920×1080，后摄一张 1600×900 |

证据：[原生交替](native-switch-1-validation.json)、[三轮预览](camera-16-validation.json)、[前摄](camera-17-validation.json)、[后摄](camera-18-validation.json)、[GUI 前后切换](snapshot-gui-r5-validation.json)、[JPEG 解码](gui-jpeg-decode-validation.json)。缓冲检查限定每帧前 65536 字节，不是整帧内容不变证明；照片可解码不等于色彩、噪声、对焦和光学正确。场景照片及原日志仅在私人目录保存，不发布像素。

GUI r1/r2受锁屏或窗口未置前影响，不能记作相机成功。r3只扫到深度20，遗漏深层切换控件；应用日志已识别双摄。r4在启动应用前因屏保 active 被守卫拒绝，没有拍照。正常会话使用 Phosh 支持的 `--unlocked` 测试启动并暂时关闭自动锁屏后，r5扫描至深度64找到真实按钮，前后摄验证通过；没有改应用。原启动覆盖、锁屏及 idle 设置均已恢复，当前会话未再次重启。[会话清理](session-cleanup-validation.json)。

Snapshot沿用此前的 Cairo/禁用 GL、Vulkan、offload 启动配置，签名应用文件未改。本次证明相机公共接口和该 CPU 显示路径可用，**默认 GPU 路径仍未修复**。图、格式和自动曝光状态由 libcamera 正常管理，关闭后未用外部 media 写回旧状态；因此前后格式/图/控制值不要求逐字回到捕获前。电源、PM 和时钟恢复单独验证。

## 内核维护分支与可复现范围

本地维护分支已同步实际部署的 PM8008、IMX319、IMX471、CAMSS、绑定和板级树，共 14 个输入文件。基于既有主线祖先 `a90ee4305c4a5df72c11b31dacfdc76e00fcf78a`，沿用已有 Kconfig/Makefile，不加入 lab 或板级 reset 模块。[源码核对](maintained-source-validation.json)、[本地内核提交 db301b64c](kernel-commit-validation.json)。Git推送连接停滞/超时，已退出相关本地进程；GitHub API复查远端仍为04d4d4f9，本地提交尚未发布。[实际远端状态](kernel-publication-status.json)。这些仍是本地驱动扩展，未声称已经上游接收。

在全源码维护树的新输出目录编译五个相机目标，W=1相机编译无诊断；外部导入符号在当前 Image183 的导出清单内。生成 DTB 的 SHA256 为 `9a2307c0d93b4ad6d5b23c570a0c84a116a930d0de6b3370d5737eb0bac768c5`，与实际 boot267 逐字一致。DTC 的两条地址单元警告位于未改的 SM8150 显示和 PM8150B 节点。[独立编译](maintained-build-validation.json)。

第一轮在没有完整 `vmlinux.o` 的新输出目录请求 `.ko`，modpost正确拒绝未解析符号；失败目录保留，没有关闭检查或部署其产物。第二轮明确只验证 `.o` 与 DTB，检查器也修正了生成 `.mod.c` 才提供的 `__this_module` 符号分类。手机实际模块仍为267/219/237各自已编译和实测的版本，Image183保持。**尚未完成新完整 Image、全部模块及 rootfs 构建。** 寄存器表保留原末尾空行，提交中记录一条既有 EOF 样式提示，源输入未被悄悄修改。

## 当前权威状态与回退

boot267/Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，guard 为 `/var/lib/samurai/k267-work/boot-id-private.txt`；运输仍用267严格原密钥和私人新 USB IPv6端点。本阶段升级库没有再刷写分区或重启内核。当前普通会话 PW16218/start341625、WP16224/start341628、Phosh15483，服务身份权威为手机 `k268-services-current-private.json`，此前267及更新中手动服务PID都属历史。[服务](services-current-validation.json)。

最终再核对：773个ko、全部五个加载模块 note 与磁盘匹配、49项包载荷匹配、无实验模块/参数/reset节点或旧 loader 配置；四rails OFF/users0、双sensor/CCI/CAMSS suspended、MCLK1/2关，新增 WARN/Oops/GPU/fatal/BT错误零、taint0、无存活 Snapshot。[最终健康](final-health-validation.json)。

原 r15/r10 七个签名包、事务前 world/repos/db 均保留，七包联合降级模拟通过。PC原包/预检归档2493300字节，SHA256 `f99a8698476eec1f3fbc6afe63480d8aff5b5238c4e876d21856d46b8288d105`。[回退记录](rollback-validation.json)。内核267的旧模块20文件归档、boot235与完整切换收据继续保留，按当前设备状态评估回退，不重放已执行事务。

后摄低照度/色彩、真实方向校准、其它后摄、录像、默认 GPU、长稳和完整 Image/rootfs 仍开放。用户延期的纯色测试不作为推进其它工作的前置条件。私人证据位于 `E:/edk2-samurai-out/kernel268` 和手机相应k268目录。
