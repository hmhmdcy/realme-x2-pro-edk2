# Linux技术文档索引

用途：技术说明和早期会话导航。整理日期：2026-11-09；当前功能与部署见[硬件清单](HARDWARE-STATUS.md)及[检查点](../../NEXT-SESSION.md)，操作规则见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 技术说明

| 文档 | 内容 |
| --- | --- |
| [STANDARD-ARM64-V731.md](STANDARD-ARM64-V731.md) | Linux v7.3.1 标准 ARM64 交付：源码锁、镜像哈希、两次实机启动、BDS 可复现构建与剩余缺口 |
| [OFFICIAL-BASELINE.md](OFFICIAL-BASELINE.md) | postmarketOS pmaports main/v26.06 与 realme 官方内核的 L2–L7 分层审计、许可证、差异和取舍 |
| [SETTINGS-PROVENANCE.md](SETTINGS-PROVENANCE.md) | 区分 postmarketOS/KDE 官方默认、板级必需薄层和仅调试设置；正式包禁用的调试策略 |
| [PUBLICATION.md](PUBLICATION.md) | 标准 ARM64 三个公开分支、提交、内容边界和历史 bring-up 分支 |
| [PORTING-WORKFLOW.md](PORTING-WORKFLOW.md) | 原厂固件/公开仓库提取优先、增量构建、按改动验证 |
| [LINUX-ADAPTATION-LAYERS.md](LINUX-ADAPTATION-LAYERS.md) | 七层适配模型、标准 ESP、DTB ABI、同型号安装和包边界 |
| [LAYER-CONVERGENCE-PLAN.md](LAYER-CONVERGENCE-PLAN.md) | L2/L3/L4 工作包、G0-G4 闸门、DTB 差异账本和飞轮基线 |
| [L2-DUAL-KERNEL-MATRIX.md](L2-DUAL-KERNEL-MATRIX.md) | k270/k363 与候选 DTB 的离线语义矩阵、运行态闸门和 SKU 边界 |
| [L2-DTB-ABI-GATE.md](L2-DTB-ABI-GATE.md) | 机器可读 DTB 契约、资源/UAPI 绑定、允许加法与拒绝样例 |
| [L3-DRIVER-OWNERSHIP.md](L3-DRIVER-OWNERSHIP.md) | 驱动组、模块/源码证据、公共 UAPI 和首轮安全动作 |
| [L3-SENSOR-POWER-BOUNDARY.md](L3-SENSOR-POWER-BOUNDARY.md) | sensor-power 的驱动/消费者边界、标准化阶梯和 L3-02 验收条件 |
| [L3-02-G2-CANDIDATE.md](L3-02-G2-CANDIDATE.md) | sensor-power G2 Image/logdump 候选、哈希、部署前置和回退边界 |
| [L3-02-RPROC-SUBDEV-CANDIDATE.md](L3-02-RPROC-SUBDEV-CANDIDATE.md) | genpd 否决后的标准 remoteproc 生命周期、真机 `#2` 验收和回读哈希 |
| [L4-UAPI-INVENTORY.md](L4-UAPI-INVENTORY.md) | 内核 UAPI、L5/L6 配置债、消费者和双栈迁移顺序 |
| [samurai-dt-v1-contract.md](../dts/samurai-dt-v1-contract.md) | DTB 稳定/动态/vendor 字段、差异账本、兼容规则、源锁和验收矩阵 |
| [HARDWARE-STATUS.md](HARDWARE-STATUS.md) | 各功能的已证明能力、缺陷和待验收范围 |
| [PLASMA-MOBILE.md](PLASMA-MOBILE.md) | Plasma Mobile 会话、D-Bus 门户、显示亮度、ModemManager、传感器与振动接口 |
| [DESKTOP-PORTABILITY.md](DESKTOP-PORTABILITY.md) | 板级公共接口与桌面适配层边界、换桌面检查清单 |
| [USB-NCM-SSH.md](USB-NCM-SSH.md) | USB网络、SSH/SCP与EUD共存路径 |
| [NFC-NEARD.md](NFC-NEARD.md) | 主线 nxp-nci-i2c、Alpine neard/OpenRC 边界和真实标签验收条件 |
| [BLUETOOTH-HOST-MODULES.md](BLUETOOTH-HOST-MODULES.md) | 主线 BNEP/UHID/uinput 模块包、官方 BlueZ 加载边界、离线签名/隔离安装和设备验收条件 |
| [STARTUP-LATENCY-AUDIT.md](STARTUP-LATENCY-AUDIT.md) | 普通重启到 Wi‑Fi/NCM 首次 SSH 的时延、固定等待审计和剩余慢路径 |
| [ROOTFS-F2FS-IMAGE.md](ROOTFS-F2FS-IMAGE.md) | F2FS镜像、构建与验证过程，部署范围按后续会话核对 |
| [ROOTFS-PRESERVE-ANDROID.md](ROOTFS-PRESERVE-ANDROID.md) | 保留Android与数据的早期研究 |
| [ANDROID-DT-REFERENCE.md](ANDROID-DT-REFERENCE.md) | 本机Android下游DTS参考来源 |
| [EDK2-KERNEL-EMBED.md](EDK2-KERNEL-EMBED.md) | 早期内核嵌入固件和引导路径 |
| [EUD-TERMINAL.md](EUD-TERMINAL.md) | 早期主机交互终端与收发方案 |
| [OLD-PROJECT-VERIFICATION.md](OLD-PROJECT-VERIFICATION.md) | 旧项目复用与错误核查 |
| [DISPLAY-90HZ.md](DISPLAY-90HZ.md) | 90Hz/双模式、Phoc 历史、Plasma Mobile/KWin、电源键与 Phosh 清理 |

