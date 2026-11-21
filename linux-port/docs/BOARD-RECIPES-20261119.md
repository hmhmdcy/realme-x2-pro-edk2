# 板级配方补齐与清洁升级（2026-11-19）

本轮目标：让**仓库源码**与**实机/镜像里的实际产物**一一对应，并让
`apk upgrade` 在没有任何网络镜像可用时也能干净返回 0。

## 1. 补齐的 6 个板级配方

此前 `linux-port/packages/` 只有 `samurai-systemd` 有配方，其余 6 个
板级包没有可追溯来源。现在它们都在本仓库中，且每个文件都经过
SHA-512 校验：

| 包 | 配方位置 | 内容 |
| --- | --- | --- |
| `device-realme-samurai` | `packages/device-realme-samurai/` | `etc/machine-info`、`deviceinfo` 与 `kernel-none` 子包的 `external-kernel.txt` |
| `samurai-ssc` | `packages/samurai-ssc/` | `samurai-ssc.py` + OpenRC init |
| `samurai-libssc` | `packages/samurai-libssc/` | `libssc.so.2` + `ssc-library.sha256` |
| `samurai-hexagonrpcd` | `packages/samurai-hexagonrpcd/` | `samurai-hexagonrpcd` + `ssc-daemon.sha256` |
| `samurai-radio-tools` | `packages/samurai-radio-tools/` | `bt-address`、`dms-mac-read`（源码在 `reference/kernel97`）、`rmtfs-cow`、`tqftpserv` |

`samurai-radio-tools` 的两个地址工具可以直接从
`reference/kernel97/{samurai-bt-address.c,dms-mac-read.c}` 编译；另外两个
是上游 `linux-msm/rmtfs`、`linux-msm/tqftpserv` 的产物，其上游提交、
补丁和 `source-lock.json` 都在 `linux-port/radio/` 中。

校验方式：

```sh
python3 linux-port/scripts/_wsl-samurai/check-sources.py   # 原始入口（device/testing 布局）
python3 <verify-packages 等价脚本>                        # 本仓库 packages/ 布局
```

## 2. 发现并修复的真实缺陷

### 2.1 板级包的签名公钥不在镜像里

证据：交付镜像 `/etc/apk/keys/` 只有 19 个上游公钥；设备上同样没有
`pmos@local-*`。但 15 个板级 APK 正是用该私钥签名的。

后果：任何把板级包放进 `apk` 仓库的尝试都会得到
`UNTRUSTED signature`，等于这些包永远无法被 `apk` 从仓库安装/升级。

修复：把与签名私钥配对的公钥
`pmos@local-6aeaf066.rsa.pub` 安装到 `/etc/apk/keys/`。该私钥只在构建
主机保留，手机只持有公钥；生成索引后已从手机删除私钥。

### 2.2 15 个板级包在任何仓库里都不存在

证据：`apk upgrade --simulate` 会列出
`device-realme-samurai … usb-signaller-systemd` 共 15 个
“no longer available from a repository”。镜像的 `/etc/apk/repositories`
只有 postmarketOS 与 Alpine 官方源，没有本机源。

修复：把当前实机产物原样打包成**本机签名仓库**
`/usr/share/samurai/packages/aarch64/`（`APKINDEX.tar.gz` + 22 个 APK），
并以 `/etc/apk/repositories.d/60-samurai-board.list` 注册。

验收：

```text
apk verify  每个板级 APK            → OK
apk --no-network upgrade --simulate → OK: 2938.7 MiB in 1245 packages
rc                                  → 0
```

仓库按 arch 子目录布局，避免了 `path repo` 下
`WARNING: opening …/aarch64/APKINDEX.tar.gz` 的无意义告警。

### 2.3 `samurai-gnss-assist` 每次启动都失败

证据：交付镜像的 unit 仍带
`ExecStartPre=/usr/bin/install -d …`，而 systemd 在 `ExecStartPre`
之前就会打开 `StandardOutput=append:…`。日志里是连续多条
`status=209/STDOUT`。服务之所以“在跑”，是因为有人手工建了日志目录。

