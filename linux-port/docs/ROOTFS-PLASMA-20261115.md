# 完整 Plasma Mobile rootfs（2026-11-15）

本轮按 pmaports `stable` 基线从零构建完整发行版 rootfs，替代此前
console 基底 + 手工补装的状态。构建成功并通过离线校验；**尚未刷入
设备**，实机验收未完成。

## 清理与空间

删除的过时构建（均为可复现产物，源码树保留）：

| 目录 | 回收 |
| --- | --- |
| `samurai-v731-usbwake-final-build-20261110` | 2.3 GB |
| `samurai-v731-build-archive-20261108` | 2.3 GB |
| `samurai-v731-standard` | 2.2 GB |
| `samurai-v731-clean` | 1.8 GB |
| `linux-rc6-clean` | 1.8 GB |
| `repro-samurai` | 1.7 GB |
| `charging-integration-20261026-01` | 15 GB |
| `pmos-samurai-rootfs01` / `kernel109` 等 | 8.5 GB |
| `x2pro-linux` 重复内核源码树 | 10 GB |

`charging-integration-20261026-01` 里被配方引用的两个文件已转移到
`~/charging-management-kept-20261114/`，并同步更新：

- `linux-port/scripts/build-eud-off-boot.py` 的 `DEFAULT_DTB`
- `linux-port/configs/v7.3.1/samurai.config` 的 `CONFIG_INITRAMFS_SOURCE`

WSL `ext4.vhdx` 原为 216 GB / 实际 148 GB，开启稀疏模式
（`wsl --manage Ubuntu --set-sparse true`）后 C 盘可用从 1.28 GB
恢复到 44 GB。

## 构建基线

`0a02ba24c921e151e2edfc509c438382f4e4e574`（pmaports `stable` 基线）
检出到 `~/samurai-dist-repo`，该提交是唯一同时包含
`community/unudhcpd`、`community/usb-signaller` 与
`device-realme-samurai` 的配方集合。

工作树 `codex/standard-arm64-settings` 与 `origin/stable` 都已移除
这两个设备包，不能直接用于构建。

配置：`plasma-mobile` + `ui_extras=true`、`kernel=none`、OpenRC。

## 构建结果

15 个目标包全部构建成功（另有 `crossdirect`、`unudhcpd`、
`usb-signaller`、`libcamera` 单独构建）：

| 包 | 版本 |
| --- | --- |
| libcamera / -ipa / -tools / -gstreamer / -v4l2 | 99990.7.2-r33 |
| samurai-camera-config / samurai-camera-stack | 0.1.0-r28 |
| samurai-platform / -pulse | 6-r18 |
| samurai-desktop | 4-r16 |
| usb-signaller | 0.4.3-r11 |
| unudhcpd | 0.5.0-r2 |
| mesa-vulkan-freedreno-samurai | 26.2.4-r2 |
| modemmanager / libmm-glib | 1.25.95_git20261005-r4 |
| geoclue | 2.8.2-r1 |
| samurai-gnss-assist | 2-r1 |

### 构建过程中处理的三个缺口

1. `unudhcpd>=0.5.0-r2`：上游索引只有 `0.5.0-r1`，必须先单独
   `pmbootstrap build unudhcpd` 让本地索引出现 r2。
2. `usb-signaller>=0.4.3-r9`：同理，先单独构建 r11。
3. `libcamera` 固定 `99990.7.2-r33`，但索引被上游 `99990.8.0-r1`
   覆盖，导致 `samurai-camera-config` 的精确依赖无法解析；必须
   `pmbootstrap build --force libcamera`。

### 源码下载绕行

`mesa.freedesktop.org` 直链限速约 45 KB/s 并在 17 MB 处 stalled。
改用重定向目标 `https://archive.mesa3d.org/mesa-26.2.4.tar.xz`
（约 320 KB/s）手工写入 `cache_distfiles`，sha512 与配方一致。

Alpine CDN 的 TLS 握手间歇失败，镜像切到
`https://mirrors.aliyun.com/alpine/`（约 2 MB/s）。postmarketOS
官方镜像无国内可用替代，靠重试。

## rootfs

1092 个包、2.6 GiB 内容。相对手机当前系统的实质变化：

- 装全 `postmarketos-ui-plasma-mobile` + `-extras`（含 okular-mobile、
  tokodon、neochat、koko、arianna、qmlkonsole）。
- `samurai-platform` 的 post-install 自动启用 NCM 链路所需服务。

固件按 `samurai/provision-firmware.py` 从本机手机只读拉取：
`/lib/firmware`（40 MB）、A.11 SLPI、`sdsp/` 与 sensors 源、
磁力计配置（sha256 `9fe3391f…` 与脚本内置值一致）、34 项 radio
manifest。写入 `lib/firmware` 与 `/var/lib/samurai/firmware`。

定制收尾（`finalize-plasma.py`，随本轮新增）：

