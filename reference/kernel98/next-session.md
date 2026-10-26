# 下一阶段：2.4GHz掉线、单播删除等待与UART脉冲（session98）

继续Realme X2 Pro Linux全硬件适配，优先Wi-Fi/蓝牙/NFC。蓝牙只扫描，不配对连接；NFC无标签，先控制器；充电阶段收尾。整体goal仍active。

先读[sessions/98](../../sessions/98-independent-radio-identities-and-key-delete-trace.md)、[reference/kernel98](README.md)及私人E:/edk2-samurai-out/kernel98/checkpoint-validation.json。重新读实际boot ID、uptime、驱动/服务/路由/文件和进程；历史boot ID/PID/哈希/目录不能直接重放。

当前Linux #97，逻辑阶段98，Wi-Fi 5GHz5180MHz COMPLETED、MPSS running、taint0，BT powered/connectable/bondable/discoverable全部0。本次双频认证/DHCP/网关/DNS/HTTP及每方向4MiB SHA通过；公网ICMP失败。两次2.4GHz reason7掉线仍在（341.149171、964.769845秒），第二次BT关闭。45个COMPLETED采样漏过首次瞬态，不是无中断共存通过。首次监听器连接超时记录保留，initial-retry1立即传输通过；不能用后续成功覆盖掉线或推定超时根因。

已完成独立地址查询/缓存：current-wlan/current-bt及各自锁，refresh wlan|bt只查一类型，原子发布、当前boot ID/root0700/0600/非symlink校验。WLAN查询故障exit42时BT真实查询仍成功，原helper恢复 byte-exact；新暖启动在手动调用前WLAN45.57/45.61秒、BT103.29/107.01秒查询/应用完成，跨暖启动身份一致。只读DMS service2/v1/instance0 GET_MAC0x005c，WLAN0/BT1、24字节回复、6字节全局单播和同机字节序保留。地址仅私人RAM；热点仍用私人RAM配置手动启动，未实现自动连接。无缓存且MPSS offline时仍无新身份来源；故障注入不是真实Wi-Fi启动/worker失败或冷启动证明。

