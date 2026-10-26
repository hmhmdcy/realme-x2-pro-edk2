# 阶段108：显示滚动花屏、错误关屏黑屏与交接（2026-10-11）

手机仍Linux #106，镜像部署记录见[107](107-qrtr-hello-reply-and-automatic-wifi-start.md)。本轮未改实际内核源码或config/DTB/CPIO，未构建Image，未刷任何分区。用户要求更新文档并准备下一会话；状态缺陷只定位，尚未实现补丁。

用户依次报告“白底上有滚动条纹”“白色背景，不规律滚动闪烁的花屏”。这不是仅凭肉眼就能认定的屏幕硬件损坏。先保存SSH dmesg、DRM/encoder、亮度、display trace/snapshot，再尝试一次正常DRM关屏/开屏，随后保存黑屏现场并受控暖重启。

## 显示发现与失败证据

- 故障现场原生1080×2400@60、command mode、brightness/actual_brightness均400/max2047。actual_brightness在这个驱动没有硬件读回实现，不能把sysfs数值当作光学亮度验证。
- 日志环中持续`dsi_err_worker: status=c`，受限速/环滚动影响不是整个启动错误总数。实际源码中FIFO=0x4、MDP FIFO underflow=0x8；worker在该位出现时调用dsi_sw_reset。DPU underrun计数仍0，不等于DSI FIFO没有下溢；故障前frame_done_cnt为2，这个名称实际统计完成超时。
- 一次正常DRM_SETCRTC关闭/恢复原fb93，ioctl退出0；用户确认**黑屏**，因此功能测试失败。保留旧display snapshot摘要一致，未清空或重武装旧故障快照。
- 随后日志：backlight disable -110、SET_DISPLAY_OFF -110、ENTER_SLEEP_MODE -110，以及“Skipping prepare of already prepared panel”“Skipping enable of already enabled panel”。黑屏时bl_power=4，亮度软件值仍400。
- 源码链条：`sofef03f_unprepare()`发送睡眠命令，随后无条件`sofef03f_power_off()`，却返回累积的DCS错误；`drm_panel_unprepare()`遇负返回值不清prepared。disable的负返回值同样阻止core清enabled。下一次prepare/enable因此被跳过，硬件断电与软件标志矛盾。这解释了本次错误关屏后黑屏；还没有证明最初DSI下溢的触发原因。
- 不把删除错误日志、延长等待、增加自动开关屏当修复。下一轮应审查超时后的关屏/断电完成语义、regulator引用平衡和重新prepare/enable路径，保留错误可见；先做真实函数的失败路径验证，再新守卫构建/刷入。

保存全部现场后，经WPA→BT→ath10k→MPSS受控停止、真实F1回执、独立fastboot身份/product校验，只执行同镜像reboot。用户确认**黑底Linux命令行可见**。新boot面板44.248578秒报告power mode0x9c；405.44秒检查点DSI错误0、显示超时0、bl_power0、brightness400、taint0。纯白画面未再做光学确认，本次成功不能覆盖旧失败或宣称永久修复。

## 无线现状与新失败

第二个新boot仍自动radio初始化成功：boot-finished0，modem首次up49.082914秒，检查点连续running356.357086秒；三个modem服务公告发送result0，真实kernel/elf_loader PD回复及固件/RAM COW NV请求，无trace丢失、无手动MPSS恢复/ADSP重启。107的QRTR修复在重复暖重启得到支持，未做断电冷启动或休眠。

5GHz私人配置重新放入RAM后，60秒窗口结束时仍SCANNING，保留`ASSOCIATION_NOT_COMPLETED_WITHIN_60_SECONDS`失败原件。之后自行到COMPLETED/5180。对已有连接做一次有限复测：DHCP得到租约、DNS有答案，但网关ping0/3、HTTP20秒被终止、正文0字节，result为`FINAL_NETWORK_TEST_FAILED`。**当前连接状态不等于网络流量正常**；本轮不能重新宣称5GHz全流程通过。107的5GHz成功记录仍有效，不能用新失败修改它。

2.4GHz本轮没有重测。107的2462MHz认证/DHCP/网关/DNS及577字节内容到达、wget收尾超时仍保留；历史reason7/密钥删除等待另行保留。本轮已经自写并Werror构建被动HTTP TCP80 AF_PACKET捕获工具（仅allowlist、最长60秒、上限8MiB），尚未部署/抓包。下一轮分别定位5GHz新失败与2.4GHz收尾，避免混为密码错误。

## 保存与验收边界

完整boot96MiB和logdump64MiB重新从80个2MiB块收取并逐块校验、重组和比对；一次SCP reset的部分块保留`.partial-first`，终止后只恢复未完成块。完整两分区、NV六项、persist与stockDTBO不变；实际内核源码diff、untracked、initramfs文件、config/DTB/CPIO/Image均与108开始时一致。rootfs01/F2FS候选未刷，原段落保留。

检查点SHA256 `ea665af1240e090ad8e6a1707c68c9a3f8e5dd42b27171d31df01de7e21407e6`，31个直接文件、3个内嵌原包，合计74项SHA验证；其余故障/重启前原包保留在私人kernel108，摘要见[manifest](../reference/kernel108/private-archive-manifest.json)与[核验](../reference/kernel108/checkpoint-validation.json)。原日志、身份、凭据、固件、NV响应、镜像和二进制均只在本机私人目录。早期重启后第一次encoder读取因debugfs未挂载而为空，随后挂载后重新取证，不把空读数当健康状态。

本轮无蓝牙配对/连接、振动脉冲、音频播放/录音或充电探针。107音频/DMIC与历史蓝牙扫描/振动电气结果单独保留，不继承为本轮验收。全15组目标仍active；没有提交、推送或运行文档同步发布脚本。

研究参考：[DSI上游源码](https://kernel.googlesource.com/pub/scm/linux/kernel/git/next/linux-next/+/8e67585674c6cf2330d411eed8031423d4689c2b/drivers/gpu/drm/msm/dsi/dsi_host.c)支持FIFO错误与reset路径的核对；[SM8150 hotdog实测报告](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-17-dsi-dsc-transport-errors.md)记录另一面板的DSC花屏与软复位失败，仅作为仪器/恢复边界参考，不能把它的status5、slice几何或结论移植为本机根因；[旧MDP5讨论](https://lists.openwall.net/linux-kernel/2019/11/11/591)同样只作线索。

继续工作见[NEXT-SESSION](../NEXT-SESSION.md)和[短提示词](../NEXT-SESSION-PROMPT.md)。下一轮kernel109，严禁原样重放108旧bootID/PID/guard目录；DTB改变必须真重建EDK2嵌入DTB。