- `tinydm` autologin UID 10000 + `startplasmamobile`
- `sshd_config.d/99-samurai.conf` 保留密码与 PAM
- `~user/.ssh/authorized_keys` 写入 `samurai-usb-bringup` 公钥
- 保留 `usb-signaller`（`default_mode=developer_mode`）与
  `unudhcpd.usb0` 开机启用

首轮收尾漏了 `var/lib/tinydm/default-session.desktop`，会让
`tinydm-run-session` 以 "no session configured" 直接退出、桌面
起不来。已补成指向 `plasma-mobile.desktop` 的符号链接，并删除
tinydm 不支持的 `AUTOLOGIN_CMD`。首版镜像因此作废，镜像按修复后
的 rootfs 重新生成，产物哈希以 `SHA256SUMS.simg.txt` 为准。

### 离线校验（`check-plasma.py`，随本轮新增）

```
installed_package_count: 1092
installed_files_verified: 902
arm64_elfs_verified: 228
services_enabled: dbus elogind tinydm networkmanager sshd usb-signaller
                  modemmanager bluetooth wpa_supplicant unudhcpd.usb0
ncm_developer_mode: true
ssh_public_key: true
ui_autologin: plasma-mobile
gi_qmi_namespace_loaded: true
hardware_tested: false
```

## 镜像

| 产物 | 大小 | SHA-256 |
| --- | --- | --- |
| `samurai-rootfs-f2fs-partuuid.raw.img` | 119,033,245,696 | 未归档（本地 `~/samurai-build/rootfs-image/`） |
| `samurai-rootfs-f2fs-partuuid.simg` | 2,746,311,720 | `2f0480113e3c71e05cae5516e70c6fb7a9e369e28480687513c3f97bfe0a67f8` |

镜像容量与 `userdata`（`/dev/sda16`, PARTUUID
`fce252a8-deb1-7d74-0dbc-bfdabfa3710a`）逐字节一致，F2FS UUID
保留为 `32dd1191-5c73-4eb7-8d45-2213af0f2001`，与当前
`/etc/fstab` 匹配；分区表不需要改动。`sload.f2fs` 灌入后
`fsck.f2fs` 无错误。

## 刷入前修正（2026-11-15 晚）

首版镜像漏装了两个已构建但未进入 rootfs 的设备包，会造成实际功能
缺失：

| 包 | 缺失后果 |
| --- | --- |
| `samurai-radio-tools` | `/usr/sbin/samurai-tqftpserv`、`-rmtfs-cow`、`-dms-mac-read`、`-bt-address` 全缺；`samurai-radio` 开机服务直接调用它们，Wi‑Fi/modem 固件加载必失败 |
| `samurai-openrc` | 缺 `iio-sensor-proxy` 的 `LIBSSC_LIGHT_DATA_TYPE`/`LD_LIBRARY_PATH`，且 `bluetooth.initd` 少了 `need samurai-radio` 与 `samurai-bluetooth` 前置、`elogind.initd` 少了 PID 跟踪 |

两者都在镜像自带的 `@samurai` 仓库里，但该索引签名密钥
（`pmos@local`）不在镜像内，无法在设备上 `apk add`。改为离线
用 apk 2.14 在 chroot 中安装（`--allow-untrusted --no-network`），
包数 1092 → 1093（`samurai-radio-tools`），再替换 4 个标准
openrc 包后为 1090，仍是全部必需项。

复核结果（`linux-port/scripts/inspect-rootfs.py`）：

- 22 个必需包全部 `OK`，6 个必需命令全部 `OK`；
- `samurai-radio`、`bluetooth`、`elogind`、`iio-sensor-proxy`、
  `postmarketos-zram-swap` 仍在默认 runlevel；
- `fsck.f2fs --dry-run` 无错误；sparse 还原后的 raw 与源逐字节一致。

