# samurai-platform 6-r15 (source candidate; live rootfs 6-r14)

> 2026-11-13 22:40 source candidate: `6-r17` updates the read-only
> `samurai-otg-capture` helper to recognize the board's MP2650
> `mp2650-vbus` regulator as well as the older PM8150B `usb_vbus`
> name.  This is source-only; the signed APK has not been rebuilt.
> The current live rootfs still has the directly installed helper,
> and the standard URS/VBUS behavior itself is unchanged.

> 2026-11-13 candidate: `6-r15` adds the read-only
> `/usr/sbin/samurai-otg-capture` udev helper and
> `/usr/lib/udev/rules.d/90-samurai-otg-capture.rules`. It records
> USB role transitions, Type-C/PM8150B VBUS state, xHCI/lsusb/lsblk,
> usb-moded state and the read-only OTG probes into
> `/var/log/samurai/otg-events.log`; it does not mount, change roles,
> restart services or poll. The signed APKs verify:
> `samurai-platform-6-r15.apk` SHA-256
> `4f10f6e794ba54ce35bf05b688ad774b5ab26a4dfea4e7d71db1df54656f5205`;
> `samurai-platform-pulse-6-r15.apk` SHA-256
> `0a202e2ff692d519b5c93c10c6c3fd873b70e31507332b58ae7f04aa6429ead2`.
> The live rootfs remains on `6-r14`: apk 3.0.8 could not solve the
> upgrade against the existing `cmd:` provider versions and an
> unrelated openssh version constraint. The helper and rule are
> currently installed directly for physical-test capture; remove the
> `/etc/udev/rules.d` copy before a future package-managed r15 upgrade.

> 2026-11-13 final: `6-r14` raises the package dependency to
> `usb-signaller>=0.4.3-r9`, matching the packaged supervisor restart
> fix. The board files are unchanged from r13. Signed APKs:
> `samurai-platform-6-r14.apk` SHA-256
> `d3903ce6981c474dcc1bca8b394388c16c74e1e950cb6e005151ce09b7b522df`;
> `samurai-platform-pulse-6-r14.apk` SHA-256
> `335161fbabd6e2e4528e4762d58c3ac405b35830875b2b2fd2937445675e2d9b`.
> The main APK was upgraded with `--scripts=no` so the live USB state
> was not torn down; `apk info -R samurai-platform` reports the r9
> dependency.

> 2026-11-13 后续：`6-r13` source adds
> `[main] default_mode = "developer_mode"` to the board
> `/etc/usb-signaller.d/90-samurai.toml` drop-in. This makes a clean
> `usb-signaller` start return to Developer NCM after Charging-only.
> The file was deployed directly on the handset and verified with
> Developer/UDC/carrier/NetworkManager/unudhcpd. The signed
> `samurai-platform-6-r13.apk` was then built with the intentional
> `/usr/local` ModemManager D-Bus override and installed with
> `--scripts=no`; three host→device rounds and USB NCM SSH passed.
> APK SHA-256 `b8f7b11a88d702ab7b3fb9cf512e1207aa9456688bebb0b691e37fbe32062598`.
> `APKBUILD` uses `options="!check !fhs"` solely because that
> pre-existing distribution override lives under `/usr/local`; this is
> not a general allowance for new board-private files.

6-r9 began the current OTG recovery candidate line. It keeps the standard postmarketOS
USB ownership model and adds the bounded `samurai-usb-recover` path:

```text
usb-signaller 0.4.3-r9
unudhcpd 0.5.0-r2
postmarketos-usb-moded
NetworkManager + unudhcpd.usb0 + umtprd
Developer 172.16.42.1/16, 0525:a4a1, qmult=20
Tethering 10.42.0.1/24
MTP 0525:a4a2
```

When the installed dual-role kernel registers a standard `usb_role`
provider, `usb-signaller` exposes `host_mode` through the same
usb-moded D-Bus API. In synthetic host/device tests the role switch,
`usb-moded.mode_request=host_mode`, xHCI root buses and return to
Developer NCM all worked without a board-owned host command. Physical
OTG adapters and attached peripherals are still a separate hardware
acceptance.

