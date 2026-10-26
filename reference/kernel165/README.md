# 165：同一 boot164/kernel163 第二次启动软件验收

保持固件与内核，按新的当前身份正常停机/F2FS冻结，单次F1后核对实际bootloader，仅fastboot reboot，没有新增刷写。停机时只为退出164失败boot接受那一个已记录音频WARN；新启动仍要求零WARN和taint0。[工具范围](tools-validation.json)

新boot仍kernel163、boot164/logdump163/modules132/software132+Mesa149。Phoc19.73/Phosh21.45秒，全boot KMS/DSI/DPU/GPU/WARN/audio DMA prepare均0，taint0。boot164及logdump163真实读回、persist/NV/模块/Mesa均保持。[运行验证](runtime-validation.json)、[启动时间](boot-timing-validation.json)

UEFI保留日志再次记录BeforeExitBootServices回调Success、无ring丢失；固件在Linux开始初始化前请求GPIO6物理低，原生面板负责后续恢复。native CTRL先停再清CTL；初始PP TX done后约210微秒wait成功；24次标准DPMS无新增错误，12次实际亮屏门控均在PP TX done及ret0等待后完成，早期/电源trace无丢失。[顺序验证](startup-order-validation.json)、[电源回归](cycles-validation.json)

连续601.15秒、21次采样到uptime918.47，同boot/桌面PID保持，关键故障0、taint0，没有看到非指令重启。最终现场再次核对同一boot、桌面进程及taint0，临时启动记录器已停并退出runlevel。[稳态验证](steady-validation.json)、[最终现场](final-live-validation.json)

后续用户实屏反馈：“现在倒是不会了，EDK2 之后会黑屏一段时间，然后再看到命令行。”本次观察的交接白屏/花屏验收通过；黑屏等待仍存在，用户未报告时长。固件没有添加固定延时，而是在BeforeExitBootServices保持面板复位，待Linux正常初始化恢复。此时只读核对为新的boot，仍kernel163、boot164/logdump163读回匹配、桌面进程存在、taint0，全boot显示/GPU/WARN/audio DMA prepare计数0。165的601秒与24次DPMS证据属于此前boot，不复用于这个新boot；本轮没有发送重启或刷写命令，不推断其启动来源。[实屏反馈及当前核对](physical-feedback-validation.json)

164首次的WCD934x WARN及917条DMA prepare失败没有在165及反馈后的新boot重现，原因仍未知，不宣称音频已修复。157非指令重启原因也仍未知。本次显示故障按已测范围收尾；冷启动、休眠及更长期稳定性仍开放。[当前范围](current-validation.json)

可审查内核合并补丁基于154，含15个文件，当前源码哈希与编译163一致，逆向apply检查通过；固件164补丁属于另一个仓库。[内核补丁](kernel-display-fix-from154.patch)、[固件补丁](../kernel164/before-exit-panel-reset.patch)

完整私人启动/回归档案SHA256：`8ff3b50e321f2cb55abe2036a4274dbd252458b7944d8fc9e607f52ef27e807e`。其它私人档案只公开哈希，不公开原始日志或密钥。[归档摘要](evidence-archives.json)