产物位置：
`E:\edk2-samurai-out\standard-arm64-v731\rootfs-plasma-20261115\`

## 刷入（待执行）

`linux-port/scripts/flash-plasma-rootfs.ps1` 默认只做校验与
`getvar` 预检，必须显式确认才写 `userdata`，不动 boot/logdump/DTB。

现场前置：设备进入 fastboot（关机后 Volume-Down + Power）。

2026-11-15 晚设备已进入 fastboot（`62bc28a1`，`product: msmnile`，
`max-download-size: 805306368`）。脚本 dry run 通过：镜像哈希/尺寸
校验、串号匹配、`-S 767M` 分块，均只指向 `userdata`。

### 实际刷入（2026-11-15 15:47–16:04）

已执行并完成写入：

```
flash-plasma-rootfs.ps1 -Confirm:$true
# image verified ... sha256=2f0480113e...
# fastboot -s 62bc28a1 -S 767M flash userdata <simg>
# flash complete; rebooting into the existing EDK2 boot chain
```

脚本打印了 `flash complete`，说明 `userdata` 写入成功，耗时约
3 分钟。**但随后的 `fastboot reboot` 失败**：

```
fastboot -s 62bc28a1 reboot
FAILED (AdbWriteEndpointSync failed: 信号灯超时时间已到 (121))
```

设备随后枚举状态：

- Windows PnP：仍为 `USB\VID_18D1&PID_D00D\62BC28A1`，
  `Android Bootloader Interface`，没有掉到 EDL `05c6:9008`；
- `fastboot devices`：串号变成 `????????????`；
- `getvar product` / `continue` / `reboot`：全部
  `AdbWriteEndpointSync failed (121)`；
- WSL `adb devices` 为空，无 `172.16.42.x` NCM 接口。

即：**刷写已完成，bootloader 的 USB 命令通道在写入后挂死**，
设备没有按预期重启进 Linux。这与镜像内容无关；写入前的镜像校验
和 `fsck` 都通过，刷写阶段也未报错。

现场恢复：长按电源键约 15 秒强制断电，再正常开机；若再次进入
bootloader，按 Volume-Down + Power 进入 fastboot 后重试
`fastboot reboot` 或直接开机。不要重复刷写 `userdata`。

### 进入系统后 NCM 排查（2026-11-15 16:10）

设备开机后 NCM 链路是通的：Windows 枚举 `UsbNcm Host Device #3`
（MAC `02-62-BC-28-A1-02`），`169.254.42.1` 可 ping 通（2 ms）。

但有两个现象说明**当前运行的不是本次刷入的 rootfs**：

| 项 | 本次镜像应有 | 设备实际 |
| --- | --- | --- |
| SSH 服务 | `openssh` / `sshd` | banner `SSH-2.0-dropbear_2026.94` |
| DHCP 网段 | `172.16.42.1`（`unudhcpd.usb0`） | 无 DHCP 应答，Windows 只得 APIPA |

根因：设备内核内嵌的是**调试 initramfs**
（`CONFIG_INITRAMFS_SOURCE=/home/cy122/charging-management-kept-20261114/baseline-initramfs.cpio.gz`），
其 `init` 结尾是：

```sh
# EUD_RX_TEST_LOOP: stay alive so the RX probe keeps running and the box does
# not panic and reboot after the dump (handover 27.2, candidate b).
while true; do sleep 3600; done
```

整个脚本没有任何 `switch_root`，因此 `userdata` 上的 rootfs 从未被
挂载。NCM gadget、`samurai-usb`、dropbear 都由这个 initramfs 提供。
`docs/27-userspace-and-shortcuts.md` 也把它标为 bring-up 工具，
“a real root filesystem and switch_root” 才是后续步骤。

### 下一步

要真正进入发行版 rootfs，必须换掉内嵌调试 initramfs 的内核（或让
initramfs 执行 `switch_root` 到 `userdata`）。当前 `Image-v731` 就是用
这个调试 cpio 编出来的，所以仅刷 `userdata` 不会改变运行状态。

调试 initramfs 上的 dropbear 只接受 publickey，密钥在
`/root/.ssh/authorized_keys`（`SHA256:MJFUR9BsjAXOdjFL6zVatq+XtOT+d5F4fYQV0SkDUTs`）。
本次尝试用同一私钥登录被拒，说明该实例的 `authorized_keys` 与本地
私钥已不匹配；这条路不能作为验收依据。

## 刷入后必须补的一步：内核模块

镜像里 **没有** `/lib/modules`。设备是 `kernel=none`，模块不随
rootfs 打包，必须另装 `7.3.1-rmx1931-samurai-v731`（与 EDK2 内
`Image-v731` 的 release 严格一致）：

```
tar -xzf modules-v731.tar.gz -C /
```

漏装会让 `samurai-bluetooth` 找不到 `hci_uart.ko`/`btqca.ko`，
Wi‑Fi/modem 相关模块同样不可用；模块目录名与 `uname -r` 有一字
之差都会失效。这是首启动后、验收前的前置条件。

## 未完成

- 实机刷入与首启动。
- 首启动后安装匹配 release 的内核模块（见上节）。
- 开机后 NCM SSH 连通性验收（`172.16.42.1`）。
- 应用集补齐与实机验收（见下节）。

## 完整应用集补齐（2026-11-17）

后续实机检查确认 rootfs 为 1088 个包，Firefox、Discover、Dolphin、
Konsole、Kate 等均未安装。原因不是桌面菜单隐藏，而是构建集合本身：

- `postmarketos-ui-plasma-mobile` 在 aarch64 上选择
  `postmarketos-ui-plasma-mobile-web`，默认浏览器是 Angelfish；
  Firefox 只在 armv7 分支作为 `postmarketos-ui-plasma-mobile-web`
  的替代品。
- `postmarketos-ui-plasma-mobile-extras` 的
  `_pmb_recommends`（Dolphin、KClock、KWeather、Plasma Dialer、
  QMLKonsole、Spacebar、TTY Escape 等）没有进入本轮 rootfs；
  `extras-web` 的硬依赖（Arianna、Koko、NeoChat、Okular Mobile、
  Tokodon）则已安装。