修复：仓库 `samurai-systemd` 已改为“包本体提供 `/var/lib/samurai/gnss-assist`、
unit 去掉 `ExecStartPre`”，并同步到设备；重启后服务直接 `active`。

### 2.4 `nftables.service` 在每个 boot 失败

证据：内核配置 `# CONFIG_NF_TABLES is not set`，`nft` 直接报
`Unable to initialize Netlink socket: Protocol not supported`；而 Alpine
`90-base.preset` 默认启用该 unit。

修复：在 `samurai-systemd` 的 `50-samurai.preset` 中显式
`disable nftables.service`，并在设备上 `disable + mask`。这既消除了
每 boot 的失败，也避免将来内核补上 netfilter 后突然启用默认拒绝规则。

### 2.5 仓库源码落后于实机

以下 4 个文件在设备上比仓库新；已把设备版本取回仓库（`pkgrel` 相应
递增），保证 `source == artifact`：

| 文件 | 设备 SHA-512 前缀 |
| --- | --- |
| `samurai-platform/usr_sbin_samurai-usb-recover` | `0dde2cb9…` |
| `samurai-platform/usr_sbin_samurai-usb-network-watchdog` | `dfb3105a…` |
| `samurai-gnss-assist/samurai-gnss-assist.py` | `62b725c1…` |
| `samurai-camera-config/camss-s5kgw1.yaml` | `e02ddc2e…` |

`samurai-ssc` 则相反：仓库版本（用 manifest 校验、去掉固定 20 s 等待）
比镜像里的旧版更新，镜像记为**已知偏差**，重建时以仓库为准。

## 3. 本轮实机硬件结论

| 接口 | 结论 | 证据 |
| --- | --- | --- |
| Wi‑Fi | 正常 | `wlan0` `TP-LINK_156D`、5 GHz、-69 dBm |
| USB/NCM | 正常 | `usb0` 同时有 `172.16.42.1/24` 与 `169.254.42.1/16`，主机 ping 1 ms |
| 蓝牙 | 正常 | `58:85:A2:CF:12:BE`，Powered yes |
| 传感器 | 正常 | 加速度/光线/接近/指南针实时读数 |
| 音频 | 正常 | `speaker-test` 双声道输出通过，默认 sink/source 均为 HiFi |
| GNSS | 链路正常 | `mmcli --location-get` 持续输出 NMEA；室内无 fix |
| 手电 | 正常 | 写 `white:flash` 开关成功 |
| 触控/显示 | 正常 | Synaptics S3706A、1080x2400 |
| 调制解调器 | 部分 | modem 已 running，`sim-missing`（未插卡，预期） |
| 相机 | **未通** | `cam -l` 无相机，见下节 |

## 4. 相机：根因已定位，不在本轮修

media graph（用未安装的 `v4l2-utils` 临时解包只读运行）显示：

- 4 个 sensor 实体都在（`s5kgw1 8-0010`、`imx471 7-0010`、
  `imx319 9-0010`、`s5k3m5 6-002d`），驱动均已 bound；
- 但每个 sensor 都是 `0 link`，CSIPHY0..3 的 sink 端没有上游连接。

DTB 侧是完整的：`camss@acb3000/ports/port@N` 有 `remote-endpoint`，
各自指回 sensor 的 endpoint。缺失发生在内核
`camss_subdev_notifier_complete()`——只有它才会调用
`media_create_pad_link(sensor → csiphy sink)`。也就是说异步绑定
没有走到 complete，而不是设备树没写。

这属于内核 CAMSS/async-notifier 行为，需要重新编译内核并刷 boot 分区，
和“最小适配、不锁版本”的原则冲突；本轮不夹带。相机因此仍记为未完成。

## 5. 仓库自检结果

用与 `check-sources.py` 相同的展开规则扫描 `linux-port/packages/`：

