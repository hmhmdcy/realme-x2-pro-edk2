# kernel108：显示故障取证与下一会话交接

关联[session108](../../sessions/108-display-flicker-and-panel-state-handover.md)和[next-session](next-session.md)。手机仍#106；没有修改实际内核、构建新Image或刷分区。用户已确认重启恢复黑底命令行；白底尚未复查。一次DRM开关屏导致黑屏，错误状态路径只定位未修。当前5GHzCOMPLETED，但数据复测失败。

公开目录只有自写工具/脚本、脱敏核验和文档。完整boot/logdump、所有原日志/tar、凭据/身份/固件响应、可执行工具和备份块只在私人E:/edk2-samurai-out/kernel108。

- collect-display-live.sh、inspect-display.py：只读故障现场，保留display snapshot。
- drm-panel-cycle.c、build-display-probe.sh、recover-display-once.sh：实际单次正常DRM关闭/恢复原fb，**ioctl退出0但用户黑屏，功能失败**；SHA守卫/新目录拒绝重放。
- display-recovery-summary.json是首版有限过滤结果，wifi字段为空源于漏指定wpa-control路径，不能据此判掉线；最终事实用checkpoint-validation.json与本会话用户报告。恢复脚本的同一错误已在封存时纠正，不重新执行。
- reboot-display-same-kernel.ps1、reboot-f1.ps1、read-eud.ps1：受控停radio/F1/独立fastboot只reboot，未flash；新boot身份和所有输出私人。
- test-auto-network.sh、final-network-state.sh：分别保存60秒关联超时原件与已有5G连接的网关/HTTP失败，不覆盖或改判。
- http-packet-capture.c、build-probes.sh：被动限定TCP80抓包工具Werror静态构建完成，尚未部署或抓包；不代表数据诊断完成。
- collect-checkpoint.sh、verify-handover.py、checkpoint-validation.json、private-archive-manifest.json：31直接文件/3原包/74项SHA、源码与完整备份/保留核验。
- prepare-tools.py及其余继承辅助工具：本轮新守卫准备记录；下一轮kernel109，不原样重放108目录/bootID/PID。

两个守卫误用历史build-hashes（其中无probe SHA）及带BOM/多行baseline文件，均在关屏执行前拒绝；改为本轮自写工具及独立LF私有bootID后才执行一次。一次重启后debugfs未挂载的空读数保留并补采。全目标active，充电/BT/振动/NFC约束保持，不提交推送。