- Discover 不属于 Plasma Mobile UI 的依赖或推荐集合，必须显式安装
  Alpine 的 `discover`。它带 `libapk-qt` 原生后端和
  `discover-backend-fwupd`，不是旧的 `plasma-discover` 包名。

补齐集合为 `samurai-apps` 元包（`linux-port/packages/samurai-apps`），
包含：

- Firefox ESR + `mobile-config-firefox`；
- Discover + fwupd 后端；
- 上游 `_pmb_recommends` 和 `extras-web` 之外的完整 Plasma Mobile
  推荐应用；
- Konsole、Kate、Ark、Gwenview、KCalc、Spectacle 等常用桌面工具。

`plasma-camera` 被有意排除：Alpine 当前二进制依赖 libcamera 0.8，
而板级相机栈固定 `libcamera=99990.7.2-r33`（0.7 ABI）。直接安装会
升级/替换 `libcamera` 并破坏 `samurai-camera-config` 与
`samurai-camera-stack`。要恢复 Plasma Camera，必须先用板级
libcamera 重新构建它，不能把它加入普通应用集。

离线解析以设备当前 `/lib/apk/db/installed` 和 `/etc/apk/world`
为基线。180 个 APK、约 241 MiB，模拟事务 181 项，没有降级、升级
或冲突；`usb-signaller-openrc` 与 `modemmanager-openrc` 保持
`@samurai` 的 r11/r4，不被 Alpine 的 r0 覆盖。

设备侧安装使用
`linux-port/scripts/install-plasma-apps.sh`。该脚本只暴露本地
`@samurai` 索引、使用 `--no-network`，避免解析到旧版 Alpine openrc
子包，并在安装后执行 `check-plasma-apps.sh` 和 KService 缓存刷新。

产物与校验清单位于：

