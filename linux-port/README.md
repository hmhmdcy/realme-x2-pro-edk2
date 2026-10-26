# Linux 移植工作区：Realme X2 Pro / RMX1931 / samurai

用途：Linux源码、补丁、设备树、rootfs及工具导航。文档整理：2026-10-23；部署身份与实机验收以[当前检查点](../NEXT-SESSION.md)和[硬件清单](docs/HARDWARE-STATUS.md)为准。

## 续作入口

先读[检查点](../NEXT-SESSION.md)与[操作边界](../WORKING-BOUNDARIES.md)，再按[适配工作流](docs/PORTING-WORKFLOW.md)选择本轮资料和验证范围。硬件/校准优先提取原厂固件或公开仓库的数据、文件与算法，缺项再实测；复用已有提取物和增量构建。目录名、内核release、工作区Image或固件文件名不能单独证明它们与实际运行组合一致；源码路径、部署包和回退收据由检查点指路。

## 内容与来源

| 位置 | 用途 |
| --- | --- |
| [docs/](docs/00-INDEX.md) | 技术说明、rootfs研究与早期19—28节历史 |
| [patches/](patches/) | 已保存的内核/用户态补丁；当前完整显示补丁由检查点链接，不假定此目录包含所有晚期改动 |
| [dts/](dts/) | 保存的samurai设备树源与候选，构建时依据实际DTB证据核对 |
| [scripts/](scripts/) | 构建、验证、日志与文档工具；早期部署脚本的参数需按当前任务核对 |
| [refs/19781/](refs/19781/) | 本机项目号19781的Android下游DTS摘录，见[参考说明](docs/ANDROID-DT-REFERENCE.md) |
| [initramfs/](initramfs/) | 早期诊断用户空间与启动脚本 |
| [packages/](packages/README.md) | GNSS辅助服务、MM源码锁与APK构建工具 |
| [radio/](radio/README.md) | modem RAM工作文件服务、固定来源与可复现构建 |
| `eud.c`、`eud_earlycon.c` | 保存的EUD实现；与晚期源码的差异按具体会话补丁核对 |
| `artifacts/` | 本地生成产物，不通过文档同步工具复制到仓库 |

主线内核、EDK2与Mesa属于不同源码/构建范围。历史初始化补丁或旧Image只能复现对应阶段；实际版本与模块/DTB匹配关系见[检查点](../NEXT-SESSION.md)。

## 构建与部署参考

- [EDK2内核嵌入](docs/EDK2-KERNEL-EMBED.md)：早期引导路径与打包方法。
- [F2FS完整rootfs](docs/ROOTFS-F2FS-IMAGE.md)、[保留Android的研究](docs/ROOTFS-PRESERVE-ANDROID.md)：方案与历史边界，结合后续会话核对部署范围。
- [USB NCM/SSH](docs/USB-NCM-SSH.md)：通信路径与验收。
- [测试飞轮](../FLYWHEEL.md)：按本次设备、源码和镜像身份实施一轮验证。
- [会话索引](../sessions/INDEX.md)：阶段实验、补丁与reference证据；[显示152—165](../sessions/display-handoff-152-165.md)为本次整理的专题历史。

## 文档维护

编辑在Windows工作区进行，通过[文档导航](../DOCS-INDEX.md)中的命令检查并同步。原README中的早期“DTB是小米9”“GPU/Wi-Fi禁用”“真机未测”等陈述保存在[维护前快照](../archive/docs-before-maintenance-2026-10-14/README.md)，按其阶段解释。
