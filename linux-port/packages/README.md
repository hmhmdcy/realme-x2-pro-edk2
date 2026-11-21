# Samurai 软件包与构建配方

本目录保存已在项目中公开的设备软件包、补丁和构建输入。安装状态与实机验收必须按各目录 README 和[当前检查点](../../NEXT-SESSION.md)核对；源码或成功构建不等于已经部署。

**稳定版（v26.06 systemd）只用 `device/testing/` 下的 samurai 板级配方，
加上 `temp/libcamera`。** 本目录中的 `kwin`、`plasma-nm`、`geoclue`、
`modemmanager`、`pipewire-common`、`gst-*`、`phoc`、`samurai-refresh`、
`samurai-snapshot-preview`、`samurai-apps`、`samurai-charging` 均属早期
edge/Plasma 6.8 方案的历史输入，不再进入稳定版镜像；保留是为了可追溯与
回退，不要误当成本轮必须打的补丁。2026-11-19 镜像里 `plasma-nm` 是官方
`6.6.6-r0`，没有任何 KWin/plasma-nm 私有补丁。

### 镜像的基线是 Alpine v3.24（2026-11-20 实测，纠正早期误判）

交付镜像自带 1245 个包，与 **Alpine v3.24** 的 `main` + `community`
索引逐包比对的结果是：

```text
match     1127  (90.5%)   已经是官方版本
stripped    14  ( 1.1%)   同上游、只多了 9999 前缀
drifted     27  ( 2.2%)   版本与 v3.24 不同
absent      77  ( 6.2%)   官方仓库没有这个名字
  其中 15 个是板级包（应当缺席），62 个是 pmOS 的 *-systemd 子包
```

判据来自镜像自身：`alpine-release 3.24.4-r0`、`apk-tools 3.0.9-r0`、
`python3 3.14.10-r1`、`qt6-qtbase 6.11.1-r0`、`kwin 6.6.6-r0`——这些
都只存在于 Alpine v3.24，而不是 v3.22。

**早期的一次结论是错的**：拿 v3.22 索引对比得到"841 个包偏离、67.6%"，
那是基线取错造成的假阳性。同理，"镜像是 edge 快照冒充 v26.06"也不成立——
日期上 Alpine v3.24（2026-05）恰好是 postMarketOS v26.06（2026-06）的
基线。所以 `bootstrap.py` 的 `channel=v26.06` 与镜像内容一致。

复跑方式：

```sh
sh /mnt/e/wsl-recover/work/drift324.sh
```

### 镜像的仓库配置是完整的（2026-11-20 实测，直读镜像）

只读挂载交付镜像后读到的 `/etc/apk/repositories`：

```text
https://mirror.postmarketos.org/postmarketos/extra-repos/systemd/v26.06
https://mirror.postmarketos.org/postmarketos/v26.06
https://dl-cdn.alpinelinux.org/alpine/v3.24/main
https://dl-cdn.alpinelinux.org/alpine/v3.24/community
```

`/etc/apk/repositories.d/60-samurai-board.list` 指向
`/usr/share/samurai/packages`，该目录有 23 个文件（22 个 APK + 索引）。
`/etc/os-release` 是 `postmarketOS v26.06`。

**所以"缺 systemd 仓库"这个假设不成立。** 四个上游仓库 + 板级本地仓库
都在。之前几轮基于推测提出"补仓库"，实测后应予撤回。

### 真正的问题：板级公钥不在镜像里（唯一硬阻塞）

`apk-tools` 自己的验签结果，比任何推测都可靠：

```text
== verify against the image key set ==      （镜像 /etc/apk/keys）
  UNTRUSTED device-realme-samurai-2-r1.apk
  UNTRUSTED libcamera-99990.7.2-r33.apk
  ... （22 个板级 APK 全部 UNTRUSTED）
  UNTRUSTED APKINDEX.tar.gz

== verify against the full key set ==       （/root/installed_keys）
  22/22 verified with the full key set
```

也就是说：**板级包的签名完全有效，但镜像不信任签名它的那把公钥。**

已解包的真实根树 `work/test` 里，`/etc/apk/keys` 只有 18 个 Alpine
官方密钥加 `build.postmarketos.org.rsa.pub`，**没有任何本项目公钥**；
`pmos@local-6aeaf066.rsa.pub` 等 5 个只存在于 WSL 的 `/root/installed_keys`。

（先前我用 `grep -i samurai` 判断"有无板级公钥"，那是错的判据——公钥名是
`pmos@local-*.rsa.pub`，不含 "samurai"。已改为"列出全部非 Alpine 密钥"。）