`E:\edk2-samurai-out\standard-arm64-v731\plasma-apps-20261117\`

2026-11-17 已完成实机安装：

- 180 个本地 APK 全部通过 `SHA256SUMS`，`apk add` 以
  `--no-network` 安装，未从网络解析替代版本；
- 包数 1088 → 1269，`check-plasma-apps.sh` 返回 `RESULT: PASS`；
- Firefox ESR、Discover、Dolphin、Konsole、Kate 等命令和
  `.desktop` 入口均存在，Discover 的 apk KAuth helper 存在；
- `libcamera` 保持 `99990.7.2-r33`，
  `usb-signaller-openrc` 保持 `0.4.3-r11`，
  `modemmanager-openrc` 保持 `1.25.95_git20261005-r4`；
- `samurai-apps` 已写入 apk world，可整体审计或回退。
- `@samurai` 索引的签名公钥
  `pmos@local-6af86f33.rsa.pub` 已安装到 `/etc/apk/keys`；
  `apk verify --keys-dir /etc/apk/keys` 对
  `/var/lib/samurai/apk/aarch64/APKINDEX.tar.gz` 返回 `OK`。

实机启动时系统时间原为 1970 年，已用 `date -s` 校到
2026-11-17 09:06 CST，否则 Discover 访问 HTTPS 软件源会因证书
有效期失败。该机没有可写的 `/dev/rtc`，`hwclock -w` 返回
`No such device`；重启后时间仍会回退，需要 Wi‑Fi 下由 chronyd
校时或再次手动校时。

### Wi‑Fi 与商店源（2026-11-17）

- 手机已连接电脑同一网络的 5GHz BSSID
  `FA:8C:21:91:15:68`（SSID `TP-LINK_156D`），地址
  `192.168.0.100/24`，默认路由 `192.168.0.1`。
- 网关 ping、DNS 解析和 HTTPS 均通过；Alpine 索引返回 200，
  postmarketOS 镜像返回 301 跳转到 `mirror.nura.eco`。
- 原 rootfs 只把公钥放在 `/usr/share/apk/keys`，`/etc/apk/keys`
  缺少官方公钥，导致所有仓库显示 `UNTRUSTED signature`。已把
  `/usr/share/apk/keys` 下的 Alpine 与 postmarketOS 公钥复制到
  `/etc/apk/keys`；`apk update` 现在返回
  `OK: 37430 distinct packages available`。
- 为防止 Discover 安装新包时把 `@samurai` 的 openrc 子包降级，
  `/etc/apk/world` 已固定：
  `usb-signaller=0.4.3-r11`、
  `usb-signaller-openrc=0.4.3-r11`、
  `modemmanager=1.25.95_git20261005-r4`、
  `modemmanager-openrc=1.25.95_git20261005-r4`。
  `apk add --simulate nano` 现在只安装 nano，不再降级上述包。
- 固定后补入了 gnome-keyring/gcr 五个依赖，当前包数为 1274。

## 官方稳定版 rootfs（2026-11-18）

按 postmarketOS `v26.06` + Alpine `3.24` 从零构建的 systemd 稳定版，
替代此前的 edge/OpenRC 系统。**已刷入实机并首启验证（NCM、SSH、Wi‑Fi
均工作）；首启后修正的两项缺陷已回写配方，最新镜像待重新刷入。**

### 实机首启结果（2026-11-18）

| 项目 | 结果 |
| --- | --- |
| `/etc/os-release` | `postmarketOS v26.06`，`uname -r` = `7.3.1-rmx1931-samurai-v731-usbwake-otg` |
| systemd | 起来；`usb-signaller`、`unudhcpd@usb0`、`NetworkManager`、`ModemManager`、`iio-sensor-proxy`、`plasma-mobile`、`sshd` 均 `active` |
| NCM | 主机经 DHCP 取得 `172.16.42.2/24`，`ssh user@172.16.42.1` 可用 |
| Wi‑Fi | 预置 profile 直接生效：`TP-LINK_156D: activated`，`wlan0` = `192.168.0.109/24`，可与 NCM 同时 SSH |

首启暴露并已修正的两处缺陷：

1. `device-realme-samurai` 的依赖漏了 `samurai-radio-tools`，导致
   `/usr/sbin/samurai-tqftpserv`、`samurai-rmtfs-cow` 不在 rootfs，
   `samurai-radio` 立即失败、Wi‑Fi 与蓝牙都起不来。已把它加入依赖
   （`device-realme-samurai` 2-r1）。
2. `samurai-radio-start` 不幂等：`samurai-wifi` 没有 stop 路径，
   `prepare()` 断言 MPSS 处于 `offline`，服务重启时必然失败。已改为
   首启执行、`ready` 存在后直接返回成功，并把 unit 设为
   `RemainAfterExit=yes`、去掉 `Restart=`（`samurai-systemd` 1-r4）。

两处缺陷的现场绕过（不重刷即可复现）：今天已在设备上 `apk add
--allow-untrusted samurai-radio-tools-1-r0.apk` 并覆盖
`samurai-radio-start`，Wi‑Fi 随即可用；但该绕过不会进入 APK 数据库
之外的配方，重刷后以新镜像为准。

### OpenRC 残留清理（2026-11-18）

systemd 构建不需要 `init.d`，但四个包的 `package()` 里仍无条件安装：
`samurai-platform`（3 个）、`samurai-ssc`（1 个）、
`samurai-gnss-assist`（1 个）。已改成 `$pkgname-openrc` 条件子包
（`install_if="<pkg>=<ver> openrc"`），主包不再携带 OpenRC 脚本：

| 包 | 主包版本 | 子包 |
| --- | --- | --- |
| `samurai-platform` | 6-r21 | `samurai-platform-openrc` 6-r21 |
| `samurai-ssc` | 1-r2 | `samurai-ssc-openrc` 1-r2 |
| `samurai-gnss-assist` | 2-r3 | `samurai-gnss-assist-openrc` 2-r3 |

镜像内 `etc/init.d` 已为空，`apk` 数据库版本与配方一致。这样保留
OpenRC 变体（另有用例）的同时，systemd 镜像只装它需要的东西。

另修正一处误操作：`temp/libcamera` 是 v26.06 上游的受版本控制目录
（Pinephone softISP 三补丁），此前被误删，已 `git checkout --` 还原。

### 适配面审计（2026-11-18）

对上游 `v26.06` 的改动只有一处文件内容修改，其余全是新增包：

| 类别 | 内容 |
| --- | --- |
| 修改上游文件 | `cross/crossdirect/crossdirect.c`（`argv[0] = newExecutable`，3 行）+ `APKBUILD` 版本号/校验和 |
| 新增设备包 | `device-realme-samurai`、`samurai-platform`、`samurai-desktop`、`samurai-systemd`、`samurai-camera-config`、`samurai-gnss-assist`、`samurai-ssc`、`samurai-libssc`、`samurai-hexagonrpcd`、`samurai-radio-tools`、`mesa-vulkan-freedreno-samurai` |
| 新增社区包 | `usb-signaller`（0.4.3-r11，10 个补丁）、`unudhcpd`（0.5.0-r2，1 个补丁） |
| 新增构建树 | `samurai/`（构建脚本与文档）、`channels.cfg`（channel 元数据，v26.06 分支不带此文件） |
| 删除上游内容 | 无 |

`libcamera` 的 51 个补丁按用途分三类：

- **CAMSS/IPE 硬件管线**（0029–0051，23 个）：本机 SM8150 走 VFE/IPE，
  `simple` 软件 ISP 只能出低帧率 RAW。`0029` 单独 3281 行、动 26 个文件，
  是把 qualcomm camss 私有 UAPI 接进 libcamera 的核心补丁，无法再拆分。
- **本机传感器增益**（0007/0008/0011/0021/0024/0025）：IMX319、IMX471、
  S5K3M5、S5KGW1 的模拟增益模型，缺这些会曝光失控。
- **通用 softISP/上游件**（0001–0006、0013–0020、0022/0023/0026–0028）：
  多数是 upstream 已提交或待合并的修复。其中 `0002`（Sony IMX355）与本机
  四个传感器无关，属于上游 Pinephone 补丁，是**可去除**的一项；其余与
  RAW 抓帧、控制快照、AF 有关，去掉会退化拍照能力。

`0039-synchronous-ipa-reentrancy` 修的是 libcamera 事件循环在同步 IPC
递归派发时的 map 失效，属通用缺陷修复，与设备无关。

### libcamera 收敛与目录归位（2026-11-19）

`0002`（Sony IMX355 传感器属性）已移除：本机四个传感器是 IMX319、
IMX471、S5K3M5、S5KGW1，IMX355 只服务 Pinephone。移除后按顺序重放
其余 50 个补丁，`git apply --check` 全部通过（`applied=50 failed=0`），
补丁编号不连续不影响应用。

同时修正了一个目录归属错误：按上游 `COMMITSTYLE.md`，
`temp/<pkgname>` 是"fork from Alpine"的标准位置。我们的相机包原先放在
`device/testing/libcamera`，与上游 `temp/libcamera` 同名，触发
pmbootstrap 的 `Package libcamera found in multiple aports subfolders`。
现已归位到 `temp/libcamera`（`pkgver` 99990.7.2、`pkgrel` 33、50 补丁），
`device/testing/libcamera` 删除。这样既符合上游约定，也不再需要
绕过 pmbootstrap 的重复检查。

上游的 3 个 Pinephone 补丁（`0001/0002/0003-libcamera-simple*`、
`0003-RFC-egl*`）与 tuning YAML 作为上游暂存内容**原样保留在目录中**，
本机 APKBUILD 不引用它们；`check-sources.py` 因此只比对 APKBUILD 列出的
补丁，不再要求目录内全部 `00*.patch` 都属于本配方。

构建过程中生成的 `ipa-priv-key.pem` 必须留在构建目录、不得进入仓库：
它曾随手动拷贝落到 `temp/libcamera/`，被 `check-sources.py` 的私钥扫描
拦下；现已删除并把 `ipa-priv-key.pem` 加入 `.gitignore`。

构建注意：用 pmbootstrap 的 crossdirect 交叉编译约 9 分钟；直接在
chroot 里跑 abuild 会退化成 `qemu-aarch64-static` 逐目标模拟，耗时超过
1 小时仍无法完成，不要走那条路。

### 自检脚本对齐（2026-11-19）

`samurai/check-sources.py` 与 `samurai/check-rootfs.py` 原为 OpenRC/edge
构建写的，稳定版下有三类失配，已一并修正：

| 问题 | 处理 |
| --- | --- |
| 引用不存在的 `temp/modemmanager`、`temp/geoclue`、`temp/pipewire` | 从配方清单移除；稳定版不再对这些包打补丁 |
| 私钥扫描遍历整个仓库，命中上游 `linux-xiaomi-latte/MOK.key` | 限定为项目自有目录（`samurai/`、`cross/crossdirect`、`temp/libcamera` 及 `samurai-*` 包） |
| `check-rootfs.py` 断言 OpenRC runlevel、`mesa-vulkan-freedreno-samurai`、`samurai-openrc`、`neard`；`logind.conf` 只找 `/etc` | 增加 systemd 分支（校验 13 个 unit、11 个 `multi-user.target.wants` 链接、`display-manager.service`、两个 preset）；`HandlePowerKey=ignore` 按 `etc/` → `usr/lib/` 顺序查找；本地 APK 产物校验只覆盖真正自建的包 |

`check-sources.py` 结果：14 个配方、134 处本地 sha512、159 个源文件、
50 个 libcamera 补丁、198 个文件无私钥内容。

`check-rootfs.py` 在新镜像上通过：13 个 systemd unit 与 11 个开机链接齐备，
374 个已装文件哈希、140 个 ARM64 ELF、`gi.require_version('Qmi')` 均通过，
`hardware_tested` 仍为 `false`（本轮修复尚未实机复验）。

过程中还发现并修掉一处镜像不一致：早前手工写入
`/usr/lib/systemd/system-preset/50-samurai.preset` 后未更新 APK 数据库，
`check-rootfs.py` 报 `Package file changed`。改用 `apk add` 覆盖
`samurai-systemd`/`device-realme-samurai` 后数据库与磁盘一致。

### 构建脚本与文档同步（2026-11-19）

仓库里"一键复现"路径此前仍产出 edge/OpenRC/Phosh，与实机相反，现已全部
对齐到 v26.06 + systemd + Plasma Mobile：

| 文件 | 改动 |
| --- | --- |
| `samurai/bootstrap.py` | `ui=plasma-mobile`、`ui_extras=true`、`service_manager=systemd`；目标包 17 → 13（去掉 `mesa-vulkan-freedreno-samurai`、`geoclue`、`pipewire`、`modemmanager`、`samurai-openrc`，加入 `samurai-systemd`）；`extra_packages` 增加 Firefox ESR / Discover / `mobile-config-firefox` |
| `samurai/sources.json` | `pmaports_base` 从 edge `862c5af2…` 改为 `v26.06` 的 `b72b1699…`，`branch=v26.06` |
| `samurai/finalize-plasma-rootfs.py` | 新增 systemd 分支：写 `plasma-mobile.service.d/10-samurai.conf`（`User/Group=10000`）、建 `display-manager.service` 链接、按 unit 建 `multi-user.target.wants` 链接；tinydm `AUTOLOGIN_UID` 与 `etc/runlevels` 仅保留在 OpenRC 分支 |
| `samurai/README.md` | 包版本、目标包数、仓库通道、`packages/v26.06` 全部更新 |
| `samurai/STATUS.md` | 包版本表与补丁数（52 → 50）更新 |
| `samurai/libcamera-source-lock.json`、`REPRODUCIBILITY.md` | `patched_tree_sha256` 按 50 补丁重放重算为 `387651cc…cde8f` |

验证：`finalize-plasma-rootfs.py` 在镜像副本上跑通（输出 `uid=10000`、
`autologin=plasma-mobile`、`ncm_default=developer_mode`）；随后
`check-rootfs.py` 仍 374 文件 / 140 ELF / GI-QMI 全通过。

**注意**：不要对 `samurai-radio` 执行 `systemctl restart`，也不要
`echo stop > /sys/class/remoteproc/remoteproc1/state`。停 MPSS 会同时
拆掉 Wi‑Fi 与 USB gadget，设备随即重启且 NCM 一并消失，只能长按电源
重启恢复。

### 基线

- pmaports 分支 `v26.06`（`b72b1699328f7ecb9aa171e29b755d5f02875e76`），
  `pmaports.cfg` 的 `channel=v26.06`。
- Alpine `v3.24` main/community；仓库写入 rootfs 为
  `https://mirror.postmarketos.org/postmarketos/{v26.06,extra-repos/systemd/v26.06}`
  与 `https://dl-cdn.alpinelinux.org/alpine/v3.24/{main,community}`。
