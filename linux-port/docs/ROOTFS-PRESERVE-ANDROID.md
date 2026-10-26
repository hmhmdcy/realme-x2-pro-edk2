# postmarketOS 持久 rootfs：保留 Android 和全部数据

当前状态以[阶段145部署与收尾](../../sessions/145-dsi-deployment-and-session-closeout.md)和[下一轮检查点](../../NEXT-SESSION.md)为准：持久F2FS系统132已在手机运行，当前内核145；本轮只刷logdump，没有重刷userdata。下方“未部署/未安装rootfs”等描述属于此前方案或离线构建阶段，不是当前状态。

> 历史方案。2026-10-11 用户改为不保留 Android，选择 userdata/F2FS，已制作离线镜像；见 [F2FS 镜像说明](ROOTFS-F2FS-IMAGE.md)。本文件保留此前约束和研究证据，手机尚未刷入 rootfs。

Session71只刷boot/logdump接入触摸，Android/全部userdata保留；没有安装rootfs。
新64MiB logdump镜像内Image30317056/DTB95933字节，FAT空闲36605952字节
（约34.91MiB），旧session70的36737024字节是其保留旧镜像容量，仍然有效。
两者均不足以证明完整、可持久更新的postmarketOS布局。


2026-10-10，session66研究、session70只读容量复核。用户明确选择保留 Android 和全部数据；当前只允许刷 boot/logdump。session68曾更新boot固件DTB；rootfs未部署，没有格式化、缩容、改 GPT 或写 userdata。

目前没有确认可直接刷入完整持久 postmarketOS 的空闲分区。继续使用 RAM initramfs；下一步评估 logdump 内极小的只读 rootfs，或 USB 可用后的外置存储。普通发行版、固件、模块、图形界面与更新空间不能按一个最小 Alpine 压缩包的大小估计。

session70只读检查保留的64 MiB logdump-k67-usb.img，Image=30185984字节、DTB=94803字节，FAT空闲36737024字节（约35.04 MiB）。镜像哈希保持；这不是重新扫描手机文件系统或GPT，也不证明能容纳完整pmOS或持久更新空间。证据在reference/kernel70/filesystem-capacity.json；本轮无刷机。

## 分区证据及候选

`reference/kernel66/gpt-backup-audit.json` 是既有 GPT 备份的离线解析，4096 字节扇区，LUN0/4 的头和分区表 CRC 均通过。它不是本轮当前 GPT 的完整有效导出。LUN0 first usable LBA=6，分区间无空隙；LUN4 唯一空隙约 4.3 MiB。本轮读取 34 扇区会越过 GPT 进入早期分区内容，且导出交错，已排除作当前证据；原件仅本地保留。

| 位置 | 备份所见容量 | 保留数据时的判断 |
|---|---:|---|
| logdump | 64 MiB | 当前承载 FAT、约 30 MiB 内核和 DTB。可能容纳极小压缩 rootfs；未制作或验证持久方案，不能保证完整发行版可用。 |
| boot | 96 MiB | 引导分区，不作为普通可写 rootfs。session68更新过固件DTB，未刷入rootfs。 |
| cache | 512 MiB | 未证明为空或 Android/OTA 不再使用；不格式化，也不凭名称认定安全。 |
| userdata | 约 110.9 GiB | 保留全部数据，禁止覆盖或缩容。文件内 rootfs 需先证明 Linux 能读取 Android 数据及加密格式。 |
| system/vendor/odm | 4280/1632/256 MiB | Android 使用，排除重用。 |
| persist、metadata、rawdump、vm-*、op* 等 | 各异 | 用途或数据必须保留，不因容量大就作为空闲分区。 |

既有 Android 采集显示 `/data/user/0` 来自 `/dev/block/dm-35`，不能据此认定主线 Linux 可直接挂载 userdata。Android 的 CE/DE 密钥与设备安全环境有关；厂商 `fileencryption=ice` 也可能使用专有格式。需先只读核对该机 fstab、映射与加密参数，不尝试绕过密钥或修改元数据。依据：[Android FBE 文档](https://source.android.com/docs/security/features/encryption/file-based)、[Linux fscrypt 文档](https://docs.kernel.org/filesystems/fscrypt.html)。

## 安装资料的适用边界

[官方 FAQ](https://nura.eco/faq/) 给出了支持设备的 SD 卡双启动；不证明 X2 Pro 存在可用 SD 插槽或可重用 A/B 槽。本机是否 A/B、各分区用途以实际 GPT/Android 证据为准。

[pmaports 历史 rootfs 布局提案](https://gitlab.com/postmarketOS/pmaports/-/issues/3219) 讨论 userdata 内文件与分区发现，并非允许覆盖 userdata 的安装政策，也不是本机已经验证的 stowaway 实现。

当前结论：没有安全的大分区刷写建议。小 rootfs 放 logdump 只作为待验证设计；外置 USB 需要先解决 USB 控制器/角色问题；userdata 内文件方案需要 Android 加密兼容性证据。任何超出 boot/logdump 的写入或分区调整都不在本轮授权内。
