# 阶段98：独立无线地址供应与密钥删除时序定位

2026-10-11已部署Linux #97，完整备份、候选包装、部署读回和121文件私人checkpoint校验通过。本轮完成按无线设备独立地址查询/缓存；增加ath10k过滤trace和BT UART错误阶段诊断。密钥等待和UART解析/脉冲时序未修复。Wi-Fi双频网络与每方向4MiB通过，但两次2.4GHz非主动reason7掉线仍在，第二次蓝牙已关闭；不能把45个COMPLETED采样或取证脚本退出0写成无中断共存通过。当前恢复5GHz连接，BT电源/接入/配对/可发现标志全部关闭，未配对/连接。整体goal仍active。

`samurai-radio-address`改为`current-wlan`与`current-bt`，各自query目录、请求锁和原子指针。`refresh wlan|bt`只查指定类型；失败留存私人目录且不发布指针，不调用另一类型查询。按当前boot ID核对root0700目录/0600文件、拒绝符号链接。既有缓存可在MPSS停止后复用；无缓存时仍要求MPSS running，没有新离线身份来源。只读DMS service2/v1/instance0 GET_MAC0x005c，WLAN0/BT1，回复24字节和6字节全局单播验证及同机字节序规则保留，不写原NV/persist，不输出身份。WLAN仅关闭接口时改地址；BT保持关闭并核对MGMT 280字节READ_INFO。

刷前RAM故障隔离：临时包装真实DMS helper，使WLAN查询exit42、不发布缓存，再让BT真实独立查询成功；之后恢复原helper字节，WLAN查询成功且活动连接地址不变。52文件私人包和校验保留。这是查询故障注入，不是首次真实Wi-Fi/MPSS启动失败验证，也不是冷启动离线来源测试。

刷后手动调用前已保存自动启动日志、实际netdev/MGMT地址与独立RAM缓存：WLAN查询45.57秒、应用45.61秒；Wi-Fi实际完成状态0，BT在92.73秒读到结束记录，103.08秒注册、103.29秒独立查询、107.01秒地址就绪。两种地址与刷前同机DMS一致。热点认证使用随后加入的私人RAM配置；自动本机地址供应不等于自动热点连接。启动等待、幂等启停与锁保留；真实worker中止/超时分支未新增验收。

构建只把CONFIG_ATH10K_TRACING由n改为y，ath10k debug_mask仍0。hci_qca新增错误阶段/请求波特率/块大小/半帧长度/首字节诊断，保持原错误返回、解析、RTS、脉冲、延时和重试。CPIO集合/模式/所有者/链接不变，仅无线地址服务和hci_uart.ko字节改变；btbcm/btqca沿用94，vermagic一致，实机taint0。init、其它服务/工具、DTB相同。实际DTB来自EDK2内嵌，复用boot，仅刷logdump。内核HEAD仍e42788eafb0bb9d8dfce319c71ca54c5207b2295，其它显示/EUD/触摸/电源差异保持；不重置、不提交/推送。

刷前Linux #96受控BT关闭断开基线已复现key操作-110，19文件包校验通过。新#97在独立trace实例中只启用mac80211 key/返回、ath10k的sec ind及install-key文本、DPU超时事件；不启用原始WMI/HTT/密钥dump，不提高printk日志量。trace overrun0。三次单播DISABLE_KEY（cmd1、flags0x9、idx0）耗时3130.843/3120.212/3210.609毫秒，均-110，返回前HTT security indication为0。八次SET_KEY返回0且各有一次确认，耗时0.305–2.542毫秒；有效peer上的组密钥替换有确认，不能把peer已删除后的无发送清理混为等待。证据定位到单播删除等待，不能说安装/所有key操作均失败，也不能说删除等待导致最初掉线。

