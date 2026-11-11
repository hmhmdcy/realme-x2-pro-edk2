# 90Hz 显示、动态刷新率与 60fps 取景：证据、改动与当前阻塞

整理日期：2026-11-04。双模式内核、动态切换和 Phoc 兼容补丁已在
RMX1931 实机验证；同日完成 Plasma Mobile/KWin 的 60/90Hz 实机切换。
随后按用户要求卸载 Phosh/Phoc 并清理其桌面栈。镜像与 APK 保留在主机
的 `edk2-samurai-out`。

## 电脑端 Linux 如何处理高刷屏

桌面 Linux 不是由内核“强制所有页面跑 90Hz”，而是把显示能力交给
DRM/KMS，再由 compositor 决定每个输出的扫描模式：

1. 内核 DRM/KMS 上报 connector 支持的 mode（分辨率、porch、pixel clock、
   refresh）以及 VRR 能力；
2. Mutter、KWin 或 wlroots 为每个 output 选择 mode，提交 atomic commit，
   通过 page-flip fence 在 vblank 边界切换 scanout；
3. compositor 用 damage tracking、direct scanout 和 frame clock 安排重绘。
   页面没有新内容时可以复用旧 buffer，有动画时才按 compositor frame
   clock 提交新帧；
4. 策略层通常是“每输出”的刷新率设置。主流 Wayland 桌面没有稳定、统一的
   per-app 刷新率 API；游戏、视频播放器和部分 compositor 会自行选择
   VRR、帧率上限或 24/30/60fps cadence。

因此 PC 上 90Hz 是否顺滑，不只取决于面板设置，还取决于应用能否在
每个 vblank 前完成 CPU/GPU 提交。同一块 90Hz 屏幕下不同页面卡顿不同，
通常是应用合成路径、GPU 负载或掉帧差异，而不是显示模式没有生效。

支持 VRR（`DRM_CRTC_VRR_ENABLED`）的 PC 显示器可以让 vtotal 随内容帧
到达时间伸缩，60fps 内容仍按接近 60Hz 扫描。固定刷新率面板没有这个
能力，只能选择可整除的 cadence：

- 90Hz 输出 60fps：3 个 vblank 显示 2 帧，节奏为 2/1/2/1，会看到
  uneven cadence；
- 90Hz 输出 45fps 或 30fps：分别稳定为 2 或 3 个 vblank 一帧；
- 60Hz 输出 60fps：一比一，最稳定，但界面动画上限也只有 60Hz。

RMX1931 的 SOFEF03F 只有固定 60/90 两档，没有 VRR。因此本机最合适的
做法不是伪造“全局 90”，而是同时暴露两档：默认 90Hz，遇到 60fps 视频、
相机预览或固定 60fps cadence 的页面时可切到 60Hz；游戏则优先按
90/45/30 的整除关系限帧。

