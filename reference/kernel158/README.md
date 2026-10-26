# 158：在 DPU 清理固件 CTL 之前停止 DSI

157 真实首次启动在 CTL 接管处返回 -22，早于其 before-PHY 停机路径。单次重探测和原 initial_session 暂时恢复桌面进程，之后出现不同 boot ID 的 RAM 诊断启动，UFS 再次阻塞，重启原因未知。

158 在 SM8150 的 DPU boot cleanup 内、dpu_rm_clear_boot_config 之前，逐一停止已经绑定的 DSI host。复用 157 的 runtime PM、读回确认和一次性标志，before-PHY 路径继续作为幂等回退。首帧门控函数与普通面板行为保持。[补丁](before-ctl-stop.patch)

实际提取四个函数，22 项普通及 ASAN/UBSAN 测试通过；157 基线缺少 pre-CTL 动作，两个早停负对照失败。检查真实 hw_init 源码确认 stop 调用早于 CTL cleanup，并限定在 SM8150 分支。W=1、完整 Image/模块/DTB、checkpatch、FAT 和模块兼容检查通过。[测试](actual-function-test-validation.json)、[构建](build-package-validation.json)

准备脚本的函数定位守卫先因前置声明匹配被阻止，在确认源码未改动后修正定位。首次 checkpatch 缺少函数前空行，被构建入口阻止，修正后通过。保留原检查记录。

实际切换使用新 #157 RAM boot 身份，确认无磁盘文件系统、taint0、无桌面进程并保存现场。一次 F1 已受理，device_shutdown 被存储探测阻塞；保存 SysRq w 后再次确认同一 RAM 状态，一次 SysRq b 完成已接受的 bootloader 切换。独立核实实际 bootloader、设备身份、产品及分区大小，只刷 logdump158。

158 已实际首次启动成功，日志先记录 CTRL=0x1f5→0，再记录 CTL0 清理成功，随后 PHY/host native 初始化。Phosh 在 uptime19.99秒启动。全boot KMS初始化失败、DSI错误、DPU超时、GPU fault、WARN均0，taint0；原有音频DMA prepare9仍是其它待办。实际logdump读回、boot/persist、NV、770原模块、Mesa149库均核验通过。[首次结果](first-boot-validation.json)、[运行核验](runtime-validation.json)

24次标准DPMS无新增错误，12次亮屏均在真实PP TX done和成功wait之后放行背光；用户手动多次开关屏确认不再闪屏。[时序](first-frame-order-validation.json)、[电源回归](cycles-validation.json)。首次158的现场采集从uptime230.65秒开始，92.94秒无丢失，KMS快照是late live；早期顺序依据完整dmesg及bootconfig记录，不能称late快照为首帧快照。

159只重启同一158镜像，没有刷写；第二次首次CTRL/CTL接管同样成功，全boot关键错误计数0。早期服务17.72秒开始，93.05秒无丢失，记录真实初始PP TX done后44微秒wait成功。Phosh19.56秒，另24次DPMS与12次背光门控顺序通过，两次累计48次电源转换。实体启动过渡与连续稳定观察仍待收尾。[159复测](../kernel159/README.md)

可审查的合并补丁基于154，包含156、157、158的14个源码文件修改；当前源码逆向apply检查通过。[完整补丁](display-fix-from154.patch)、[补丁核验](consolidated-patch-validation.json)。greetd启动顺序配置是独立可回退改动，详见156记录。
