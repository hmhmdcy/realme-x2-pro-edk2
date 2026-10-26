# 下一会话：显示状态修复与Wi-Fi新启动数据回归

先读[阶段108](../../sessions/108-display-flicker-and-panel-state-handover.md)、[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)及[核验](checkpoint-validation.json)。全硬件goal active，无预算；用户本轮要求保存文档和短提示词，未创建新会话、未构建或刷入面板修复。

手机仍为Linux #106（阶段107镜像）；阶段108只做诊断、一次正常DRM开关屏和一次同镜像暖重启，没有构建新内核或刷分区，实际内核源码/config/DTB/CPIO/boot/logdump保持。
用户确认白底不规律滚动花屏；故障现场持续DSI status=c（FIFO/MDP FIFO下溢）、显示完成超时累计2。单次DRM开关屏虽然ioctl返回0，但用户确认黑屏；日志有DCS关屏/睡眠-110及already prepared/enabled。面板驱动断电后返回传输错误，使DRM core保留状态并跳过重新开启，状态处理缺陷已定位、尚未修复；不能把这次开关屏记为通过。
同镜像重启后用户确认黑底Linux命令行可见；405.44秒检查点DSI错误0、显示超时0、双DSP running、taint0。只证明本次命令行恢复，未复查纯白光学画面，未证明首次接管/长稳或永久修复。
新boot自动radio初始化auto0、三个modem服务公告result0、真实PD/固件/RAM COW请求和trace无丢失通过，无手动MPSS恢复。5GHz关联未在60秒窗口完成，后来COMPLETED/5180；最终DHCP和DNS有结果，但网关0/3、HTTP20秒终止且无正文，当前数据复测失败。107的5GHz全流程成功仍是历史证据；2.4GHz577B内容到达但wget收尾超时也保留，本轮未重测2.4GHz。
下一轮使用kernel109新前缀/新bootID/新完整备份，优先修SOFEF03F超时断电后的状态生命周期，再查DSI下溢及5GHz新启动数据失败；不盲目重复开关屏。蓝牙停止不配对，振动按用户要求只看日志/代码，NFC仅控制器，充电收尾保持；Android/data/GPT/NV/persist/SSH/rootfs01/F2FS与旧显示85–88快照保留，私人凭据/身份/固件/原日志/镜像不公开，不提交推送；全硬件goal active。

当前身份用私人`E:/edk2-samurai-out/kernel108/runtime-boot-id-after-private.txt`核对，实际仍#106（13:48:23 CST构建），不能再用kernel107的旧bootID。检查点405.44秒，SHA `ea665af1240e090ad8e6a1707c68c9a3f8e5dd42b27171d31df01de7e21407e6`，31直接文件/3内嵌包/74项验证；后续只读确认仍COMPLETED/5180。进入下一轮先重新获取当前现场和身份，用kernel109全新前缀，不能重放旧目录。

1. 优先修`drivers/gpu/drm/panel/panel-samsung-sofef03f.c`失败关屏路径：DCS -110后已经physical power-off，但返回错误使`drm_panel_unprepare/disable`保留prepared/enabled，重新开启被跳过。审查disable→unprepare和enable→backlight全链；确保强制关屏、regulator引用平衡、原厂等待/电压/引脚和错误日志保持。源码还没改，勿把计划写成已部署。拿实际函数做错误路径验证，再按新守卫构建刷入，单次有界复测。
2. 原滚动花屏与DSI status=c/FIFO+MDP FIFO下溢同时出现，worker反复reset；DPU underrun0不能排除它。旧启动已保存故障kms/clk/trace/snapshot和用户黑屏观察；当前新boot零错误不算永久修复。保留85–88及108原件，检查首次接管/TE/autorefresh、DSI控制/7nm PHY/DSC，勿盲加MDSS复位、改寄存器或重复开关屏。
3. 当前5GHzCOMPLETED/5180，60秒关联窗口失败，随后DHCP和DNS有结果、网关0/3、HTTP20秒/0字节失败。没有后续成功流量测试，勿称当前Wi-Fi正常。107全流程通过是历史证据。下一步有限捕获wlan0 TCP/ARP/ICMP路径或正确限定测试端点；108 HTTP工具只构建未部署，需新输出/真实程序PID和allowlist。2.4GHz107收到577B但wget结束超时，历史reason7/删除等待独立保留；本轮没有重测2.4。
4. 两轮#106新boot自动MPSS服务/PD/TFTP/RAM COW启动支持QRTR修复，无手动恢复；冷断电/休眠/长期稳定未验收。保留主动endpoint/MHI resume HELLO与NS先回复后公告；不要全量回退544d85d或改NV假治故障。

实际Linux源码`/home/cy122/x2pro-linux/linux`、initramfs`/home/cy122/x2pro-linux/initramfs`、EDK2`/home/cy122/edk2-samurai/repo`。当前Image/DTB/CPIO摘要见私人108/preparation.json及107/kernel-validation.json。显示/radio bootconfig原106不可变路径保持；linux-port/dts旧镜像不覆盖；DTB变更必须重建EDK2内嵌DTB。kernel109构建前保存完整源码/配置/CPIO/初始化目录及boot/logdump备份并核对PARTNAME/容量/身份，授权分区只有boot/logdump。

MPSS通过`/usr/sbin/samurai-modem-remoteproc`按唯一OF/PAS/固件定位，不固定remoteproc编号。SSH用reference/kernel72/usb-ssh.ps1；私有5G/2G配置在108输出目录，密码不写文档/内核/CPIO。HCI为空、辅助模块卸载；用户蓝牙暂不配对连接。振动仅日志/静态分析、不重新提问或发脉冲；NFC仅控制器。音频107真实播放/DMIC历史保留，本轮PCM关闭、功放start0/stop0/failed0。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS、历史85–88与108快照。NV仅RAM COW；充电收尾，不执行旧OEM/配置/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。原日志/凭据/身份/固件/音频/镜像私人，不提交推送或运行sync-docs-to-repo.sh。USBipd保持Running，EUD最终detached；hrdevmon警告保留，不forcebind。继续15组硬件，验收需区分源码、构建、部署、数字数据与实物可见结果。
