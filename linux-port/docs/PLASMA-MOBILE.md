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

当前 KWin 是临时的 `6.8.2-r2`：只回移了 KDE `Plasma/6.8` 分支中的两个上游
修复，没有 Realme 专用逻辑。它是桌面层例外，不属于板级包。Plasma 6.8.3
计划于 2026-11-10 发布并包含这两项修复；届时应升级 Alpine 的签名二进制包，
完成实体触摸/电源键验收后删除本地 KWin 构建目录和补丁。

会话由 `tinydm` 自动登录 UID 10000。当前 Wayland socket 是
`wayland-1`，不能假设一定是 `wayland-0`：

```text
/etc/conf.d/tinydm（官方默认；4-r11 起不再本地写覆盖）:
  AUTOLOGIN_UID=10000
  rc_cgroup_cleanup="yes"
/var/lib/tinydm/default-session.desktop ->
  /usr/share/wayland-sessions/plasma-mobile.desktop
```

当前实装仍是历史 `samurai-platform` 5-r22 / `samurai-desktop` 4-r10；
正式候选是 5-r23 / 4-r11。r11 会删除历史 tinydm 覆盖，只保留官方
`postmarketos-base-ui` 配置。设置来源分层见
[SETTINGS-PROVENANCE.md](SETTINGS-PROVENANCE.md)。

`samurai-desktop` 4-r10 已安装 `/usr/libexec/samurai-tinydm-stop`，并在
`/etc/conf.d/tinydm` 注入 `stop_pre()`。tinydm 停止时先让 elogind 正常
终止 seat 会话，再对捕获到的旧 KWin session cgroup 做有界
`cgroup.kill`。这修复了 `rc-service tinydm restart` 后旧 compositor
仍留在 `c15`/`c187` 等 cgroup、继续占用 DRM 和 power-key 锁，导致第二套
Plasma 会话共存的问题。实机复测旧会话 cgroup 进程数从 50 降到 0，新会话
单实例启动并自动运行 power-key bridge，USB SSH 保持在线。

`samurai-desktop` 4-r11 只调用 `tinydm-set-session` 和 OpenRC
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

## 电源键

受 KDE PowerDevil 6.8.2 tablet-mode 行为影响，电源键默认绑定
`Turn Off Screen`。屏幕熄灭时，KWin 的 `DpmsInputEventFilter` 先处理
物理按键并把 DPMS 置为 On；同一输入随后仍可能进入 KGlobalAccel，
PowerDevil 再以缓存的旧状态执行 `KScreen::Dpms::Toggle`，立即把屏幕
再次关掉。仅把快捷键从 `Turn Off Screen` 改到 `PowerOff` 不够，因为
`PowerButtonAction=128` 最终仍走同一个 Toggle。

`samurai-desktop` 安装 [`samurai-powerkey`](../packages/samurai-desktop/samurai-powerkey)
会话桥接和 `/etc/init.d/samurai-powerkey`。桥接只使用
公共接口：

- 通过 evdev `EVIOCGRAB` 独占 `pm8941_pwrkey`，让 PowerDevil 不再收到
  同一个物理按键；
- 用标准 `kscreen-doctor --dpms show` 读取 KWin 的真实 DPMS 状态；
- 只把 `/sys/class/backlight/*/bl_power` 当作面板首帧门控的唤醒提示。
  modeset 和 DPMS 切换期间该值会被面板驱动自行改写，不能用来判断
  显示是否真的开启；
- 关屏前通过标准 `org.freedesktop.ScreenSaver` 接口锁定会话，再调用
  `kscreen-doctor --dpms off/on`；
- 唤醒时先显式断言 DPMS On；实测正常路径可在毫秒级恢复首帧。只有
  背光门控 1 秒后仍未放行时，才执行一次备用模式 → 当前模式的切换；
- 如果 KWin 的输入过滤器已经抢先把 DPMS 点亮，桥接会根据
  `bl_power` 关闭态或待恢复标记把这次快捷键仍判定为唤醒，而不会把它
  当成第二次关屏；若 KWin 随后又把 DPMS 改回 Off，桥接在 6 秒窗口内
  最多执行两次 `wake race` 恢复；
- 如果 KWin 在唤醒后又被旧状态改回 Off，桥接只在没有用户主动关屏的
  情况下、6 秒窗口内最多纠正两次，不做持续轮询或反复强制点亮。

`bl_power=0` 但屏幕全黑、截图却正常，是 KWin 已关闭输出而面板首帧
门控仍把背光节点显示为打开。此时单击触摸不会唤醒（KWin 默认要求
双击），短暂亮屏也只是强制 modeset 的假象。桥接现在先确认 KWin
DPMS 为 On 再切换模式，避免出现“亮一下，触摸后立刻黑”的状态。

长按电源键目前有意不执行动作，避免 PowerDevil 6.8.2 重复弹出隐藏的
注销确认框。音量键被 KWin 归类为媒体键，设计上不会唤醒 DPMS；黑屏时
有音量提示音只能说明系统未休眠。

在已经登录的 Plasma 会话里也可用下面的脚本安装并立即启动同一桥接：

```sh
sh linux-port/scripts/fix-plasma-powerkey.sh
```

实体按键测试可运行只读观察脚本；它会同时记录
`pm8941_pwrkey`、`bl_power` 和桥接日志：

```sh
sh linux-port/scripts/test-plasma-powerkey.sh 60
```

修改后的 `kscreen-doctor` 验证已覆盖：正常开关屏从
`bl_power=0 → 4 → 0`；外部点亮后 200 ms 内注入同一快捷键会被忽略；
超过保护窗口后再次按键仍可正常关屏。实体电源键与长按测试需在连接
USB NCM 后完成，结果记录在本节。

Plasma 会话重启曾复现 `KScreen enabled`、背光可用，但
`kscreen-doctor --dpms show` 为 `DSI-1: off`、`bl_power=4` 的黑屏状态。
`samurai-powerkey` 现在在启动约 1 秒后读取 DPMS，并以 1 秒间隔最多
重试 10 次；若没有用户主动关屏记录而状态仍为 Off，则通过标准 KScreen
接口断言 On。实机
`tinydm restart` 后新会话自动得到 `DPMS on`、`bl_power=0`，bridge
同时自动独占 evdev 电源键，USB SSH 保持在线。

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
把它唤醒。5-r23 起正式系统直接使用 postmarketOS 的官方
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

当前设备的 `/home/cy122/.config/powerdevilrc` 已在 AC、Battery 和
LowBattery 三个 profile 都写入 `AutoSuspendAction=0`。屏幕可以由
KWin/DPMS 单独关闭；活跃 SSH 会话由上游 `ssh-session-open` 保持系统
在线，不应为了保持 SSH 而常亮屏幕。`samurai-platform` 5-r22 已安装并
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
