# RMX1931 Plasma Mobile 接口与板级接入

整理日期：2026-11-05。本文记录在现有 Nura/rootfs 上完成的 Plasma Mobile
桌面切换和板级接口验收。所有操作都在当前启动内完成，没有刷写分区，也没有
重启手机。

## 当前基线

```text
Linux 7.3.1-rmx1931-samurai-v731
postmarketos-ui-plasma-mobile 6-r10
plasma-mobile/kwin/kscreen/powerdevil 6.8.2
xdg-desktop-portal-kde 6.8.2
calls 50.0 / chatty 0.8.9 / mmsd-tng 2.6.4
```

当前 KWin 是临时的 `6.8.2-r3`：回移 KDE `Plasma/6.8` 分支中的两个
上游修复，并带本地瞬时 EBUSY 重试补丁，没有 Realme 专用逻辑。它是
桌面层例外，不属于板级包。Plasma 6.8.3 计划于 2026-11-10 发布并包含
这两项上游修复；届时应升级 Alpine 的签名二进制包，完成实体触摸/电源键
验收后删除本地 KWin 构建目录和补丁。

会话由 `tinydm` 自动登录 UID 10000。当前 Wayland socket 是
`wayland-1`，不能假设一定是 `wayland-0`：

```text
/etc/conf.d/tinydm（官方默认；5-r24 起不再本地写覆盖）:
  AUTOLOGIN_UID=10000
  rc_cgroup_cleanup="yes"
/var/lib/tinydm/default-session.desktop ->
  /usr/share/wayland-sessions/plasma-mobile.desktop
```

当前已安装 `samurai-platform` 5-r24 / `samurai-desktop` 4-r15；
4-r16 候选删除 `samurai-powerkey` 桥，只
保留官方 `postmarketos-base-ui`/tinydm/PowerDevil 配置。设置来源分层见
[SETTINGS-PROVENANCE.md](SETTINGS-PROVENANCE.md)。

`samurai-desktop` 安装 `/usr/libexec/samurai-tinydm-stop`，并在
`/etc/conf.d/tinydm` 注入 `stop_pre()`。tinydm 停止时先让 elogind 正常
终止 seat 会话，再对捕获到的旧 KWin session cgroup 做有界
`cgroup.kill`。这修复了 `rc-service tinydm restart` 后旧 compositor
仍留在 `c15`/`c187` 等 cgroup、继续占用 DRM 和 power-key 锁，导致第二套
Plasma 会话共存的问题。实机复测旧会话 cgroup 进程数从 50 降到 0，新会话
单实例启动；4-r16 起不再运行 power-key bridge，USB SSH 保持在线。

`samurai-desktop` 4-r16 只调用 `tinydm-set-session` 和 OpenRC
`rc-update`，不写 `rc_need`/`rc_use`/`AUTOLOGIN_UID`，也不安装
Phosh/greetd 会话。若 Phosh 时代遗留的 greetd 仍在运行，安装钩子会先
停止它，避免和 tinydm 竞争 DRM。

板级 `samurai-platform` 5-r16 已改为 `noarch`，不再安装 Phosh/Phoc
配置；显示模式、背光、USB、udev、音频 UCM、ModemManager 等公共接口与
Plasma 适配层分离；PulseAudio 由可选的 `samurai-platform-pulse` 子包
提供。换桌面时的边界和检查顺序见
[`DESKTOP-PORTABILITY.md`](DESKTOP-PORTABILITY.md)。

当前用户的首次启动向导已完成：

```ini
[InitialStart]
wizardRun=true
```

该标记写入 `/home/cy122/.config/plasmamobilerc`。新用户仍保留 Plasma
Mobile 默认首次启动向导，不会用系统级文件永久跳过。

## 显示与亮度

显示仍使用主线 DRM/KMS、DSI 和 panel backlight class：

```text
kscreen-doctor -o
  DSI-1 Panel, enabled
  Modes: 1080x2400@90.00*  1080x2400@60.00
  Vrr: incapable
  Brightness control: supported
  Automatic brightness: supported, disabled

/sys/class/backlight/ae94000.dsi.0
  type=raw
  max_brightness=2047
  brightness / actual_brightness change with KScreen
```

亮度链路没有新增 ioctl：

