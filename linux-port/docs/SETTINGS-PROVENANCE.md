# 设置来源分层：官方默认、板级必需与仅调试

整理日期：2026-11-09。本文回答一个问题：某个设置为什么存在于
RMX1931 的正式系统里，它来自 postmarketOS/KDE 官方默认，还是来自
这块板子无法标准化的硬件差异，还是只应在调试时临时使用。

## 1. 规则

正式系统只允许两类持久设置：

1. **官方默认**：由 postmarketOS 包、Plasma Mobile 或上游 KDE/内核
   自己拥有，本地包不改写。
2. **板级必需薄层**：只描述这块板子的硬件事实或不可替代的硬件启动
   顺序，使用 Linux 主线已有模型/API，不改变通用用户策略。

调试期间需要但正式系统不应持久的设置，必须放在
`linux-port/scripts/`、`linux-port/debug/` 或一次性的主机命令里，
不能安装成 OpenRC 服务、不能写进 `/etc` 的正式配置、不能改写
PowerDevil/tinydm/sleep-inhibitor 的官方文件。

## 2. postmarketOS 官方默认（本地不得改写）

基准提交：
`postmarketOS/pmaports@b5810eb2f3b24ce380a00c54569236f5559f78b1`
（2026-11-08）。

| 项目 | 官方默认 | 正式系统处理 |
| --- | --- | --- |
| `/etc/sleep-inhibitor.conf` | 只有 `ssh-session-open` 和 `apk-running` 两个插件 | 原样保留 |
| `sleep-inhibitor` OpenRC 服务 | 由 `postmarketos-base-ui` 的 elogind 安装钩子加入 `default` | 原样保留 |
| `/etc/conf.d/tinydm` | 只有 `rc_cgroup_cleanup="yes"` 和 `AUTOLOGIN_UID=10000`，没有可选硬件的 `rc_need`/`rc_after` | 原样保留 |
| NetworkManager / sshd / ModemManager | 各自独立启动，通过 udev/QRTR 发现硬件；不由板级 radio/USB 硬门控 | 板级包只做必要的软排序 |
| Plasma Mobile | postmarketOS 不额外安装 `powerdevilrc`；PowerDevil 使用上游 KDE 默认 | 板级 `samurai-desktop` 4-r19 加一份 `/etc/xdg/powerdevilrc`，三档 `AutoSuspendAction=0` + `AutoSuspendIdleTimeoutSec=0`（KDE“永不”），用户 `~/.config` 仍优先 |

PowerDevil 的上游移动端默认（KDE PowerDevil
`daemon/powerdevilsettingsdefaults.cpp`）是：

- 自动休眠：启用，类型 `Sleep`；
- AC 空闲 900 秒、Battery 空闲 300 秒、LowBattery 空闲 300 秒；
- 关屏：AC 600 秒、Battery 120 秒、LowBattery 60 秒。

官方默认会让设备在 AC 15 分钟、电池 5 分钟后自动 `s2idle`。本机实测
`s2idle` 会同时断开 USB/NCM 和 Wi‑Fi，也就是断开所有远程通道，因此
板级把三档都写成 `AutoSuspendAction=0` + `AutoSuspendIdleTimeoutSec=0`。
这不是调试覆盖，而是 KDE 两个电源前端“永不”写下的同一组值：
桌面 KCM 写 `AutoSuspendAction=0`（`PowerButtonAction::NoAction`），
Plasma Mobile KCM 写 `AutoSuspendIdleTimeoutSec=0`。`suspendsession.cpp`
在 `m_idleTime != 0s` 时才注册空闲计时器，而 `loadAction()` 在
`NoAction` 时直接返回；两键同时为 0，任一 UI 打开都显示“永不”，
`check-settings-provenance.sh` 会同时校验这两个键。

低电量保护不在此列：`[BatteryManagement] BatteryCriticalAction` 保持
上游默认（可挂起时为 `Sleep`），5% 时仍会告警并休眠，防止过放。

活跃 SSH 会话由 postmarketOS 的 `ssh-session-open` 插件持有 sleep 锁；
屏幕仍可由 KWin 单独 DPMS 关闭。手动 `loginctl suspend` 或直接写
RTC 不属于官方策略，也不应在无人值守时运行。

## 3. 板级必需薄层（可以持久，但必须是硬件事实）

这些不是“用户设置”，而是这块板子无法由通用 ARM64 平台自动发现的
硬件接线或启动事实：

- DTS 中的 PMIC/regulator/GPIO/panel/camera/CCI/CSI 接线；
- 主线内核驱动需要的板级兼容属性、固件路径和标准 UAPI 节点；
- `samurai-radio`、`samurai-usb`、`samurai-ssc` 等硬件启动服务；
- NetworkManager 的板级 `wlan0`/`usb0` 接口策略和 DHCP 地址；
- USB gadget 的标准 configfs 身份、UDC 选择和 `qmult=20`；
- SOFEF03F 面板的 HBM/首帧亮度时序驱动薄层（标准 DRM panel、backlight
  class 和 MIPI DCS，不新增私有 UAPI）；
