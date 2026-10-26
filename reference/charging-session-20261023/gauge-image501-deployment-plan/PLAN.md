# Image501 启动载体与回退

本阶段仅离线生成私有可审载体，不安装、刷写、重启或连接手机。Image501 已冻结，不重编内核；C 默认开关仍为 false。

实际 EFI stub 在 LoadOptions 非空时覆盖运行时 `/chosen/bootargs`（`fdt.c:88–90`）。R2 BDS 直接以 UTF16 `mSamuraiLinuxCmdLine` 构造并启动 `NewOption`，因此仅在原 R2 字符串末尾追加 `bq27xxx_battery.samurai_instant_current=1`。实际内置对象确认前缀为 `bq27xxx_battery`。不修改原 native DTB9271，不把静态 chosen 改动误当有效参数。

只有两个分区需要后续成对激活：

1. `boot`：从当前完整 96MiB 4126 载体出发，仅更换 BDS FFS。只编 PlatformBm 对象、单成员 PlatformBootManagerLib、重链接 BdsDxe 和 GenFw；其余 40 库逐字保持。native DTB9271、另外 100 个完整 FFS、SEC 全文与位置、shim、compat、ramdisk 和绝对尾部保持。Android v1 头只允许 kernel_size/ID 随负载变化。当前4126的 used 为6684672，且该位置已有非零尾字节；本次严格要求 newused≤6684672，不能套用旧a30的6686720界限。
2. `logdump`：私有复制实际 ACA 64MiB FAT，只用现有 mcopy 替换 `/Image` 为冻结 Image501（3a656c75…e8cc02，59243008B）。保留其它 FAT 条目、DTB和文件内容，完整读回并 `fsck.fat -n`。其中 FAT DTB365不承担运行时 native DTB选择；后者仍来自 boot 的9271。

精确回退组合为当前 **boot4126 + logdump ACA（内含 Image363）**。不用早期a30或更早logdump。两分区写入不具有硬件原子性；未来执行器必须在 bootloader 中记录各写入终态，两个候选均确认成功才允许 candidate reboot。任何部分写入失败/未知都不得重放或启动混合组合；先确认原子进程已终态，再按独立回退 claim 恢复两个原件，核对后方可 reboot-original。此阶段不生成或执行该激活流程。

EUD-off、原 R2 关闭逻辑、Image501之外的 initramfs/模块、正常500脚本、rootfs、R8和相机481文件均不在写入路径。参数启用、实际电流和剩余图标延迟仍需后续新启动及受控采集证明；离线载体不能代替实机验收。

`inputs.json` 绑定原件、工具、源证据和原四条构建命令；该只读调查保留原字段 `tail_limit=6686720` 作为旧a30格式记录，本计划和候选执行器对当前4126使用更严格6684672。私有新目录拒绝重放；失败保留全部原件，不补PE/FV/gzip头、不放宽差异门。
