# 160：同一 #158 第三次启动，早期白屏仍未验收

用户要求再重启一次，按新的实际启动身份完成正常停机、F2FS 冻结、单次 F1 进入 bootloader，核对设备与产品后执行 fastboot reboot。没有刷写、没有新增内核构建，也没有使用紧急 SysRq。

本次 Phoc 在 uptime 17.44 秒、Phosh 在 19.43 秒启动。全 boot KMS 初始化失败、DSI 错误、DPU timeout、GPU fault 和 WARN 均 0，taint 0；音频 DMA prepare 9 仍是既有开放项。boot/persist、logdump158、模块132、NV 和 Mesa149 修复均核验通过。[运行验证](runtime-validation.json)、[启动时间](boot-timing-validation.json)

早期记录器 17.32 秒就绪，初始 TX wait 在真实 PP TX done 之后约 225 微秒、ret=0，固件 CTRL=0x1f5 停至 0 仍先于 CTL0 清理。临时启动记录服务已停止并移出 boot runlevel。[启动顺序](startup-order-validation.json)、[采集结果](startup-validation.json)

用户明确反馈：开机速度变快，但白屏花屏发生在 **edk2 画面消失后、Linux 命令行出现之前**。因此 #158 只通过已测唤醒及后续原生显示检查，整个显示 BUG 尚未完成。继续检查早期固件帧缓冲和硬件接管；不把零错误日志当成实体画面验收。用户已去睡觉，后续实体验收待回来。

本次 simpledrm 控制台在 uptime 13.23 秒建立，原生 msm 控制台在 14.82 秒建立。EFI 描述的帧缓冲地址 0x9d000000 在保留区内，simpledrm 使用的 1080x2400x4 字节范围也在该区内。ARM SMMU 的“preserved 0 boot mappings”日志只统计 ACPI RMR 条目，**不能据此认定 Qualcomm DT 路径没有继承固件 SMR**。早期 SMMU、时钟和电源初始化仍需实际取证。

私人启动档案 SHA256：`7ca5dd36d902f6efbebc38150d7a001e612b33369fdde31c42ad5124a5e56156`。当前源、镜像及实机均 #158；旧 #157 未指令重启的原因仍未知，保留历史，不由本轮结果推断其根因。