`repack-embeddings.sh` 本有一步做这件事，当前交付镜像里却没有——
这是这台机器上 `apk upgrade` 无法解析板级依赖的直接原因。

复现方式：

```sh
sh /mnt/e/wsl-recover/work/verify-board.sh
```

### 9999x 前缀、27 个 drifted 与更正后的 7 个（2026-11-20 复测）

`9999` 是 postMarketOS 自己的重建前缀，不是本项目私有。**这里必须按
镜像实际的四个仓库重新比对，否则结论会被放大**：只拿 Alpine
`main`/`community` 对比，会把 pmOS 的 `9999x` 包全算成“漂移”（实测 27
个）；把镜像自己的 `extra-repos/systemd/v26.06` 与 `postmarketos/v26.06`
一起算进去后，真实结果只有 **7 个**：

```text
match     1232 (98.2%)
drifted      7 ( 0.6%)
absent      15 ( 1.2%)   ← 全部是板级包（预期内），0 个意外缺席
```

7 个 drifted 全部是有意的板级适配，不是漏装：

- `libcamera` 及 4 个子包 `99990.7.2-r33`（官方 `99990.7.1-r0`）：
  含 51 条相机补丁，降级会丢掉相机能力；
- `unudhcpd` / `unudhcpd-systemd` `0.5.0-r2`（官方 `0.3.0-r0`）：
  只加一条 DHCP broadcast 回复补丁（Windows NCM 重新枚举后需要）。

早期两个被推翻的判断：

- ❌“841 个包偏离官方、67.6%”——那是拿 Alpine v3.22 索引比对的假阳性；
  镜像基线是 Alpine v3.24 + pmOS v26.06。
- ❌“`tinydm-systemd 122-r0` 是错误打包”——它正是
  `extra-repos/systemd/v26.06` 官方发布的版本（同一索引里就有），
  不需要动。

另外 `gnutls`、`libssl3`、`libcrypto3` 曾差一个 rebuild 号
(`3.5.9-r0` 对 `-r1`)，那是编译镜像时缓存索引还是旧的；现在镜像已随
官方升到 `gnutls 3.8.14-r0`、`libssl3/libcrypto3 3.5.9-r1`。

对照下表即可看出哪些是"同版本只差前缀"、哪些是"镜像确实更新":

```text
dbus 全系列            99991.16.2-r1
networkmanager 全系列  99991.52.2-r1   (libnm 同)
polkit 系列            9999127-r2
upower 系列            99991.91.0-r2
plasma-workspace 系列  99996.6.6-r0
kwin / kscreenlocker   99996.6.6-r0
xorg-server 系列       999921.1.23-r0
accountsservice        999923.13.9-r0
libgnome-desktop 3/4   999944.5-r0
xkeyboard-config       99992.47-r0
cups-libs              99992.4.19-r1
libcamera 全系列       99990.7.2-r33
```

板级仓库 `/root/boardrepo-r17`（22 个 APK）里只有自建包 + libcamera；
上述 `9999x` 包都由 pmOS 官方仓库提供并在官方索引里，不属于板级仓库。
早期文档把“官方重建标记”当成“43 个无法升级的钉子”，这个结论已经
撤回——它们能被官方仓库正常升级。

被误判为孤儿的 `pipewire-spa-libcamera` 与 `pipewire-webrtc`：两者
`0-r0` 都由 `postmarketos/v26.06` 官方索引提供，`origin` 写作
`pipewire-dummy-subpackages` 是 pmOS 的分包方式，不是本地伪造。

`/etc/apk/world` 曾经**不干净**：本轮实测发现 13 条 `<Q1…=` 校验和钉
（`gnutls`、`gst-libav`、`hkdm`、`samurai-desktop` 等），全部来自离线
构建时用 `apk add <文件路径>` 安装。实测证据：`samurai-desktop` 被钉在
4-r19 时，即使板级仓库已发布 4-r20，`apk upgrade` 也只报
`OK: ... in 1254 packages`、什么都不升；把 `<Q…=` 去掉后，同一命令立刻
升级到 4-r20。所以这条钉是**“apk upgrade 看起来没事可做”的真实根因**。
现在 `repack-embeddings.sh` 在所有 `apk add` 之后统一清理 world：
13 条钉 → 0，57 条世界项、0 个 `=`、0 个 `~`，且三个纯库
（`gnutls`/`libssl3`/`libcrypto3`）不再作为用户选择写进 world。

