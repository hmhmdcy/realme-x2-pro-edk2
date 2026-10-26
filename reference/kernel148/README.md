# 阶段148：Vulkan VM_BIND 调试

2026-10-13按用户要求完成本轮收尾，修复目标尚未完成。手机运行阶段147内核及software132；进入本阶段前，GNOME Settings出现新的CCU READ TRANSLATION，累计GPU fault为1。阶段147验收只覆盖旧式内核管理VM/GLES，不能用该验收证明Vulkan已修复。最终复核见[closeout-final-check.json](closeout-final-check.json)，收据/归档/源码语法核对见[closeout-verification.json](closeout-verification.json)。

本阶段使用现有本地源码、隔离编译工具和USB SSH进行驱动调试。没有刷写分区，也没有替换系统Mesa。以[当前操作边界](../../WORKING-BOUNDARIES.md)为准。

已从官方Mesa 26.2.4源码在手机隔离目录编译未修改基线及候选。候选仅对A640的自动VM_BIND IOVA分配采用64 KiB对齐；显式capture/replay地址、映射长度、稀疏绑定偏移及其他GPU保持原语义。源补丁见[a640-vm-bind-iova-alignment-diagnostic.patch](a640-vm-bind-iova-alignment-diagnostic.patch)，源码和库摘要见[candidate-preparation.json](candidate-preparation.json)。两套库通过测试进程的VK_DRIVER_FILES选择。

[vulkan-validation.json](vulkan-validation.json)保存36条测试收据，32条返回成功，4条失败如实保留；返回成功也不等于所有应用功能均已验收，早期Settings测试有意终止进程。测试前后累计fault均为1表示没有新增fault，不能写成累计fault为0。原始GNOME故障完整devcoredump未及时保存，本阶段尚未复现；候选通过测试不构成根因证明。最终设备和清理核验见[closeout.json](closeout.json)。

已验证：同构建基线与候选离屏像素读回、1x/4x MSAA及不同分辨率；GTK模糊/透明渲染；GPU运行时挂起与恢复；稀疏缓冲区重绑定与解绑定；capture/replay。候选自动映射起点实际全部64 KiB对齐。候选已成功重放旧基线的非64 KiB对齐捕获地址，两个重放的写入/读回全部一致；其中显式映射仍未对齐，属于有意保留的API语义。

双Vulkan进程基线/候选分别完成192次绘制、1854次映射与解映射，像素全一致，退出后观察60秒无新增fault。两套驱动也通过Vulkan与GTK OpenGL同时渲染，候选完成931次映射、927次解映射，Vulkan读回108,887,136像素全一致。新像素矩阵覆盖RGBA8、BGRA8 sRGB、RGBA16F与360×753、37×21、1080×2259、801×603、320×640；基线与候选30次循环全通过。

两套驱动均通过四次有限扫描的内存回收及后续12次像素读回。追踪记录基线purge 2560页、evict 3120页，候选evict 10258页；实际回收按整个BO进行，可超过请求的64页扫描额度。接口返回SHRINK_STOP不代表没有回收，本结论以msm_gem_shrink追踪为据。没有证明被回收的每个对象都属于测试进程。

两套驱动均以--gapplication-service启动GNOME Settings，完成18次面板打开，经实际存在的quit action正常退出，随后观察60秒无新增fault；新测试有单独的应用退出收据，不只依赖Phoc退出码。独立无头显示设置为1080×2259、3倍缩放后，两套驱动同样通过生命周期测试。系统原驱动和候选还在默认自动调优模式下各完成18次面板打开和正常退出；首个TU转储前3帧未见bin render/resolve，不能据此判断整个应用的渲染模式。

最后一组默认自动调优测试交替提交1次/128次绘制；基线和候选各完成24次读回、27,221,784像素、242次映射与解映射，以及21次GPU挂起/恢复，退出后观察60秒无新增fault。基线有228次非64KiB对齐映射，候选为0。两套驱动首个TU转储前12帧均已解码，各包含447次bin render和6次resolve，证明默认模式下实际执行过GMEM；限定帧解码不能当作全部命令的结论。

真实GPU命令解码确认候选GTK执行1824次bin render和576次resolve，与对应基线相同。像素PM归档已限定到前3帧成功解码，执行30次bin render和6次resolve；此前完整解码超时仍如实保留。

失败与限制：物理锁屏会话上的两个vkcube尝试超时，开关输出的尝试导致原Phosh会话退出，已按原greetd配置恢复。独立无头会话180帧vkcube超时，24帧成功。首次旧地址重放测试因测试程序误拒绝合法的零opaque buffer地址退出9；已依据Mesa实现修正并重跑。早期Settings循环误用了accessibility面板名，已按实际列表改为universal-access。独立Phoc缺少Mutter DisplayConfig服务，不能据此验收完整显示设置功能。

最早两个物理vkcube超时收据把请求的退出后观察时间记成了实际观察时间，但异常路径跳过了该窗口。收集报告已保留原值并把实际延后观察修正为0；这些失败不能作为延迟故障验收通过。新runner按实际观察秒数记录。

原始地址、启动身份、进程日志、GPU命令及归档只保存在私有E:/edk2-samurai-out/kernel148和手机/var/lib/samurai/k148-*。公开报告仅保留统计和摘要。解码较大像素命令归档的首次尝试超过120秒；须限定帧范围后重新解码，不能把该次超时写成成功。

本内核没有msm_gpu_vm_update/msm_gpu_vm_switch_enqueue这两个追踪事件；其结果计数0不能证明没有VM切换。实际启用事件由新测试的enabled_trace_events记录，映射对齐证据来自成功的VM_BIND ioctl观察。

后续调查仍需复现原始CCU fault，取得完整转储及映射关系，再决定是否部署候选。本轮按用户要求停止增加测试，候选未推广，系统驱动SHA256仍为c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955。

30分钟有界core捕获窗口已自行退出，active=false，捕获0份新core、0次捕获错误，fault计数1→1。收尾时测试进程和k148追踪实例均为0；原启动及恢复后的Phosh/Phoc保持，taint0，系统Mesa、包数据库和原greetd配置摘要均保持。

36份测试归档和入口归档共37份已逐一核对SHA256，转存手机持久目录/var/lib/samurai/k148-private-archives，清除/tmp重复副本约578MiB。21份上传源码保存到/var/lib/samurai/k148-tools/uploaded-sources后移除临时副本。手机源码、两套构建和隔离SDK保留；SDK位于/tmp，重启后需重新准备。主机已有24份原始归档、收尾收据包及两套库副本，复制后的SHA256均核对通过；其余原始归档保存在手机持久目录，不声称全部已下载到主机。

最后的离线解码结束后，WSL的118诊断构建卷已卸载，对应loop已释放，20GiB ext4镜像及原备份保持。恢复工作时先检查实际手机状态。需要运行旧工具时，从公开源码重新上传/tmp/k148-*.py等依赖；不要直接复用仅在旧启动有效的进程号或启动身份。[closeout.py](closeout.py)已执行完成，拒绝在完成标记存在时再次执行。