已启用CONFIG_ATH10K_TRACING及过滤trace，debug_mask0，没有raw WMI/HTT/key dump。trace overrun0：三个单播DISABLE_KEY耗时3130.843/3120.212/3210.609毫秒均-110且无security indication；八个SET_KEY各收到确认并返回0，0.305–2.542毫秒。有效peer组替换有确认。本轮未改key等待；全启动6条key操作-110，其中三条操作类型由trace直接确定。[ath10k RFC](https://lists.openwall.net/linux-kernel/2026/09/18/12)是参考，其diff还改QCA6174，下一轮不能原样扩大到未测硬件。

三个BT -84错误均power-on pulse阶段/请求115200/chunk1/partial0/first00，不是baud-change阶段；标签不证明物理字节来源。波特率重试0，无TLV timeout。只有诊断变更，没有丢字节、忽略错误、脉冲/RTS/延时/重试修复。BT扫描100秒发现13个地址/类型组合，10次discoverystart，当前关闭；未配对连接。

显示唯一229.278733秒frame-done timeout发生在Wi-Fi认证/扫描之前，trace前后都是1，最终vsync34234/underrun0/frame_done_cnt1。原因独立待查，保持CTL/SMMU保护与历史85–88快照。阶段94–98五次受控暖重启首次MPSS/显示注册成功，不是断电冷启动或运行期无故障。阶段96 MSA权限回收、一次完整Wi-Fi热恢复、MPSS停止时已有RAM身份扫描与NFC四条控制器命令证据保留，本轮未重测这些。

下一优先：

1. 在同机WCN3990/SNOC范围修复已证实的单播删除无确认等待，保留发送错误、SET/组密钥等待和其它硬件行为；新trace对照删除延迟、八类安装确认/重连、双频数据与异常路径。不要把删除等待修复宣称reason7根因已解决。
2. 2.4GHz BT-off独立对照，持续事件日志结合有界空闲/保活流量与逐段计数，定位两次非主动reason7。`iw get power_save`当前on；时间间隔不固定，不猜AP/校准/国家码/省电根因，不以永久关闭省电代替完整适配。显示超时独立保留诊断。
3. UART power pulse RX/RTS/port reopen边界及有界恢复，保证有效H4/命令响应，不盲加延时、屏蔽错误或无限重试；继续仅扫描。
4. 真正首次Wi-Fi失败/worker被杀或超时、无缓存MPSS失败时只读离线身份、断电冷启动、多次Wi-Fi/MPSS热循环、休眠/唤醒与长期双频共存。regulatory downgrade、宽信道/吞吐、公网ICMP仍待办。
5. NFC先控制器；完整[15组硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)保留，包括音频/摄像头/传感器/指纹/振动/GNSS/蜂窝、显示90Hz/亮度、USB外设及充电未完成项。
6. 每轮新现场和完整boot/logdump备份，审计CPIO/模块/配置/真实EDK2内嵌DTB。DTB改变须重建真正EDK2，FAT DTB不能替代固件。停止顺序WPA退出→BT关闭/卸载→ath10k解绑（MPSS仍运行）→MPSS stop；F1确认后独立fastboot核对私人身份/产品/大小再写。

本次CPIO只变无线地址服务和hci_uart.ko，其余集合/模式/所有者/链接及init保持；配置只增ATH10K_TRACING，DTB不变，btbcm/btqca沿用94，vermagic一致。只刷logdump，boot复用。内核HEAD e42788eafb0bb9d8dfce319c71ca54c5207b2295；其它显示/EUD/触摸/电源差异保持，无提交/推送。首次扩大modules构建已中止、特定目标retry1完成；所有失败日志与原现场保留。

| 产物/证据 | SHA256 |
|---|---|
| Image #97 | `2788635e0c892a539717bc7201b78f1505ab9a6ec15e3a34e5192fc3a641e4e6` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `dfa0e0b5d2bb09101c5f73de98a64f983da7edd434b4eabe7ddba62e87d52e2d` |
| hci_uart.ko | `242b576888e14725533c7401e6a7b50702da230f2e83bca25cead85283204d04` |
| 复用boot头部 | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| 新logdump | `0ebd3ec3ab41a70b86f03b09cff2dd0d9e39d0bcdf739b2fdf2c96d0694e0fc2` |
| 完整boot备份/读回 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 完整旧logdump备份 | `935141253c61f2b9bb4ab92103217adaa45800a00894215326e1dac0d955718a` |
| 刷前110文件 | `4a763d4c8f185a7e38581ebfad1b84cf045d9a28af3ad7d17ca560d6b7b8f239` |
| 自动地址21文件 | `46ddecaf532d535a14d1274c702fa3d8c7e4adf7fd9e8a77a75a17d3c13345b2` |
| trace36文件 | `c0e7777e28de5c858bed0b2683d94f1d6a47e5b9660eb097c8d3b876018e1979` |
| 最终121文件checkpoint | `cf4979b98510024e0b4123354ef796ca5f613e869f26e4efa32120c069d01396` |

121文件含嵌套清单逐一SHA校验，自动取证/trace原包绑定及boot/logdump/init/工具/服务/模块读回通过，6个原NV和persist不变。私人checkpoint-validation.json明确两次掉线、一次显示超时、三次BT帧错误及goal_complete=false。

Linux /home/cy122/x2pro-linux/linux；initramfs /home/cy122/x2pro-linux/initramfs；EDK2 /home/cy122/edk2-samurai/repo；私人E:/edk2-samurai-out/kernel98。SSH沿用reference/kernel72/usb-ssh.ps1与私人固定身份；SCP限速reference/kernel98/scp-private.ps1。序列号仅私人fastboot-identity.json。所有构建/测试/扫描/传输已终止，MPSS/WPA/rmtfs/tftp/dropbear是当前正常服务；不要按文件名重启旧任务。EUD Windows/Shared未Attached，reader/USBIPD/隐藏keepalive释放；辅助抓取不代替设备完整日志。

只刷boot/logdump，保留Android、userdata/GPT、原NV/persist、SSH身份和旧显示快照；NV仅RAM COW。公开仅自有代码/patch/脱敏摘要，固件/二进制/镜像/OEM库/原日志/地址/周边身份/凭据/密钥不入Git。vendor仅当前安装同机来源，ro,noload，不称未经修改OEM、不跑旧探针。充电不写配置/解封/NV/OTP/FET/OTG/MCU/GPIO，不用I2C_FORCE；旧显示快照不清空或重武装。另一线程linux-port/README.md的rootfs/F2FS头部与E:/edk2-samurai-out/rootfs01保持。
