# L4 公共 UAPI 与硬编码清单（草案）

整理日期：2026-11-05。

本文是 [L2-L4 收敛计划](LAYER-CONVERGENCE-PLAN.md) 的 L4-01 交付物。
它区分内核 UAPI、板级用户态和桌面策略，避免把“发行版配置债”误当成
“内核 ABI”。本文不删除任何接口，也不改运行中的服务。

## 1. 原则

1. 有公共子系统的接口优先，例如 DRM/KMS、evdev、ALSA、IIO、
   power_supply、cfg80211、BlueZ、ModemManager、GeoClue、feedbackd。
2. 旧接口先保留，新增标准接口/别名，再迁移消费者，最后才删除。
3. 设备名、connector 名、Wayland socket、UID 不能当作稳定 ABI。
4. `/usr/local` 覆盖不是硬件接口；它属于 L5/L6 的发行版策略。

## 2. 内核 UAPI/硬件接口

| 当前接口 | 实际消费者/证据 | 标准方向 | 当前动作 |
| --- | --- | --- | --- |
| `/sys/devices/platform/sensor-power/state` | [270 native-quiesce](../../reference/kernel270/native-quiesce.py)、[restart-bootloader](../../reference/kernel270/restart-bootloader.py)、板级 quiesce 流程 | 通用 remoteproc prepare/unprepare subdevice；`state` 只读兼容 | genpd/PAS proxy 方案已在真机 `#9` 否决并回退 `#5`；`rproc_subdev` 已在真机 `#2` 通过启动/停止、readiness 和冷启动；旧 `state` 继续保留到消费者迁移完成 |
| `/sys/class/udc/a600000.usb` | [samurai-usb](../packages/samurai-platform/usr_sbin_samurai-usb)、检查脚本 | 枚举 `/sys/class/udc`，优先当前控制器、单 UDC 回退 | 源级离线测试通过：优先 `a600000.usb`、任意单 UDC 回退、多个 UDC 要求 `SAMURAI_UDC`、显式缺失报错；5-r24 不再安装 debug sleep guard |
| `/sys/class/typec/port0` | USB2 Type-C 离线检查脚本 | 标准 Type-C class（power_role/data_role/port_type/orientation） | sink/dual DTB 已构建但未部署；真机门禁用只读枚举，不新增板级 ioctl/sysfs |
| `/sys/bus/platform/devices/extcon-usb1/power/wakeup` | udev 规则、`check-usb-wake-baseline.sh` | 通用 power wakeup sysfs + `extcon-usb-gpio` | DTB-only 候选已构建；udev 只把 capability 设为 enabled，不新增服务或私有 ioctl；同线 USB resume 不在该 UAPI 内 |
| `/sys/class/backlight/ae94000.dsi.0` | [桌面边界](DESKTOP-PORTABILITY.md)、Plasma/Phosh 文档 | backlight class 发现，不写死设备名 | 文档/检查脚本先改用 glob/属性读取 |
| `DSI-1` connector 名 | [Plasma 文档](PLASMA-MOBILE.md)、检查脚本 | DRM connector 枚举/KScreen 查询 | 检查和桌面适配不应把名字当硬件 ABI |
| `/sys/class/power_supply/samurai-usb-input/*` | 充电状态、power_supply 消费者 | 标准 power_supply 属性 | 属性名是当前板级驱动接口，新增标准属性时保留旧属性 |
| `realme,samurai` compatible | [samurai-usb](../packages/samurai-platform/usr_sbin_samurai-usb)、[audio route](../packages/samurai-platform/usr_libexec_samurai-audio-route) | 稳定的板级 DT identity | 保留；这是识别，不是私有 ioctl |
| ALSA card/control 名 | `samurai-audio-route`、UCM | ALSA/UCM、按 card ID 发现 | 先区分 UCM 路由和固定 card 名 |
| AW8697 input/ff | feedbackd udev、input 设备 | input/ff、feedbackd D-Bus | 保留 udev 规则；桌面不直接写寄存器 |
| PM8150L flash | 主线 `leds-qcom-flash`；候选 DTB `led-0` | LED flash class、V4L2 flash subdevice | 使用 function/color 发现，不用固定 `/sys/class/leds` 名字；先低亮度短测并 finally 归零 |

## 3. L5/L6 配置债（不是 L4）

