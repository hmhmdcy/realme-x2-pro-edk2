# 当前 Linux 修复保存与返回方案（248）

用户现在选择自行手动刷 Android。本轮只准备 Linux 返回文件，不自动刷 Android。**完整userdata已保存，PC实际恢复及F2FS检查通过；尚未做实机Android→Linux往返。** 完成状态见 [STATUS.md](STATUS.md)。

## 修复放在哪里

这里的“硬件修复”主要是 Linux/UEFI 软件适配，切换系统会改变手机使用的软件。源码和备份保存在电脑上；刷回时必须恢复彼此匹配的部署。

| 载体 | 当前内容 | 典型适配 |
| --- | --- | --- |
| `boot` | UEFI235及其中的板级DTB | 显示交接、板级资源、相机/PMIC实验配置 |
| `logdump` | Image183及内置RAM恢复环境 | 内建内核驱动、音频离线流恢复、显示/总线/电源基础设施 |
| `userdata`中的F2FS rootfs | Alpine系统、当前789项模块清单对应的文件、固件、软件包、服务与用户配置 | Mesa149、音频UCM、蓝牙/传感器/相机模块与辅助服务、libcamera r15/config-r10、Snapshot CPU启动覆盖、GNSS/QMI初始化工具 |
| modem/vendor/persist/NV等 | 原厂固件、配置和校准，另行保留快照 | modem运行基础与校准；不属于普通rootfs重编译产物 |

同一功能常跨两层或三层。只恢复boot，或使用旧rootfs132镜像，都不能代表恢复当前修复。源码可用于重建功能，但源码之外的软件包版本、配置、所有权、扩展属性和实际文件也需要保存；当前系统备份是直接返回的依据。公开源码不包含私人密钥、NV、原始校准和个人文件。

## 已完成的备份

私人目录为 `E:/edk2-samurai-out/kernel248`，与公开工作区分离。20项分区镜像见 [核验](partition-backup-validation.json)，另有 [logdump核验](logdump-backup-validation.json)，共21项。`linux-return-partitions/boot.img`为当前boot235，`logdump.img`为当前Image183启动载体。六个UFS LUN的GPT头尾另有 [核验](gpt-backup-validation.json)。

内置恢复环境已经实际启动且严格密钥SSH可达；当前手机就在RAM恢复环境，原Linux根标记已恢复，userdata卸载并设置块设备只读。备份工具只读兼容修正通过 [模拟扇区差异的备份/恢复检查](partclone-ro-fixture-validation.json)，当前手机userdata的完整采集与恢复检查也已通过，见[userdata验收](userdata-backup-validation.json)。

## 返回流程

1. 使用本轮最终核验清单，保留完整rootfs压缩备份、匹配的boot/logdump和其他启动分区快照，以及离线恢复工具。失败尝试产生的文件不可用于恢复。
2. Android测试后，在刷写前重新确认实际设备、解锁状态、分区名和几何；与本轮GPT/尺寸不符时先分析差异，不执行旧的刷写脚本。
3. 恢复本轮匹配的Linux启动载体。Android的userdata没有Linux根标记时，已验证的Image183内置恢复环境可提供USB/SSH；重新核对身份后加载PC上保存的恢复工具。
4. 在userdata完全卸载时，将经过完整校验的partclone镜像恢复到已确认的userdata分区。恢复后检查文件系统和根标记、UUID；保留分区原尺寸。源码编译或重新格式化一个空rootfs都不能代替这一步。
5. 按Image183已验证的显示/EUD退场顺序受控重启，核对boot/logdump、模块、软件包和关键配置，再复查各硬件功能。

以上是恢复路线说明，**不是可以盲目执行的通用刷机命令**。21个备份分区不要求全部回刷；尤其GPT、NV、校准和persist不能批量覆盖。是否需要恢复modem/vendor等，应依据Android前后的实际差异判断。Android测试也可能留下不同的运行配置，所以返回后仍需核验。

## GitHub保存情况

初次只读核对时两个远端均停在10月14日。用户随后明确要求发布全部后续硬件适配源码；内核已推送四组31文件至`04d4d4f93171574201db1837a1b195e3aeccde4e`并核对远端，EDK2配套源码和记录同步发布。最终收据见[10月17日发布记录](../publication-2026-10-17/README.md)。

公开源码和当前系统快照分别保存：GitHub不包含rootfs镜像、密钥、NV或个人文件。返回现机状态仍使用本轮私人备份，不能用旧rootfs132替代。当前canonical源码树保持原样；发布使用逐项一致的副本，没有重置本机开发文件。
