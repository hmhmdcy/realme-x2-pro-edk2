# kernel74：本机DPU5显示接管证据

结果见[sessions/74](../../sessions/74-sm8150-display-boot-handoff.md)。最终#68两次
自动启动无SMMU/DSI/vblank异常，18次显示电源循环、六组A/B/A与144个硬件CRC通过。
#65/#66/#67失败也保存，不能将中间候选当成稳定基线。GPU/90Hz/休眠/冷断电/光学输出未验。

| 文件 | 用途 |
|---|---|
| before/handoff/reboot/no-start/reprepare/detach/drain/final日志及.gz | 新设备完整日志、失败与最终两启动 |
| capture-receipts/validation.json | 22份设备SHA/gzip CRC/长度链 |
| drain-display-tests、drain-reboot-display-tests | 两次真实三组A/B/A、九次显示电源循环；工具源码在kernel73/kms-smoke.c |
| handoff-candidate/no-start/detach/drain.patch、dpu_*.before/after | 四个增量版本；0010最终为drain，与实际源逐字匹配 |
| prepare-*.py、build-*.sh、*-build.log、checkpatch-* | 实作/构建及保留的接口编译失败；部署验证与回退 |
| *-f1-wsl.*、*-confirm-*、*-flash-*、*-reboot.* | 六次新F1、独立fastboot、四次logdump部署和同镜像重启 |
| core-preservation、initramfs-validation、artifact-manifest | 未改核心源/配置/DTB与本地大产物身份；无私钥或专有blob发布 |
| final-facts、native-eud.*、host-* | 实际分区/旧基础功能/原生命令和连接释放 |
| research.md、gpu-loader-validation.json | 维护者/仓库来源，本机固件布局预检与明确运行未验项 |
| evidence-validation.json、verify-evidence.py、patch-validation.json | 只读离线设备/失败/最终判据与增量源码检查 |

只读离线复核：`python3 verify-evidence.py`。SHA256SUMS封存本目录所有文件。
构建、部署、准备脚本使用本地路径；准备/备份有首次检查，部署要求新证据前缀，
不应原样重跑覆盖回退。flash-drain.ps1是已验最终候选，旧flash-*保留为过程证据。
本次只支持已验本机command-mode接管，没有上游合并或通用支持声明。
