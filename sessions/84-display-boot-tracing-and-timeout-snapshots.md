# Session84：显示首次启动跟踪与超时快照

日期2026-10-10。部署了保留现有硬件修复的诊断内核。当前为#85，启动ID
f02d218a-cc7d-4b92-8858-c8eeaeab5777；404.09秒完整采集和513.90秒复查均taint0、
显示超时0、underrun0。两个独立600翻页探测的完成事件和CRC均通过。
77首次接管失败、80两次帧完成超时仍开放；本轮没有新光学观察，也没有证明根因已修复。

## 配置、部署和保留范围

实际源码仍在/home/cy122/x2pro-linux/linux，initramfs仍在同级initramfs目录。
源代码及设备树未修改：保留全部dirty修复、备份文件、EUD、显示/GPU、触摸、电量计、
QUP1总线和USB SSH配置。新旧initramfs CPIO逐字节相同，init/USB hook/SSH身份与模式保留。
编译器为aarch64-linux-gnu-gcc15.2.0，实际构建版本先#84后#85。

仅启用事件跟踪及依赖，FUNCTION_TRACER/FUNCTION_GRAPH_TRACER/DYNAMIC_DEBUG保持关闭。
第一次配置有57项差异，包含依赖和未选默认项；修正有6项差异，详见final-validation.json。
这不表示新增57个硬件驱动。初始tracer为nop，clock为mono；没有启用函数插桩、
动态kprobe/BPF程序、全局事件printk或其它未经验证的硬件驱动。

两次均只写logdump。分别核对F1回执、WSL owner释放、fastboot序列62bc28a1、product
msmnile及64MiB容量；写前检查PARTNAME、分区大小、运行boot ID和旧镜像哈希。
FAT只替换Image，samurai.dtb逐字节保持。boot、Android、userdata及GPT未写。
boot回读校验为原镜像长度6682624字节的前缀，不是整个96MiB分区的哈希。

| 对象 | SHA256 |
|---|---|
| boot原镜像长度前缀，前后保持 | 08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 |
| session75/#76 logdump回退镜像 | 607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0 |
| #84诊断logdump | 8bb97ccb828dc8ccfaeb856be00b9a83f3b9fc57340208a24a7f9a51d88d8abe |
| 当前#85诊断logdump，64MiB | 60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b |
| 当前Image，36719104字节 | 1e7bb4a9696973f3f487a1dc0e6a7f087deeac957f7eaf0f69699787cea4a9d9 |
| 当前完整配置，私人保存 | 130b0e0de1206bd57bb7e00ae236536554735d9c38209daf806bece3bd39fc41 |
| FAT设备树，前后保持 | 9b0fcb9f5cba32c2649e35377a055d166bc1a32fe67cb77423156bdc652cd9d6 |

私人回退位于E:/edk2-samurai-out/kernel84/boot-before.img、logdump-before.img。
无需回退boot即可恢复部署前的#76 Image；若需要session75其它基线组合，仍按原记录核对。
不运行旧build-image.sh，不重置源码树。ARM64 image_size包含BSS，可以大于Image文件长度。

## 失败迭代和修正

#84在184.14秒保存了启动状态，DPU跟踪工作、显示超时0，但日志有两条明确错误：
未启用HIST_TRIGGERS，启动配置未安装snapshot动作；drm:drm_vblank_event*未成功启用。
当时trigger只有可用动作列表，没有活动快照动作。该启动的环形缓冲也已覆盖部分早期事件，
完整dmesg和实际错误均保留，不能把它作为自动快照成功或完整首次接管证据。

