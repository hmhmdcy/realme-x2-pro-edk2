# 桌面可替换接口边界

整理日期：2026-11-08。本文定义 RMX1931 上板级 Linux 与桌面环境之间的
接口边界。目标是让内核、udev、D-Bus、ALSA、NetworkManager、ModemManager
等公共能力不依赖 Plasma Mobile；更换桌面时只需要替换桌面适配层。

## 分层原则

1. **板级层**只使用主线 Linux 已有入口：DRM/KMS、input evdev、backlight
   class、configfs、udev、ALSA UCM、IIO、NetworkManager、ModemManager、
   GeoClue、feedbackd、PipeWire/libcamera。
2. **桌面适配层**负责 compositor 自己的策略：DPMS/输出管理、锁屏、
   亮度 UI、旋转合成、portal 后端。Plasma 的 KWin/KScreen/PowerDevil
   适配不能放进板级平台包。
3. **应用层**负责 Calls/Chatty、相机应用、浏览器等业务；应用存在不等于
   底层链路已经验收。
4. 不用 `/usr/local` 覆盖发行版文件，不把某个桌面的配置文件安装到
   `/etc` 后假定其它桌面也会读取。

## 当前接口矩阵

| 功能 | 板级公共入口 | 当前实现 | 桌面适配 | 状态 |
| --- | --- | --- | --- | --- |
| 显示模式 | DRM/KMS、`/sys/class/drm` | 主线 DSI panel，60/90Hz | Plasma 用 KScreen；wlroots 可用 output-management | 实机已验证 |
| 背光 | `/sys/class/backlight/ae94000.dsi.0/brightness` | 标准 backlight class | Plasma 用 PowerDevil/KAuth；其它桌面可直接写 sysfs 或使用 brightnessctl | 实机已验证 |
| DPMS/电源键 | input `KEY_POWER`、backlight `bl_power` | 内核输入和面板状态 | Plasma 由 `samurai-desktop` 的 `samurai-powerkey` 接管 | 快捷键路径已验证，实体键待复测 |
| USB 网络 | USB configfs、`/sys/class/udc` | `samurai-platform` 的 `samurai-usb`，串号取 `/sys/devices/soc0/serial_number` | 无，发行版 `sshd.pam` 提供 SSH | 实机幂等启动已验证 |
| Wi-Fi | NetworkManager、cfg80211/mac80211 | `samurai-wifi`/`samurai-udhcpc-wlan` | 无 | 实机已验证 |
| 蜂窝 | ModemManager、QRTR/QMI | `samurai-radio` 和 `samurai-modem-*`；OpenRC 独占 ModemManager，禁止 D-Bus 抢先激活 | Calls/Chatty 只是客户端 | 单实例枚举已恢复；SIM 缺失，注册/通话/数据未验收 |
| 音频 | ALSA UCM、`/usr/share/alsa/ucm2` | 板级 UCM 和路由助手 | 当前 PulseAudio；Plasma 使用其音频栈 | 基本播放/录音已验证，长稳未验收 |
| 传感器 | IIO、iio-sensor-proxy D-Bus | SSC/FastRPC 服务 | compositor 读取 SensorProxy 做旋转 | 实机已验证 |
| 振动 | input evdev、feedbackd udev | AW8697 输入设备 | feedbackd D-Bus 客户端 | D-Bus 触发已验证，手感未验收 |
| GNSS | GeoClue、ModemManager GNSS | 现有 GNSS 生命周期适配 | 桌面定位客户端 | 室外定位未复测 |
| 相机 | V4L2、libcamera、PipeWire | CAMSS/CCI 内核路径 | PipeWire/WirePlumber 或应用 | 枚举和拍照路径已有记录，桌面应用验收分开 |
| 会话 | OpenRC、elogind、tinydm | `samurai-desktop` 选择会话；4-r9 候选不再等待可选外设；stop hook 清理旧 KWin cgroup | Plasma Mobile 会话文件 | tinydm restart 单会话已通过；4-r9 冷启动待复测 |
| 门户 | `org.freedesktop.portal.Desktop` | 发行版 portal | Plasma 用 `xdg-desktop-portal-kde` | Plasma 后端已验证 |

## 包边界

| 包 | 应包含 | 不应包含 |
| --- | --- | --- |
| `samurai-platform` | 板级脚本、OpenRC、udev、NetworkManager、ALSA UCM、USB NCM | Phosh/Phoc 配置、Plasma 配置；当前已改为 `noarch` |
| `samurai-platform-pulse` | PulseAudio 采样参数和蓝牙 Pulse 插件 | ALSA UCM、公共音频路由；可选适配子包 |
| `samurai-desktop` | Plasma Mobile 元包、tinydm 会话选择、Plasma 电源键适配，并选择 PulseAudio 子包 | 内核、通用 udev、硬件服务 |
| `samurai-refresh` | Phoc/wlroots 输出管理历史工具 | 不属于 Plasma 或板级平台的默认依赖 |
| 相机/音频应用包 | 应用和桌面集成 | 代替内核/固件/PipeWire 验收 |

PulseAudio 已从板级主包拆成 `samurai-platform-pulse`；后续切换到纯
PipeWire 桌面时不要安装该子包，改为选择对应的 PipeWire/WirePlumber
适配层。板级主包只保留 ALSA UCM 和 `samurai-audio-route`。

当前实机两份 Realme udev 规则仍在 `/etc/udev/rules.d`，是历史手工部署
位置；5-r6 包按发行版标准安装到 `/usr/lib/udev/rules.d`。安装后先逐文件
比较 SHA-512，确认内容一致再删除 `/etc` 副本，否则 `/etc` 中同名规则会
继续遮蔽包内更新。

## 更换桌面时的检查顺序

```sh
# 1. 板级身份和输入
tr '\0' '\n' < /proc/device-tree/compatible
evtest

# 2. 显示与背光
ls /sys/class/drm
cat /sys/class/backlight/*/max_brightness
cat /sys/class/backlight/*/brightness

# 3. 网络、蜂窝、音频
nmcli device status
mmcli -L
pactl info                 # 或 wpctl status

# 4. 传感器、振动、定位
monitor-sensor
gdbus call --session --dest org.sigxcpu.Feedback \
  --object-path /org/sigxcpu/Feedback \
  --method org.sigxcpu.Feedback.TriggerFeedback button-pressed

# 5. 会话与门户
loginctl list-sessions
gdbus introspect --session --dest org.freedesktop.portal.Desktop \
  --object-path /org/freedesktop/portal/desktop
```

显示 DPMS、锁屏和电源键动作必须在目标桌面的 compositor 内验证；只看到
`bl_power` 或 D-Bus 名称存在，不等于该桌面的唤醒和关屏策略正确。

部署后可在设备上运行只读边界检查：

```sh
sh linux-port/scripts/check-desktop-boundaries.sh
```

## 仍未完成

- 实体电源键短按/长按和冷启动会话复测；
- PipeWire 桌面的音频路由与 UCM 验收；
- SIM 注册、通话、短信和移动数据；
- 相机/音频长稳、GNSS 室外定位和新用户首次启动向导。