1. KWin 通过 DRM/KMS 和
   `kde_external_brightness_v1` 发布显示亮度能力；
2. PowerDevil 通过 KAuth 背光 helper 读写 sysfs；
3. 应用使用 `org.kde.ScreenBrightness` 的 `display0` 子对象。

实机 D-Bus 验证：

```text
SetBrightness(1500) -> sysfs brightness 308
SetBrightness(5000) -> sysfs brightness 1024
```

`org.kde.ScreenBrightness.Display.MaxBrightness` 为 10000，
`IsInternal=true`，`Label="Built-in Screen"`。

KWin 6.8.2 在下一帧合成时才提交硬件亮度。静态桌面没有新帧时，设置会先
更新 KScreen 状态，直到下一次有内容提交才写 backlight；触摸操作、界面
动画或一次 DPMS off/on 都会触发提交。验收亮度时不能只看 D-Bus 属性，
还要核对 sysfs 或 `actual_brightness`。

### PowerDevil 会话注意项

PowerDevil 必须由 Plasma 会话自身的进程树启动。手工从 root SSH 用
`runuser` 启动时，进程可能落入另一个 cgroup（例如 `c348`），polkit
因此拒绝 `org.kde.powerdevil.backlighthelper.*`，KScreen 会显示
`Brightness control: unsupported`。正常 tinydm/Plasma 自动启动时，
PowerDevil 应位于会话 cgroup（本次为 `c142`）。

检查命令：

```sh
cat /proc/<powerdevil-pid>/cgroup
pkcheck --action-id org.kde.powerdevil.backlighthelper.brightness \
  --process <powerdevil-pid>
```

不要在排查亮度时先修改内核面板驱动；本次根因是用户会话/polkit，
背光 sysfs 和 DSI 面板本身已经正常。

## 电源键与 DPMS

官方 postmarketOS Plasma 路径是：

- `postmarketos-base-ui` 设置 `HandlePowerKey=ignore`，elogind 不执行
  电源动作；
- KWin 的 `DpmsInputEventFilter` 在 DPMS Off 时接收物理按键并唤醒；
- PowerDevil 移动端默认 `PowerButtonAction=ToggleScreenOnOff`（128），
  与当前用户配置一致。

因此生产路径不再安装或启动 `samurai-powerkey`。`samurai-desktop`
4-r16 删除该 Python 桥接和 OpenRC 服务；升级脚本只负责停止、禁用并
清理 4-r7..4-r15 留下的旧文件。旧版 r15 APK 仅保留作回滚诊断。

KWin 6.8.2 原生支持长按电源键：`GlobalShortcutFilter` 对
`Qt::Key_PowerOff` 启动 1000 ms 定时器，超时后合成
`Qt::Key_PowerDown`；PowerDevil 6.8.2 注册 `PowerDown` 全局快捷键，
默认动作是 `PromptLogoutDialog`。因此“长按无菜单”不是 Plasma Mobile
缺少该功能。

本机根因是 `~/.config/kglobalshortcutsrc` 中的
`PowerDown=none,Power Down,Power Down`：action 已注册，但 active
shortcut 为空，KGlobalAccel 的 autoload 路径不会自动恢复默认值。
2026-11-11 已通过 KGlobalAccel `setForeignShortcutKeys` 恢复为
`Power Down`，配置持久化为
`PowerDown=Power Down,Power Down,Power Down`。未锁屏时用 D-Bus 触发
`PowerDown`，已实测出现 Restart / Shut Down / Log Out 菜单；实体长按
用 `event0` 注入 1.2 秒 `KEY_POWER` 也走通了 KWin 长按合成路径，菜单
同样出现；实体按键最终手感由用户确认。恢复入口也可以是桌面快捷键设置
中的 Power Management → Power Down。Plasma Mobile 快速设置里的 **Power Menu**
(`org.kde.plasma.quicksetting.powermenu`) 仍是独立入口；不要把长按
逻辑塞进面板驱动或板级服务。

已确认安装在 r2 上的上游触摸序列取消修复由 `kwin-6.8.2-r3` 保留：
此前反汇编 `libkwin.so.6.8.2` 的 `DpmsInputEventFilter` 构造函数，
在 `0x377488` 处调用了 `KWin::TouchInputRedirection::cancel()`。r3
另带本地 `0103-retry-transient-ebusy-commits.patch`。