## 旧19—28节

这些文件保留原阶段正文，旧节号可通过[交接映射](../../HANDOVER-NEXT.md#旧830节映射)定位。

- [19-loadoptions.md](19-loadoptions.md)：19. 内核命令行进了 boot option 的 LoadOptions（2026-10-07 14:4x）
- [20-linux-boot.md](20-linux-boot.md)：20. 主线 Linux 真机启动成功：内核改放 FAT 分区（2026-10-07 16:0x）
- [21-eud-framing.md](21-eud-framing.md)：21. EUD 日志乱码的真因：内核侧 FIFO 溢出，不是主机重组（2026-10-07 16:0x）
- [22-kernel-upstream.md](22-kernel-upstream.md)：22. 内核侧进入 GitHub：从上游 fork（2026-10-07 16:2x）
- [23-upstream-push.md](23-upstream-push.md)：23. 内核侧上 GitHub：完成 fetch 与分支，卡在 push（2026-10-07 16:3x）
- [24-push-done.md](24-push-done.md)：24. `samurai-bringup` 已推上 GitHub（2026-10-07 16:46）
- [25-eud-console.md](25-eud-console.md)：25. EUD 真 console 落地 + 固件 cmdline/DTB 更新，等待真机验证（2026-10-07 18:1x）
- [26-real-machine-review.md](26-real-machine-review.md)：26. Real-hardware review: console works, two real culprits, panic loop (2026-10-07)
- [27-userspace-and-shortcuts.md](27-userspace-and-shortcuts.md)：27. Userspace reached; console moved to /dev/kmsg; shortcuts vs proper goals (2026-10-08)
- [28-flywheel.md](28-flywheel.md)：28. Button-free fastboot and a hands-off flywheel: PON reboot-mode, EUD COM RX, fastboot flash logdump (2026-10-08)

后续阶段与reference证据见[会话索引](../../sessions/INDEX.md)。文档检查和仅同步命令见[DOCS-INDEX](../../DOCS-INDEX.md#检查与同步)。