```text
{
  "recipes": 23,
  "local_sha512_checks": 163,
  "source_files_checked": 218,
  "libcamera_patches": 51,
  "private_key_scan_files": 279,
  "private_build_paths_required": false,
  "hardware_tested": false
}
```

`linux-port/scripts/_wsl-samurai/check-sources.py` 原本仍指向
`device/testing/`、`temp/`、`cross/` 三个已经不存在的旧目录，跑不起来。
本轮把它改为扫描本仓库实际的 `packages/` 布局，并补上三处真实缺口：

1. `${pkgver/_/.}` 这类 shell 参数替换此前没有展开，`phoc` 会被误报；
2. `samurai-apps` 是没有 `source=` 的元包，现在会跳过而不是断言失败；
3. 二进制的放行条件从“一律禁止 ELF”改为“**只有当配方把该文件列为
   `source` 且钉住 SHA-512 时才允许**”，这样预编译的
   `libssc.so.2`、`samurai-hexagonrpcd`、`samurai-rmtfs-cow`、
   `samurai-tqftpserv` 有了明确的白名单，而不是把规则整个删掉。

同时清掉了两个不该出现的构建残留：

- `packages/samurai-snapshot-preview/samucapsinject.so`（未跟踪的编译产物，
  配方只用 `samucapsinject.c` 现场编译）；
- `packages/samurai-ssc/` 里误放的 `libssc.so.2`、`samurai-hexagonrpcd`
  和两个清单文件（它们分别属于 `samurai-libssc`、`samurai-hexagonrpcd`）。

同时修掉了两个会被 `abuild` 直接拒绝的顺序缺陷：

| 配方 | 原问题 | 修复 |
| --- | --- | --- |
| `libcamera` | `qcam.desktop` 与 `_tuning_files` 的校验行排在中间补丁之后 | 按 `source` 顺序重排 |
| `samurai-charging` | `artifacts/*.ko` 的校验行未按 `source` 顺序 | 按 `source` 顺序重排 |

## 5.1 libcamera 版本对齐（r32 → r33）

配方写的是 `pkgrel=32`，但：

- `0051-camss-raw-only-pd10-policy.patch` 已经在 `source=` 里，
  也就是说 r32 配方本来就包含产生 r33 的那次改动；
- 实机和交付镜像装的都是 `libcamera-*99990.7.2-r33`；
- `README.md` 的文字仍停留在 r32。

所以是**配方落后**，不是产物超前。已把 `pkgrel` 改为 33，把
`samurai-camera-config` 的 5 处 `=99990.7.2-r32` 精确依赖改为 `r33`，
并刷新 `source-lock.json` 的 `package_version` 与 `APKBUILD` 哈希。

`phoc` 的 `${pkgver/_/.}` 只是 shell 参数替换写法；按 abuild 规则展开后
与校验行一致，不是缺陷。

## 6. 相机

如上节所述，根因在内核 async-notifier，需要重编内核，本轮未修。

## 6. 复现命令

## 7. 板级默认“永不休眠”与文件归属（2026-11-20）

`samurai-desktop 4-r17` 把 `/etc/xdg/powerdevilrc` 作为**系统默认**安装，
AC/电池/低电量三档都是 `AutoSuspendIdleTimeoutSec=0`（等价于 KDE
“永不休眠”），用户的 `~/.config/powerdevilrc` 仍然优先。刻意不写
已被禁用的调试键 `AutoSuspendAction=0`。

运行时复核不看文件、直接读生效值：

```text
kreadconfig6 AC=0  Battery=0  LowBattery=0
kreadconfig6 AutoSuspendAction=<未设置>
全新 HOME（无用户配置）同样 0/0/0，说明系统默认会被新账户继承
```

`check-powerdevil-effective.sh` 原先按“本次开机发生过几次 suspend”判定，
把用户自己按和平键/合盖触发的合法休眠也算 FAIL。现在改为以
`/etc/xdg/powerdevilrc` 的安装时间（mtime）为界，只统计**看板默认落地之后**
的 suspend 请求；实测 `suspend requests since config install: 0`。