- `postmarketos-ui-plasma-mobile` 在 v26.06 只支持 systemd
  （`pmb:default-systemd pmb:support-systemd`，无 `pmb:support-openrc`），
  因此整机改为 systemd。官方版本为 Plasma/KWin `6.6.6` + Qt `6.11.1`。

### 保留的最小适配

| 项 | 内容 |
| --- | --- |
| `samurai-systemd`（新增） | 5 个 unit：`samurai-radio`、`samurai-ssc`、`samurai-gnss-assist`、`samurai-usb-network`、`samurai-usb-recover`；2 个 drop-in：`bluetooth`（起 BlueZ 前读 DMS 地址）、`iio-sensor-proxy`（`LIBSSC_LIGHT_DATA_TYPE`、`LD_LIBRARY_PATH`）；`unudhcpd@usb0` 地址 drop-in 与 preset |
| `plasma-mobile.service` drop-in | `User=10000`/`Group=10000`，上游 unit 硬编码 1000 |
| 依赖收敛 | `samurai-camera-config`、`samurai-gnss-assist`、`samurai-ssc`、`samurai-platform` 去掉 `openrc`；`samurai-platform` 去掉 `neard`、`postmarketos-usb-moded` |
| 组包取舍 | 不装 `samurai-openrc`、`mesa-vulkan-freedreno-samurai`（改用 3.24 自带 mesa）、`neard`（3.24 无此包） |
| 工具链 | `cross/crossdirect` 恢复 `argv[0] = newExecutable`，否则 aarch64 交叉编译报 `cannot execute 'cc1'` |
| `libcamera` | 板级 fork `99990.7.2-r32`（51 补丁）；只修 `sha512sums` 与 `source` 顺序不一致，并在 `build()` 里本地生成 IPA 私钥 |

