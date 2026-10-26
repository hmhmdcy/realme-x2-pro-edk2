# 2026-10-17：保存全部后续硬件适配源码

用户要求将尚未上传的硬件修复全部推送到GitHub。本轮延续10月14日的发布，覆盖随后音频、传感器、蓝牙、相机、modem/GNSS及Linux返回准备的源码、补丁、构建脚本和脱敏验证记录。已验收范围和未解决的问题仍以[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)为准，不因发布而扩大验收结论。

## 两个源码仓库

- [hmhmdcy/linux / samurai-bringup](https://github.com/hmhmdcy/linux/tree/samurai-bringup)：从本机canonical树逐项复制31个更新/新增文件，原树没有被重置或修改。四组提交包括音频、FastRPC传感器、蓝牙RX唤醒，以及相机/PMIC/可选OF辅助驱动与DTS。新tip为`04d4d4f93171574201db1837a1b195e3aeccde4e`，已经读取GitHub实际远端确认一致。
- [hmhmdcy/edk2-realme-x2-pro / master](https://github.com/hmhmdcy/edk2-realme-x2-pro/tree/master)：保存平台构建材料、独立模块及包补丁、用户态工具、启动配置、各阶段实测记录和本轮发布收据；平台目录为`Platform/Realme/sm8150`。

内核四组提交：

| 组别 | 提交 |
| --- | --- |
| 音频恢复、SLIMbus离线流与PDR | `45bc36dd26404608d49cdd8cf5ac15263ecacc8e` |
| FastRPC传感器生命周期与PM | `d61955398768b1ca96d6db98c566adb5edb06d93` |
| 蓝牙RX唤醒 | `6306d695e3c823576e6c98cd9b60c13afc5c5627` |
| 相机、PMIC及板级资源 | `04d4d4f93171574201db1837a1b195e3aeccde4e` |

## 当前部署与源码的关系

手机保留boot235/Image183，并安装后续模块与用户态软件。单独编译内核分支不能代替完整系统重建；独立模块、DTB构建输入、软件包和配置需要按各自部署锁配套使用。[检查点](../../NEXT-SESSION.md)记录最后核对的版本与差异。

- 音频：见[183实际离线流恢复与两次s2idle](../kernel183/README.md)。合成故障恢复不等于真实固件watchdog或长稳验收。
- 传感器/蓝牙/modem：FastRPC与SLPI服务、RX唤醒、RAM文件服务、MCFG准备及其失败记录均保留；GNSS目前仍无fix。
- 相机：见[相机部署锁及启动配置](../../linux-port/camera/README.md)、[239 libcamera r15](../kernel239/README.md)、[240桌面CPU预览](../kernel240/README.md)。Snapshot默认Vulkan故障、缓冲账本及后摄问题没有写成已修复。
- Mesa：既有[149 VM_BIND对齐修复](../../linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch)与后续新GPU故障分开记录。
- GNSS：保留[247启动期MEMSHARE与OEM差异](../kernel247/README.md)及之前HAL/RF/时钟分析，零CNR根因仍待定位。
- 返回Linux：见[248当前备份状态](../kernel248/STATUS.md)和[恢复说明](../kernel248/RESTORE-NOTES.md)。用户自行刷Android，本轮没有自动刷写Android。

## 公开范围与核对

公开副本按同步manifest生成；原始工作区保留。排除手机镜像、rootfs、NV/校准、原始运行日志、照片/音频、SSH和其他密钥，脱敏设备标识、启动UUID和MAC。复制后的源码与canonical文件一致，静态差异检查通过；原有实机结果用于说明部署，发布本身不新增硬件测试结论。

当前本地工作区中一个既有生成DTB不在源码发布清单内，保持原样；对应实际部署的DTB来源和构建脚本已保留。不会用未核验的生成文件覆盖已锁定启动产物。内核构建树、私人回退文件及旧工厂备份不因本轮发布而清理。
