# 100：全源就绪等待已部署，首次MPSS启动崩溃仍待修复

2026-10-11。Linux #99 已只刷logdump，保留 [阶段99](99-aw8697-haptics-and-ufs-readiness.md) 的AW8697驱动、配置、DTB、模块和真实EDK2 boot。当前一次有界手动恢复后的5GHz认证/DHCP/网关/DNS/HTTP通过，MPSS running、taint0、蓝牙关闭；**自动无线启动仍未通过**。全硬件goal仍active，按用户要求继续下一硬件，振动机械确认仍等待用户，蓝牙暂不配对连接。

## 就绪修复与实际失败

CPIO内容只有 `usr/sbin/samurai-wifi` 变化：[全部源检查](../reference/kernel99/wifi-all-source-readiness.patch)先等modem和六个NV源，逐个核对标签/大小/同机型号，最多60秒；超时不做部分复制。init、既有文件集合/权限/所有者/链接/设备号、所有模块及历史显示快照保持。配置与DTB逐字节相同；实际EDK2 fd/boot及内嵌DTB核对相同，未用FAT DTB代替固件。

这次真实暖启动记录了14次等待（uptime20.69–33.77秒），随后firmware/NV prepare成功，原NV哈希校验通过。MPSS在dmesg **42.993094秒**报告up，但在**82.980862秒**报告fatal error without message，间隔**39.988秒**。没有WLAN可用状态，Wi-Fi worker退出1；蓝牙驱动注册后因全新MPSS离线身份来源不可用也退出。原自动boot-finished=1、两份原日志和完整失败现场保持，不能用后续恢复覆盖。

