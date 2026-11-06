# samurai-platform 5-r14

5-r14 从标准 ARM64 平台的依赖中移除 `samurai-charging`。Linux v7.3.1
使用 DTS `mps,mp2650` 绑定和内核 `power_supply` 类；历史充电实验包
继续存在，但只按显式 opt-in 使用，不再由板级元包自动带入。

5-r13 是 UDC 发现候选：优先保留 `a600000.usb`，缺失时接受唯一的
`/sys/class/udc/*`，也可用 `SAMURAI_UDC` 覆盖；`samurai-usb`、
sleep guard 和只读检查脚本使用同一规则。当前设备仍走原来的
`a600000.usb` 分支；此版本尚未构建、安装或实机验收。

5-r12 同时提供 `post-upgrade` 钩子，保证 OpenRC 在升级而非首次安装时也会
切换板级 sleep-inhibitor 的 runlevel 并清理旧 cgroup。

5-r11 把板级 sleep-inhibitor 的 runlevel 切换做成幂等操作，并清理旧
`openrc.sleep-inhibitor` cgroup 中可能遗留的插件子进程。板级服务使用
独立的 `openrc.samurai-sleep-inhibitor` cgroup，不会误杀当前的 USB
guard。

5-r10 不再安装上游 `sleep-inhibitor-openrc` 拥有的
`/etc/conf.d/sleep-inhibitor`。板级策略改由独立
`samurai-sleep-inhibitor` 服务选择 `/etc/samurai/sleep-inhibitor.conf`，
安装钩子先启动新实例，再停用发行版实例，避免 USB SSH 在线时出现睡眠锁
空窗。它也把旧 `/usr/local/sbin` USB init 的 `.apk-new` 收敛回包内
`/usr/sbin/samurai-usb` 路径。

5-r9 把 `samurai-charging` 设为板级依赖。充电模块、OpenRC 服务和
manifest 由独立 aarch64 包拥有，不再作为系统目录里的裸文件部署。
本版本同时把 `samurai-usb` 的 rootfs 实现和 init 路径收回到
`/usr/sbin`，移除对 `/usr/local/sbin` 临时覆盖的依赖。

本包现在是 `noarch`，只承载板级脚本、OpenRC/udev、NetworkManager、ALSA
UCM 和 USB NCM 等 Linux 公共接口，不安装 Phosh/Phoc 配置。桌面相关配置
应由对应桌面适配包维护，后续切换到其它 Wayland 桌面时无需先删除板级包
带来的旧桌面文件。

5-r6 把 PulseAudio 专用配置和依赖拆到可选子包
`samurai-platform-pulse`。板级主包仍提供 ALSA UCM 和
`samurai-audio-route`；Plasma Mobile 元包显式选择 PulseAudio 适配子包，
后续纯 PipeWire 桌面可选择自己的音频适配层。

5-r6 的 `samurai-usb` 已包含当前 rootfs 的 `MaxPower=500` 幂等处理；它不
替代充电长测。若设备正在进行充电/供电验证，安装前仍应先核对现场脚本和
当前测量状态，不要用一个未经验证的包覆盖正在使用的电源路径。

5-r5 把当前实机 rootfs 的 CDC NCM 修复回写到包载荷：USB gadget 串号
从主线 `/sys/devices/soc0/serial_number` 生成，保留 `MaxPower=500`
重枚举修复，并移除 initramfs 专用的 Dropbear/devpts 路径。包内 init
脚本继续使用发行版标准 `/usr/sbin/samurai-usb`，不再依赖现场
`/usr/local` 临时覆盖。

5-r7 增加 `/usr/libexec/samurai-usb-sleep-guard`。DWC3 在系统
suspend 时会撤掉 gadget pull-up，主机的 NCM 数据包无法把手机唤回，
所以不能把“USB 网卡仍显示 Up”当作链路可恢复。安装钩子通过发行版
已有的 `sleep-inhibitor` + `elogind-inhibit` 公共接口，在 UDC
configured 且 `usb0` carrier=1 时持有 sleep 锁；屏幕仍可由 KWin
DPMS 关闭，但系统不会在 USB SSH 可用的状态下进入 suspend。5-r8
修正 RTC 安全限位：检测到旧 wall-clock 域 alarm 时先清除活动 alarm，
再按 PMIC RTC 的 `since_epoch + 900` 重新布置；安装钩子先显式终止
USB guard 插件及其 `elogind-inhibit` 子进程，再用 OpenRC 的
`cgroup_cleanup` 清理剩余 worker 后启动唯一实例。5-r8 同时
安装 `/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service`
（`Exec=/bin/false`）：本机由 OpenRC 独占 ModemManager，禁止 Nura 的
标准 D-Bus 自动激活抢先拉起未管理实例；安装钩子会接管迁移前的旧进程。

5-r4 在现有 payload 上补齐 AW8697 的 feedbackd udev 规则，并增加安装钩子：
把 `modemmanager` 的 OpenRC 依赖设为 `samurai-radio`，移除旧脚本遗留的
临时 D-Bus 覆盖，然后重载输入 udev 规则。5-r8 不再把它当临时修补，
而是以包管理文件明确采用 OpenRC 单所有者策略。完整包仍包含 USB/充电
脚本源码快照；5-r9 起充电路径由 `samurai-charging` 包管理，安装前仍须
核对它的 manifest、模块 ABI 和当前充电状态。

5-r2仅把已有 `pulseaudio-bluez` 显式加入包依赖，源载荷保持5-r1不变。现有rootfs已包含该插件，本次是重建/升级依赖固化，不是新的蓝牙音频验收；配对、连接和实际音频仍须实机验证。

音频路由助手和两份UCM与173已验证载荷逐字一致；当前samurai-wifi和MCFG复制助手也已包含207修复。单独运行的TFTP207服务及k363蓝牙模块的APK采用候选见[固化审计](../../../reference/package-hardening-20261023/README.md)，设备文件所有权和候选安装仍按当前设备窗口核对。

本轮已在独立Linux目录执行实际package()，校验19份源载荷和权限并两次生成逐字相同的可信签名5-r2候选；没有安装或运行服务钩子。整个平台候选包含既有USB脚本源码快照，安装前必须与充电会话的当前现场差异核对，不能覆盖其后续修复。
