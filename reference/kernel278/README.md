# 278：标准单次自动对焦、不可变帧统计与镜头回执

2026-10-18。完整多摄及骁龙 ISP 目标保持 active。**GW1 已通过原生 libcamera 的单次触发 AF，包含取消、重触发和自动曝光下搜索；连续 AF、手动距离标定、完整画质、GUI/录像及 Spectra 硬件成像仍未完成。** [277统计基础](../kernel277/README.md)、[276镜头/CCI](../kernel276/README.md)

## 实际部署与层次

手机仍 boot276/Image183、`7.3.0-rc6-rmx1931-samurai-k132+`，776模块/961包；libcamera五组件 `99990.7.2-r24`，config/stack `0.1.0-r19`，PW/SPA/Gst 1.6.9-r3保持。本阶段未刷写、重启、卸载/替换驱动、修改设备树或停启DSP。Phoc3586/Phosh3803保持，PW13112/WP13115正常重启并加载匹配系统库。[七包原生事务](package-install-validation.json)

| 层 | 本阶段内容 |
| --- | --- |
| SoC／主线内核／板级 | 沿用276的CAMSS、CCI、lens与DT，全部776模块保持，无新增Spectra功能 |
| 通用libcamera设备层 | 按V4L2返回的标志为每个buffer记录是否使用CLOCK_MONOTONIC；不猜测未知时钟 |
| 通用软件ISP／IPA传输 | FocusFoM在生产者拥有该帧时计算，随frame作为标量穿过工作线程和IPA接口，不异步重读共享focus结构 |
| 通用镜头控制 | Simple通过CameraLens标准V4L2控制发送位置，串号回执包含结果与命令完成的单调时钟时间；停流前关闭操作入口，拒绝晚到命令 |
| libipa／Simple AF | 可复用的有界粗扫、细扫、返回所选位置复验；标准AfModeAuto、AfTriggerStart/Cancel、AfState |
| 设备调校数据包 | 只为已匹配的GW1＋lc898219xi提供起始搜索参数和行程；没有把地址/机型/场景写入控制器 |

