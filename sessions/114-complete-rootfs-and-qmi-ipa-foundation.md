# 阶段114：完整用户态 rootfs 镜像、原生 QMI/LOC 与 IPA 源码候选

2026-10-12。用户重新要求持续适配，采用无人值守自动调试、互联网/源码研究；长时间无进展问题记录后切换。完整系统目标仍 active，不要求人工画面、触摸、转动、遮挡或听音检查。

已生成新的本机专用 postmarketOS/Nura edge F2FS sparse rootfs：**1,783,174,616 字节**，展开后 **119,033,245,696 字节**，936 个软件包。私有文件 `E:/edk2-samurai-out/kernel114/samurai-rootfs-f2fs.simg`，SHA-256 `37d0ccd221e857465da303b249d5bff09e9e0a2c93a7c7f5cd9c7d24c9bc3f52`。13,254 个已安装系统/配置文件在导出前后及离线导入后核验；加入软件包后的 SSH 配置、schema、启动脚本、关键服务链接与固件服务工具通过离线检查。sparse 数据逐块与源 raw 比较，跳过范围确认为源文件空洞，重建 raw；源与重建文件的 F2FS fsck 均通过。最后 coreutils 哈希发生内存分配失败，已用 4 MiB 有界 Python 读块计算并独立匹配 sparse 校验 SHA，不重做已通过的文件系统测试。见[镜像核验](../reference/kernel114/rootfs-image-validation.json)。

镜像包含现有 Phosh/Phoc、原生 UCM、USB SSH、无线及同机只读固件/RAM COW 服务，并补入 Calls、Chatty、Firefox/mobile-config-firefox、Megapixels、libcamera-tools、qmi-utils、rsync、strace。导出排除运行挂载、诊断目录及用户缓存/日志，不是正在运行文件系统的完整块级快照。镜像保留本机启动身份与凭据，仅用于私有本机；沿用 #113 内核配套模块和启动检查。它**已经构建，但没有刷入 userdata**。

同样的应用和工具已通过签名 APK 安装到当前手机的持久 F2FS：936 包，原 Phosh launcher/greetd/UCM 4 文件哈希保持，Phosh/Phoc 存在，PCM 两项 closed、双功放 powered=0/muted=1，NV6/source4 保持。安装窗口新增 DPU 超时0/GPU故障0，仍是 #113/boot15、taint512。没有 erase、刷机、重启或启动应用做画面验收。[实机用户态核验](../reference/kernel114/live-userspace-validation.json)保留。

原生 qmicli 的 DMS capabilities/operating-mode、UIM card-status、NAS system-info 四项只读请求均退出0，确认 QRTR modem 控制通道可用；ModemManager 仍未枚举 modem，主机端没有蜂窝 netdev。第一条 LOC 请求用了不存在的 CLI 选项，其失败发生在工具解析阶段，不能认作 modem/定位协议故障。改用 loc-get-operation-mode/engine-lock/nmea-types 后三项均成功。[QMI核验](../reference/kernel114/qmi-readonly-validation.json)、[LOC核验](../reference/kernel114/loc-readonly-validation.json)。

进一步以独立 session114 发送 LOC start，55秒有界监听 position/SV/NMEA，然后 LOC stop；start/stop 均明确成功，监听只产生取消提示，未取得定位、卫星或NMEA事件。return0 不是定位成功；已得到 stop 回执，NV6/source4与SLPI offline/供电0保持。记录这一短窗口后转到其它项，不要求用户移到室外。[窗口核验](../reference/kernel114/gnss-window-validation.json)。

