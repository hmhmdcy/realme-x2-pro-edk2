# 补丁面审计（2026-11-19，v26.06 systemd 稳定版）

问题：Plasma 桌面 UI 层的补丁是否打得太重，哪些是不必要的？

## 结论

**稳定版镜像里已经没有任何 Plasma/KDE UI 层私有补丁。** 镜像内：

| 包 | 镜像版本 | 配方来源 |
| --- | --- | --- |
| `plasma-workspace` | `99996.6.6-r0` | 官方 `extra-repos/systemd/plasma-workspace`，0 补丁 |
| `kwin` | `99996.6.6-r0` | 官方 `extra-repos/systemd/kwin`，0 补丁 |
| `plasma-nm` | `6.6.6-r0` | 官方 `main/plasma-nm`，0 补丁 |
| `plasma-mobile` | `6.6.6-r0` | 官方 `main/postmarketos-ui-plasma-mobile` |

重放清单：`temp/` 里除 `libcamera` 外的补丁目录（`gnome-shell-mobile`、
`usb-moded`、`akms`、`devpod`、`mutter-mobile`、`xkeyboard-config`）
都没有进入 `samurai/bootstrap.py` 的 13 个目标包，也不在镜像里。

结论：用户此前在 edge / Plasma 6.8 上看到的 KWin、plasma-nm 私有补丁，
在切到 v26.06 稳定版后已经整体去掉，不需要再逐个甄别。

## 仍然保留、且确实必要的补丁

## 量化核查（2026-11-19，交付镜像 `apps2`）

不是靠人工读清单，而是把镜像内 1245 条安装记录逐条与镜像自带的四个
官方索引（`/var/cache/apk/APKINDEX.*`，共 29,949 个包名）比对：

| 类别 | 数量 | 说明 |
| --- | ---: | --- |
| 与官方版本完全一致 | **1223 / 1245** | 无本地改动 |
| 不在任何官方索引（私有壳包） | 15 | 见下表 |
| 版本偏离官方 | 7 | 见下表 |

15 个私有壳包（`device-realme-samurai`、`device-realme-samurai-kernel-none`、
`samurai-platform`、`samurai-platform-pulse`、`samurai-systemd`、
`samurai-desktop`、`samurai-camera-config`、`samurai-camera-stack`、
`samurai-ssc`、`samurai-hexagonrpcd`、`samurai-libssc`、
`samurai-radio-tools`、`samurai-gnss-assist`、`usb-signaller`、
`usb-signaller-systemd`）就是本机必需的板级适配面，没有一个是“顺手加的”。

7 个版本偏离都有既有记录：

- `libcamera` 及其 4 个子包 `99990.7.2-r33`：本机唯一的相机栈，
  50 个 sensor/ISP/tuning 补丁，见 [PACKAGE-PIN-AUDIT](PACKAGE-PIN-AUDIT.md)。
- `unudhcpd` / `unudhcpd-systemd` `0.5.0-r2`：NCM DHCP 的 broadcast 标志，
  见同文档 §3。

所以“Plasma UI 层补丁过重”的担心在稳定版里已经不成立：UI 层补丁为 0，
全部私有面收敛到 15 个板级壳包 + 相机/DHCP 两处必要偏离。

| 包 | 补丁数 | 性质 |
| --- | ---: | --- |
| `temp/libcamera` | 50（目录里另有 3 个未引用的上游 Pinephone 补丁） | 相机 sensor/ISP/tuning，本机唯一相机栈 |
| `device/testing/samurai-platform` | 0（直接装文件） | ALSA UCM、Wi-Fi、Modem、USB 配置 |
| `device/testing/samurai-systemd` | 0（直接装 unit） | 8 个板级 unit + preset + drop-in |
| `device/testing/usb-signaller` | 10 | 见下节 |
| `device/testing/samurai-radio-tools` | 3 | `rmtfs` 运行时目录与 COW、`tqftpserv` 工作文件 |
| `device/testing/samurai-hexagonrpcd`、`samurai-libssc` | 各 1 | SLPI/sensor 运行时路径 |
| `device/testing/unudhcpd` | 1 | DHCP broadcast 标志 |

## usb-signaller 的 10 个补丁：哪些能收敛

这些补丁全部针对上游 `v0.4.3`，且 `service.rs` 在 systemd 和 OpenRC 下
都会调用 `systemctl start/stop`，所以 0006/0008 在 systemd 下**不是死代码**。