### 离线校验

- `systemd-analyze verify --root` 对 6 个 unit 无输出（语法通过）。
- 镜像内 `PRETTY_NAME="postmarketOS v26.06"`，`/etc/apk/keys` 含 19
  个公钥（含 `build.postmarketos.org.rsa.pub`），`/etc/apk/world` 为
  15 条意图项、无版本锁定，`/etc/machine-id` 已生成。
- 已启用的 systemd 单元包含 5 个 `samurai-*`、
  `usb-signaller-developer-mode`、`sshd`、`wpa_supplicant`，
  `display-manager.service → plasma-mobile.service`。
- `mkfs.f2fs`/`rsync` 拷贝 73740 个条目，源/目标数量一致，
  `fsck.f2fs` 无错误；F2FS UUID 保持
  `32dd1191-5c73-4eb7-8d45-2213af0f2001`，卷标 `pmos_root`。
- 唯一已知缺失：`gst-ptp-helper` 的 `security.capability` 无法在
  WSL 的 f2fs 驱动上写入（仅此一文件，不影响手机功能）。

### 镜像补齐（生成后修正）

pmbootstrap 的 rootfs chroot 在关闭后会丢掉 bind-mount 的
`/etc/apk/keys`，且 `kernel=none` 不会带内核模块。生成镜像后补了四项：