互联网研究找到[同为 SM8150 的 Hotdog 项目](https://github.com/Sr-0w/hotdog-linux-bringup)，固定源码提交 `47087509c4289c2580c54f5433e55366b2e00445`，保存29份相关源码/补丁及逐文件SHA。其 IPA v4.1 平台、寄存器和 binding 补丁提供可研究实现。原 #113 配置已有 QCOM_IPA/RMNET，但主线驱动没有 SM8150 数据/匹配表，SoC DTS 无 IPA 节点。本机 Realme 下游 sm8150.dtsi 同样明确 IPA v4.1、寄存器与两项 IRQ；不是再打开 CONFIG_QCOM_IPA 就能解决。ModemManager 的无 netdev 根因仍需本机 daemon 日志闭环，不能单凭另一个设备的记录替代本机证据。[ModemManager 官方源码](https://github.com/linux-mobile-broadband/ModemManager)。

隔离的 `/home/cy122/pmos-samurai-kernel114/{kernel,initramfs}` 已移植共享 IPA 驱动和禁用状态 SoC 节点，排除 Hotdog 板级启用/固件路径，保留新内核已有5.2数据。同时准备 ZSMALLOC/ZRAM 与 SYN_COOKIES 配置，处理当前 zram 缺驱动、sysctl缺项。首次定向模块构建因新增 zsmalloc 未生成符号表而失败；首次完整构建 DTB 目标写成完整路径而失败，已更正为 `qcom/sm8150-samurai.dtb`。完整Image/全部modules/DTB构建通过；ZRAM和ZSMALLOC均为模块，SYN_COOKIES启用。离线核验曾把ZSMALLOC误假定为builtin、把两条banner误假定为唯一条，已按实际配置和完整UTS_VERSION筛选修正核验，没有为此重编。见[构建核验](../reference/kernel114/kernel-build-validation.json)。未部署。运行系统仍#113，不能说#114已经上机。

OpenRC 还发现 zram 的 `provide swap` 与真实 swap 服务同名冲突；elogind 有活动 DBus daemon 但 OpenRC failed、iio-sensor-proxy 缺 SSC 的 failed 状态保留。未为消除状态而停止活动登录会话，也不把关闭服务当成硬件修复。

接下来：核对同机 IPA IMEM/时钟、固件来源/loader mode及 SSR 有界等待，再设计#113当前 taint512 的安全正常重启/刷机守卫。显示/GPU稳定、传感器完整性、蜂窝数据/通话、GNSS定位、摄像头、指纹、充电控制、OTG、休眠等仍未完成。15组硬件清单保留。

原始日志、固件、APK缓存、系统与个人身份、定位输出、镜像全部留在私有输出，公共目录只留脚本/核验摘要；没有提交、推送或公开。


## GNSS 同一客户端闭环

确认目标已有Qmi/Qrtr GI后，编写单LOC客户端流程：发现QRTR0、open EXPECT_INDICATIONS、注册事件、periodic start、55秒监听、同客户端stop。v1在start前因未实现fix-session-state信号退出；v2在start前因PERIODIC枚举名错误退出，均保留档案/补充stop请求。GI的get_result在成功时返回None而在失败时抛异常，不能用bool(None)判失败。v3使用PERIODIC_FIXES及正确GI结果处理。

v3注册/start/stop都通过、Python错误0；收到engine-state1、position-report55、NMEA55、gnss-sv-info54。55个position-report状态均IN_PROGRESS，没有有效位置fix。这个闭环证明真实连续事件通道可以使用，也表明先前分进程CLI无事件不足以判断硬件不工作；GNSS实际定位与桌面集成仍未完成。NV6/source4保持，session117停止回执取得。[同客户端核验](../reference/kernel114/gnss-single-client-validation.json)。不因室内短窗口未fix要求用户人工搬动手机，也不反复等待，继续IPA/其它项。

参考IPA DTS的0x1e40000/0x1e47000与本机下游ipa-base 0x1e00000/0x34000存在待解释地址转换差异，列为下一项资源审查，不因离线编译成功直接启用。最终[健康核验](../reference/kernel114/final-health-validation.json)及[聚合核验](../reference/kernel114/checkpoint-validation.json)通过：同boot/taint、无新增DPU/GPU故障、trace关闭、PCM closed/双功放静音、Phosh/Phoc存在、SLPI offline/供电0、NV6/source4保持，没有遗留QMI或构建进程。下一轮继续完整系统目标。
