# 阶段140：首次DMA诊断与显示启动超时

2026-10-12。当前实际#140/software132：保留139未提交TX回收，只增加首次NULL/BAM分配失败/挂起拒绝诊断，没有修改挂起顺序或GFP策略。139实际函数注入12项通过，100次失败后仍可发送，较早在途槽位与TID/PM回收保持。140四件套、770模块/DTB原字节和实际boot/logdump/liveDT/GPT18/persist/NV来源校验全通过，只刷logdump。140本次无TX DMA失败，三条诊断均未触发，不能证明根因已修。启动观察DPU1→4、桌面自主恢复；随后28.622秒8次被动观察，计数/PID稳定=True，累计DPU4/DSI0/GPU0/WARN0/DMA0，taint0。显示、GPU延迟CCU和充电控制保护仍未验收，完整系统goal active。

源码候选：NGD runtime_suspend先exit_dma再请求QMI；EBUSY返回时PM仍active且状态未进入ASLEEP，代码上能留下空channel。当前KPROBES/FUNCTION_TRACER关闭。140仅加入dev_err_once/dev_info_once数值诊断；没有改MFD、挂起顺序、GFP_NOWAIT、显示/GPU命令或充电寄存器。三条诊断都未触发是本次没有相应失败，不是空channel、内存不足或EBUSY机制已被证明。既有139 host注入用于回收逻辑，不覆盖140诊断或QMI/硬件时序。

Image/W=1对象/770模块/DTB、depmod、checkpatch均无警告错误。FAT两文件精确读取和只读fsck通过；模块770与DTB字节仍与132一致，initramfs蓝牙模块相符，boot及完整rootfs132936包复用。四件套重新完整hash。当前139先完整来源/分区审计、排空服务/DRM/PCM/功放/远端/追踪，freeze/F1各一次，只刷logdump。主机外层误把USB断开后的native exit当PS脚本失败，随后核对F1=1/out=1/freeze确认后继续；没有重发请求或重放转换。

实际140 boot/目标logdump/liveDT/GPT18/persist/770模块/NV6/来源4/vendor1/桌面3配置校验全通过。第一次28.563秒观察横跨桌面启动，PID由无到有、DPU由1到4，应保留为增长记录。后续独立settled窗口只读确认当前计数与PID，不重放内核/负载/寄存器读。所有原始身份、PID、地址、dmesg、镜像与日志在E:/edk2-samurai-out/kernel140及phone /var/lib/samurai/k140-*。

当前保留140诊断内核，所有本轮一次性部署终态。不得将DMA0的一个boot视作永久修复。未运行新GPU负载；136固定800×600仍有两次延迟CCU fault，故障地址未被所属VM记录的映射覆盖，7 BO各自在有效映射内，根因开放。充电138两节/目标8.725V/恢复阈值8.525V/termination已读回，不等于持续充电与保护完成。

下一工作转回显示：保存140启动DPU timeout与encoder/DRM时序，明确fbcon→Phosh过程中首TE/帧完成及pending kickoff状态。不因启动timeout计数已稳定宣称无报错，也不重复33场景或启用全局GPU debug。NGD首次NULL/QMI拒绝诊断留在当前内核等待真实事件，避免凭猜测改DMA分配政策。

证据：reference/kernel140/dma-diagnostic-source-validation.json、dma-diagnostic-build-package-validation.json、first-runtime-validation.json、first-health-validation.json、dma-first-failure-validation.json、settled-health-validation.json。前序功能回收见[139](139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)。