| 补丁 | 是否仍必要 | 说明 |
| --- | --- | --- |
| 0001 | 必要 | board descriptor 覆盖；本机 USB 描述符需要 |
| 0002 | 必要 | NCM 用标准 `/etc/unudhcpd.conf` 地址、恢复 NM 管理 |
| 0003 | 必要 | 等 `usb0` 出现再激活，避免慢枚举落到充电模式 |
| 0004 | 必要 | 角色切换后 NM 接受设备的竞态重试 |
| 0005 | 必要 | 主机只到 SET_ADDRESS/SET_CONFIGURATION 时保留模式 |
| 0006 | 必要（systemd 也走 `systemctl stop`） | 切 host 前停模式单元 |
| 0007 | 必要 | stop 时 netdev 已消失不应把单元留成 started |
| 0008 | 必要（systemd 也走 `systemctl start`） | 模式单元启动瞬时失败的有界重试 |
| 0009 | 必要 | 只在 carrier=1 时 `nmcli connection up`，否则状态栏假连接 |
| 0010 | 必要 | 角色切回 device 后 UDC 异步注册，需有界等待 |

可收敛的部分：
- 0006/0007/0008 描述的是 OpenRC 的“服务状态残留”语义，但代码路径对
  systemd 同样生效；**不能按“OpenRC 专用”删掉**，除非先确认 systemd
  下 `systemctl stop/start` 的这些失败分支确实不会发生。
- 0006 在 `urs.rs` 里用 `let _ = service_stop(...)` 吞掉错误；在 systemd 下
  `systemctl stop` 对未加载的单元会返回非零。当前行为与上游 `udc.rs` 的
  “忽略错误”一致，属于设计选择，不是缺陷。

## 下一步建议

1. 先把 0001–0005、0009、0010 作为“必需板级/生命周期修复”保留。
2. 若上游 usb-signaller 发布包含这些修复的新 tag，整体换成官方包，
   私有补丁面可降到 0；这是唯一能进一步收敛的方向。
3. 不建议为了“补丁少”而删 0006/0007/0008：它们解决的是真实发生过的
   host→device 循环失败，删掉会退回“新模式无 usb0 / 状态栏假连接”。

## 补丁重放证据（离线，2026-11-19）

`samurai/replay-patches.sh` 把每个私有补丁系列应用到对应的**原始上游
归档**（`patch --fuzz=0`，不使用构建缓存里的已打补丁树）：

```text
usb-signaller          applied=10 failed=0
tqftpserv-work-files   ok
rmtfs-cow-handler      ok
rmtfs-runtime-root     ok
unudhcpd               applied=1  failed=0
libssc                 applied=1  failed=0
hexagonrpcd            applied=1  failed=0
```

也就是说 16 个私有补丁都可以在原始上游代码上零 fuzz 重放，没有
“补丁实际上已过期、只靠缓存树能构建”的情况。libcamera 的 50 个补丁另有
`check-sources.py` 与 `libcamera-source-lock.json` 的树哈希约束。

## 配方 ↔ 镜像版本一致性

对 16 个自建配方逐个比较 `pkgver/pkgrel` 与镜像 `/lib/apk/db/installed`：

- 13 个已安装包全部一致，包括 `libcamera 99990.7.2-r33`
  （配方 `pkgver=9999$_pkgver` + `_pkgver=0.7.2`）；
- 3 个不在镜像内，属预期：`crossdirect`（仅构建期工具）、
  `samurai-openrc`（OpenRC 变体）、`mesa-vulkan-freedreno-samurai`
  （Turnip 未装入稳定版镜像）。

## 补装 Plasma Camera 后相机 ABI 仍一致

`plasma-camera 2.1.1-r2` 依赖 `so:libcamera.so.0.7` 与
`so:libcamera-base.so.0.7`；板级 `libcamera 99990.7.2-r33` 正好提供
`so:libcamera.so.0.7=0.7.2`，`apk add` 没有替换它。这解决了此前
“Plasma Camera 依赖 libcamera 0.8 会破坏 0.7 栈”的顾虑：在 v26.06
稳定版里两者是同一 0.7 ABI。

补装后的 world 为 38 条纯包名，`apk update` + `apk upgrade --simulate`
仍返回 0（1150 包，2700.7 MiB）。
