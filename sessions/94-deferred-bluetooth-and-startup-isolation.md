# session94：延后蓝牙 UART，恢复显示与首次 MPSS 启动

2026-10-11。继续全硬件目标，蓝牙按用户要求只扫描附近设备，不配对或连接；NFC仍只验证控制器。

Linux #92启动时蓝牙两次TLV超时、显示CTL reset -22和首次MPSS 40秒fatal。为隔离启动时序，将HCI UART及其两个依赖从内建改为模块，Wi-Fi服务首次启动并稳定45秒、写入ready后再加载。显示源码、设备树、固件和NV处理不改。这是一次受控对照，尚不能证明三个故障的完整因果关系。

构建Linux #93，配置仅BT_HCIUART、BT_BCM、BT_QCA由y改m；CPIO仅修改init并新增加载服务、三个模块和目录。现有文件内容、模式、身份、符号链接保留。模块同内核构建，依赖btbcm/btqca；不放入Wi-Fi凭据或永久蓝牙地址。

设备树与session93逐字节相同，复用已部署EDK2 boot镜像。保存当前两个完整分区、日志和6个NV校验，经独立fastboot枚举只刷logdump。初次备份SCP最后一份缺32KiB，原文件保留；限速重新传输后哈希通过，未用不完整备份刷机。

| 产物 | SHA256 |
|---|---|
| Image #93 | `2239079ef501fa6b5ba0f173355865ac9f72632c6d19f8e77667fa17b5a1ce04` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `aebee608ed54d41acc5884fe00e318e7539954ad13d04c5cfa40610e337e4ab1` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `7ea0b8a9706f8c3f60e9e982a2cf71f20ee4372b5d32ea30275c092a572bfc29` |
| 刷前完整boot | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 刷前完整logdump | `7905d198f229f44cfd279d14f044bf659b050be0baa02a3d1a5d67c135f9c4ee` |
| 刷前日志归档 | `8fd2578bc6244a37c79777bc65c752f522575d50416539089beb1a4b801cce9e` |

## 实机结果与脚本修正

显示约37.7秒CTL清理成功，约38.4秒DRM/fb0注册。首次MPSS约42.3秒up，约43.9秒收到WLFW/QMI信息；未发生40秒fatal，Wi-Fi服务产生WIFI_READY。2.4GHz WPA2/CCMP、DHCP通过。

自动蓝牙服务约94.8秒收到Wi-Fi ready，但使用不存在的`/sbin/insmod`，退出127；实际BusyBox链接在`/bin/insmod`。失败原日志保存。先用session95修正版在RAM加载同样三个模块，约125.9秒注册hci0、约130.6秒完成原机revision-21固件初始化，没有TLV tx timeout。这证明本轮正常显示与首次Wi-Fi启动发生在蓝牙模块尚未加载时；自动加载修正必须重新启动验收，不能把RAM修正当已部署。

诊断脚本还遇到两个MGMT时序边界：未配置控制器的READ_INFO返回Invalid Index是预期；SET_PUBLIC_ADDRESS成功确认后，控制器重初始化/Index Added尚未完成，立即SET_POWERED也会被拒绝。保留初次拒绝日志，后续明确等待未配置列表与正常索引列表后操作。临时地址只在RAM，不接入或改写原NV。依据[BlueZ MGMT协议](https://raw.githubusercontent.com/bluez/bluez/master/doc/mgmt-protocol.rst)的控制器配置/Index Added流程；修正后的测试等待逻辑保存在自有源码。

NFC GET_DEVICE、DEV_UP、powered=1、DEV_DOWN通过。BR/LE联合扫描自然结束，共发现11个不同地址/类型组合，未配对或连接。90秒/45样本MPSS running、WPA COMPLETED、DRM存在、taint0；显示vsync从6130增至8830、underrun0。扫描期间Wi-Fi双向各4MiB TCP，手机与宿主分别绑定WLAN地址，双方哈希相同。

| 2.4GHz共存流量 | SHA256 |
|---|---|
| 手机发送 / 宿主接收 | `5cc82a5dbaad21fba1ff8c9066c074d04a157b86cec0ca2a5328ea0789466289` |
| 宿主发送 / 手机接收 | `a3307919b843877c99dc3ab3a7e0de21b09947e300cfdd02ca51bfc0193b9a9e` |

6个原NV和persist哈希不变。完整现场由session95刷前归档保存，SHA256 `4e9488151d7edd289ef2176e947882b2d5f91577da277f34f1ee7a0f325d7f5e`，44个文件逐一验证。`reference/kernel94/verify-runtime-checkpoint.py`明确标记自动加载失败、RAM修正已测试、修正自动启动尚未验证、goal_complete=false。

下一步用session95只改加载器路径的镜像验证自动加载与两个Wi-Fi频段。当前ready依赖是隔离试验：Wi-Fi启动失败时BT不会自动加载，独立启停、失败路径、出厂地址和冷/暖启动可靠性仍需完善。保留全部显示、充电和其它硬件待办。

私人目录为`E:/edk2-samurai-out/kernel94`及kernel95/preflash.tar。专有固件、完整日志、附近设备身份、PSK和可执行程序不发布。原Android、userdata、GPT、NV及历史85–88显示快照保留。