相关[2026-09-18 ath10k RFC](https://lists.openwall.net/linux-kernel/2026/09/18/12)报告WCN3990的cipher-none单播删除无确认、组删除为随机替换且有确认，与本机trace吻合。其说明与diff对QCA6174范围存在差别：diff还启用了QCA6174 profile，不能原样扩大到未测硬件。本轮未应用RFC；下一轮拟仅针对本机已测WCN3990/SNOC保留发送错误和SET/组密钥等待，验证删除延迟及重连。该方向不会自动解决reason7。

100秒BT扫描窗口实际10次discoverystart，13个地址/类型组合，不作物理设备数；45个两秒采样均COMPLETED，但事件日志记录一次reason7（341.149171秒）且自动重连，采样漏过瞬态掉线。之后关闭BT，再做受控断开/重连和5GHz切换；整次启动后续2.4GHz又在964.769845秒reason7掉线，此时BT仍关闭。两个关联至掉线间隔约73.49与155.41秒，不能据此认定固定空闲定时器。当前`iw get power_save`为on，但未证明省电/AP/发包路径根因，不直接把关闭省电当最终修复。整次启动6条key操作-110，trace直接识别其中三次单播删除；后续仍需有界BT-off对照和持续事件/流量记录。

5GHz、2.4GHz分别WPA认证、DHCP、网关三包、DNS和577字节HTTP成功，公网ICMP两次失败。各频段每方向4MiB TCP主机/手机SHA一致。首次2.4GHz监听器仅READY，稍后主机连接超时并确认进程已结束；服务有60秒poll和90秒alarm，且该段也有真实掉线，不能仅凭连接超时归因驱动。失败原件保留，改用启动监听器后立即传输的新前缀initial-retry1通过，最后回5GHz。

本次三个BT Frame reassembly -84全部phase2（power-on pulse）、请求115200、chunk1、partial0、first00；两次自动初始化，一次重新上电。波特率重试0、无TLV tx timeout。诊断不证明首字节来源；当前phase标签覆盖对应程序阶段，并非示波器测得物理脉冲。[历史WCN3990 UART讨论](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/1910.2/04059.html)指出延时可能丢弃接收数据；本机错误不在baud-change阶段，不盲加50毫秒或屏蔽错误。下一步核对power pulse RX/RTS/port reopen边界，保持有效H4/命令响应和有界错误恢复。蓝牙只扫描，配对连接等待用户恢复测试。

显示启动取证时frame_done_cnt0；229.278733秒出现一次frame-done timeout，早于trace开始和首次Wi-Fi认证/扫描。trace前已有1、后仍1，最终vsync34234、underrun0、frame_done_cnt1。不能归因本次扫描/掉线，也不能以持续刷新宣称显示恢复问题已解决。保留旧85–88快照和CTL/SMMU保护。阶段94–98五次受控暖重启首次MPSS/DRM注册成功；不是断电冷启动或运行期零故障证明。

NFC本轮未重测，保留阶段96四条控制器命令通过；没有标签，RF/读卡/eSE未验收。完整15组清单保留，充电阶段收尾，不重跑旧探针，不写配置/解封/NV/OTP/FET/OTG/MCU/GPIO，不使用I2C_FORCE。另一线程rootfs/F2FS头部和私人rootfs01不改。

失败记录保留：首次make modules扩大到非目标模块后按实际PID中止，特定三个BT目标新日志构建通过；扫描工具生成断言和缺失工具的早期运行在创建测试目录/操作硬件前失败；traffic初次编译缺GNU声明后修正；显示计数校验正则未考虑紧连mode字段后按数值读取修正。原错误日志、首次SSH/NCM未就绪、首个2.4GHz传输超时与两次掉线不覆盖。证据校验通过不代表全功能通过，checkpoint中goal_complete=false。

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

121文件逐一SHA校验包含嵌套清单，自动取证和trace子树与各原包字节一致；boot/logdump/init/服务/工具/三个模块部署读回通过。六个原NV跨启动哈希一致，persist整分区不变。身份、周边地址、凭据、固件/二进制/镜像、原日志和SSH身份仅私人E:/edk2-samurai-out/kernel98，公开仅自有源码/patch/脱敏摘要。EUD辅助15秒4646帧不等于完整无损日志，以同次启动设备保存副本和SHA为准；reader/USBIPD/隐藏keepalive结束释放。继续见[下一阶段](../NEXT-SESSION.md)、[工具说明](../reference/kernel98/README.md)和[15组硬件](../linux-port/docs/HARDWARE-STATUS.md)。
