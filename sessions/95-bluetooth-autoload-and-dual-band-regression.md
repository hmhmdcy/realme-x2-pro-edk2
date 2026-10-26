# session95：蓝牙自动加载、双频 Wi-Fi 与显示回归

2026-10-11。延续全硬件目标；蓝牙只扫描，NFC只控制器。session94的UART模块化对照恢复了显示和首次MPSS启动，但加载器路径错误，需要用修正版重新启动验收。

Linux #94的CPIO只将`samurai-bluetooth`三处`/sbin/insmod`改为`/bin/insmod`，逐项确认原镜像BusyBox符号链接。配置、设备树、三个模块与其它CPIO文件内容/模式/链接不变；保留既有显示SMMU切换保护。未增加凭据、地址或其它固件。

重新保存本轮现场、6个NV/persist校验和两个完整分区。原EDK2 boot镜像与DTB相同，只更换FAT Image并刷logdump。首次刷写脚本因候选文件名仍是k94在写入前拒绝；修正名称后使用新输出前缀重新检查设备/产品/大小/守卫，并成功刷写、reboot。F1收到确认后读取EIO是USB断开，最终依据独立fastboot枚举。只读EUD启动日志中途EIO也保留，后续SSH确认Linux #94、同一启动和完整日志；不把不完整串口片段当完整启动证据。

| 产物 | SHA256 |
|---|---|
| Image #94 | `3d944fd99ca419dfc986c37f546d81118fea2ba5b6f27a7eb49b14ddb85c6499` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `47502022313c4b5a613a03e52640633a6cd742136a9a216e1f674999ed981315` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `f69091aa4dde55bee83f639ee1442ba567190ca52fa3baf2216f0eae84da4fe5` |
| 刷前完整boot | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 刷前完整logdump | `7ea0b8a9706f8c3f60e9e982a2cf71f20ee4372b5d32ea30275c092a572bfc29` |
| 刷前现场/阶段94结果 | `4e9488151d7edd289ef2176e947882b2d5f91577da277f34f1ee7a0f325d7f5e` |

## 新启动与功能结果

显示约37.5秒CTL清理成功、38.4秒DRM/fb0注册。首次MPSS约42.4秒up，44秒QMI，约49秒wlan0；服务稳定45秒后产生WIFI_READY。本轮没有首次40秒fatal，也没有手动MPSS重试。

蓝牙服务在Wi-Fi ready后自动加载：服务uptime约94.8秒，注册hci0约95.1秒；dmesg约100.1秒原机revision-21固件setup completed，无TLV tx timeout。二者使用不同日志时间基准，不能把差值当加载精确耗时。未配置控制器按MGMT列表等待，RAM临时地址确认后再等Index Added/正常列表，随后配置并扫描，全部有真实响应。出厂地址接入尚未完成。

NFC GET_DEVICE、DEV_UP、powered=1、DEV_DOWN均成功，不涉及RF、标签、eSE或升级。2.4GHz WPA2/CCMP、DHCP和双向各4MiB TCP校验一致，扫描共存观测90秒/45样本保持MPSS running、WPA COMPLETED、DRM存在、taint0。5GHz通过显式reassociate进入5180MHz，并通过DHCP、网关、DNS、HTTP和双向各4MiB TCP。公网ICMP仍失败，不能称公网ping通过。

| 流量 | 手机发送 / 宿主接收 SHA256 | 宿主发送 / 手机接收 SHA256 |
|---|---|---|
| 2.4GHz各4MiB | `e00de09fe698bb336c47d708c65525e1a5da5e4c1cf0f58f2735b4bf84a53417` | `dd59bfc0b9077af524e5b7cd09ef4292aa2471d4c13f85e4013798063a3836e0` |
| 5GHz各4MiB | `1f3c3029aae2a1a0bbdf30eef492b1296fcd0599f8f12dadaf08b596dfed2eba` | `cd7945a864e2bd568315fd63c369ee465a96cbfa4f65915d1bdff187d9b897ee` |

阶段94–95两次受控暖重启的首次MPSS、显示均成功，且阶段95自动BT模块加载通过；这支持继续完善启动顺序，但不能把两次暖重启当断电冷启动或长期可靠性验收。Wi-Fi ready绑定BT加载仍是对照试验，失败分支与独立生命周期需设计。

两个频段各完成90秒/45样本扫描共存，分别发现11、12个不同地址/类型组合；不是唯一物理设备数。显示vsync分别3353→6028、6956→9648，underrun0。最终现场归档`checkpoint-final.tar` SHA256 `4764f18f5ce50552957d73474814617a2d4004d36f0f3599b241e1c4ca5c9afa`，65个文件逐一校验。6个原NV与前一启动原哈希一致，persist不变；当前完整boot、logdump、三个模块和加载器读回匹配候选，taint0。证据校验通过，goal_complete=false。

归档后结束扫描测试，SET_POWERED=0返回成功；同一启动MPSS仍running、5GHz COMPLETED，显示vsync继续增长且underrun0。NFC此前DEV_DOWN关闭。蓝牙驱动和RAM测试地址保留，控制器当前关闭；没有配对连接。EUD已释放给Windows/Shared，未Attached。新增刷写脚本从私人`fastboot-identity.json`读取已验证序列号，公开源码不保留真实序列号；原执行日志和失败输出不改。

旧peer密钥移除-110、regulatory downgrade、启动时Frame reassembly -84、Wi-Fi出厂MAC和BT出厂地址仍待定位。不能以屏蔽日志、跳过reset错误、修改国家码/校准或写原NV来验收。宽信道/吞吐、休眠、长期共存、蓝牙配对传输、NFC实物及其它硬件继续待办。

自有脚本在reference/kernel95，完整日志、镜像、固件/二进制、地址和PSK只在私人`E:/edk2-samurai-out/kernel95`。原Android、userdata、GPT、NV、persist、SSH身份与历史显示85–88快照保留；另一个线程的rootfs/F2FS工作不变。