[完整0028补丁](0028-simple-contrast-autofocus.patch)、[实际AF引擎](contrast_af.h)、[设备数据](s5kgw1.yaml)。内核维护树仍为`samurai-cci-io276`／`0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，未推送；下游代码不等于上游接收。Image183未整体重编，最新完整统一内核/rootfs仍未部署。

## 时序、控制语义与调校边界

AF只消费有明确单调时钟的捕获时间；镜头命令失败或时钟不明时不盲目继续。按回执完成时间、调校settle时间以及曝光＋帧读出预算排除过早采样；相同/倒序采样不能重复计数。CAMSS当前时间戳可来自WM-done，不能当成曝光开始时刻直接等待。其它IPA算法仍沿用原有共享统计路径，本次没有声称全面重构全部异步统计。

搜索时每点取三份有效统计的中值，先全行程粗扫，再局部细扫，最后重新移动到所选位置并复验。低峰值、缺少相对峰值、复验下降、命令错误或总超时会失败，不能把走到行程端点记为Focused。扫描中重复Start忽略；Cancel仅取消正在进行的扫描，不另行移动镜头，已Focused/Failed时的Cancel不改状态。停止/取消后旧串号回执不能推进新搜索。

当前只声明Auto模式，启动后不主动扫描，等待Trigger；未伪造LensPosition的屈光度单位，也未声明Continuous。设备数据最低码208，最高码926是原厂初始码/区域行程提供的起点，并与驱动0…1023范围校验；步长、100ms稳定时间、阈值等是待继续优化的调校参数，**不是本模组EEPROM/距离标定结果**。不同供应商模组不能只凭GW1名称共用镜头参数。当前无独立可读actuator chip-ID/实际位置反馈证明。

## 构建、主机测试与保留失败

实际生产引擎C++17/Werror、ASan/UBSan通过：粗细扫/复验、扫描中重复触发、取消、取消后新串号、Focused/Failed时取消忽略、错误/迟到回执、过早/重复帧、低纹理、复验丢焦、超时、配置边界、无效/未来时钟均有用例。未在实机注入I2C或电源故障。[主机验证](af-engine-host-validation.json)

完整正常abuild构建13个签名包，保留既有27补丁和发行版功能；34个AArch64 ELF、五IPA签名、匹配新core/verifier、ARM工具/Qt/Python入口QA通过。原214工作区2254项恢复；r2构建保留r23缓存2276项，r3保留r2缓存2278项。r3完整补丁另从原r23源重现，再用两文件增量完成最终正常打包。[最终构建](r24-package-build-validation.json)、[源重现](r3-source-reproduction-validation.json)、[完整QA](complete-host-qa-validation.json)

保留失败及修正：首轮const CameraSensor调用非const镜头访问器编译失败，SDK已恢复，改为构造边界显式传lens；r2准备脚本误改旧manifest读取名，在移动工作区之前失败并修正。r2完整构建通过但未部署；发现取消已完成扫描的语义需纠正，r3改两文件并重建。探针初次生成断言发生于编译之前。旧r23负对照已成功返回AF控制不存在；末尾APK CLI描述被误当版本导致断言，读取实际installed数据库补验，没有重复启动探针。[负对照](negative-support-validation.json)

## 原生实机AF验收

应用探针仅发送标准libcamera控制，不实现搜索、不直接写lens或原始I2C。并行配置RAW4608×3456／RGB2048×1536，同请求序号/时间戳一致，并从RAW独立重算每个已报告FoM；所有预期的每四帧快照均到达且完全一致。root测试器仅在会话结束后读缓存控制值，它不是硬件位置反馈。

| 场景 | 配对帧 | 结果 |
| --- | ---: | --- |
| 无触发 | 48 | 全Idle，零AF位置命令 |
| 单次搜索 | 293 | Idle→Scanning→Focused，17次命令，选择256；末段FoM中位4355 |
| 扫描中取消 | 72 | Scanning→Idle，后续保持Idle |
| 取消后重新触发 | 441 | 取消后Idle，第二次搜索Focused，选择272；末段FoM4121 |
| 扫描中停流 | 36 | 正常停止，无强杀，资源回收 |
| 自动曝光/增益 | 389 | Focused，23次命令，选择320；增益1…4.71875，末段FoM12297 |

固定曝光场景使用31999us/1倍增益。扫描中的重复Start没有重置粗扫序列；到Focused后再发Cancel仍保持Focused。最后复验帧时间晚于最后位置命令及稳定/曝光预算。自动曝光场景曝光33215us，增益参与调节；不同曝光/增益下FoM数值不能直接用于宣称画质提升。[五场景](native-af-r1-validation.json)、[自动曝光AF](ae-af-r1-validation.json)

配对测量中，首次扫描到Focused约9.05秒，自动曝光下约12.24秒，仍需加速。取消再触发记录13.97秒包含前一段被取消扫描与空闲等待，不能当作纯第二次扫描时长。这是带RAW独立重算的测量路径，不是无探针普通应用的性能验收。[时序](af-timing-validation.json)

随后保持所选缓存位置320，经普通原生libcamerasrc重新开流取得私人JPEG；预览没有新的AF位置命令，能辨认场景和窗帘纹理，边缘扩散代理约8.75px。噪声、颜色及整体偏软仍可见，**该JPEG与AF结果是不同会话，不是假称同request画质/距离标定验收**。[预览](af-selected-preview-validation.json)、[离线查看](af-selected-preview-optical-analysis.json)

## 最终状态、回退与下一步

新旧七包签名/原生升级/精确降级模拟通过；50载荷复核，其余954包记录与全部776模块保持，十个相关加载模块note匹配。精确旧r23/r18七包回退在手机/PC双份，2533478字节，SHA `f90a2ba7695c1a0364e6b27e217c91f28c6022508b77243530d7167bab07f570`，未实际往返。[回退](rollback-validation.json)

前摄＋三后摄18段232帧交替通过，含主摄SIGINT正常退出28帧与重开，无强杀，回归期无服务重启。最终四sensor/lens/双CCI/CAMSS休眠，九rails与共享I/O OFF/users0、四MCLK/双CCI clocks0；fault0/taint0、CCI错误无、pstore空。SSC/SensorProxy/greetd正常、三DSP运行；物理旋转未重测，旧273 EPERM根因未证明修复，GPU默认故障/Cairo CPU回退及旧modem watchdog仍开放。[四摄](four-camera-regression-validation.json)、[最终核对](final-health-validation.json)

实际r24/r19配方/锁已提升，旧r23/277锁已归档。续作用`reference/kernel278/host.py`，仍核`/var/lib/samurai/k276-work/boot-id-private.txt`；服务身份`/var/lib/samurai/k278-services-verified-private.json`，没有k278启动guard。私人像素/日志/回退在`E:/edk2-samurai-out/kernel278`。所有本轮构建、包事务和采集均终态。[提升](source-promotion-validation.json)

继续AF速度/更多场景、连续模式与手动距离标定，四摄GUI/录像及黑电平/颜色/阴影/噪声调校。273严格手动曝光矩阵失败、274两次通过但根因未明，r24完整矩阵仍未重测；其它镜头与第四枚物理后摄仍待接入/确认。Spectra仍是RAW RDI→CPU ISP：公共硬件PIX/统计、参数接口、pipeline/IPA尚需实现，不能以本次软件AF代替。[ISP分层](../kernel274/ISP-ADAPTATION.md)、[原厂资料](../kernel276/OEM-TUNING.md)