1. `/usr/share/apk/keys/*.pub` → `/etc/apk/keys/`（19 个公钥）；
   rootfs 内 `apk update` 返回 `OK: 30159 distinct packages available`。
2. `/etc/apk/world` 重写为 15 条意图项，去掉 `apk add` 批量安装留下的
   1008 条带校验和锁定条目。
3. `/etc/machine-id` 生成。
4. `/etc/samurai-rootfs-release`（`ROOTFS_ID=samurai-f2fs-rootfs01`）与
   `/lib/modules/7.3.1-rmx1931-samurai-v731{,-usbwake-otg}`（1538 个
   `.ko`，含 `modules.dep`，取自运行中的同机内核）；否则启动 init 会
   回落诊断环境、切根后蓝牙/Wi‑Fi 模块全部缺失。
5. `usb-signaller.service` 的独立启动：上游单元只有
   `WantedBy=usb-gadget.target`，而该 target 没有 `[Install]`、也不被任何
   默认 target 拉取，按原样启用会导致 NCM/SSH 全无。`samurai-systemd`
   增加 `usb-signaller.service.d/10-board.conf`（`WantedBy=multi-user.target`）
   并显式启用；当前启用的板级单元共 8 个（5 个 `samurai-*`、`usb-signaller`、
   `usb-signaller-developer-mode`、`unudhcpd@usb0`）。
6. `systemctl --root=… preset-all --preset-mode=enable-only`：安装顺序导致
   `90-base.preset` 从未生效，`NetworkManager`、`bluetooth`、
   `ModemManager`、`avahi`、`systemd-timesyncd` 都没有开机链接；
   `iio-sensor-proxy` 是无 `[Install]` 的 static 单元，另建
   `multi-user.target.wants` 链接。现 `is-enabled` 全部为 `enabled`。
7. 备份预置：`/home/user`（246 MiB、305 个文件，uid/gid 10000，
   排除 `.cache`）与
   `/etc/NetworkManager/system-connections/TP-LINK_156D.nmconnection`
   （`root:root 0600`，含 PSK）已提前写入镜像，刷完即可登录并自动连
   Wi‑Fi，无需再手工回填。

### 已知风险

- Nura 镜像的 pmOS 仓库中 71 个包由构建端本地密钥重签（索引仍由
  `build.postmarketos.org` 签名），安装时使用 `--allow-untrusted`；
  916 个 Alpine 包为官方签名。
- systemd 首次在该内核上运行，`cgroup2`/unit 依赖满足情况只能实机验证。

### 产物

| 产物 | 大小 | SHA-256 |
| --- | ---: | --- |
| `E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261119-apps\samurai-stable-f2fs-partuuid.simg` | 3,628,436,896 | `93e23bc2c30de36d98797942b7317a38a8c19c330de8699938ed9df7dfffd02e` |

`20261119-apps` 在 `20261119` 基础上补装了上游
`postmarketos-ui-plasma-mobile` 的 `_pmb_recommends` 应用集（34 个包），
以及 `postmarketos-ui-plasma-mobile-extras` 自己的递归推荐（95 个包）；
1116 → 1245，两次都零冲突，`libcamera` 未变。应用包括 Dolphin、Konsole、
Kate、KClock、KWeather、KRecorder、Plasma Camera、Dialer、Phonebook、
qmlkonsole、Spacebar，以及 alligator、audiotube、elisa、itinerary、
kalgebra、kalk、kasts、kdeconnect、keysmith。根因是构建命令带了
`--no-recommends`；README 已修正，`check-rootfs.py` 现在缺任一推荐应用即
失败。

`20261119` 在 `20261118` 之上只修正 `/etc/apk/world` 的 12 条 `<Q1...=`
APK 校验钉（改为 27 条纯包名），避免首启后 `apk upgrade` 无解；解压后
重跑 `check-rootfs.py` 为 1116 包 / 374 文件 / 140 ARM64 ELF / GI-QMI
通过。仓库内副本见 `linux-port/artifacts/samurai-stable-f2fs-partuuid.simg`，
哈希相同。

构建工作区：`~/stable-build-20261117`（aports：`~/samurai-stable-repo`；
镜像离线审计副本在 `~/rootfs-audit-20261119`，只作校验用，不参与构建）。
回退镜像：`rootfs-password-20261117`（edge，`c48581d0…`）；用户数据备份
`E:\edk2-samurai-out\standard-arm64-v731\pre-stable-backup-20261117\`。
