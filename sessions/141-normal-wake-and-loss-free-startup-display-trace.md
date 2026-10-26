# 阶段141：普通亮屏和新启动显示追踪

2026-10-12。阶段141实际仍为#140/software132，普通亮屏53.835秒观察无新增错误；同一内核受控重启一次、未写分区。新启动86.699秒追踪保留两次显示超时完整窗口、无丢失，帧完成回调在91.018/95.291ms到达，83ms看门狗保持。桌面1869次GPU提交/刷新/退休对应、无fault，不能替代136专项迟发CCU故障的验收。首次TX诊断确认state=DOWN且channel为空，前有PDR监听超时和SSR唤醒失败；BAM分配失败/挂起拒绝诊断未出现。实际boot/logdump/liveDT/GPT18/persist/770模块及来源全通过；随后28.564秒8次观察桌面PID、taint0及计数不变，累计DPU3/DSI0/GPU0/WARN0/TXprepare9。显示、GPU、充电与完整系统目标仍active。

旧140 boot的四次显示timeout与默认trace逐一对应，但CPU0/1/2有overrun，只用于有证据的时序，不由事件缺失推断没有中断。旧boot同函数trace紧邻错误打印的四对偏移约2.856921秒，范围仅该boot；不能移用到136或本次新boot。一次普通wlr-randr亮屏中4次PP帧完成为14–26ms，5次桌面GPU submit/flush/retired对应，53.835秒计数不变。该测试没有独立GPU benchmark，不证明专项CCU根因修复，也未取得实际像素可见性确认。

完整140来源/分区审计、GUI/DRM/PCM/功放/三个远端排空、freeze/F1各一次，然后fastboot仅reboot。同一#140版本号不能证明新启动，已另验真实boot标识改变。没有构建141内核或写boot/logdump/userdata。当前真实身份以私有kernel141/embedded-boot-id-private.txt、phone k141-first-runtime为准；kernel141/source-boot-id为重启前的旧140，kernel140/embedded-boot-id也已成为历史。

新boot59.33秒起的独立8192KiB/CPU实例持续86.699秒，8CPU的overrun/commit overrun/dropped均0；最后Phosh/Phoc稳定，实例已禁用移除。1182次kickoff及PP完成对应，1869次普通桌面GPU提交均退休；正常看门狗完成中位16.437ms，两次超时对应91.018ms和95.291ms的迟到PP回调，期间没有新的kickoff，资源状态ON。回调晚到不证明是假超时；现有trace没有IRQ entry/exit、CPU idle和完整硬件TE边沿，下一项需补充它们区分中断延迟/硬件停帧。默认early实例虽未overrun且有最初一次timeout，但第一条已是timeout，缺其前置arm，不能说三个超时都有完整前因。

首次TX diagnostic为state3/qmi1/channel0/device0/sg0/config_sg0/len8。源码枚举证明3是DOWN；前有两次PDR listener -110和HW wakeup attempt during SSR。之后9次prepare失败，稍后codec再次探测成功；139未提交资源回收保持，没有ENOSPC。此次不是BAM malloc失败或已证明EBUSY挂起链，不改GFP。runtime_resume会丢弃power_up的错误是真实代码缺陷候选，但直接return ret可能让runtime PM保留错误、阻止下次QMI UP恢复；先核查恢复语义和实际函数测试，再决定补丁。尚未应用该修改。

用户询问搜索线索后核对了上游DPU空闲timer竞态讨论、SLIMbus error-path提案、Mesa Freedreno缓存说明和MPS MP2650官方产品说明。DPU讨论的busy已清零条件不等于当前busy1；SLIMbus提案作者只做编译测试，本地139已有12项实际函数注入和实机恢复证据；Mesa CCU资料支持检查图像回写/缓存/映射方向，不等于现成修复；MP2650支持buck或boost和2–4节，不能由USB5V直接判为不能充电。来源和适用范围见reference/kernel141/internet-leads.md。

充电仍只有观测链和138只读阈值证据，当前132没有134输入额度驱动；恢复阈值8.525V、目标8.725V不能替代保护、温度、失联和持续充电验收。后续被动8次观察无计数/PID增长，但累计3个DPU和9个TX错误保持，因此仍不满足无报错目标。

所有raw日志、地址、PID、boot标识、来源、镜像在E:/edk2-samurai-out/kernel141与phone /var/lib/samurai/k141-*。141一次性动作已终态，下一次诊断使用新阶段/新前缀和当前真实boot审计，不重放141。

证据：reference/kernel141/normal-wake-validation.json、reboot140-startup-validation.json、early-startup-validation.json、new-boot-findings-validation.json、first-runtime-validation.json、settled-health-validation.json。既有功能回收见[139](139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)，GPU故障见[136](136-legacy-gpu-vm-trace-and-ccu-address-correlation.md)，充电见[138](138-readonly-charger-recharge-threshold.md)。