### 当前面板问题

官方 KWin 路径能收到 `pm8941_pwrkey`，也能完成 DPMS wake：

```text
drm_panel_backlight phase=0 brightness=1024
dpu_first_frame_backlight ret=0
drm_panel_backlight phase=1 brightness=1024
```

此前把物理黑屏归因于 first-frame 后第一次 DCS 亮度写入的时序；2026-11-10
最终定位为 SOFEF03F 的 HBM 边界：`brightness > 1023` 必须先写
`MIPI_DCS_WRITE_CONTROL_DISPLAY (0x53) = 0xe0` 进入 HBM，离开 HBM 时
先写亮度、再写 `0x53 = 0x20`。旧驱动直接写 1024，面板因此物理黑屏；
随后 KScreen 把亮度降到 308（30% 调光）又回到普通区间，所以看起来像
“过一会自己恢复”。

修复位于
[`0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch`](../patches/v7.3.1/0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch)
（部署时使用等价的 0009；0010 已收敛 0003/0005/0009 并与部署源码逐字节一致）：
在面板驱动内用标准 DRM panel、backlight class 和 MIPI DCS 补上 HBM
序列，并串行化 first-frame post-on 与亮度更新，不改 KWin/DPMS API。
10 轮 DPMS off/on（每轮 brightness 1024）全部为
`On/enabled/1024/bl_power=0`，HBM/亮度错误 0、KWin EBUSY 0；用户真实
上滑多次确认不再黑屏。产物见
`E:/edk2-samurai-out/standard-arm64-v731/panel-hbm-20261110/`。

Phosh/Phoc 时期主要停留在内核默认 400 或 308 附近，没有 KScreen 的
`50% -> 1024` 恢复路径，所以没有跨过 1023/1024 的 HBM 边界。这个 bug
是潜伏的边界条件，不是 Plasma 引入的回归；Plasma 第一次稳定写 1024
才把它暴露出来。实体电源键的“DPMS 已唤醒但物理屏黑”也正属于这条链，
但修复后仍应单独做一次实体键验收，不能只用 `kscreen-doctor --dpms`
代替。

## 蜂窝、网络、蓝牙与音频

```text
mmcli -L
  /org/freedesktop/ModemManager1/Modem/0 [QUALCOMM INCORPORATED] 0
  state: failed (sim-missing)

nmcli device status
  wlan0  wifi  connected

bluetoothctl show
  Powered: yes

pactl info
  Default Sink:   alsa_output.platform-sound.HiFi__Speaker__sink
  Default Source: alsa_input.platform-sound.HiFi__Mic__source
```

当前已安装的 r17/r8 组合中，ModemManager 仍通过 OpenRC 的硬依赖等待
板级 radio 初始化：

```text
/etc/conf.d/modemmanager:
  rc_need="samurai-radio"

/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service:
  Exec=/bin/false
```

`/usr/local` 的 D-Bus 覆盖是板级策略，不是临时修补：Nura 的标准
ModemManager D-Bus 激活文件会执行 `/usr/sbin/ModemManager`。如果
Plasma 在 OpenRC 服务之前查询 ModemManager，D-Bus 会先拉起一个不受
OpenRC 管理的实例，随后 OpenRC 因总线名被占用而反复失败。覆盖为
`Exec=/bin/false` 后，系统总线不再抢跑；ModemManager 的唯一所有者是
OpenRC。r9 候选已移除 `tinydm` 对 ModemManager/Bluetooth 的
`rc_after` 顺序；ModemManager 的 `samurai-radio` 硬依赖仍保留，
因为当前主线 modem 需要板级 QRTR/remoteproc 先发布，后续可在实机
时间线证明后改为软依赖。

单实例 OpenRC 启动后，ModemManager 会自动枚举 QRTR/QMI 设备；本机无
SIM 时完整枚举约需 30 秒。期间 `qmicli -d qrtr://0 --dms-get-ids`
已能读取设备 ID，随后 `mmcli -L` 出现 `Modem/0`。不要用每秒重复
`mmcli --scan-modems` 来“加速”，那会不断重启异步扫描。检查脚本最多
等待 35 秒，不主动触发扫描。

