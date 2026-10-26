# 阶段144：重启回执竞态定位与显示时钟核对

2026-10-12，完整显示、GPU、充电目标继续 active。

阶段144：确认143重启路径把F1日志入队后立即关闭EUD，实际函数宿主模型复现未发送回执和关闭后TTY写硬件两项回归。新补丁26项测试在普通编译及ASAN/UBSAN下通过，驱动W=1编译无警告；完整镜像链接中断，工作盘约120MiB可用，未产出144镜像、未部署。构建树源码144，残留Image仍为拒收143；手机仍为回退140/software132。140/143亮屏快照五项关键时钟相同，但143有171条status=c欠载记录，动态带宽/触发时序未证明。显示、136迟发CCU GPU、充电控制保护均未验收，goal active。

## 已验证的改动与边界

仅修改 drivers/tty/serial/eud.c。完整Git差异对比证明其他源码字节相同，139 TX失败回收、140 DMA诊断及内核配置均保留。重启路径先等待日志队列、注销打印线程，再与TTY发送互斥完成硬件关闭，并阻止关闭后的任何发送写入。

12个驱动函数直接抽取入宿主测试。旧143普通及ASAN/UBSAN各复现两项退出回归，新144普通及ASAN/UBSAN各通过26项，包含原16项普通发送、退出排空、重复命令、错误长度、RX IRQ同步、并发打印和首次flush失败后的注销。模型证明同步机制，不能代替真实主机收到F1，也没有实机panic证明。

驱动对象W=1编译通过、checkpatch零错误/警告；完整Image/modules/DTB构建在链接vmlinux.unstripped处中断，日志没有可据以确认原因的编译器报错，WSL随后重新启动。E盘只余约120MiB。当前vmlinux.o、若干.tmp_vmlinux对象及vmlinux.unstripped为零字节，不能直接沿用其时间戳。未重试同一构建，未生成完整新镜像、刷机包或新模块安装树。

## 显示证据

140启动、143启动与当前140空闲快照均核对所选文件manifest。两次亮屏的MDP200MHz、PCLK61.768MHz、BYTE46.326MHz、BYTE_INTF23.163MHz、DSI VCO1.482GHz及准备/启用计数相同。140快照DSI状态记录0、DPU超时2；143为171条status=c及DPU0。记录数量不是物理欠载次数。这不是控制变量时钟实验，快照不能证明动态ICC带宽或TE/MDP触发关系。

当前140只读快照累计DPU0/DSI0/GPU0/WARN0/TXprepare9、taint0，显示已自动空闲。空闲无新增报错不能算显示或迟发GPU专项验收。

## 上游线索与适用范围

- [Linux printk文档](https://cdn.kernel.org/doc/html/latest/core-api/printk-basics.html)：旧式控制台同步打印会长时间关中断，推荐nbcon线程。与142/143实测机制相符。
- [Linux DSI源码](https://code.googlesource.com/linux/torvalds/linux/+/2a565258b3f4bbdc7a3c09cd02082cb286a7bffc/drivers/gpu/drm/msm/dsi/dsi_host.c)：FIFO错误先读原始寄存器再写回清除，worker收到MDP欠载后复位。聚合status=c只说明FIFO和MDP欠载，不能指认面板、带宽或时序根因。
- [Mesa Freedreno文档](https://docs.mesa3d.org/drivers/freedreno.html)：CCU用于系统内存渲染目标、2D搬运和GMEM解析；GPU流水线使故障快照位置可能晚于触发命令。仅为136迟发CCU的调查方向，并不证明缓存配置、映射生命周期或某个BO已错。
- [MP2650原厂资料](https://www.monolithicpower.com/en/mp2650.html)与[原厂手册](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/)：可核对输入额度、2节电池调压、温度与故障保护。138终止/恢复阈值现场仍是本机证据；可读电压、电流不能代替持续充电控制验收。
- [SLIMbus TX失败资源回收讨论](https://lkml.iu.edu/2609.2/05810.html)提出相同泄漏问题，但审阅者仍追问真机验证；不能照搬其推进head的实现覆盖本地保留旧在途描述符的139修复。
- [SLIMbus ABBA修复](https://lists.openwall.net/linux-kernel/2026/04/01/251)说明SSR锁序风险，本地已包含对应移除，不能重新盲加tx_lock。
- [Realme官方Android源码](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)可作原厂行为参考，本轮未找到已经针对本机验证、可以直接套用的三项完整修复。

## 下一步与现场约束

先检查可用内存和磁盘，再清理仅限本次零字节生成物后重试链接；可核查GNU ld的--no-keep-memory以减少链接峰值，不修改内核功能配置或用户全局交换设置。Image构建成功前禁止打包/部署，不能把残留143 Image当作144。

显示优先记录现有读取到的DSI原始FIFO状态及worker复位边界，关联已有DPU kickoff/完成事件，避免增加printk和重复MMIO读取；先验证寄存器清除顺序未改，再设计一次新启动实验。不能直接重刷143或仅加超时/调高频率。

GPU136迟发CCU两次错误仍开放，gpu_probe_allowed=false；先关联同一VM和提交时刻的映射、BO与CCU状态，禁止旧33矩阵、全局debug/缓存刷新或凭画面正确接受。充电持续控制、输入/温度/保护/失联安全待办。143所有停机、切换、recorder、A/B和回退均终态，禁止重放。

手机身份仍只用私有kernel143/embedded-boot-id-private.txt或phone k143-rollback140-runtime。来源/原始日志/地址/镜像保存在私有out，不公开。E118访问仍需ensure与依赖读取同一WSL调用；原C VHD不动。不全刷userdata、无提交推送、BT不配对、振动不新增脉冲、无FET/OTG/OTP/unseal写入。