The recovery service preserves the active usb-moded mode across a DWC3
unbind/bind, restarts the matching standard mode service, and bounds
`rc-service` calls so a stalled controller cannot hang the monitor.
6-r2 and later toggle the standard UDC `soft_connect` control so the host
performs a clean enumeration and DHCP exchange instead of retaining its
failed NCM adapter state. The ordinary reboot and `ip link down`
recovery tests are recorded in `linux-port/docs/PMOS-USB-20261112.md`.
Physical cable/orientation checks and same-cable U3 host-resume remain
open.

6-r3 added a separate bounded reattach path for an explicit transition
from `host_mode` (or another non-NCM mode) back to Developer/Tethering.
The previous controller can report UDC `configured` while the host never
raises NCM carrier; because VBUS never toggles, the older recovery state
machine stayed disarmed. The new path records
`MODE_REATTACH mode=...`, waits for the standard mode service, then uses
the same bounded DWC3 unbind/bind and UDC `soft_connect` recovery. The
attempt budget remains at most two per cable session.

6-r4 and 6-r5 close the mode-transition race found by repeated
`test-usb-moded-host-mode.sh` runs:

- an unrecognised D-Bus state pauses recovery instead of falling back to
  the wrong configfs mode;
- the mode-request D-Bus call has an explicit reply timeout;
- a new Developer/Tethering session resets the bounded retry budget,
  logged as `BUDGET_RESET reason=mode_transition`;
- the offline mode-transition test checks the reset explicitly.

6-r6 also makes a missed short `host_mode` transition recoverable. The
monitor records the active configfs gadget generation (inode and
timestamps), not only the polled D-Bus mode name. A later gadget
generation is treated as a new user session even if the monitor never
sampled `host_mode`. Recovery writes the post-rebind generation back as
the baseline, so the watchdog cannot mistake its own restart for a new
session and reset its retry budget forever. A three-round handset run of
the standard host-mode test passed with a bounded attempt count. The
offline generation regression is
`linux-port/diagnostics/test-usb-recover-generation.sh`.

6-r7 introduced a soft-first path for `MODE_REATTACH`: when UDC is still
`configured` but NCM carrier is missing, the recovery service first
toggles the public UDC `soft_connect` control and waits for carrier. It
only performs the full DWC3 unbind/bind when that lightweight reconnect
does not recover the link.

6-r8 extends the same soft-first behavior to an established `link_lost`
event. Offline fake-sysfs tests `test-usb-recover-soft-first.sh` and
`test-usb-recover-soft-link-lost.sh` prove that successful soft recovery
emits `SOFT_RECOVER_OK`, leaves the DWC3 unbind control untouched, and
does not consume a full-recovery attempt. This keeps the standard
controller reset as the fallback while avoiding an unnecessary DWC3
rebind on a stale host-side link.

6-r9 adds a separate bounded path for a host that addressed the UDC but
stopped before SET_CONFIGURATION. When VBUS is online, the selected mode
is Developer/Tethering, and UDC state is `default` or `address` with a
known link speed, recovery first toggles the standard UDC `soft_connect`
and then falls back to the same bounded DWC3 rebind. It never acts on an
unattached UDC or a charger-only cable. The matching offline test is
`test-usb-recover-enum-stuck.sh`.

6-r10 removes the earlier carrier-loss and mode-reattach recovery
paths. A configured UDC with NCM carrier 0 is a valid network state:
Windows may leave the NCM data interface at alt 0 while idle. Rebinding
DWC3 there caused a reset/enumeration feedback loop. Recovery now acts
only after `default`/`address` persists for 30 seconds, does not reset
its attempt budget on a gadget-generation change, and never treats
carrier loss as a USB reset condition. The regression is
`test-usb-recover-carrier-no-reset.sh`; the removed soft-first and
soft-link-lost tests no longer apply.

6-r11 adds `/usr/sbin/samurai-wifi-recover`. The Plasma Mobile Wi-Fi
KCM (`plasma-settings -m kcm_mobile_wifi`) can get stuck sending
NetworkManager radio-control on/off requests; when that happens,
`rfkill` may remain soft-blocked and `wlan0` stays down. The recovery
script kills only that stuck KCM, clears the Wi-Fi rfkill block,
enables the NetworkManager radio and brings `wlan0` up without
restarting NetworkManager, so USB NCM SSH remains available.