当前没有 SIM，因此只能确认 ModemManager、QRTR/QMI、Calls/Chatty 所需
服务已接入，不能宣称注册、通话、短信或移动数据已通过。

## 传感器、旋转与振动

`iio-sensor-proxy` 由 tinydm 的 `rc_use` 有顺序地尝试启动；
`iio-sensor-proxy` 又把 `samurai-ssc` 作为软依赖。因此 SSC 固件
暂时未就绪时，SensorProxy 可以降级，Plasma 登录不被整条依赖链阻塞。
KWin 使用标准 Wayland/KScreen 输出配置处理旋转；KScreen 当前报告
`Auto Rotate Policy: inTabletMode`，设备平放时按传感器姿态旋转。

AW8697 振动输入在主线输入子系统中注册为
`Realme X2 Pro AW8697 haptics`。通用 feedbackd udev 规则不会匹配这个
名称，因此板级包增加：

```text
/usr/lib/udev/rules.d/99-realme-rmx1931-haptics.rules
  ENV{FEEDBACKD_TYPE}=vibra
```

实机 `udevadm info` 已看到 `FEEDBACKD_TYPE=vibra`，并通过标准
`org.sigxcpu.Feedback.TriggerFeedback` 触发
`button-pressed`（返回 id 2、`EndFeedback` 成功）。这证明 Linux 输入、
udev、feedbackd 和 D-Bus 链路已通；实际振幅/手感仍需用户确认。

## 桌面门户与定位

用户会话中 `org.freedesktop.portal.Desktop` 和
`org.freedesktop.impl.portal.desktop.kde` 均存在。Settings portal 版本
为 2，文件、截图、通知和 KDE 后端可按 Plasma Mobile 默认配置使用。

GeoClue 2.8.2、ModemManager GNSS 生命周期补丁和已有桌面定位验收继续
沿用 [GNSS 证据](../../reference/kernel260/README.md)，本文不重复宣称
新的室外定位结果。

## 相机边界

PipeWire/WirePlumber 已枚举四路 libcamera 源，现有四摄命名、取景和
RAW 拍照路径仍按相机文档维护。Megapixels、Snapshot 与照片/录像应用
不是 Plasma Mobile UI 元包的唯一默认入口；相机工作不用于证明本次
Plasma 桌面接口验收完成。

## 仍需现场或后续验收

- 真实 SIM 注册、通话、短信、MMS 和移动数据；
- 振动实际手感、耳机/耳麦和音频长稳；
- 冷启动首次会话、自动休眠/唤醒后的亮度与旋转恢复；
- 自动亮度曲线和真实环境光校准（默认仍关闭）；
- 新用户首次启动向导与 Plasma Mobile 默认布局的整机验收。

## USB SSH 与系统 suspend

Plasma Mobile 的 KWin DPMS 关屏不等于系统 suspend。设备侧 DWC3 在
系统 suspend 时会 soft-disconnect USB gadget，主机的 NCM 流量无法
把它唤醒。5-r24 起正式系统直接使用 postmarketOS 的官方
`/etc/sleep-inhibitor.conf` 和官方 `sleep-inhibitor` 服务：
`ssh-session-open` 在存在活跃 SSH 会话时持有 `sleep` 锁，`apk-running`
在包事务期间持锁。只要 SSH 会话保持，面板可以关闭而系统不休眠。

“仅插着 USB 充电线”不持有唤醒锁；carrier-only guard 已移到
`linux-port/debug/sleep-policy/`，只允许手动调试，不再安装
`/usr/libexec/samurai-usb-sleep-guard` 或 `samurai-sleep-inhibitor`。
正式包不写 `powerdevilrc`，PowerDevil 使用上游 KDE 默认。
`samurai-platform` 5-r20 起还移除了 `sshd -> samurai-usb` 和
`NetworkManager -> samurai-radio` 顺序，使通用 SSH/网络守护进程不再
等待 NCM 或 radio 准备；安装后必须用时间线确认 Wi‑Fi 首连仍正常。

2026-11-08 在新普通重启 `f26c6cdc…` 上实测：`card1-DSI-1` 已
`DPMS=Off`、`enabled=disabled` 时，Wi‑Fi SSH 心跳持续运行，
`usb0` 仍 up、UDC 仍 configured，活跃 SSH 会话的 `sleep` block 锁保持；
同一 boot 的 Wi‑Fi 1800 样本/1810 秒
心跳通过。因此“KDE 桌面 + 熄屏”本身不是断连根因，之前的故障是启动期
OpenRC 硬依赖连锁和 USB/NCM 大传输路径。