| 当前硬编码 | 位置 | 迁移方向 | 删除条件 |
| --- | --- | --- | --- |
| `/usr/local/share/dbus-1/system-services/org.freedesktop.ModemManager1.service` | [samurai-platform APKBUILD](../packages/samurai-platform/APKBUILD) | OpenRC/systemd 发行版适配包或标准 D-Bus 策略 | 所有 init 适配都禁止双实例后 |
| `AUTOLOGIN_UID=10000` | [samurai-desktop post-install](../packages/samurai-desktop/samurai-desktop.post-install) | 安装时从普通本地账号推导，保留已有值 | 新用户/旧用户迁移验证后 |
| `wayland-1` | [Plasma 文档](PLASMA-MOBILE.md)、检查脚本 | `WAYLAND_DISPLAY`/socket 发现 | 检查脚本和桌面启动器都不再假定编号 |
| `samurai-powerkey`（已退役） | [samurai-desktop](../packages/samurai-desktop/APKBUILD) | 4-r16 删除；电源键/DPMS 交回 KWin/PowerDevil 官方路径 | 已满足删除条件，保留 r15 APK 仅作回滚 |
| `tinydm` 会话配置 | [samurai-desktop README](../packages/samurai-desktop/README.md) | 保留在桌面适配包 | 板级包不再写桌面会话 |
| `samurai-refresh` | [samurai-refresh](../packages/samurai-refresh/README.md) | 保留为 Phoc/wlroots 历史工具 | 不再作为板级默认依赖 |

`/usr/local` 的 ModemManager 覆盖是**发行版/init 策略**。把它从板级
硬件包移走，不等于删除 ModemManager；目标是让其它 init 系统有自己的
单实例策略，而不是把 OpenRC 的实现强加给所有发行版。

## 4. 双栈迁移顺序

1. **L4-01**：记录每个接口的实际读写者、调用命令、失败后果；
2. **L4-02**：新增标准接口/别名，旧接口保持；
3. **L4-03**：迁移检查脚本、板级 helper 和桌面客户端；
4. **L4-04**：在旧消费者全部迁移并有一个回退包后，才删除旧接口；
5. **L4-05**：用标准工具做回归，不用“sysfs 路径存在”代替功能通过。

## 5. 回归命令模板

这些命令是只读检查，不代表已经在本机运行：

```sh
tr '\0' '\n' < /proc/device-tree/compatible
ls /sys/class/udc /sys/class/backlight /sys/class/power_supply
ls /sys/class/drm /sys/bus/iio/devices
evtest
pactl info                 # 或 wpctl status
nmcli device status
mmcli -L
monitor-sensor
gdbus introspect --session \
  --dest org.freedesktop.portal.Desktop \
  --object-path /org/freedesktop/portal/desktop
```

实施 L4-02 时，应把每个命令与当前飞轮基线和目标功能对应起来；不能只
因为命令返回 0 就宣称硬件验收通过。

## 6. L4-02：UDC 发现离线验收

[`check-udc-discovery.sh`](../scripts/check-udc-discovery.sh) 用临时
目录模拟 `/sys/class/udc`，同时检查包内脚本和开发脚本，不写 `/sys`，
不创建 gadget：

```sh
sh linux-port/scripts/check-udc-discovery.sh
```

覆盖的契约：

- 只有 `a600000.usb` 时选择它；
- 只有其它单个 UDC 时回退到该 UDC；
- `a600000.usb` 与其它 UDC 并存时仍优先它；
- 多个任意 UDC 且未指定 `SAMURAI_UDC` 时失败并要求显式选择；
- `SAMURAI_UDC` 可覆盖多 UDC；
- 指定的 UDC 不存在时失败；
- 没有 UDC 时失败。

2026-11-05 的两个脚本各 7 个用例全部通过，日志
`E:\edk2-samurai-out\layer-adaptation-20261105\l4-uapi\udc-discovery-test.log`
的 SHA-256 为 `fda060f8...fab4`。这证明脚本不再把
`a600000.usb` 当作唯一可用名字；它不证明当前已安装的板级包已经包含
该逻辑，也不替代运行态 USB/SSH 验收。

2026-11-05 复跑包内脚本和开发脚本仍为 14/14，日志
`...\l4-uapi\udc-discovery-rerun.log` 的 SHA-256 同为
`fda060f8...fab4`。`samurai-platform` 的 APKBUILD `sha512sums`
全部匹配，`usr_sbin_samurai-usb` 的 SHA-512 为
`600cde92...90f6`，确认 UDC 发现逻辑就是包输入，而不是只在开发目录
里的副本。

本轮没有构建或安装 APK：工作区没有包签名私钥，无法生成可用的签名包；
这属于发布链缺口，不是脚本逻辑失败。G4 前需要在受控签名环境中重建
`samurai-platform`，再验证安装后的脚本哈希和运行态 UDC 行为。