Earlier signed candidate:

```text
E:/edk2-samurai-out/standard-arm64-v731/
  usb-hotfix-otg-r8-20261112/samurai-platform-6-r8.apk
SHA-256 a69d81d8cb2729fd51cfc6a9c1e73b001e6efa29e2bf0369c4fb3ced5a4bd3f3
```

The 6-r6 generation fix and the 6-r10 carrier-no-reset policy are the
live recovery implementation. The 6-r8 soft-first fallback was
offline-tested but has been withdrawn because carrier 0 is a valid NCM
idle state and the rebind caused a host enumeration feedback loop. The
6-r10 script is deployed; the signed APK package still needs rebuilding
and package-level verification.

6-r1 moved the runtime USB gadget owner from the board script
`samurai-usb` to the standard postmarketOS stack:

- `usb-signaller` owns configfs modes, UDC binding and the usb-moded D-Bus API;
- NetworkManager owns `usb0` for Developer and Tethering modes;
- `unudhcpd` provides the standard `172.16.42.1` / `172.16.42.2` address pair;
- `umtprd` owns FunctionFS MTP;
- `samurai-usb-recover` remains the bounded SM8150 DWC3 controller recovery,
  but restarts the active `usb-signaller` backend.

Board USB descriptors live in
`/etc/usb-signaller.d/90-samurai.toml`, not in a private gadget builder.
The override uses an upstreamable `[gadget]` layer in
`usb-signaller>=0.4.3-r9`: `0525:a4a1`, composite class `ef/02/01`,
`MaxPower=500` and NCM `qmult=20`. MTP uses `0525:a4a2`.

The legacy `/usr/sbin/samurai-usb` remains installed as an explicit
fallback and now tells NetworkManager to release the interface when it is
selected. It is removed from the boot runlevel by the package migration.
The old static NetworkManager `usb0` unmanaged rule is retired.

Runtime evidence on the handset:

- configfs descriptor values match the board drop-in;
- Developer, Tethering and MTP all reach UDC `configured`;
- Windows reports `USB\VID_0525&PID_A4A1` Problem 0 for NCM and
  `USB\VID_0525&PID_A4A2` Problem 0 for MTP;
- Developer/Tethering service transitions now stop the previous OpenRC
  mode service instead of leaving it `crashed`;
- `samurai-usb-recover` reports `armed=1` with the usb-signaller backend.
- a forced `ip link down` recovery re-establishes DWC3 and triggers a
  fresh Windows DHCP lease (`172.16.42.2/24`) without an adapter reset;
  both the composite device and UsbNcm remain at Problem 0.

Still requiring physical cable/orientation checks, unplug/replug after a
suspend, and long-time suspend/resume soak. The ordinary reboot path is
recorded in `linux-port/docs/PMOS-USB-20261112.md`; it starts the
standard usb-signaller Developer gadget without the legacy service.

5-r30 extends `samurai-usb-recover` with a bounded VBUS-on reattach
watchdog. It already recovers an established NCM link after 12 seconds
lost while VBUS is present, performing at most two complete DWC3
unbind/bind cycles per cable session. The new path also waits 20 seconds
after a VBUS 0 -> 1 transition if the UDC never becomes `configured`;
that covers an unplug/replug that leaves the controller stale. A
successful recovery returns to the normal five-minute attempt-reset
window. Both the established-link and reattach paths use the same
standard DWC3 unbind/bind interface, log their reason, and stop after the
two-attempt budget; there is no infinite loop or private kernel ABI. The
reattach state machine has an offline fake-sysfs test. It only activates
after a cable session has reached UDC `configured` at least once, so a
wall charger that never enumerates does not cause a rebind loop. A physical
unplug/replug and cold-boot acceptance are still required.

5-r26 removes the 5-r25 USB VBUS wake udev rule. The PM8150 GPIO10
`extcon-usb-gpio` assumption was disproved on hardware: the vendor DTS
comments out `vbus-gpio` and its `&usb1` consumer, GPIO10 does not follow
VBUS, and IRQ 120 never fires. The package no longer installs any extcon
wake policy. The board now uses the standard DWC3 gadget suspend/resume
path; USB wake is not claimed. See
`linux-port/docs/USB-REMOTE-WAKE-20261111.md`.