- `samurai-tinydm-stop` 的旧 KWin cgroup 清理钩子（不改变 tinydm
  的启动依赖或系统电源策略）；
- ModemManager 的 D-Bus 单所有者覆盖（防止 OpenRC 实例和 D-Bus
  自动激活同时拉起；如果上游解决该竞争，应作为独立候选删除）；
- ALSA UCM、sensor/haptics 的 udev 规则；
- `clk_ignore_unused` 这类有实测证据、尚未找到缺失 clock consumer
  之前的启动约束。

板级薄层不得顺便改变电源策略、桌面默认、SSH 默认、用户 session
策略或 PowerDevil 配置。

## 4. 仅调试（不得安装进正式系统）

| 调试手段 | 位置 | 正式系统处理 |
| --- | --- | --- |
| NCM 长测的 7200 秒 `elogind-inhibit --what=sleep --mode=block` | `linux-port/scripts/test-usb-ncm-stability.py` | 只在测试进程存活期间持有，结束释放 |
| USB carrier-only keep-awake | `linux-port/debug/sleep-policy/` | 手动运行；不安装 OpenRC 服务 |
| USBwake 插电/NCM keep-awake | `linux-port/debug/sleep-policy/usbwake-guard` | 手动运行；等价 PinePhone 的插电不休眠，正式系统不安装 |
| `usbwake-debug` OpenRC 服务 | `linux-port/debug/sleep-policy/install-usbwake-debug.sh` | 仅调试；正式系统不安装、不加入 runlevel |
| `rtcwake -m mem -s N` suspend 验收 | `linux-port/scripts/test-suspend-rtcwake.sh` | 需显式 `SAMURAI_ALLOW_SUSPEND=1`，且有人工唤醒条件 |
| 直接写 RTC sysfs / `loginctl suspend` | 历史证据 | 禁止再用于无人值守测试 |
| 详细 dmesg/trace/网络抓包 | 测试目录 | 测试结束清理 |

## 5. 当前需要清理的本地覆盖

以下不是 postmarketOS 官方默认，正式版必须移除或恢复：

| 覆盖 | 来源 | 处理 |
| --- | --- | --- |
| `samurai-sleep-inhibitor` 独立服务 | 早期为了绕过上游 `conf.d` 所有权而复制官方两个插件 | 从 `samurai-platform` 移除；恢复官方 `sleep-inhibitor` |
| `/etc/samurai/sleep-inhibitor.conf` | 上述服务的板级配置 | 不再安装；debug 示例移到 `linux-port/debug/sleep-policy/` |
| `/usr/libexec/samurai-usb-sleep-guard` | 早期默认开启的 carrier-only 防休眠 | 移出正式包；仅保留为手动 debug helper |
| `tinydm` 的 `rc_need="dbus elogind"` 和 `rc_use="iio-sensor-proxy samurai-sleep-inhibitor"` | 早期启动顺序实验 | 从 `samurai-desktop` 安装钩子移除，恢复官方 tinydm 配置 |
| `powerdevilrc` 中 `AutoSuspendAction=0` | 早期作为“调试关闭”写入；KDE 桌面 KCM 的“永不”也是这个值 | 保留为正式系统默认（4-r19 起），但必须与 `AutoSuspendIdleTimeoutSec=0` 成对出现；任何非 0 的 action 一律拒绝 |
| `/etc/xdg/powerdevilrc` 由镜像直写而未被任何包记录 | 镜像组装脚本直接拷贝文件，绕过了 `samurai-desktop` | 已由 `samurai-desktop` 4-r17 接管；`check-settings-provenance.sh` 断言 `apk info -W` 能找到属主 |
| `sshd` 放在 `boot` runlevel | 早期为了更早获得 SSH 的本地排序 | 标为调试期便利；正式版应另立候选恢复官方 `default` |

## 6. 验收检查

设备恢复后，正式基线必须满足：

```text
/etc/sleep-inhibitor.conf          -> ssh-session-open + apk-running
rc-service sleep-inhibitor status  -> started
rc-service samurai-sleep-inhibitor -> 不存在
/etc/samurai/sleep-inhibitor.conf  -> 不存在
/etc/conf.d/tinydm                 -> 无本地 rc_need/rc_use 覆盖
/etc/xdg/powerdevilrc              -> 三档 AutoSuspendAction=0 + AutoSuspendIdleTimeoutSec=0，属主 samurai-desktop
~/.config/powerdevilrc             -> 若存在，同样不得启用自动挂起
```

检查脚本：

```sh
sh linux-port/scripts/check-settings-provenance.sh
```

4-r19 起 `AutoSuspendAction=0` 是正式默认值，不再是需要清理的调试覆盖。
用户级 `~/.config/powerdevilrc` 仍优先；如果它残留旧值，
`linux-port/scripts/check-settings-provenance.sh` 会指出具体文件。
`clear-powerdevil-debug-override.py` 已标记为过时，仅保留用于审查历史
镜像里的旧调试文件，正式系统不要再运行它。
