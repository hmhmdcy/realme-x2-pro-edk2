# 273：GW1 主摄实机接入、四摄取流与未完成项

2026-10-18。本轮取得实机进展：**GW1 主摄已通过 chip-ID、C-PHY RAW/RGB 采集及真实场景 JPEG，当前前摄一颗、后摄三颗均可原生取流。** 四摄交替回归通过。完整控制切换验证、AF、画质、四摄 GUI/录像、Spectra 硬件成像处理仍未完成；新启动 SSC 失败使自动旋转不可用，桌面仅临时恢复。目标保持 active，不能按完整手机相机验收。

## 当前部署与回退

- boot273/Image183，release `7.3.0-rc6-rmx1931-samurai-k132+`；775 个模块、961 个包。新增 GW1 ko SHA256 `0c907b122065b8657dc9f9e68ff17784c5419ed1994fe9f1ced5ccfa60c90ade`，原 774 个模块逐字保持。八个相机模块加载 build note 与磁盘一致。
- libcamera 五组件 `99990.7.2-r21`，config/stack `0.1.0-r16`；PW/SPA/Gst 仍 1.6.9-r3。原其它 954 个包记录保持。当前 49 项相机包载荷重新读回通过；GW1 helper 对应原生码 32…1024，S5K3M5 原生 32…512/helper 配套仍保留。
- 本次只刷 boot：SHA256 `dd4c34e4f18a4292cb70dd9b3d87ad710ce4f6e4e4048fe85c7b94eee911d475`，DTB `615f7523df579313f514d0dfa809fcde96355a419ad24dbb62b1eaa60955d252`。Image183 与 logdump 未写；固件比对确认只改变内嵌设备树，bootshim、其它固件代码、ramdisk、兼容 DT、分区尾部保持。[构建](build-package-validation.json)、[实际刷写](flash-validation.json)、[新启动与读回](postboot-identity-validation.json)。
- 运输必须改用本目录 [host.py](host.py)，严格原主机密钥及新 USB 接口已核对；手机 guard 为 `/var/lib/samurai/k273-work/boot-id-private.txt`。旧 270/271/272 guard 属于旧启动，不能用于当前操作。
- 当前 Phoc4610/start66605、Phosh4682/start66754、PW6088/start67241、WP6095/start67244；手机 `/var/lib/samurai/k273-services-current-private.json`。这些身份也需续作重核。
- 匹配的 boot270、原 r20/r15 七个签名包、原模块依赖文件和配置/数据库备份已保留手机与 PC 两份，回退归档 26116631 字节、SHA256 `209908a882a9508b49adc6b7eed3cf1f4fc726ae0a8d4da4b745a32217aabeac`。[回退](rollback-validation.json)。只验证原包验签及七包原生降级模拟，没有实际刷回往返；回退应匹配 boot270/r20/r15，保留现有 S5K3M5 原生增益驱动/helper 对。

## 实际接入和构建范围

[272](../kernel272/README.md) 的标准 GW1 驱动、静态板级 DTS/binding 本轮已经部署。内核树 `/home/cy122/x2pro-linux/camera270-kernel`，分支 `samurai-main-camera272`，提交 `3184c56b7f206ab000ab79bc99eb83d35c3e1d65`，本轮未改内核源码、未推送；不代表上游接收。现机 Image 仍旧183，GW1模块按其 ABI 匹配构建。269完整 Image/模块候选尚未部署，完整最新 rootfs 未重建。

r21 在保留 r20 源/对象上应用第25个 GW1 helper 补丁，通过正常 abuild build/rootpkg/index 构建13个完整功能签名 APK；不是全新 SDK 解包或完整 rootfs 构建。原214工作目录2254个文件/链接/模式恢复，r20缓存2272项保持。[构建](r21-package-build-validation.json)、[完整 QA](complete-host-qa-validation.json)、[实际构建 helper 的993码和旧r20负向对照](built-helper-validation.json)。

boot273固件构建确认只增加11个主摄资源/CSI节点并启用 CCI0 master0，既有相机与其它外设属性保持。固件原有30条诊断模板无新增；不是全固件零告警。现机在 `s5kgw1 6-0010` 读取真实 ID 后绑定，libcamera 原生枚举 IMX471/GW1/IMX319/S5K3M5。[绑定、八模块和枚举](postboot-hardware-validation.json)。

旧 r20/r15 配方、产品部署/源码锁及检查点归档于 `archive/camera-before273-2026-10-18`。当前 Windows 产品配方和锁已按真实部署更新，[晋升收据](source-promotion-validation.json)、[现机读回锁](current-lock-validation.json)。公开 pmaports 分支未在本轮同步/发布。

## 图像与控制验证

