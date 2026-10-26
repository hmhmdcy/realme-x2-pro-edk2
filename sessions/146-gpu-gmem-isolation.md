# GPU GMEM 隔离实验（2026-10-13）

用户授权无人值守修复 GPU。操作边界以 WORKING-BOUNDARIES.md 为准。

在原 #145 上，固定 800×600 glmark2 build 用例像素校验成功，但退出后增加两次 CCU READ TRANSLATION fault。#146 将 A640 的内核 CCU invalidate 从用户 IB 前移到后，编译和 20 个命令序列测试通过，实机仍增加两次相同故障，候选拒绝。仅凭像素校验或 exit 0 不能验收。

在同一 #146 启动上，每进程使用 Mesa 调试选项隔离：

| 用例 | 完成次数 | 新增 GPU fault |
| --- | ---: | ---: |
| 默认 | 1 | 2 |
| noubwc | 1 | 2 |
| sysmem | 3 | 0 |
| nobin | 1 | 2 |
| notile | 1 | 2 |
| flush | 1 | 2 |
| 默认并保存完整 RD | 1 | 2 |

各用例固定大小、确认 FD640、逐次像素验证并观察退出后 20–40 秒；失败后停止重复。sysmem 的结果是定位证据，尚未作为系统性修复。命令流及实际 GPU core 已用本地 Mesa 26.2.4 crashdec 解码；启动 DPU core 单独分类。GPU 访问在已映射渲染 BO 起点之前，释放后 UAF 尚未证实。

#146 本次启动有一条 wcd934x_comp_probe 警告（taint512），初始 DPU timeout1/DSI222，DMA prepare917；探测期间这些计数保持不变，桌面进程身份保留。原 #145 基线没有这些启动问题，#146 不能当作干净验收结果。

#147 已撤销无效 CCU 顺序修改，单独测试 A640 内核管理私有 VM 的 64 KiB IOVA 对齐，BO 大小和映射范围不变。W=1 MSM 和整机 Image/modules/DTB 编译无警告；770 个模块逐字节等同132，config和DTB不变。仅修改三个 MSM 文件，其他已有差异核对保留。此对齐是待验证诊断假设，未宣称硬件普遍要求。

#146→147 切换前重新读取实际启动身份，停止桌面和远程处理器，检查无新增 GPU fault、NV/固件来源及分区校验。保存并核对唯一 F1 收据，fastboot 校验身份、产品和64MiB几何后只刷 logdump，写入和重启成功。后续 #147 的26次回归已完成并通过，见[147修复与验收](147-a640-gmem-alignment-fix.md)。

脚本与脱敏结果在 reference/kernel146、reference/kernel147；原始 core/RD、启动身份、分区哈希与转场收据只保存在 E:/edk2-samurai-out/kernel146 和 kernel147。

宿主机恢复记录：解压旧20GiB诊断构建卷时，C盘空间被占满；删除本次不完整解压文件并恢复WSL正常挂载后，改在E盘恢复原卷。为腾挪临时移动的下载文件已校验并恢复原位置；原压缩备份保留。后续解压应检查Windows实际卷空间，不能仅依赖WSL虚拟容量。
