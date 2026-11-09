# RMX1931 Plasma Mobile 桌面配方 4-r11

4-r11 restores the postmarketOS tinydm baseline. The package no longer
writes `rc_need`, `rc_use`, `rc_cgroup_cleanup` or `AUTOLOGIN_UID` into
`/etc/conf.d/tinydm`; it only removes the exact board-era values left by
4-r7..4-r10. `postmarketos-base-ui` owns the file, including
`rc_cgroup_cleanup="yes"` and `AUTOLOGIN_UID=10000`.

This means the graphical session follows the upstream tinydm dependency
graph (`need localmount`, `want dbus elogind`) instead of a local hard
dependency on optional hardware or a board sleep service. Active SSH is
protected by the official `ssh-session-open` plugin in the upstream
sleep-inhibitor configuration. USB carrier-only keep-awake is no longer
installed by any production package.

4-r10 and 4-r9 were the prior transition versions. They removed historical
`tinydm` ordering behind ModemManager, Bluetooth and the sensor proxy, but
still left `rc_need="dbus elogind"` and a board `rc_use` line. 4-r11 removes
those remaining overrides.

4-r8 把 `iio-sensor-proxy` 从 tinydm 的硬依赖改为有顺序的 `rc_use`
软依赖。这样 `samurai-ssc` 或 SensorProxy 在启动早期失败时，Plasma
仍能启动；传感器恢复后仍可由正常的 OpenRC 服务重新提供，不用把整个
桌面登录链绑定到一条可选硬件路径。当前包已安装并做过运行态检查，
多次冷启动仍待验证。

4-r7 是历史实现：它曾让 `tinydm` 的 `rc_need` 指向板级
`samurai-sleep-inhibitor`，4-r11 已恢复上游服务。

此目录对应 `device/testing/samurai-desktop` 的 Plasma Mobile 默认桌面
元包。它不再安装或启动 Phosh、Phoc、greetd；旧的
`samurai-phosh-*`、`greetd.confd` 和 Snapshot 配置仅作为历史文件保留，
不进入新包的 payload。

`depends` 显式固定 Plasma Mobile、tinydm、板级平台包、通话/SMS 和门户
依赖，并显式选择含 OpenRC 服务的 `modemmanager`/`bluez`；当前 Plasma
音频栈通过 `samurai-platform-pulse` 选择 PulseAudio 适配层。
`samurai-desktop.post-install` 只调用发行版已有的
`tinydm-set-session` 和 OpenRC 接口：

- 默认会话设为 `plasma-mobile.desktop`；
- `tinydm` 加入 default runlevel，并移除 greetd 的 default 注册；
- 不再写 `rc_need`/`rc_use`/`AUTOLOGIN_UID`；
- 只清理 4-r7..4-r10 注入的精确旧值，保留 postmarketOS 官方配置。

该包不使用 `systemd`、`wlr-randr` 或 Phoc 私有配置。显示模式与亮度走
KWin/KScreen，亮度由 PowerDevil 的 KAuth 背光 helper 和
`org.kde.ScreenBrightness` 标准 D-Bus 接口提供。

`4-r6` 的历史配置把 `samurai-sleep-inhibitor` 放入 `rc_need`，并用
`rc_after` 等待 ModemManager/蓝牙；`4-r9` 移除了这些可选硬件顺序，
`4-r11` 又移除了剩余的本地 tinydm 覆盖。
安装时仍会停止可能占用 DRM 的遗留 `greetd`。板级 `5-r20` 起默认只由
标准 `ssh-session-open` 插件持有 sleep 锁；USB carrier guard 必须显式
启用，因此仅插着充电线不会永久阻止 suspend。

包内 `samurai-tinydm-stop` 通过 tinydm 的 `stop_pre` 钩子在停止
autologin seat 前清理旧 KWin session cgroup。这样 `tinydm restart`
不会留下第二套 compositor 或占用 power-key 锁；正常路径仍先用
`loginctl terminate-session`，仅在旧 cgroup 仍存活时才 fallback 到
有界 `cgroup.kill`。

包内还安装 `samurai-powerkey` 会话桥接。它通过 evdev 独占
`pm8941_pwrkey`，避免 PowerDevil 的缓存 Toggle 再次处理同一个按键，
并用标准 `kscreen-doctor --dpms show` 读取 KWin 的真实 DPMS
状态，不再把 `/sys/class/backlight/*/bl_power` 当成 DPMS 状态。背光值
只作为面板首帧门控的唤醒提示：唤醒时先直接断言 DPMS On；只有 1 秒内
面板仍被门控时才执行一次 60 Hz ↔ 90 Hz 模式切换。桥接由 OpenRC 的
`samurai-powerkey` 服务启动，并在关屏前调用
`org.freedesktop.ScreenSaver` 锁定会话。启动约 1 秒后开始检查
KScreen 的 DPMS 状态，最多重试 10 次；若新会话仍停在 Off 且没有用户
主动关屏记录，则用标准 KScreen 接口断言 On，修复会话重启后的黑屏。
如果 KWin 输入过滤器已经先点亮输出，桥接会根据关闭态背光或待恢复
标记把电源键仍识别为唤醒，不会重放成第二次关屏；主动关屏会取消待恢复
标记，KWin 在 6 秒唤醒窗口内翻回 Off 时最多执行两次 `wake race`
恢复。

实机验证、接口清单及 PowerDevil 会话注意事项见
[`PLASMA-MOBILE.md`](../../docs/PLASMA-MOBILE.md)。