核对本机kernel/trace/trace_boot.c发现event.actions整体受HIST_TRIGGERS门槛限制，
包括通用snapshot动作。因此#85启用HIST_TRIGGERS及其依赖，事件组改为dpu:*、drm:*、
drm_msm_atomic:*。Image中嵌入的bootconfig与私人原文件完全一致，主机同源码解析器通过。
[内核启动跟踪文档](https://www.kernel.org/doc/html/v6.12/trace/boottime-trace.html)说明
实例、缓冲、事件组及事件动作；实际门槛和匹配结果以本机源码及实机日志为准。

#85在65.28秒取得完整首次启动包：19节点bootconfig、79项启用事件、nop/mono、
实际513KiB/CPU，snapshot:count=1。无trace_boot错误，无显示超时/下溢；21409条事件，
八个CPU的overrun、dropped及commit overrun均为0。首次启动过程已实际记录。
没有人为触发显示故障，所以“真实超时执行快照”尚未验证。

## USB恢复和采集边界

F1已经回执后，EUD设备离开产生libusb EIO；finally释放了接口及WSL附着，不重复F1。
#84重启后NCM接口虽出现，CTL_OUT仅1，COM/VBUS attach位未恢复，SSH不可用。
核对现有eudtool源码/工具哈希后，使用既有com-up恢复COM与NCM。

#85的刷写/重启均成功，但flash-ready.ps1等待EUD控制口的15次500ms窗口过短，
后续恢复阶段报Expected EUD control identity absent。该错误不代表刷写失败。
控制口实际出现后重新只读确认A1 28 BC 62，再执行一次com-up；保留失败日志及恢复记录。
不重跑刷写脚本。com-up仅写COM_EN、VBUS_ATTACH、VBUS_INT及零CLR，未写CHGR_EN/INT。
它包含主机控制写帧，不能表述为“整个过程完全只读”。

NCM最终到约55秒可SSH，面板约36.68秒完成初始化；被动COM采集175帧、stray0、sent0，
端口已关闭。首次2.746MiB包的SCP连接在最后约10KiB处中断，保留不完整文件；
重新下载的完整包SHA256为93f10bf041ebf24603e8f31be8e54732eb183960457d6d43126e4470cf9a59d4，
全部成员与设备端哈希通过。后续包压缩传输，解压字节与设备端TAR哈希一致。

## 翻页、控制台及空闲观测

复用固定SHA256的已有KMS工具，每次600次双缓冲翻页；无显式CRTC关闭或面板电源循环。
分别用20.042792和20.050388秒完成；每次1199条CRC样本中，600个最终请求图案全匹配，
翻页完成事件和最终CRC序号单调。随后直接恢复控制台并继续记录5秒空闲。

第一次探测的513KiB/CPU缓冲在CPU0/CPU2覆盖111/5944条事件，其余无覆盖。
完成事件与CRC仍通过，但跟踪过程不完整；原始记录和validation的false边界保留。
第二次只把运行时display实例缓冲申请改为2048KiB/CPU，实际2051KiB/CPU；
重复600次后八核overrun/dropped/commit overrun全0，开始/返回/空闲结束标记均保留。
跟踪包含628次原子提交开始/结束、628次帧完成回调及资源/TE/中断开关过程。
内核自动空闲资源开关是正常驱动路径记录，不能说驱动从未切换电源资源。

404.09秒保存最终状态后清空已归档的活动trace，保留snapshot及其剩余计数，重新启用
display实例供后续空闲故障观测。513.90秒复查on1、snapshot:count=1、超时0、taint0。
扩大缓冲只在本次运行时生效，重启仍回到513KiB/CPU启动配置。
长时间环形缓冲自然覆盖旧事件，超时快照用于固定故障前窗口；不能称持续保留完整历史。
[ftrace文档](https://www.kernel.org/doc/html/latest/trace/ftrace.html)说明环形缓冲及快照机制。

## 电池、充电和后续

404.09秒电池包8.638V、SOC99%、31.4°C、0mA，标准接口Not charging。
固定QUP1/0x5c工具读12个已知寄存器，全部与部署前一致；仅有寄存器选择写消息，
没有配置数据写、扫描、REG14故障读取、ADC启用、复位、喂狗、GPIO/OTG/FET操作。
没有新增电量计身份/MAC/保护查询。原有NTC/watchdog关闭、终止/12小时计时器开启的
继承状态不是推荐配置，也不构成充电安全验收。

session83官方Android R/cyborg源码和Android11底包对照继续有效。精确历史构建、2719
器件/短路IC保护映射、均衡温度补偿、热敏/USB预算及失联安全仍待核实，权限足够。
本轮充电控制没有启用，无光学/GPU压力/90Hz/休眠和无线新验收，全硬件目标保持active。
下一步先保存活动trace/snapshot及完整dmesg再处理故障，不以自动开关屏隐藏问题；
没有新故障时继续本机充电保护链和无线远端服务/板数据的受限接入。

reference/kernel84的README、实际脚本、压缩原始跟踪、状态和审计结果对应本轮两次部署。
完整配置、initramfs身份清单、Image/FAT镜像、可执行工具及密钥仅留私人目录。
