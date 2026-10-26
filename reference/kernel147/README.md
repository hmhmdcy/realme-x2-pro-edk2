# A640 GMEM 迟发 fault 修复验证

当前手机运行 #147，系统、rootfs 与770模块仍为132。#147 只改变 A640 内核管理私有 GPU VM 的 IOVA 起点对齐，从4KiB改为64KiB；BO大小、实际映射范围及其他GPU默认行为保持。

原 #145 固定800×600 glmark2像素验证成功后，退出出现两次CCU READ TRANSLATION fault。#146的CCU事件位置改动无效，已撤销。#146强制sysmem正常，关闭UBWC、纹理分块、binning或强制flush仍出错。

#147真实转储已确认BO起点全部64KiB对齐。完整回归通过20次800×600像素验证和6次1080×2259持续绘制，26次退出后观察35–90秒均无fault、taint0，GPU/警告/显示/DMA错误计数为0。验收见gpu-regression-validation.json及closeout-validation.json；默认GMEM策略保持。

相关证据：

- candidate-preparation.json：候选范围。
- a640-managed-iova-alignment.patch：独立GPU改动。
- build-package-validation.json：编译与镜像、模块、DTB验证。
- source-scope-validation.json：原有其他源码差异保持。
- first-runtime-validation.json：实机启动与分区读回。
- rd-alignment-validation.json：真实命令转储中的BO对齐前后对照。
- gmem-command-validation.json：候选仍执行GMEM render与resolve。
- gpu-regression-validation.json：26次回归、7200次提交/退休与无丢事件追踪。
- closeout-validation.json：最终设备状态及来源、模块和分区核验。
- oem-alignment-source-validation.json：固定提交的原厂分配器契约。

原厂KGSL对导入的大缓冲区提高地址对齐：[kgsl.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/gpu/msm/kgsl.c#L2392)。这支持本机修复方向，但不能据此宣称所有Adreno硬件都要求64KiB对齐。当前补丁也不改变用户管理的VM_BIND地址选择；Vulkan该路径和其他型号不在本次验证范围。

原始日志、BO地址、core/RD、启动身份、分区哈希和刷写收据仅在E:/edk2-samurai-out/kernel147。仅刷logdump，boot、persist与NV校准来源未改。回退基线为E:/edk2-samurai-out/kernel145/logdump-k145-dsi-observation.img；回退也必须重新确认当前设备状态，不能复用147部署前的146身份和收据。