本轮同时发现一个归属缺陷：设备实际装的是 `4-r16`，而
`/etc/xdg/powerdevilrc` 是镜像构建时直接写入的，**不在任何包的文件
清单里**（`apk info -W` 报 `Could not find owner package`）。值是对的，
但 `apk` 无法替换该路径。apk-tools 3.x 的
`apk_db_migrate_files_for_priority()` 在 `ofile == NULL` 时走 `COMMIT`
并把文件登记给新包，所以从仓库安装真实的 4-r17 会自然完成接管，不需要
`--force-overwrite`。

因此做了两件事（2026-11-20 收口）：

- `build-board-packages.py` 原来把 desktop 包钉在 `4-r16` 并**不打包**
  `powerdevilrc`，这才是“文件无主”的根因；现已改为 `4-r17` 并把
  `etc/xdg/powerdevilrc` 放进包清单。设备已从板级仓库升级，`apk info -W`
  返回 `owned by samurai-desktop-4-r17`。
- `check-settings-provenance.sh` 的归属断言原先写的是
  `grep '^R:powerdevilrc$'`；apk 的 installed 库把嵌套文件存成
  `F:<dir>` + `R:<name>`，这条正则在任何情况下都匹配不到，会永久假 FAIL。
  现改为解析 `apk info -W` 的输出。
- 文档与 `settings-provenance.json` 里“包不发 powerdevilrc”“待移除
  powerdevil_auto_suspend_zero”的旧描述已收敛，区分
  `AutoSuspendIdleTimeoutSec=0`（用户可见设置）与
  `AutoSuspendAction=0`（已禁用的调试覆盖）。

```sh
# 板级仓库（设备侧，需 root；索引由本机私钥签名）
# --sign-key 是全局选项，必须写在 applet 名之前；写到 mkndx 之后会被静默忽略
# 而生成未签名索引。索引必须是 APKv3（设备是 apk-tools 3.0.9）。
apk --keys-dir /etc/apk/keys --sign-key <private> mkndx \
    --pkgname-spec '${name}-${version}.apk' \
    --output APKINDEX.tar.gz *.apk

# 干净升级验收（不访问网络）
apk --no-network upgrade --simulate
```

## 8. 官方 Plasma Mobile 推荐包的补齐（2026-11-20）

对照 pmaports `v26.06` 的 `postmarketos-ui-plasma-mobile`，其
`_pmb_recommends` 里有而本镜像缺的两个包是
`plasma-mobile-sounds` 与 `ttyescape`（`vvmplayer`/`vvmd`/`gst-*` 是
`vvmplayer` 的依赖）。现在 7 个包全部进镜像，**1254** 个包。

两点务必记住：

1. **不要**把官方同名包复制进板级仓库。同名同版本会产生两条索引条目，
   apk 可能选到官方那条；离线时就会报
   `package mentioned in index not found (try 'apk update')`。
   板级仓库只放自建包（23 个文件）。
2. **`ttyescape` 必须自己重签**。官方 v26.06 的 APK 由
   `pmos@local-6a19ae2a` 签名，该公钥不在任何仓库里
   （`main/postmarketos-keys` 只装 `build.postmarketos.org`），
   因此在任何 pmOS 装机上都是 `UNTRUSTED`。本仓库用官方上游 tarball
   （`sha512 b196cad0…` 与配方一致）重建，装入的两个文件与官方 APK
   逐字节相同，再用板级密钥签名。

```text
$ sha512sum ttyescape 装入的文件（与官方 APK 内文件一致）
729280a4…  togglevt.sh
88034b54…  ttyescape-hkdm.toml
```

镜像数据库里的 `f:S` 不是文件损坏：apk-tools 用它记录
`sha256_160`（来自 v2 索引的包），源码位置
`apk-tools database.c` 的 `ipkg->sha256_160`。