参考：[Kernel Mode Setting（KMS）](https://docs.kernel.org/gpu/drm-kms.html)、
[wlr output management protocol](https://wayland.app/protocols/wlr-output-management-unstable-v1)。

## 90Hz 面板

原厂 `dsi-panel-samsung-sofef03f-m-amoled-dsc-fhd-plus-90fps-cmd.dtsi`
的两组 timing 除刷新率外只有三处差异：

| 项 | 60Hz | 90Hz |
| --- | --- | --- |
| v-front-porch | 12 | 4 |
| `B0=0x01` 页 `B7` | `0x5b` | `0x53` |
| `0x60` | `0x00` | `0x10` |

其余（1080x2400、h porch 32/16/16、v back 12、pulse 4、
`panel-clockrate` 1107MHz、DSC PPS）完全相同；PPS 不含 v-front，
所以现有 DSC 校验逻辑不需要改。

90Hz 的像素时钟：

```
(1080+32+16+16) * (2400+12+4+4) * 90 / 1000 = 249163 kHz
```

主线 DSI 按 DSC 调整后 pclk ≈ 92.3MHz、byte clock ≈ 69.3MHz
（4 lane，RGB888/DSC 8bpp），远低于 PHY 上限。

按 `dsi_adjust_pclk_for_compression()` 的公式：

```
htotal=1144, vtotal=2420, mode clock=249163.2 kHz
DSC new_hdisplay=360, new_htotal=424
pclk=92.347 MHz, byte clock=69.260 MHz, lane rate=554.08 Mbps
PHY VCO≈1.108 GHz, 与原厂 panel-clockrate 1.107 GHz 相差 0.1%
```

即 90Hz 所需的链路速率正好落在原厂固定配置的 1.107GHz 附近，
而不是超出 PHY 能力的新档位。

最初的 90Hz 启动改动保留在
`linux-port/patches/0016-drm-panel-sofef03f-90hz.patch`：它只向
`get_modes()` 返回单一模式，因此只能靠模块参数在开机时二选一。

动态刷新改动是
`linux-port/patches/0017-drm-panel-sofef03f-expose-both-refresh-modes.patch`：

- `get_modes()` 同时上报 `1080x2400@90` 和 `1080x2400@60`，默认把
  模块参数选中的一档标为 `DRM_MODE_TYPE_PREFERRED`；
- 保存 panel connector，在 `prepare`/`on` 阶段读取已提交 CRTC state 的
  `mode`，用 `DRM_MODE_MATCH_TIMINGS | DRM_MODE_MATCH_CLOCK` 匹配实际
  timing，而不是把模块参数当成当前模式；
- 90Hz 写 `B7=0x53`、`0x60=0x10`，60Hz 写 `B7=0x5b`、`0x60=0x00`；
- 无法识别早期 mode 时回退到模块参数，默认仍是 90Hz。回退启动参数为
  `panel_samsung_sofef03f.refresh=60`（内建驱动）。

实现模式与已在 OnePlus 7T Pro（hotdog）上做过实机验证的
panel connector/CRTC state 方案一致；本机也已完成 60/90 往返验证。

用户态切换工具是独立包 `samurai-refresh` 中的同名命令：

```sh
samurai-refresh status
samurai-refresh 90
samurai-refresh 60
```

它从 `wlr-randr` 枚举结果中解析实际的刷新率字符串，再调用
`wlr-randr --output DSI-1 --mode 1080x2400@90.000000`（或
`@60.000000`）；root SSH 环境会自动寻找可访问的 Wayland socket。

## Phoc 输出管理兼容补丁

2026-11-04 晚：Plasma Mobile 验证完成后，Phosh/Phoc 已从设备卸载；
本节保留为历史实现和以后重新安装 Phosh 时的参考。

Phoc 0.57.0 实现了标准的 `wlr-output-management-v1`，但
`phoc_output_config_head_to_output_config()` 只在
`head->state.mode->preferred` 为真时读取固定模式，否则误读空的
`custom_mode`。结果是客户端请求 60Hz 时协议返回成功，Phoc 却回退到
首选的 90Hz。该问题不是内核 DRM 模式或 `wlr-randr` 的问题。

截至 2026-11-04，Phoc 上游 `main`（commit
`1ef2711f87f74f7493249ff9209c3831783722f4`）和 0.58.0 tag
（commit `d50d76a4add49add71b259df9cf67d58b3cbddfb`）仍保留原条件，
没有修复。

本项目的
`linux-port/packages/phoc/0001-apply-all-fixed-output-modes.patch` 把条件
改为“只要 `head->state.mode` 存在就应用该固定模式”：

```c
if (head->state.mode) {
        oc->mode.width = head->state.mode->width;
        oc->mode.height = head->state.mode->height;
        oc->mode.refresh_rate = head->state.mode->refresh / 1000.0;
} else {
        /* custom_mode */
}
```

这仍然完全使用现有 Wayland 和 DRM API，只是修正 Phoc 对协议的实现。
KDE 不走 `wlr-output-management`，而是 KScreen/DBus；同类 hotdog 设备
已用 Plasma/KScreen 实机切换 60/90Hz，因此不存在这个 Phoc 专属问题，
当时判断切换到 KDE 是桌面栈更换，不是 Phosh 的最小修复；随后已按
用户目标在 RMX1931 上实际完成 Plasma Mobile 切换。

离线构建（源码树
`/home/cy122/charging-management-20261023/charging-integration-20261026-01/source`，
配置取自设备 `/proc/config.gz`）：

```
Image-90hz          59,439,616 B
SHA256 24a2e988e80381bbdf8efbaf4c5c9ee5d4c96f6442be270d303b5ac3dba9ac58

Image-dual-refresh-k363plus  59,374,080 B
SHA256 aebe0ae7858de9e2203bd13b2f6cdf3c5af7e2026fe3e3948bbe50946a995e35
kernel release 7.3.0-rc6-rmx1931-samurai-k363+
```

双模式 Image 的两个 display mode 结构已核对：60Hz 时钟
166657/vtotal 2428，90Hz 时钟 249163/vtotal 2420；二者静态结构只带
`DRM_MODE_TYPE_DRIVER`，`get_modes()` 再根据模块参数给首选模式加
`DRM_MODE_TYPE_PREFERRED`。面板初始化日志
`initializing panel at %d Hz` 也已进入 Image。

设备真正的内核不在 boot 分区，而在 `logdump`（`/dev/sde32`，FAT，
卷标 KERNEL）里的 `Image`（59,374,080 B，k363+）。因此不需要重建
EDK2 卷，也不受 FFS 16MiB 限制。

最终 Image 已把设备上原内核内建的 initramfs 原样嵌入并核对：
压缩流 15,063,476 B，解压 cpio 29,770,240 B，SHA256 前缀
`92d47fcc331b169f` 与设备侧一致。

注意：末尾 `+` 必须保留。源码树不是 Git 仓库时 Kbuild 不会自动追加
它；漏掉后 `/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+` 不匹配，
`socinfo` 等模块无法加载，greetd 会被 `samurai-ssc` 依赖阻塞。

## Plasma Mobile / KWin 路线

目标改为 Plasma Mobile 后，显示控制链路从 Phoc 的
`wlr-output-management-v1` 换成 KWin 的 DRM/KMS + KScreen：

1. 内核仍由 0017 补丁同时上报 1080x2400@90 和 @60；
2. KWin 的 DRM backend 选择并提交 CRTC mode；
3. KScreen/DBus 暴露当前模式和可切换模式，Plasma 显示设置与
   `kscreen-doctor` 都走这条标准接口，不引入私有 ioctl。

因此 Plasma 路线不需要 Phoc 的输出管理补丁。Phosh/Phoc 已在 Plasma
验证后从设备卸载，只在本仓库保留补丁和备份 APK。面板没有 VRR，
KScreen 明确报告 `Vrr: incapable`。
Plasma 下不要使用 `wlr-randr`/`samurai-refresh`；KWin 不走
`wlr-output-management`，统一用 `kscreen-doctor` 或 Plasma 显示设置。

实机安装版本：

```text
postmarketos-ui-plasma-mobile 6-r10
plasma-mobile 6.8.2-r0
kwin 6.8.2-r3 (temporary upstream backport + local EBUSY retry)
kscreen 6.8.2-r0
```

`kwin 6.8.2-r3` 不是最终发行基线：它回移两个 KDE `Plasma/6.8`
上游修复，并带本地 `0103-retry-transient-ebusy-commits.patch`。
Plasma 6.8.3 计划于 2026-11-10 发布；升级发行版二进制包并通过实体验收
后，应删除 `linux-port/packages/kwin` 和本地构建产物。

会话由 Nura 的 `tinydm` 自动登录：

```text
/etc/conf.d/tinydm: AUTOLOGIN_UID=10000
/etc/conf.d/tinydm: rc_need="dbus elogind iio-sensor-proxy"
/var/lib/tinydm/default-session.desktop -> plasma-mobile.desktop
rc-update: tinydm default
```

本镜像用户 UID 是 10000，不是 pmOS 默认的 1000；不改
`AUTOLOGIN_UID` 会找不到用户。`tinydm` 是当前唯一显示管理器；
greetd 已随 Phosh 一起卸载。

验证：

```text
kscreen-doctor -o
  Modes: 1:1080x2400@90.00*!  2:1080x2400@60.00
  Vrr: incapable

kscreen-doctor output.DSI-1.mode.1080x2400@60
kscreen-doctor output.DSI-1.mode.1080x2400@90
```

DPMS off 后单独切 mode 不会唤醒输出（DPMS 仍为 3，CRTC 为空）；
把 `--dpms on` 和 output 设置放在同一条命令里也不会生效。必须先单独
执行唤醒，再切模式：

```sh
kscreen-doctor --dpms on
kscreen-doctor output.DSI-1.mode.1080x2400@60
```

2026-11-05 又验证了会话启动和运行期黑屏恢复。当前生产路径由
KWin/PowerDevil 管理 DPMS；历史 `samurai-powerkey` 桥的
`DPMS off → on` 恢复记录只作为旧版证据，不再作为目标实现。一次受控
`DPMS off → on` 实测从 off/4 恢复到 on/0，最终模式仍为 90Hz，日志
没有 DSI/DPU 错误。此前把“DPMS On 但物理屏黑”归因于 first-frame 后
的亮度重发；2026-11-10 已确认真正根因是 SOFEF03F 的 1023/1024 HBM
边界。`0003`/`0005` 的 first-frame 重发候选因此不是根因修复，详见
[PANEL-HBM-20261110](PANEL-HBM-20261110.md)。
`check-plasma-mobile.sh` 已强制检查 `DSI-1 DPMS on`，避免有背光但没有
实际输出时被误判为通过。

独立用 libdrm `modetest -c -p`（`libdrm-tests` 包提供）读取 CRTC，
而不是只看 KScreen 状态：

```text
90Hz: CRTC 91  #0 1080x2400 90.00 ... vtotal 2420 clock 249163
60Hz: CRTC 91  #0 1080x2400 60.00 ... vtotal 2428 clock 166657
```

连续 60/90/60/90 往返后 KWin、plasmashell、USB NCM、SSH 均正常，
日志没有 DRM atomic commit 失败或 `dsi_err`。90Hz 竖屏截图
（`spectacle`，1080x2400）与横屏截图均正常。

## Plasma Mobile 亮度与首次启动

2026-11-04 补测确认亮度也已走标准公共接口：面板仍由内核
backlight class 暴露 `/sys/class/backlight/ae94000.dsi.0`，PowerDevil
通过 KAuth helper 写 sysfs，并把设备注册为
`org.kde.ScreenBrightness` 的 `display0`。KScreen 从
`Brightness control: unsupported` 恢复为 supported 的关键不是改 DSI
驱动，而是让 PowerDevil 在 Plasma 的活跃会话 cgroup 内启动；polkit
拒绝时 helper 无法读取/写入 backlight。

实测 `SetBrightness(1500)` 使 sysfs brightness 变为 308，
`SetBrightness(5000)` 变为 1024。KWin 6.8.2 在下一帧提交硬件亮度，
所以静态桌面测试若没有新帧，会先看到 D-Bus/KScreen 数值变化而 sysfs
暂时不变；触摸、界面动画或一次 DPMS off/on 后会提交。

当前用户已写入
`/home/cy122/.config/plasmamobilerc` 的
`[InitialStart] wizardRun=true`，首次启动向导不再遮挡桌面。新用户仍
使用 Plasma Mobile 默认向导。完整接口清单见
[`PLASMA-MOBILE.md`](PLASMA-MOBILE.md)。

## Plasma Mobile 电源键与面板唤醒

官方路径不是板级电源键桥：elogind 设置 `HandlePowerKey=ignore`，KWin
的 `DpmsInputEventFilter` 接收唤醒，PowerDevil 移动端默认
`PowerButtonAction=ToggleScreenOnOff`（128）。当前用户配置正是这个
官方默认，不再由 `samurai-powerkey` 独占 `pm8941_pwrkey`。

2026-11-09 的实测把问题分成了两层：

1. KWin 已收到实体键并完成 DPMS wake；trace 为
   `drm_panel_backlight phase=0`、`dpu_first_frame_backlight ret=0`、
   `phase=1`，KWin 截图是完整锁屏；
2. 物理面板仍黑。之后通过标准 backlight class 再写一次亮度可以恢复，
   说明 SOFEF03F 对 first-frame 后第一次 DCS 亮度写入有时序问题。

`0003` 曾作为 first-frame 后重发 400/308 的候选，但它只覆盖普通亮度
区间。1024 的最终根因是 HBM 边界，见下节；`0003` 的历史细节保留在
[PANEL-FIX-20261109](PANEL-FIX-20261109.md)。`samurai-desktop` 4-r16
候选同时删除旧电源键桥。

KWin 6.8.2-r3 保留已确认的 `TouchInputRedirection::cancel()` 触摸
序列修复，并增加瞬时原子提交 `EBUSY` 重试；如果新 Image 后仍有
“触摸后关屏”，应先查 KWin 的 DPMS/输入状态，而不是重新引入桥接。

2026-11-10 最终把“锁屏亮屏后触摸变黑”定位到 SOFEF03F HBM 边界：
`brightness > 1023` 必须先写 `0x53=0xe0` 进入 HBM，离开时写
`0x53=0x20`。旧驱动直接写 1024，物理面板黑屏；随后 KScreen 降到 308
（30% 调光）回到普通区间又恢复，所以看起来像时序问题。KWin EBUSY 是
独立问题，不是根因。

修复为
[`0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch`](../patches/v7.3.1/0010-arm64-panel-sofef03f-hbm-first-frame-consolidated.patch)
（部署时使用等价的 0009；0010 已收敛 0003/0005/0009）：
在面板驱动内用标准 DRM panel、backlight class 和 MIPI DCS 补上 HBM
序列，并串行化 first-frame post-on 与亮度更新。10 轮 DPMS off/on
（每轮 1024）全部为 `On/enabled/1024/bl_power=0`，HBM/亮度错误 0；
用户真实上滑多次确认不再黑屏。boot ID
`12a652a5-ac2f-434f-8dc1-4dec0bfd4b53`，产物见
`E:/edk2-samurai-out/standard-arm64-v731/panel-hbm-20261110/`。

KWin `0103-retry-transient-ebusy-commits.patch` 仍保留，但只作为独立的
瞬时 EBUSY 重试；Plasma 6.8.3 后应优先替换为上游修复。

若 `dmesg` 里还有 `PM: suspend entry (s2idle)`，那属于空闲自动休眠，
与 DPMS 动作是两条链路。两者可能连续发生：先被按键从 s2idle 唤醒，
再被 PowerDevil 的合法关屏动作处理。排查时分别核对
`AutoSuspendIdleTimeoutSec`、`PowerButtonAction` 和 KWin DPMS 状态。

KWin 把输出配置持久化在 `~/.config/kwinoutputconfig.json`；干净重启
tinydm 后仍自动回到 90Hz（`vtotal 2420`）。旋转由传感器决定：本机
躺在桌上时 `iio-sensor-proxy` 报 `right-up`，KScreen 显示
`Rotation: 8` 是正确跟随姿态；强制 `rotation.normal` 后截图为
1080x2400 竖屏。

安装期间设备直连 CDN/DNS 不稳定，`apk` 通过主机 Clash Verge 的
局域网混合端口 `192.168.0.101:7897` 完成；这是临时网络设置，已从
`/etc/hosts` 和 `resolv.conf` 清理，未持久化。后续手动安装可用：

```sh
https_proxy=http://192.168.0.101:7897 \
http_proxy=http://192.168.0.101:7897 \
apk add --no-progress <package>
```

尚未做整机重启验证；当前只验证了 tinydm 干净重启。下次重启时应
确认 `tinydm` 在 default 运行级自动拉起 Plasma。

Phosh 已卸载，不能直接切回。需要恢复时重新安装
`postmarketos-ui-phosh` 及其 greetd/phoc 依赖，再按上面的
Phoc 0.57.0-r2 方式钉住；这会重新引入约 109 个包。

## Phosh 卸载与清理

Plasma 验证通过后，按用户要求移除 Phosh 桌面栈。清理脚本：
`linux-port/scripts/cleanup-phosh.sh`（默认 dry-run，`--apply` 执行）。

结果：

- 包数从 1275 降到 1166，安装体积从 2944.6 MiB 降到 2741.8 MiB；
- 移除 Phosh/Phoc/greetd/phrog、`postmarketos-ui-phosh*`、
  `xdg-desktop-portal-phosh`/`wlr`、GNOME session/settings/control-center/
  software、Flatpak/OSTree、ibus/uim/anthy 等 109 个包；
- 显式保留共享运行时：`bash`、`desktop-file-utils`、
  `postmarketos-base-ui-qt-wayland`/`-tweaks`、Plasma 壁纸、`colord`、
  `libseat`、`libaccountsservice`、`apk-polkit-rs`、`cellbroadcastd`、
  `fwupd`、`power-profiles-daemon`、`adwaita-icon-theme`、
  `setxkbmap`、`gst-thumbnailers`、`dconf`、`xdg-user-dirs`、
  `hunspell-en-us`；
- `apk info -e phosh phoc greetd` 均为否；
  `rc-update show` 只剩 `tinydm default`；
- 清理后干净重启 tinydm，KWin/plasmashell 正常，KScreen 仍为
  90Hz，CRTC `vtotal 2420`；
- `/var/cache/apk` 清理约 898 MB，根分区可用约 75.8 GB。

副作用：移除 GNOME 背景包后锁屏壁纸回落到黑色；桌面壁纸仍在
`/usr/share/wallpapers/postmarketos.jpg`，可在 Plasma 设置中重新选择。

## 构建与实机验证

最终设备运行：

```text
Linux samurai 7.3.0-rc6-rmx1931-samurai-k363+ #5
Plasma Mobile 6.8.2 (KWin 6.8.2 + KScreen 6.8.2)
tinydm 自动登录；Phosh/Phoc/greetd 已卸载
```

验证结果（Phosh/Phoc 路径，历史）：

- `wlr-randr` 同时报告 `1080x2400@90.000000` 和 `@60.000000`，
  `Adaptive Sync: disabled`；
- `samurai-refresh 60` 后 CRTC 为
  `60 166657 ... vtotal 2428`，内核日志为
  `initializing panel at 60 Hz`；
- `samurai-refresh 90` 后 CRTC 为
  `90 249163 ... vtotal 2420`，内核日志为
  `initializing panel at 90 Hz`；
- 连续多轮 60/90 往返后 Phoc、USB NCM、SSH 均保持在线，未出现
  `dsi_err`、atomic timeout 或 FIFO 错误；
- 60Hz 和 90Hz 的 `grim` 截图均正常，没有黑屏、花屏或紫屏。

以上为 Phosh 路径的历史记录：Phosh 空闲超时会将输出置为
`Enabled: no`；测试前用 `wlr-randr --output DSI-1 --on` 唤醒即可，
不能把 DPMS off 误判为模式切换失败。当前设备已无 Phosh。

设备 `/root/packages/` 保留的备份 APK（当前未安装）：

```text
/root/packages/phoc-0.57.0-r2.apk
/root/packages/samurai-refresh-1-r1.apk
```

Phosh 清理后 `/etc/apk/world` 已没有 `phoc`/`phosh`/`greetd` 条目；
如果以后重新安装 Phosh，再按 `phoc=0.57.0-r2` 钉住，避免换回仍带
该 bug 的 0.58.0。

刷写记录（需要人在场，失败时可从 fastboot/EDK2 恢复）：

- 最终双模式内核：
  `/mnt/e/edk2-samurai-out/hz90-20261104/Image-dual-refresh-k363plus`
- 固定 90Hz 候选：同目录 `Image-90hz`
- 旧内核备份：同目录 `logdump-Image-k363-backup`
- 主机上的 `.codex-tmp/morning-90hz-flash.sh` 仍指向固定 90Hz 镜像；
  双模式镜像本次使用校验过远程 SHA256 的直接刷写流程。

FAT 只有 64MiB，放不下两份内核，所以备份必须留在主机；
WSL 的 `/tmp` 会在重启后清空，持久目录使用上面的 `edk2-samurai-out`。

## 60fps 取景

原厂 sensormodule 的 `resolutionData`（10 个模式）按驱动使用的
1.92Gpix/s 阵列时钟推算：

| OEM mode | 输出 | line/frame | 推算帧率 |
| --- | --- | --- | --- |
| 2 | 4608x3456 | 17824/3584 | 30.06 |
| 3 | 4608x2592 | 11824/2704 | 60.06 |
| 4 | 4608x2592 | 17824/3584 | 30.06 |
| 7 | 2304x1296 | 4688/1706 | 240.2 |
| 8 | 1280x720 | 4624/864 | 最小 VTS，最高约 480 |

`0007-s5kgw1-720p-preview-mode.patch` 的 720p 模式已从 13840 行
（30fps）改为 6912 行（60.06fps）；需要 30fps 时用户态把 VBLANK
设回 13120 行（驱动上限 0xffff）。

离线模块：

```
/tmp/gw1-60fps/s5kgw1.ko
SHA256 c6189a49baf8ed518e8a26ea2f82798548ebc9a9a8b6c8e65032f17ecb283614
vermagic 7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64
```

已在 `.ko` 的 rodata 中核对 `1280,720,4624,6912` 结构，未上机加载。

热替换实测：停止 PipeWire、unbind `8-0010` 后
`/sys/module/s5kgw1/refcnt` 仍为 1，`rmmod` 返回 "in use"，
因此新模块必须重启后才能生效（与上一轮 720p 模块的部署方式一致）。
设备已恢复原模块并重新 bind，四摄枚举正常。

待验证：

- 1080p 取景请求是否自动选中 1280x720 模式（取决于 libcamera
  `getFormat()` 的选择规则；若仍选 4608x2592，需要把取景源
  caps 固定到 720p）；
- sink 是否稳定 60fps，以及 USB 900mA 下的净流；
- 若 60fps 稳定，再评估 OEM mode 3（4608x2592@60）经 VFE 缩到
  1080p 的可行性（VFE/IPA 吞吐需实测）。

### OEM mode 3（4608x2592@60，1080p 取景的免改应用方案）

对比原厂 10 个模式的寄存器，mode 3 与 mode 2/4 的 PLL/lane 配置
完全相同（`0300=4`、`0302=1`、`0304=3`、`0306=150`、`0308=0`、
`030A=3`、`0114=0x0201`），所以现有 499.2MHz link 端点可直接复用。
mode 3 只是把 line/frame 改成 `11824/2704`（60.06fps）。

测试模块已生成：

```
/mnt/e/RealmeX2Pro edk2/.codex-tmp/s5kgw1-1080p60-d9c4e578.ko
SHA256 d9c4e578e12ae7d3ac3bcaf227d14bfdfdb288a990e6b55d07e9735130c0a13d
vermagic 7.3.0-rc6-rmx1931-samurai-k363+
```

它把 16:9 的 4608x2592 模式替换为 60fps；代价是最大曝光从
3584 行降到 2704 行（约 16.6ms，1/60s），因此只适合验证
“1080p 取景 60fps 是否能跑”，不适合作为最终默认（低光照相会受限）。
验证通过后，正确做法是让 libcamera 按 stream 角色选 mode3（取景）
或 mode4（静态），而不是全局替换。

早晨一键脚本（需人在场）：

- 90Hz：`.codex-tmp/morning-90hz-flash.sh`，回退
  `.codex-tmp/morning-90hz-rollback.sh`；
- 60fps：`.codex-tmp/morning-60fps-install.sh`，测量
  `.codex-tmp/morning-60fps-measure.sh`（120 帧 1280x720，
  `cam --metadata` 取 Sensor timestamp）。

建议先只测 90Hz 内核，确认启动与帧时钟后，再单独测 60fps 模块，
避免一次重启里混入两个变量。
