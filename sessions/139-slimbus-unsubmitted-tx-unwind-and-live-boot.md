# 阶段139：SLIMbus未提交发送回收与实际启动

2026-10-12。从稳定132源码复用C侧构建存储，只改NGD和messaging两文件；136追踪和137 MFD/诊断增量恢复为132原字节，先封存137全部差异。NGD把预留槽位放到用户事务号分配后，在tx_lock内预留、组包、提交。prepare返回NULL时清completion并回退最新tail；不推进head，不回收已提交超时槽位。未提交的core/转换user事务释放TID并置零，直接user调用者维持原有TID所有权。messaging初始化TID提前，TID分配失败经过PM错误回收。DMA分配策略、GPU命令、显示和充电配置未改。

故障注入提取实际驱动5个函数与2个判定函数，宿主仅替换DMA/TID/锁/PM原语。原132连续prepare失败31次后队列耗尽，随后69次ENOMEM；139连续失败100次无耗尽，下一次有效发送及载荷正确。12项涵盖TID/PM回收、满队列、早期状态失败、转换user、直接user所有权以及较早在途槽位。地址/未定义行为检查无诊断。这证明错误回收逻辑，不等于实际DMA时序、首NULL原因或整机验收。

[上游同类槽位讨论](https://lkml.iu.edu/2609.2/05810.html)的作者确认[仅编译验证](https://lkml.iu.edu/2610.0/02660.html)；本地采用串行预留后回退tail，避免把较早在途head当未提交槽位释放。TID分配的PM回收与[已提出的修复](https://lkml.iu.edu/2609.2/04989.html)一致。没有提交、签名或声称上游已合入。

W=1对象和完整Image/770模块/DTB构建、depmod、增量checkpatch均无警告错误。全树diff检查发现继承132的eud_earlycon两处空白，保留原记录；本次两文件diff检查通过。770模块、DTB及initramfs蓝牙模块与132原字节一致。四件套重新全hash、FAT精确读回/fsck通过；boot及完整rootfs132保留，只刷logdump。服务/DRM/PCM/功放/远端/追踪先排空，freeze一次/F1一次，无userdata全量刷写。

实际#139/release k132 boot、logdump、liveDT、GPT18、persist、770模块、NV6/来源4/vendor1及桌面3配置校验通过。初始PID尚未启动，稍后Phosh/Phoc自主恢复；8次28.692秒被动观察PID不变、taint0，累计DPU2/DSI0/GPU0/WARN0/TX prepare70全部不变。70次prepare失败在26.612342–48.586130秒，未出现Message buffer unavailable或TX timeout，之后codec再次完成探测；符合回收后队列未耗尽，但首NULL原因未证明。不得因无WARN或桌面恢复宣称无报错。

当前保留#139/software132，完整rootfs936包/770模块，所有139一次性部署终态，不重放。GPU136的延迟CCU fault仍开放；139未施加GPU负载。充电仍是只读MP2650观测，138确认2S目标8.725V/恢复阈值8.525V和termination，不等于控制/保护验收。

下一定位：runtime_suspend在QMI拒绝前已清DMA channel，而EBUSY返回时PM维持active、状态未进入ASLEEP，代码上可造成后续prepare的channel空。尚未有本boot参数/返回值证明，不凭假设改DMA分配标志。当前KPROBES/FUNCTION_TRACER关闭，不能伪称已捕获动态参数；需要独立首次失败及suspend拒绝诊断。

证据：reference/kernel139/unwind-source-validation.json、host-fault-injection-validation.json、source-check-validation.json、unwind-build-package-validation.json、first-runtime-validation.json、first-health-validation.json。原始PID、地址、boot身份、日志、镜像留E:/edk2-samurai-out/kernel139与phone /var/lib/samurai/k139-*。