这证明全源等待分支执行且准备阶段通过，**不证明MPSS可靠启动已修复**。首次TFTP/RMTFS进程存活并注册服务，但RMTFS未记录modem的文件读取请求。[主线q6v5 fatal处理](https://raw.githubusercontent.com/torvalds/linux/master/drivers/remoteproc/qcom_q6v5.c)在SMEM原因读取失败、零长度或首字节为空时打印同一句日志；本次旧日志不能区分三种情况，不能据此猜TA、NV、时钟或固件根因。下一步应保存原始返回值/长度等有限诊断，再核对本机服务与启动链。

## 一次有界恢复与当前网络

保存失败现场后，停止BT模块、解绑ath10k、停止崩溃的MPSS，保留原RAM COW/固件服务和六份已验证NV副本，再绑定ath10k并启动MPSS一次；不自动循环恢复、不改波特率/保护阈值/原NV。WLAN出现后监测45秒，超过首次约40秒崩溃窗口，独立本机WLAN/BT只读查询成功，身份与上一暖启动一致。蓝牙保持powered/connectable/bondable/discoverable均0。

现有空配置WPA经私人RAM配置reconfigure，手动5GHz认证/DHCP/网关/DNS/HTTP通过，HTTP577字节。最终恢复后的WPA日志无disconnect事件。本阶段没有重测双频4MiB传输、2.4GHz长期稳定、蓝牙扫描/配对连接、公网ICMP或NFC；沿用历史证据时明确其阶段。boot-finished仍1，因为首次自动启动确实失败，自动热点连接也未实现。

AW8697在新暖启动重新识别ID97，GO0/STATE0、active0/starts0/stops0/error0。保留阶段99的三次短脉冲电气/FF、close/SIGKILL/1秒看门狗证据；本阶段没有再次播放，**用户实际振动反馈仍未收到**，不能宣称机械/休眠/冷启动通过。

86文件checkpoint时记录两次显示超时 **321.625858、438.714099秒**、三次BT上电脉冲单00帧错误保持，checkpoint显示underrun0/frame_done_cnt2。振动此次starts0，不能把显示超时归因于振动播放；其它因果关系也未证明。没有新密钥安装-110告警，不代表阶段98的单播删除等待或两次2.4GHz非主动reason7已修复。

## 备份、飞轮与验收边界

新备份包括完整96MiB boot和64MiB logdump。首次大文件SCP在约36MiB后超时，改为2MiB分块又有一次超时；两次不完整文件及日志保留，只停止经当前cmdline核对的自有失败SCP。降低本阶段SCP速率至8192Kbit/s后，80份块逐一SHA校验、重组及全分区SHA通过。手机期间仍在运行，根因未定，USB长期传输稳定性仍待办。

F1 receipt后独立fastboot验证本机身份/产品/logdump大小，只有logdump写入，实际flash/reboot成功。F1 reader在receipt后EIO/设备消失原件保留；COM首次设置在控制设备未枚举时失败，设备出现后正常COM重试成功。两次早期SSH连接失败保存，网卡及地址就绪后固定身份SSH恢复。最后EUD为Windows/Shared而非Attached，reader/隐藏keepalive/fastboot/test/传输均退出，正常MPSS/WPA/RMTFS/TFTP/dropbear保持。

自动启动验收等待在真实失败后有界终止，部分目录保留。首次最终采集因debugfs未挂载退出；挂载后新目录retry1完成，旧部分目录也收进证据。最终86文件清单、各原包绑定、boot/logdump/init/服务/模块读回通过；运行期服务等于新CPIO，无阶段99的RAM服务差异；六个原NV/persist不变。

| 产物/证据 | SHA256 |
|---|---|
| Image #99 | `2391f376fc8b8e9eb8de24002c89a8e7645eb00f2bbb2ad3794e45926a0d20be` |
| DTB保持阶段99 | `31479df0d1cb8b935f69c4ebdd396d25274a400ebde67fbbcf133737a4ba2868` |
| CPIO | `77f1c94e6ca7f43cfffd04ac82180cc88c2221b9db087bdaa3d6505f4c0e854e` |
| 复用boot头部 | `7fa3a6879f8e3409fff129befedc32c6e67785fac18665984f52bf2d0f067c1f` |
| 完整boot备份/读回 | `91b64b25be666ec62778e96bbb2e67b985c84ac1d84f4dca10c0d0911ac068df` |
| 新logdump | `02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea` |
| 完整旧logdump备份 | `c325eb6421b1194c17e309143183e0cf97192a395d7f4e537e829047ae6abea9` |
| 刷前22文件 | `6efa4f32c6400a20f82e26a3e95cb26c14216222e9a0556cda34cf021926d392` |
| 首次MPSS失败现场 | `8de8ed1799d964ef681f7274ac1d905034703f56c02be5f57351a091a707dd33` |
| 一次恢复原包 | `8f82f2badb25f89ca21d40f9ac7e0a240f2f8cdf7487c4246bdc992b66a52eb1` |
| 恢复后网络原包 | `dee52273d8a05d90dcb827785fcc3fe03f603ddef8ff73f74c2b93b870ab806e` |
| 最终86文件checkpoint | `102c6d6dedfb4804d4e0ed5ddff21d5a66156a5a6d4dc3459cb0a4714c7e6c8e` |

最后8文件只读状态在uptime 844.51秒验证同一次boot：MPSS running、5GHz COMPLETED、BT关闭、振动standby、taint0，NV/persist不变，无额外MPSS fatal，但显示新增一次超时；原包SHA `2d475c57399c95e9a624ba6100efb91395daa009a9a61f190383e445d16fb790`，私人final-status-validation.json。

私有目录 `E:/edk2-samurai-out/kernel100`；只公开自有源码/patch/脱敏摘要。内核HEAD/EDK2 HEAD和阶段99相同，已有其它dirty改动保持，未提交/推送。Android/userdata/GPT/NV/persist/SSH身份、旧显示85–88快照和另一线程rootfs01/F2FS段落保持。充电收尾，不运行旧探针或写充电控制。

后续先接收振动机械反馈，按 [15组清单](../linux-port/docs/HARDWARE-STATUS.md)继续下一硬件；保留首次MPSS启动约40秒崩溃、2.4GHz掉线、单播删除等待、UART脉冲、显示超时及USB大传输等独立待办。不要以追加固定延时、无限重启或屏蔽错误代替适配。