部署后运行只读检查：

```sh
sh linux-port/scripts/check-plasma-mobile.sh
sh linux-port/scripts/check-usb-sleep-guard.sh
```

若为了充电维护主动把 DSI-1 DPMS 关闭，可在只读检查时临时使用
`SAMURAI_ALLOW_DPMS_OFF=1`；实体电源键验收仍应使用默认条件，要求
DPMS on。

### KDE 默认值与 USB NCM 的边界

Plasma/PowerDevil 不理解“USB NCM 连接”这个板级事实，它只根据
`KIdleTime` 和 `CanSuspend` 调用系统的 suspend 接口。上游
[PowerDevil 默认值](https://github.com/KDE/powerdevil/blob/master/daemon/powerdevilsettingsdefaults.cpp)
在移动设备上会在 AC 空闲 15 分钟、电池/LowBattery 空闲 5 分钟后
自动 suspend；显示关闭时间分别是 10、2、1 分钟。`AutoSuspendAction`
的 `NoAction` 值确实是 `0`。

调试期写入的 `AutoSuspendAction=0` 覆盖已删除，当前使用 PowerDevil
官方移动默认：AC 空闲 15 分钟、Battery/LowBattery 空闲 5 分钟后自动
suspend。屏幕可以由 KWin/DPMS 单独关闭；活跃 SSH 会话由上游
`ssh-session-open` 保持系统在线，不应为了保持 SSH 而常亮屏幕。
`samurai-platform` 5-r24 已安装并
通过普通重启验收，默认关闭 USB carrier-only guard。主板直连口的 USB
NCM 已恢复并通过长测；旧 Genesys Hub 的枚举失败仍属独立物理路径问题。

2026-11-09 的一次 suspend 尝试必须单独记录为失败：在 thin-private
boot `2b17a67a…` 上，脚本用直接 `/sys/class/rtc/rtc0/wakealarm`
按 `since_epoch+45` 布防后调用 `loginctl suspend`，140 秒内 NCM/Wi‑Fi
没有恢复，Windows USB 和 fastboot 也未枚举。此前通过的是
`rtcwake -m mem` 路径；两种设闹钟方式不能混为一谈。设备需物理唤醒后，
保存 `/tmp/samurai-suspend-test.log` 和 `suspend_stats`，再用
`linux-port/scripts/test-suspend-rtcwake.sh 30` 复测，不能把本次失败
写成策略已通过或策略失效。

其他手机没有一套可直接照搬的通用规则：

- Android 使用自己的 USB gadget/charger HAL 和 PowerManager wakelock；
  ADB、USB tethering 或充电场景由 vendor/SoC 策略维持 USB 生命周期，
  不是 KDE 的 `AutoSuspendAction`。
- GNOME/Phosh、Plasma Mobile、Sway 等 Linux 手机发行版通常用
  `systemd-inhibit`、`elogind-inhibit` 或设备专用服务来阻止 suspend；
  没有跨 SoC 的“NCM 连接自动阻止休眠”属性。普通桌面插着 Ethernet
  线、甚至有人通过 SSH 登录，也不会因此阻止默认自动 suspend。
- USB NCM 是标准 CDC Ethernet gadget，链路本身不是 wakelock。DWC3
  在系统 suspend 时会 soft-disconnect，不能依赖主机发包把已经休眠的
  gadget 唤醒；远程唤醒需要控制器、PHY、host 和 class 同时支持，
  不能当作通用 NCM 能力。

因此合理的目标不是常亮屏，而是“DPMS 关屏 + 在确实需要远程访问时持有
标准 logind/elogind `sleep` 锁”。官方 postmarketOS/Nura 默认只启用
`ssh-session-open`；本板默认也应如此。若长期接 USB 只充电，应允许
休眠；只有确实需要无 SSH 活动的 USB 维护时，才显式启用板级 carrier
guard。Windows 主机在 NCM 刚枚举后的数十秒内还可能没有完成 ARP，当前
实测需要等待或重试，不能把这段主机侧窗口误判为 KDE 断开连接。
