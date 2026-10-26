# Samurai 软件包与构建配方

本目录保存已在项目中公开的设备软件包、补丁和构建输入。安装状态与实机验收必须按各目录 README 和[当前检查点](../../NEXT-SESSION.md)核对；源码或成功构建不等于已经部署。

| 目录 | 内容 |
| --- | --- |
| [apk3](apk3/) | 固定版本 APK 构建、签名和仓库生成工具 |
| [geoclue](geoclue/) | ModemManager GNSS 生命周期补丁与桌面定位依赖 |
| [gst-plugin-pipewire](gst-plugin-pipewire/) | 相机 GStreamer/PipeWire 缓冲修复 |
| [libcamera](libcamera/) | 相机驱动、IPA、ISP 与颜色处理补丁 |
| [modemmanager](modemmanager/) | 固定 ModemManager 版本及 GNSS 相关补丁 |
| [pipewire-common](pipewire-common/) | PipeWire 与相机客户端生命周期修复 |
| [samurai-camera-config](samurai-camera-config/) | 四摄 libcamera 配置、调校与堆规则 |
| [samurai-desktop](samurai-desktop/) | Phosh/greetd 桌面启动顺序配方 |
| [samurai-gnss-assist](samurai-gnss-assist/) | GNSS 辅助数据与无 SIM 电源管理服务 |
| [samurai-platform](samurai-platform/) | 音频、Wi-Fi、Modem、USB、蓝牙和桌面集成 |

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
