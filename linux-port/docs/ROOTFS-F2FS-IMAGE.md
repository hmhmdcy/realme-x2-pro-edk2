# Realme X2 Pro：userdata 上的 F2FS rootfs 镜像

当前状态以[阶段145部署与收尾](../../sessions/145-dsi-deployment-and-session-closeout.md)和[下一轮检查点](../../NEXT-SESSION.md)为准：持久F2FS系统132已在手机运行，当前内核145；本轮只刷logdump，没有重刷userdata。下方“未部署/未安装rootfs”等描述属于此前方案或离线构建阶段，不是当前状态。

2026-10-11。用户改为不保留 Android，选择 `userdata` 承载 rootfs，最终选择 F2FS。本轮完成离线镜像和配套内核候选，没有刷写手机、格式化手机分区或改 GPT。旧的 [保留 Android 方案](ROOTFS-PRESERVE-ANDROID.md) 记录此前约束。

## 镜像与分区布局

| 分区 | 本方案用途 |
|---|---|
| boot | 现有 EDK2 引导固件 |
| logdump | 64 MiB FAT，承载带原生诊断 initramfs 的 Linux Image |
| userdata | 一个 F2FS 文件系统，直接承载 `/` |

rootfs 是 **userdata 分区内容**的 Android sparse 镜像，不含嵌套分区表。展开大小来自现有 GPT 备份：119,033,245,696 字节（110.8583 GiB），逻辑扇区和文件系统块均为 4096 字节。它是该机容量的定制镜像，不是适用于所有 X2 Pro 的通用镜像。

| 本地产物 | 大小 | 用途 |
|---|---:|---|
| `E:\edk2-samurai-out\rootfs01\samurai-rootfs-f2fs.simg` | 444,602,300 字节，约 424 MiB | userdata 的 Android sparse 镜像 |
| 同目录 `samurai-rootfs-f2fs.simg.zst` | 136,719,509 字节，约 130 MiB | 压缩保存副本，须先解压为 `.simg` |
| 同目录 `Image-f2fs` | 约 44.6 MiB | 内置 F2FS 和 rootfs 切换逻辑的 ARM64 Linux Image |
| 同目录 `logdump-f2fs.img` | 64 MiB | 基于本地保存的 kernel91 FAT 模板，仅替换 Image 的启动候选 |

`.simg` 的 SHA256：

```text
fdd86e1f5f1072ed02aaf077944b3218183835beeb8a2c0aa217d3c4ef3172d7
```

各产物完整哈希见同目录 `rootfs-f2fs.sha256`、`kernel-f2fs.sha256` 和 `logdump-f2fs.sha256`。文件系统 UUID 为 `32dd1191-5c73-4eb7-8d45-2213af0f2001`，卷标为 `pmos_root`。这些镜像和其中的 SSH 主机密钥只在私人输出目录保存，不进入公开源码仓库。

## 用户空间

使用官方 pmbootstrap 3.12.0（`200f5123615808326ac796f66b02fdc6cebbcbf1`）和 edge pmaports（`862c5af2ca9a48f43e934d9ea55fee0dd47a67f2`）。edge 的系统标识现在显示 `Nura edge`，对应项目的[官方更名公告](https://nura.eco/blog/2026/09/27/nura-rename/)。

构建以 `postmarketos-trailblazer` 为 ARM64 用户空间基底，选择 `kernel=none`、console UI、OpenRC；启动内核使用本机已有的 samurai 移植。通用 mkinitfs 被隔离构建脚本跳过，官方 pmbootstrap 源码未修改；没有拿通用设备内核替代本机内核。

- 用户 `cy122`，UID/GID 10000，主机名 `samurai`，时区 `Asia/Shanghai`。
- 安装 F2FS 工具、SSH、网络工具及基础 console 环境；没有安装图形桌面。
- SSH 使用此前已授权的公钥，关闭密码 SSH 登录，root 密码锁定。
- 临时 console/sudo 密码仅保存于 WSL 的 `/home/cy122/pmos-samurai-rootfs01/login-credentials.txt`，宿主用户所有、权限 0600。该文件不在公开资料或输出日志内。
- OpenRC 启动现有 USB NCM 脚本，设备端地址 `169.254.42.1`，由发行版 sshd 提供 SSH。保留 `ttyEUD0` console；NetworkManager 不接管 usb0。
- `/etc/fstab` 按 UUID 挂载 F2FS，使用 `noatime`。本次没有开启 F2FS 文件压缩，也没有配置 Btrfs 式快照。

rootfs 未包含厂商固件、Wi-Fi 密码或 NV 快照。原有诊断 initramfs 的固件和服务文件仍在配套 Image 中；切换到持久 rootfs 后的 Wi-Fi/固件服务接入需要后续完成。

## 启动衔接与验证

内核在隔离副本 `/home/cy122/pmos-samurai-rootfs01/kernel` 中编译，F2FS、xattr、ACL、安全标签支持均内置。仅增加 F2FS 配置和隔离 initramfs 路径，保留原有诊断文件及 EUD/USB 功能。原源码树的生成文件在构建期间发生变化，本轮没有将其回写或恢复；审计见 `kernel-artifact-validation.json`。

PID 1 先检查 `userdata` 分区名、PARTUUID `fce252a8-deb1-7d74-0dbc-bfdabfa3710a`、精确容量和 4096 字节逻辑扇区；再检查 F2FS UUID。先以 `ro,norecovery` 挂载，验证 rootfs 标识和 `/sbin/init`，之后重新读写挂载并切换到 OpenRC。识别或前置挂载失败时保留原诊断启动环境。文件系统探测已使用 initramfs 实际 BusyBox 的语法核对，不依赖 util-linux 专有参数。

已完成的离线检查：

- ARM64 用户空间通过 QEMU 执行，账号权限、服务脚本、SSH 主机密钥和有效 sshd 配置检查通过。
- `sload.f2fs -P` 写入文件、保留 UID/GID；原始镜像与 sparse 还原镜像均通过 `fsck.f2fs --dry-run`。
- sparse 每个数据块与原始镜像比对，跳过范围核对为原始稀疏文件空洞；展开容量与 userdata 备份一致。
- 使用真实 ARM64 BusyBox 探测还原镜像：正确 F2FS UUID 接受，错误 UUID 和非 F2FS 输入拒绝。
- 内核配置增量、CPIO 文件内容、诊断回退入口检查通过；从 FAT 候选中提取 Image 与独立 Image 一致。

这些检查没有替代实机启动验收。实际 Linux 设备树来自 **EDK2 内嵌 DTB**；FAT 中的 DTB 文件不是当前实际设备树来源。`logdump-f2fs.img` 来自保存的模板，不代表当前手机的备份。部署前需核对当前 GPT/分区容量和实际 EDK2/内核组合，后续再验证 rootfs 切换、USB/SSH 和硬件服务。

**以后刷入 userdata 将覆盖其中的 Android 数据。** 本轮仅制作镜像，没有执行刷写；也没有生成自动刷机脚本。

构建环境与 raw 稀疏文件保存在 `/home/cy122/pmos-samurai-rootfs01`。私人输出目录的脚本、配置、日志和 JSON 记录可用于复核本次构建；重新定制须同时更新镜像 UUID、启动校验参数和分区容量。
