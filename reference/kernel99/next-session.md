# 阶段99交接：振动机械确认与无线启动就绪

按用户更新后的goal继续下一硬件，当前接入AW8697；不继续以Wi-Fi稳定性为唯一优先。蓝牙暂不配对连接，NFC无标签先控制器，充电收尾。全硬件goal仍active。

先读 [session99](../../sessions/99-aw8697-haptics-and-ufs-readiness.md)、本目录README及私人 `E:/edk2-samurai-out/kernel99/checkpoint-validation.json`。Linux #98、逻辑阶段99，标准FF与电气状态、close/SIGKILL/1秒看门狗停振通过，六次开始/结束、watchdog1/error0。三次20%/150ms短振动已经执行，用户是否感到振动的提问仍待答；不把电气状态等同机械通过。

Wi-Fi首次自动启动在NV LUN尚未枚举时退出1，MPSS offline；37.347674秒退出早于37.729198秒sdf分区表。完整失败现场、原失败目录/空日志保留。RAM有界等待全部源恢复后5GHz认证/DHCP/网关/DNS/HTTP通过，蓝牙注册/独立查询成功且关闭。实际RAM samurai-wifi与闪存CPIO有意不同，等待修复尚未刷入；阶段100已构建候选 #99，不能在其审计/部署前宣称自动启动修复。

DTB QUP7/89c000/0x5a、reset116/IRQ24；本机19781 profile170Hz普通上限52/过驱动125按强度缩放。驱动只有本机兼容串、先ID97、工作队列、保护状态轮询、有界停振、无NV/OTP/波形固件写入。actual WSL DTS与真实EDK2已更新；linux-port旧DTS镜像落后但保持原件，不能直接用来构建。driver初次API编译失败、debugfs缺失导致首次采集未播放、联网脚本首次在已有WPA检查前退出，原件均保留。

两个显示超时146.422852/775.627053秒、两个BT上电脉冲单00帧错误保留；最早311日志行滚出最终环，初始完整日志在first-boot-failure.tar。阶段98两次2.4GHz非主动reason7、单播删除约3.1秒等待、独立显示/UART问题仍待办。暖启动、RAM恢复和地址故障隔离不能当断电冷启动、全新离线身份或长期稳定通过。

141文件checkpoint逐一清单/嵌套原包/boot头部及全分区/logdump/init/模块读回通过；6个NV及persist不变。私人完整日志/镜像/固件/二进制/身份/凭据/密钥不发布。阶段99 boot头部SHA `7fa3a6879f8e3409fff129befedc32c6e67785fac18665984f52bf2d0f067c1f`，实际Linux build是#98。logdump SHA `c325eb6421b1194c17e309143183e0cf97192a395d7f4e537e829047ae6abea9`；checkpoint SHA `8518599702fa99be94e63f2689eb295d13516db965cd71dda1fddd83d95d72f2`。

继续先检查实际boot ID/uptime/进程/目录/驱动和文件哈希；不得重放旧PID、starts=0测试或已有前缀。SSH沿用reference/kernel72/usb-ssh.ps1固定私人身份。下一次只刷logdump需全分区新备份和独立fastboot核对；停止WPA→BT关闭/卸载→ath10k解绑（MPSS仍运行）→MPSS stop。保留Android/userdata/GPT/NV/persist/旧显示85–88快照及rootfs01；充电不写配置/解封/NV/OTP/FET/OTG/MCU/GPIO，不用I2C_FORCE。振动GPIO116复位不属于充电控制。
