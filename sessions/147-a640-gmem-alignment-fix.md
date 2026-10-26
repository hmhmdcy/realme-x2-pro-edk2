# A640 GMEM 迟发 CCU fault 修复（阶段147，2026-10-13）

本次GPU目标完成：已修复并实机验收此前固定800×600 glmark2成功退出后出现的CCU READ TRANSLATION故障。手机当前#147/software132，boot132、logdump147、770模块132。仅刷logdump。

修复为A640内核管理私有GPU VM的IOVA起点采用64KiB对齐；默认及其他GPU仍按PAGE_SIZE，用户管理VM_BIND地址由用户态选择。BO大小、实际映射范围保持，虚拟地址空隙不映射物理内存。#146无效的CCU事件顺序实验已撤销。独立补丁在[reference/kernel147/a640-managed-iova-alignment.patch](../reference/kernel147/a640-managed-iova-alignment.patch)，其他原有源码差异已核对保留。

证据链包括原#145默认GMEM失败、#146多个隔离对照、#147实际RD中BO起点对齐确认。原版转储30条BO记录全部不满足64KiB对齐，#147对应30条全部对齐；它们各有18个不同BO、3次提交。该实验指向本机GMEM resolve地址对齐问题，尚不等同于证明所有Adreno的硬件规范。固定提交的原厂KGSL也提高大导入缓冲区对齐，来源见reference/kernel147/oem-alignment-source-validation.json。

同一#147启动通过20次800×600像素验证：带RD默认build8、无RD默认build4、不用VBO2、最近邻纹理3、线性纹理3；又通过6次1080×2259连续绘制：build、线性纹理、Phong各2次，每轮2秒。默认Mesa策略保持，未强制sysmem或关闭UBWC/binning。每次退出观察35、40或90秒，总26次退出无GPU fault，taint0，警告、DPU timeout、DSI error、DMA prepare计数均为0，桌面进程身份保持。每组提交追踪没有丢事件，所有归档和内部文件SHA256已验证。

连续绘制实际使用1080×2259，首个控制脚本误要求800×600而中断；修正尺寸断言后复核原始结果并继续剩余场景，未重复已经完成的GPU负载。两个分辨率分别记录，未把benchmark当作像素验证。

W=1 MSM与完整Image/modules/DTB编译无警告；config与DTB保持，770模块逐字节等同132。刷写前重新核验#146实际身份、静止状态、分区和来源；唯一F1收据后确认fastboot身份/产品/几何再刷logdump。实机logdump读回匹配，boot与persist哈希保持。结束时NV、原厂来源、模块校验通过，没有遗留临时GPU追踪或待取core。源代码验收后只改了一行说明注释，不改变已部署机器码的行为。

当前验收范围是本机A640旧式内核管理私有VM的GLES默认GMEM路径。Vulkan用户管理VM_BIND、其他GPU型号未验收。显示启动偶发问题、音频、充电和其他整机适配问题仍是独立待办，本次干净窗口不代表它们已修复。

实机与校验报告见reference/kernel147/gpu-regression-validation.json、closeout-validation.json、build-package-validation.json、rd-alignment-validation.json。原始core/RD、BO地址、启动身份及刷写收据只在E:/edk2-samurai-out/kernel146和kernel147。原#145回退镜像保留；再次切换必须确认当前#147状态，不能重用部署前#146收据。
