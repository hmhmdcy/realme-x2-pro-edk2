# 154：DSI首次初始化候选未修复，标准DPMS恢复桌面

2026-10-13。只刷logdump154，当前实际内核#154，boot132/modules132/software132和Mesa149修复保持。**永久显示修复仍未完成**；用户报告此次首次启动又出现白屏、局部闪烁花屏。完整关屏、开屏后用户确认恢复桌面或锁屏。

候选保留153面板GPIO处理，DSI在link clocks可用、manager尚未开启IRQ时先写CTRL=0，屏障后再timing_setup和soft-reset，防止恢复固件启用状态；记录power-on前后CTRL/MDP2/DSC/TRIG/FIFO。没有混入152 worker同步补丁。11项实际函数普通和ASAN/UBSAN通过，旧实现失败3项；时钟/硬件操作仍为桩。[补丁](host-init.patch)、[测试](actual-function-test-validation.json)

完整构建/checkpatch/W=1/FAT通过，770模块与132逐字节一致、配置/DTB/其它源修改保持。初次checkpatch缺少屏障注释，修正后通过；打包模板遗留modules-root152被存在性守卫阻止，未覆盖旧模块目录。改成154目录后复用已完成完整构建、继续模块安装及镜像核验。[构建](build-package-validation.json)

真实启动CTL0清空成功，首次继承CTRL=0x1f5，native为0x1f1，FIFO由0x99991390复位至0x11111010；随后仍产生欠载，所以关闭继承CTRL不足以解决问题。记录器从uptime17.29秒开始，91.44秒无丢失采集，dmesg197条限频错误；随后累计212条。Phoc/Phosh约83秒存在并不能代表实体画面正常。受控标准DPMS后15秒未新增DPU/DSI/GPU/WARN错误，taint0，DMA prepare9。

实际logdump154读回一致、boot/persist/模块132/NV来源/Mesa149核验通过，27.51秒采样稳定；全boot DSI零错误验收失败，保留退出码1。临时154启动服务已停止并从boot runlevel删除。

此次完整KMS快照采集晚于自动关屏：第一份DRM active=0，后一份恢复后active=1。差异不能用于推导“故障亮屏与正常亮屏”的根因，原始快照和最初diff仍保留，比较工具现会拒绝该状态。155将用同一154镜像重启，不新增刷写；启动时分别在fbcon和桌面首次active=1阶段记录快照，并在读取前后复核active状态。

153运行时背光对照等待真实DPU TX完成后恢复亮度，用户未看到自动对照，但随后手动唤醒未出现花屏；不能把它当已证明的永久修复。原厂SOFEF03F配置第35行明确要求首帧后更新背光，当前驱动尚未实现。下一步同时保留该唤醒线索与首次硬件初始化差异调查，不使用固定延时冒充首帧完成。