审计工具：`linux-port/scripts/clean-apk-upgrade.sh`（默认只读）。

### SSH 门禁（离线）

```sh
python3 linux-port/scripts/_wsl-samurai/check-ssh-image.py \
    --image E:/edk2-samurai-out/standard-arm64-v731/rootfs-stable-20261119-clean/samurai-stable-f2fs-partuuid.simg
```

它检查 5 件事：`sshd.service` 是否在某个启动目标里启用、`sshdgenkeys`
是否被 `Wants/After` 拉起、`/run/sshd` 是否有创建者、`sshd -T`（在镜像内
用 qemu 实跑）是否监听 `0.0.0.0:22` 且 `PasswordAuthentication=yes`、
登录账户是否可用（shell、密码、authorized_keys）。当前镜像结果：

```text
RESULT: ssh image check passed
```

注意 `/tmp` 在 WSL 里只有 3.9 GB，脚本默认在 `/root` 下展开稀疏镜像
（需要约 120 GB），用完自动删除。

### 镜像不得携带私有凭据

```sh
python3 linux-port/scripts/_wsl-samurai/check-secrets.py --root <image-root>
# RESULT: no private credentials in the image
```

上一版镜像曾把家里的 Wi‑Fi 明文 PSK
（`/etc/NetworkManager/system-connections/TP-LINK_156D.nmconnection`）
烧进去，且该文件不被任何包拥有。现在 `repack-embeddings.sh` 3c 步会删除
任何带 `psk=`/`password=`/`private-key=` 的连接配置，门禁再独立验证一次。

### 无主文件盘点

```sh
python3 linux-port/scripts/_wsl-samurai/check-unowned.py --root <image-root>
# owned: 72810 paths
# unowned: 2818 files under /etc and /usr
```

剩余无主文件主要是 `/usr/lib/modules`（1566 个内核模块）与
`/usr/lib/firmware`（160 个固件）。这是 `kernel-none` 外部内核设计的
直接后果：内核由 UEFI 提供，模块/固件由镜像组装直写，`apk` 不认识它们。
`shared-mime-info` 的 `/usr/share/mime` 缓存（992 个）在首次登录时生成，
属正常。

| 目录 | 内容 |
| --- | --- |
| [apk3](apk3/) | 固定版本 APK 构建、签名和仓库生成工具 |
| [geoclue](geoclue/) | ModemManager GNSS 生命周期补丁与桌面定位依赖 |
| [gst-plugin-pipewire](gst-plugin-pipewire/) | 相机 GStreamer/PipeWire 缓冲修复 |
| [gst-plugins-bad](gst-plugins-bad/) | `viewfinderbin` 预览缩放顺序与 854x480 BGRx 输出 |
| [libcamera](libcamera/) | 相机驱动、IPA、ISP 与颜色处理补丁 |
| [modemmanager](modemmanager/) | 固定 ModemManager 版本及 GNSS 相关补丁 |
| [pipewire-common](pipewire-common/) | PipeWire 与相机客户端生命周期修复 |
| [plasma-nm](plasma-nm/) | 临时桌面层修复：移动 Wi-Fi KCM 的 radio-control 反馈循环；非板级包 |
| [samurai-camera-config](samurai-camera-config/) | 四摄 libcamera 配置、调校与堆规则 |
| [samurai-apps](samurai-apps/) | 完整 Plasma Mobile 应用元包：Firefox ESR、Discover、推荐应用与常用桌面工具 |
| [samurai-charging](samurai-charging/) | 旧 k363 充电实验包；标准 v7.3.1 不使用，默认不启用 |
| [samurai-snapshot-preview](samurai-snapshot-preview/) | 四摄命名、默认主摄与 Snapshot 720p60 取景 caps 覆盖 |
| [samurai-desktop](samurai-desktop/) | Plasma Mobile/tinydm 桌面依赖、自动登录和会话默认配置 |
| [samurai-gnss-assist](samurai-gnss-assist/) | GNSS 辅助数据与无 SIM 电源管理服务 |
| [samurai-platform](samurai-platform/) | noarch 板级公共层：ALSA UCM、Wi-Fi、Modem、USB、蓝牙；PulseAudio 为可选子包 |
| [samurai-refresh](samurai-refresh/) | Phoc/wlr-output-management 历史工具；Plasma 使用 KScreen |
| [phoc](phoc/) | 修复 Phoc 对非首选固定输出模式的处理 |
| [unudhcpd](unudhcpd/) | 标准 unudhcpd 的 DHCP broadcast 回复修复；Developer/Tethering 共用 |
| [usb-signaller](usb-signaller/) | USB gadget 模式栈补丁；含 host→device service 生命周期修复 |
| [device-realme-samurai](device-realme-samurai/) | 设备身份、`deviceinfo` 与 `kernel-none` 外部内核标记 |
| [samurai-ssc](samurai-ssc/) | SLPI/文件服务生命周期与私有传感器注册表 |
| [samurai-libssc](samurai-libssc/) | 带 OEM `wise_light` 支持的 libssc |
| [samurai-hexagonrpcd](samurai-hexagonrpcd/) | SLPI FastRPC 文件服务 |
| [samurai-radio-tools](samurai-radio-tools/) | 蓝牙地址、DMS MAC、RMTFS COW 与 TFTP 服务 |