5-r23 removes the board-owned `samurai-sleep-inhibitor` service,
`/etc/samurai/sleep-inhibitor.conf` and installed
`samurai-usb-sleep-guard` from the production package. The handset now
uses the postmarketOS default `/etc/sleep-inhibitor.conf`
(`ssh-session-open` + `apk-running`) and the upstream `sleep-inhibitor`
service. The carrier-only guard is debug-only and lives outside the
package in `linux-port/debug/sleep-policy/`; it is never registered in a
runlevel.

This is a settings-provenance cleanup, not a new suspend policy. KDE
PowerDevil keeps its upstream defaults; the package does not ship a
`powerdevilrc`. The per-test `elogind-inhibit` lock remains in
`linux-port/scripts/test-usb-ncm-stability.py` and is released when the
test exits.

5-r22 adds the Alpine `neard-openrc` dependency and places the upstream
`neard` service in the default OpenRC runlevel. The package does not start
or restart a live daemon during upgrade; the standard `org.neard` D-Bus
adapter is probed separately. The signed offline candidate is
`E:/edk2-samurai-out/standard-arm64-v731/nfc-neard-20261109/`.

5-r21 is installed on the handset. A controlled ordinary reboot created a
fresh boot ID with UDC `configured`, `usb0` carrier 1 and configfs
`qmult=20`, so the fix is applied by the normal startup path rather than by
the manual runtime experiment. The package remains `noarch`; it uses only
the mainline `f_ncm`/`u_ether` configfs interface.

5-r20 removes the remaining board-level service ordering that can turn a
slow NCM or radio bootstrap into a late first SSH: `sshd` is no longer
ordered behind `samurai-usb`, NetworkManager no longer waits for
`samurai-radio`, and ModemManager treats the radio as an optional ordered
service instead of a hard dependency. This follows the official
postmarketOS OpenRC behavior, where the generic network and SSH daemons
start independently and discover devices through udev/QRTR. The change is
an offline candidate until an ordinary reboot and the timeline collector
prove that Wi-Fi association, DHCP and SSH still converge.

5-r23 goes one step further and removes the remaining local
`wpa_supplicant`/ModemManager `rc_use`/`rc_after` lines, restoring the
official base-ui files rather than keeping a board ordering policy.

5-r19 aligned the default sleep policy with postmarketOS/Nura base UI. The
standard `sleep-inhibitor` plugins remain `ssh-session-open` and
`apk-running`; an active SSH session keeps the system awake while the panel
can stay off. The USB-NCM carrier guard is no longer loaded by default,
because keeping a charging-only cable from ever suspending the phone is an
unnecessary platform-wide constraint. The helper remains installed for
explicit opt-in unattended USB maintenance; its YAML entry is documented as a
commented example in `/etc/samurai/sleep-inhibitor.conf`.

5-r18 removes the historical fixed uptime-60 and 10-second isolation waits
from the legacy `samurai-bluetooth boot()` path. The Wi-Fi bootstrap
completion and display registration are now the readiness gates; an optional
bounded isolation window remains available through
`SAMURAI_BT_BOOT_MIN_UPTIME` and `SAMURAI_BT_BOOT_SETTLE`. The installed
`bluetooth` init currently calls `start()`, so this is not a device-proven
Bluetooth boot fix; the change only removes dead waits from an unused path.

The signed offline candidate is
`E:/edk2-samurai-out/standard-arm64-v731/bluetooth-fast-20261108-r4/samurai-platform-5-r18.apk`
(SHA-256 `81fa68c3806d13d0ab5d63d1b71ce95cb45d22faef15bf064d6b3c8e4f404fc2`).
It was not installed when this note was written; r21 is now the
device-proven package.

5-r17 在 5-r16 基础上把 `samurai-wifi` 启动时固定的 45 秒等待改为
有界 MPSS `running` 轮询；MPSS 正常进入运行态时立即放行
`wpa_supplicant`/NetworkManager，异常时仍最多等待 45 秒并失败记录。
这是启动时延修复，不改变 WiFi 固件/NV 的私有来源。

