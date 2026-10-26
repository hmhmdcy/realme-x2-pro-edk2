# Linux技术文档索引

用途：技术说明和早期会话导航。整理日期：2026-10-23；当前功能与部署见[硬件清单](HARDWARE-STATUS.md)及[检查点](../../NEXT-SESSION.md)，操作规则见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 技术说明

| 文档 | 内容 |
| --- | --- |
| [PORTING-WORKFLOW.md](PORTING-WORKFLOW.md) | 原厂固件/公开仓库提取优先、增量构建、按改动验证 |
| [HARDWARE-STATUS.md](HARDWARE-STATUS.md) | 各功能的已证明能力、缺陷和待验收范围 |
| [USB-NCM-SSH.md](USB-NCM-SSH.md) | USB网络、SSH/SCP与EUD共存路径 |
| [ROOTFS-F2FS-IMAGE.md](ROOTFS-F2FS-IMAGE.md) | F2FS镜像、构建与验证过程，部署范围按后续会话核对 |
| [ROOTFS-PRESERVE-ANDROID.md](ROOTFS-PRESERVE-ANDROID.md) | 保留Android与数据的早期研究 |
| [ANDROID-DT-REFERENCE.md](ANDROID-DT-REFERENCE.md) | 本机Android下游DTS参考来源 |
| [EDK2-KERNEL-EMBED.md](EDK2-KERNEL-EMBED.md) | 早期内核嵌入固件和引导路径 |
| [EUD-TERMINAL.md](EUD-TERMINAL.md) | 早期主机交互终端与收发方案 |
| [OLD-PROJECT-VERIFICATION.md](OLD-PROJECT-VERIFICATION.md) | 旧项目复用与错误核查 |

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