## GNSS 软件包

阶段203把已经验收的 MM191 和 helper202 纳入 APK 管理。当前实机已安装；离线 rootfs132 镜像尚未更新，整机适配仍未完成。

| 软件包 | 版本 | 内容 |
| --- | --- | --- |
| modemmanager / modemmanager-openrc / modemmanager-udev | 1.25.95_git20261005-r1 | 固定191补丁的 daemon；官方 r0 其它133个文件保持 |
| libmm-glib | 1.25.95_git20261005-r0 | 保持原 ABI 配套依赖 |
| samurai-gnss-assist | 0.1.0-r0 | 202 helper、OpenRC init、安装与卸载钩子、NOTICE |
| samurai-gnss-stack | 0.1.0-r0 | 精确约束上述 helper 与三个 MM r1 包 |

`modemmanager/source-lock.json` 固定上游提交、源码归档、两个补丁、修改后源码和 daemon 哈希。`reference/kernel203/rebuild-mm.py` 在原隔离原生 SDK 中重新编译，原始和处理后的二进制均逐字匹配191。构建器不会把当前系统中未知的 MM 二进制直接装包。

## 构建

使用 APK tools 3.0.8；宿主可为 x86_64 Linux，目标 daemon 是 aarch64。三个官方 r0 APK 须来自固定版本，构建器校验官方签名与固定 SHA-256。构建目录必须是新的 Linux 文件系统目录；不能在 WSL `/mnt/*` 上提取 payload，否则文件模式可能丢失。输出目录可以位于共享盘。

```sh
python3 linux-port/packages/apk3/build.py \
  --inputs /path/to/verified-upstream-apks \
  --candidate /path/to/rebuilt-ModemManager191 \
  --apk /path/to/apk.static \
  --trusted-keys /path/to/official-alpine-public-keys \
  --sign-key /private/path/samurai-linux-203.rsa \
  --build-root /home/build/samurai-gnss-new-build \
  --output /path/to/new-package-output
```

固定构建时间、元数据、文件模式/所有者和压缩参数后，五个 APK 已完成两次独立构建、逐字相同比较。签名索引的生成和验签见 `reference/kernel203/build-repository.py`；不使用 `--allow-untrusted`。未知签名和篡改 payload 的拒绝检查已通过。

首次生成的签名私钥仅保存在主机私有目录，后续复用；勿覆盖、上传或放入 rootfs。手机仅持有公开验签密钥。产物与证据在 `E:/edk2-samurai-out/kernel203`，不纳入源码镜像。

## 当前部署

手机仓库为 `/var/lib/samurai/packages/gnss-203`，包括五个 APK、`packages.adb` 和 payload 清单；公开密钥为 `/etc/apk/keys/samurai-linux-203.rsa.pub`。`/etc/apk/repositories.d/50-samurai-gnss.list` 指向此签名索引。未来升级 MM 必须同时更新配套包和 stack 约束，再验收 LOC 补丁；现有精确约束不是对所有未来仓库升级行为的验收。

安装钩子只启用 helper 的 default runlevel，不在采用现有文件时强制重启。阶段203安装只执行一次事务，之后显式重启 helper 并通过真实 UID10000 GeoClue GNSS-only 会话。MM 进程未重启、二进制内容未变化，但原已加载 inode 已被替换；后续身份检查应校验 `/proc/PID/exe` 内容哈希，不能仅依赖路径不带 ` (deleted)`。

helper 在 GPS 空闲且 chrony 同步时准备 UTC；只在 GPS 活动时按有效性刷新辅助数据，不自行开启 GPS 或切换电源。实际 fix、正 CNR、精度与长期稳定性仍未通过。完整证据见[203报告](../../reference/kernel203/README.md)。