5-r16 是上一已安装版本，在 5-r15 启动依赖加固之上
增加标准 `dnsmasq` USB NCM DHCP 服务（`10.42.0.1/24`），同时保留
`169.254.42.1/16` 调试地址和现有 SSH 主机密钥。5-r15 修正了
`samurai-radio`、`samurai-usb` 和 `samurai-ssc` 在启动早期硬件尚未
枚举时把整条 OpenRC 依赖链拖垮的问题：

- `samurai-usb` 按需加载标准 `socinfo` 驱动，并把 SoC serial 等待从
  30 秒延长到 60 秒；
- `samurai-wifi` 对 UFS/radio 来源和 `wlan0` 枚举分别使用 120 秒有界
  等待；失败日志保存到 `/var/log/samurai/wifi-boot-failure.log`；
- NetworkManager 把 `samurai-radio` 从硬依赖改为有顺序的软依赖；
- sshd 把 `samurai-usb` 从硬依赖改为有顺序的软依赖，Wi‑Fi SSH 不再
  因 NCM gadget 失败而拒绝启动；
- wpa_supplicant 在存在 `samurai-radio` 时等待其完成；
- `samurai-ssc` 的 init 依赖仍保留顺序，但 SensorProxy 对 SSC 使用
  软依赖，SSC 慢启动不再阻塞桌面。

5-r16 已在设备上通过 APK 签名、`samurai-usb start` 幂等启动、DHCP
地址/DNS 服务、服务状态和桌面边界检查；**仍需多次冷启动验证**，不能
把一次运行态冒烟当作启动顺序问题已经根治。

5-r21 把 CDC NCM 的 configfs `qmult` 显式设为 20，仍使用主线
`f_ncm`/`u_ether` 接口，不引入私有传输层。Windows UsbNcm 在连续
4 MiB device-to-host 读取时会短暂停止 bulk-IN 轮询；默认 `qmult=5`
（10 个在途请求）在同一设备上观测到约 31 秒 TX 停顿并导致
`Broken pipe`。`qmult=20`（40 个在途请求）在同一最终 boot 上连续
24 次 4 MiB 下载全部成功，耗时约 0.36–0.61 秒；仍需在普通重启和
冷启动后复测。普通重启后的自动 `qmult=20` 已通过，并在同一 boot
完成双向 24/24、1798.828 秒 NCM 心跳和 1810 样本/1820.51 秒
Wi‑Fi 心跳；冷启动仍未验。
若 initramfs 已创建旧 gadget，脚本只给出需要重启
重新创建 gadget 的告警，不会在运行中的 NCM 上强拆链路。

5-r14 从标准 ARM64 平台的依赖中移除 `samurai-charging`。Linux v7.3.1
使用 DTS `mps,mp2650` 绑定和内核 `power_supply` 类；历史充电实验包
继续存在，但只按显式 opt-in 使用，不再由板级元包自动带入。

5-r13 是 UDC 发现候选（历史）：优先保留 `a600000.usb`，缺失时接受唯一的
`/sys/class/udc/*`，也可用 `SAMURAI_UDC` 覆盖；`samurai-usb`、
sleep guard 和只读检查脚本使用同一规则。当前设备仍走原来的
`a600000.usb` 分支；此版本尚未构建、安装或实机验收。

5-r12 曾提供 `post-upgrade` 钩子（历史），保证 OpenRC 在升级而非首次安装时也会
切换板级 sleep-inhibitor 的 runlevel 并清理旧 cgroup。

5-r11 曾把板级 sleep-inhibitor 的 runlevel 切换做成幂等操作（历史），并清理旧
`openrc.sleep-inhibitor` cgroup 中可能遗留的插件子进程。板级服务使用
独立的 `openrc.samurai-sleep-inhibitor` cgroup，不会误杀当前的 USB
guard。

5-r10 是历史实现，5-r23 已删除其板级服务。它曾不再安装上游
`sleep-inhibitor-openrc` 拥有的
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

5-r7 曾增加 `/usr/libexec/samurai-usb-sleep-guard`（历史）；5-r23 已把它移出
生产包。DWC3 在系统
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
