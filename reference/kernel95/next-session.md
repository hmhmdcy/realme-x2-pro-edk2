# 下一阶段：连接生命周期、身份与启动可靠性（session95）

继续完整Realme X2 Pro Linux全硬件目标，优先Wi-Fi、蓝牙和NFC。用户最新范围：蓝牙只扫描附近设备，暂不配对/连接；NFC无标签，先验证控制器。充电阶段收尾；其余硬件待办和历史显示快照保留。

先读sessions/94–95、reference/kernel94–95和私人kernel95/checkpoint-validation.json。重新确认现场，不能重放旧boot ID、PID、哈希或输出前缀。

当前部署Linux #94，逻辑阶段95。BT_HCIUART及其依赖BT_BCM/BT_QCA为模块，其它配置/显示代码未变。Wi-Fi第一次MPSS启动、wlan0与服务稳定45秒后ready，蓝牙服务再加载3个模块；没有自动凭据/永久地址/扫描/连接。

阶段94–95两次受控暖重启首次MPSS和显示成功，#94自动BT加载通过、没有TLV tx timeout。DRM/fb0当前存在，两个频段共存vsync增长、underrun0。不能把暖重启和90秒观测当断电冷启动或长期可靠性；不能绕过CTL reset/SMMU切换保护。

2.4GHz、5GHz（5180MHz）WPA2/CCMP、DHCP、网关、DNS、HTTP和双向各4MiB TCP通过，两个频段各90秒/45样本保持MPSS running、WPA COMPLETED、DRM存在、taint0。公网ICMP仍失败。蓝牙联合BR/LE扫描分别11/12个地址/类型记录，未配对/连接；临时本地管理测试地址仅在RAM。NFC GET_DEVICE、DEV_UP/NCI初始化、powered=1、DEV_DOWN通过；RF/tag/eSE未验收。

下一优先：

1. 完善BT独立生命周期和失败分支。目前180秒等待Wi-Fi ready，没有ready就退出；这是隔离试验，不能让独立蓝牙功能永久依赖Wi-Fi成功。保留Wi-Fi优先与显示接管边界，先证据/有界验证后改，不盲加无限MPSS重试。
2. 调查本机Wi-Fi出厂MAC和BT出厂地址的只读来源。当前Wi-Fi随机地址和BT RAM测试地址明确区分，不能猜测、复制其它机型或写原NV；persist此前ro,noload没有常规bt_nv文件。Android/加密userdata保持，不自行改rootfs分区。
3. 冷/暖启动、独立启停、休眠与长期共存回归；定位旧peer key remove -110、regulatory downgrade和QCA Frame reassembly -84，不隐藏告警或无证据改国家码/校准。宽信道/吞吐需真实验收。
4. 用户BT继续只扫描，配对连接待用户恢复范围；NFC无标签继续控制器范围。音频、摄像头、传感器、指纹、振动、GNSS、蜂窝、显示90Hz/亮度、USB外设及充电未完成项保留。
5. 每次刷机前新现场/完整boot-logdump备份、配置/CPIO/模块/固件审计。DTB不变时可复用已验证boot，只替换FAT Image；DTB变化需重建真实EDK2嵌入。受控停止：wpa退出→BT off→ath10k解绑（MPSS仍运行）→MPSS stop，再F1确认与独立fastboot枚举。

阶段94自动加载首次失败是`/sbin/insmod`路径错误，实际`/bin/insmod -> busybox`，RAM修正已验后阶段95固化。MGMT READ_INFO对未配置控制器返回Invalid Index为预期；SET_PUBLIC_ADDRESS成功后仍须等正常索引/Index Added，不能立即SET_POWERED。阶段95测试脚本已有明确等待，初次拒绝和路径失败日志保留。

| 当前产物 | SHA256 |
|---|---|
| Image #94 | `3d944fd99ca419dfc986c37f546d81118fea2ba5b6f27a7eb49b14ddb85c6499` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `47502022313c4b5a613a03e52640633a6cd742136a9a216e1f674999ed981315` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `f69091aa4dde55bee83f639ee1442ba567190ca52fa3baf2216f0eae84da4fe5` |
| 完整boot备份 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 完整logdump备份 | `7ea0b8a9706f8c3f60e9e982a2cf71f20ee4372b5d32ea30275c092a572bfc29` |
| 最终checkpoint-final.tar | `4764f18f5ce50552957d73474814617a2d4004d36f0f3599b241e1c4ca5c9afa` |

最终65个私人文件逐一校验，boot/logdump/3模块/加载器读回通过，6个原NV跨启动哈希相同、persist不变，taint0。通过是证据验证，goal_complete=false。当前boot ID/地址/PID仅按私人现场重新获取。

归档后蓝牙SET_POWERED=0成功，扫描结束，驱动仍加载、RAM临时地址仍在；5GHz和MPSS running继续保持，显示vsync增长/underrun0。NFC已DEV_DOWN。EUD Windows/Shared未Attached，所有本轮reader/USBIPD owner释放。序列号由私人fastboot-identity.json读取，不把真实身份硬编码进新增公开脚本。

Linux `/home/cy122/x2pro-linux/linux`；initramfs `/home/cy122/x2pro-linux/initramfs`；EDK2 `/home/cy122/edk2-samurai/repo`；私人 `E:/edk2-samurai-out/kernel94`、kernel95。kernel95模块字节沿用kernel94，uname构建号改变不改变vermagic；CPIO审计证明模块字节未变，实机taint0。公开仅自有源码/patch/脱敏摘要，固件/镜像/二进制/完整日志/设备身份/凭据和SSH身份不入Git。本轮无提交/推送。

只刷boot/logdump；原Android、userdata、GPT、原NV、persist和密钥保持。另一个线程rootfs/F2FS头部和`E:/edk2-samurai-out/rootfs01`不改。充电不写配置/解封/NVM/OTP/FET/OTG/GPIO/MCU、不跑旧OEM探针、不用I2C_FORCE。历史85–88显示快照不清空/重武装。