| 验证 | 事实与限制 |
| --- | --- |
| 标准 cam 主摄 | RAW 和 CPU RGB 各12帧完整通过，序号递增，退出后四 sensor/九 rails 回收。RAW默认选择4608×2592，RGB默认4600×3456；不能将两个输出尺寸当成同一帧配对。[记录](main-capture-validation.json) |
| 普通 libcamerasrc | CPU JPEG 1280×960连续600帧，PTS跨度19.92985秒，36/180/600帧私下留样。36和600帧均可辨认真实场景，600更明亮；整体虚焦、颜色/噪声/方向仍未校准，不归因为已完成 AF 或原厂画质。[采集](main-ae-validation.json)、[核看与分析](main-evidence-analysis.json) |
| 同request RAW/RGB | RAW4608×3456＋RGB2048×1536取得66组完整配对，序号/时间戳匹配；2ms/8ms/32ms与1/1.5/2倍已观察物理响应。原计划96组，切换4倍阶段时元数据未在规定窗口匹配，程序报错并正常停流，**该完整测试失败**。[失败记录](main-manual-r1-validation.json) |
| 默认模式时序 | 以上66组按相邻传感器序号差归一，周期中位数33.27225ms，约30.05508fps；反推阵列速率约1.91995GHz，与1.92GHz候选相符。直接交付间隔中位数约133ms来自全帧统计 probe 的负载/跳序，不能说sensor仅7.5fps。只覆盖默认FLL模式2，未校准物理曝光延迟或所有时序。[分析](main-evidence-analysis.json) |
| 四摄交替 | 18段238帧，覆盖前摄和三颗后摄、主摄 SIGINT正常退出和重开，无强杀、期间未重启服务。不能扩称四摄同时并发、GUI选择或录像通过。[回归](four-camera-regression-validation.json) |

完整控制测试失败时，旧阶段第60…65个已交付请求仍报告2倍；停止后标准控件缓存为gain code128，即4倍。此信息只提示继续检查控制应用/统计和元数据时序，**不能单独证明是哪一层错，也不能用放宽断言把原失败改成通过**。早期各档 RAW 均值依次约66.588、74.831、108.343、130.397、152.770，未把场景拟合当黑电平或ISO标定。诊断binary在 `/run/samurai-camera273-probes/main-control-probe273`，原测试上下文已经终态。

本轮 GW1 未添加或调用未验证的 test-pattern 控件；初始化/模式保持原厂数据，真实场景样片作为光学证据。原始图像、全帧直方图和环境只保留私人目录。

## 新启动的 SSC/桌面问题

默认启动时 SSC 已尝试一次：SLPI启动后文件服务退出4，日志为 `Could not attach to FastRPC node: Operation not permitted`；SSC已清理为 SLPI offline、sensor-power OFF，状态记录 attempted/started=false/stopped=true。FastRPC磁盘模块 SHA256 `2abde0ead81c2feb78f639da2ab29d7c3e29654a9d013a098418b232a5cfd794`，加载note与磁盘匹配；未发现当前内核 fatal/WARN。这不是正常 SSC 启动通过，也未证明由 GW1 或 r21 直接导致。

由于 greetd 依赖 SensorProxy，桌面当时未启动。已用一次 `rc-service --nodeps greetd start` 恢复正常 Phoc/Phosh/PW/WP；永久依赖配置逐字保持，没有重新尝试已失败的 SLPI attach。[临时恢复](desktop-restore-validation.json)。**当前自动旋转/SSC功能不可用，正常开机依赖链仍需修复。** 269的旧旋转通过不能代替本次启动结果。后续先保存当前SSC错误上下文、检查 attach错误来源与启动时序，不盲目清除 `/run/samurai-ssc/state.json` 反复重试已知尚未收敛的共享池停启。

## 部署中保留的失败与当前健康

安装七包实际成功，49载荷、961包及其它954记录均匹配；随后的降级模拟因误用了本机 apk 不支持的 `--allow-downgrades` 参数而中止。确认安装进程终止和已部署状态后，采用原生显式版本请求完成七包降级模拟；**没有重复安装**。原失败状态保留，独立 `packages-verified-state-private.json` 才用于重启检查。[安装后独立核验](packages-install-validation.json)。最早构建脚本替换规则多余断言发生在构建提交前，修正后才启动构建；控制probe第一次解析AST失败发生在实际采集提交前，既有上传binary按哈希核对后使用。

最终[相机健康](final-health-validation.json)：四 sensor/双CCI/CAMSS suspended，九rails disabled/users0，MCLK0…3关闭，无相机客户端，fault0/taint0、pstore空；775模块、961包、49载荷和WP正常系统库路径保持。**相机资源健康不等于 SSC/旋转健康，也不抹除旧 Snapshot/modem watchdog 故障。**

继续修复高分辨率控制切换/元数据问题与 SSC 默认启动，再推进 GW1/长焦 AF、模组校准、AE速度/画质、更多模式、四摄 GUI与录像及长稳。当前 Qualcomm CSIPHY/CSID/VFE RDI 已完成 C-PHY RAW 采集；成像仍 CPU software ISP，**Spectra硬件成像处理未接通**。默认GPU故障、完整统一 kernel/rootfs及上游接收继续开放。

私人产物在 `E:/edk2-samurai-out/kernel273` 和手机 `/var/lib/samurai/k273-*`。所有构建、切换、安装和采集上下文都已终态；续作使用当前身份和新事务，不重放已提交动作。
