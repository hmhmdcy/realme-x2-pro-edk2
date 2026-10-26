> 后续用户已暂缓振动机械确认；当前已部署#100音频DSP基础候选，见 [阶段101交接](../kernel101/next-session.md)。以下为阶段100当时的记录。

# 下一阶段：振动机械确认、下一硬件及首次MPSS崩溃（session100）

继续用户更新后的goal：Realme X2 Pro下一硬件Linux适配，用完整内核日志/互联网来源/调试飞轮持续修复、刷入和测试。当前AW8697已接入，机械确认未完成。蓝牙暂不配对连接，NFC无标签先控制器，充电阶段收尾；全硬件goal仍active。

先读 [session100](../../sessions/100-all-source-readiness-and-first-mpss-crash.md)、[session99](../../sessions/99-aw8697-haptics-and-ufs-readiness.md)、本目录README及私人 `E:/edk2-samurai-out/kernel100/checkpoint-validation.json`。重新读实际boot ID/uptime/目录/进程/驱动/路由/文件哈希；历史PID、boot ID、脚本starts=0或已有前缀不能重放。

当前Linux #99，逻辑阶段100，只刷logdump；MPSS running、5GHz5180 COMPLETED、taint0、蓝牙powered/connectable/bondable/discoverable全0。**首次自动无线启动失败，当前网络经一次有界手动恢复。** prepare前全源就绪修复已经刷入，14次等待后firmware/NV准备成功；首次MPSS在42.993094秒up、82.980862秒fatal without message，相隔39.988秒，原Wi-Fi/BT日志和boot-finished=1保留。不能宣称自动启动或自动热点连接已通过。

一次停止BT→解绑ath10k→停止崩溃MPSS→绑定ath10k→启动MPSS恢复成功；复用已验证RAM COW/固件服务，不动原NV。WLAN出现后45秒监测、独立WLAN/BT只读DMS地址与上一次暖启动一致，手动5GHz认证/DHCP/网关/DNS/HTTP577字节通过，恢复后的WPA日志无disconnect。阶段98双频/每方向4MiB证据保留，本阶段未重测这些。2.4GHz两次非主动reason7（第二次BT关闭）、单播删除約3.1秒无确认等待尚未修复；没有新key告警不是修复证明。

AW8697本机19781：QUP7/89c000、0x5a、reset116/IRQ24，ID97；170Hz、普通驱动上限52/过驱动125按强度缩放。标准FF_RUMBLE/异步I2C/保护状态轮询/1秒看门狗/关闭停振已部署。阶段99三次20%150ms电气状态、close/SIGKILL/1.02秒看门狗通过，六次开始/停止、error0；本次新暖启动重新probe/standby且starts0，没有再次播放。**用户“是否感到三次短振动”的提问仍待答。** 如果需要重试，新目录和当前boot ID/计数护栏；若无感觉，先核对本机马达/Shipping API/profile，不能盲加幅度或以GO/STATE当机械验收。

实际WSL DTS已更新并真正重建EDK2（阶段99）；linux-port/dts旧镜像落后，保持原件，不能拿它构建。当前DTB/boot/驱动/配置/所有模块保持99；CPIO仅samurai-wifi变化，实际RAM服务与新CPIO相同。DMS身份只有私人RAM，原QUERY类型/长度/全局单播/同机字节序验证保持；无缓存MPSS offline时仍无全新身份源。

本次累计三次显示超时321.625858/438.714099/443.047118秒；86文件checkpoint时underrun0/frame_done_cnt2，最后8文件又记录第三次；三次BT错误均power-on pulse/115200/chunk1/partial0/first00。首轮MPSS无原因字符串；主线同一句日志包含SMEM读取错误/零长度/首字节空三条路径，下一次先加有限诊断区分，不能直接猜TA或增加固定延时/无限恢复。阶段94–98五次首次MPSS暖启动成功不能覆盖99源就绪失败及100首次MPSS崩溃；断电冷启动、长期运行、休眠仍未验收。

接下来：

1. 收集振动机械反馈/必要的新短脉冲测试，保留低强度、有界停振；随后按 [15组硬件](../../linux-port/docs/HARDWARE-STATUS.md)继续下一项，可先只读核对音频ADSP或SLPI本机资源/固件链，勿混入未核对的其它设备配置。
2. 维护无线可用基线并定位首次MPSS约40秒fatal：只保存有限SMEM返回值/长度、服务注册/QRTR/启动握手与同机时序，先保留失败再恢复；当前只有一次手动恢复成功，不是自动修复。
3. 独立待办：2.4GHz BT-off空闲/流量对照、WCN3990/SNOC狭窄单播删除等待、UART上电脉冲、显示超时、USB大传输、冷启动/休眠。2026-09-18ath10k RFC的diff还涉及QCA6174，不能直接扩大到未测硬件。
4. 每轮完整当前boot/logdump备份与候选审计；本轮两次SCP超时保留，80个2MiB块降低至8192Kbit/s后逐块/整体SHA通过。只停止已核对当前cmdline的自有SCP；不杀另一线程任务。飞轮F1 receipt后仍独立fastboot核对本机身份/产品/大小，DTB改变必须重建真正EDK2。

最后8文件只读状态在uptime 844.51秒验证同一次boot：MPSS running、5GHz COMPLETED、BT关闭、振动standby、taint0，NV/persist不变，无额外MPSS fatal，但显示新增一次超时；原包SHA `2d475c57399c95e9a624ba6100efb91395daa009a9a61f190383e445d16fb790`，私人final-status-validation.json。

阶段100 Image SHA `2391f376fc8b8e9eb8de24002c89a8e7645eb00f2bbb2ad3794e45926a0d20be`；DTB SHA `31479df0d1cb8b935f69c4ebdd396d25274a400ebde67fbbcf133737a4ba2868`；CPIO SHA `77f1c94e6ca7f43cfffd04ac82180cc88c2221b9db087bdaa3d6505f4c0e854e`；logdump SHA `02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea`。boot复用阶段99，完整boot SHA `91b64b25be666ec62778e96bbb2e67b985c84ac1d84f4dca10c0d0911ac068df`。最终86文件checkpoint `102c6d6dedfb4804d4e0ed5ddff21d5a66156a5a6d4dc3459cb0a4714c7e6c8e`，清单/原包/部署读回/6NV与persist不变验证通过，goal_complete=false。

Linux `/home/cy122/x2pro-linux/linux`，initramfs `/home/cy122/x2pro-linux/initramfs`，EDK2 `/home/cy122/edk2-samurai/repo`，私人 `E:/edk2-samurai-out/kernel100`。HEAD仍e42788eafb0bb9d8dfce319c71ca54c5207b2295/f23a9f8aa619388412c8aad5834a460e51eae9eb，无提交/推送。SSH reference/kernel72/usb-ssh.ps1及私人固定身份；SCP本目录限速版本。当前EUD Windows/Shared，reader/隐藏keepalive/fastboot/构建/采集/传输退出，正常服务继续运行。

只刷boot/logdump，保留Android、userdata/GPT、原NV/persist、SSH身份、历史显示85–88快照与另一线程rootfs01/F2FS段落。NV仅RAM COW；固件/镜像/二进制/OEM库/原日志/身份/凭据/密钥不公开。不跑旧充电探针，不写充电配置/解封/NV/OTP/FET/OTG/MCU/GPIO，不用I2C_FORCE；振动reset116与充电控制无关。
