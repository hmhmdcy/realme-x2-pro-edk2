# session96：Wi-Fi MSA回收、蓝牙独立扫描与本机NV地址

2026-10-11。继续完整硬件目标，Wi-Fi优先；蓝牙按用户最新范围仅扫描，不配对/连接，NFC仅验证控制器。

本轮刷入Linux #95。配置、DTB和三个BT模块字节不变；CPIO仅改init/蓝牙服务，内核增量只有ath10k qmi.c/qmi.h。保留既有显示接管/SMMU保护、真实EDK2内嵌DTB和历史快照。仅刷logdump，复用相同boot；完整备份、独立fastboot身份/产品/大小核对、候选审计与读回均通过。

## 发现、修复与对照

阶段95现场先用RAM新服务连续停止/启动BT各两次，5GHz保持连接；关闭Wi-Fi与MPSS后BT又初始化并扫描成功。人为设置的Wi-Fi失败结束标记也允许服务继续，此项只证明dispatch分支，不是实际冷启动失败验证。恢复Wi-Fi时，MPSS running但ath10k报MSA分配-22，wlan0未出现；完整失败现场保留。该阶段还出现BT波特率重试和一次显示frame-done timeout。

源码显示，server-exit路径会回收MSA权限，但驱动主动解绑时QMI deinit没有执行该回收。新补丁记录每个成功授予的区域，在QMI工作停止后于deinit回收；失败/未授予区域不回收，成功回收后清除记录。SCM错误、范围检查、fixed-perm原逻辑保留，没有跳过安全错误。实现基线核对了 [Linux ath10k QMI源码](https://github.com/torvalds/linux/blob/master/drivers/net/wireless/ath/ath10k/qmi.c)。

新启动首次MPSS约41.7秒up，显示DRM/fb0注册。Wi-Fi worker在uptime93.1秒正常结束，BT驱动103.4秒注册，dmesg约108秒QCA setup完成。阶段94–96三次受控暖重启的首次MPSS/显示均成功，仍不能视为断电冷启动或长期可靠性验收。

新蓝牙服务等Wi-Fi尝试的实际结束状态，成功/失败均可继续，240秒仍未结束则拒绝重叠启动；保留最早60秒、最多30秒显示等待与10秒安静窗口。显式start/stop幂等，RAM锁拒绝并发操作；不强制卸载，不自动选择地址、扫描或连接。Wi-Fi首次真实失败、worker被杀/超时等启动分支仍待实机验证。

新内核按相同顺序执行wpa退出、BT关闭/卸载、ath10k解绑、MPSS停止。MPSS offline时BT重新初始化并扫描17个不同地址/类型组合。再卸载BT、绑定ath10k并启动MPSS，恢复wlan0、2.4GHz认证/DHCP及双向流量，没有再出现MSA map/unmap错误。只验证了一次该完整热循环，不宣称所有重启/恢复情形完成。

## 本机地址来源与边界

只读DMS GET_MAC 0x005c请求采用WLAN=0、BT=1，核对了 [libqmi DMS消息定义](https://github.com/linux-mobile-broadband/libqmi/blob/main/data/qmi-service-dms.json)。查询工具动态寻找唯一DMS端点，验证源/事务/消息长度、TLV结果与6字节地址；没有泛用QMI指令、NV写入或调制解调器模式切换。

最初误把libqrtr成功返回0当作发送字节数，修正后保留了失败输出。最初按数组首字节检查WLAN单播位而拒绝了成功响应，后来通过本机安装的cnss-daemon确认：其检查最后字节的低两位，再反转6字节作为WLAN MAC；BT HAL的DMS函数原样复制。修正验证后，两种NV返回地址跨暖启动一致。

vendor和persist仅ro,noload挂载，前后完整哈希相同；persist中隐藏`.bt_nv.bin`不存在。保存的是当前安装的同机Android库，不能因采集脚本名而宣称其为未经修改的OEM系统。未执行OEM库/探针或写原分区。Wi-Fi地址只在netdev RAM中设置，BT只用MGMT SET_PUBLIC_ADDRESS临时设置；当前实际WLAN MAC和READ_INFO地址与验证后的DMS数据一致。MGMT格式核对了 [BlueZ协议](https://github.com/bluez/bluez/blob/master/doc/mgmt-protocol.rst)。

两种地址尚未自动集成到开机服务；Wi-Fi/MPSS首次失败时还没有验证过的离线地址来源。独立扫描用的是本次MPSS启动后保存于RAM的本机地址，不能据此宣称全新冷启动完全不依赖MPSS地址供应。

## 网络、扫描和控制器实测

| 阶段 | 流量与共存 | 不同地址/类型记录 | 显示vsync |
|---|---|---|---|
| 初始2.4GHz | 双向各4MiB，90秒/45样本通过 | 15 | 8214→10876 |
| 热恢复后2.4GHz | 双向各4MiB，90秒/45样本通过 | 16 | 14867→17551 |
| 5GHz 5180MHz | 双向各4MiB，90秒/45样本通过 | 16 | 20643→23321 |

三个阶段均通过认证、DHCP、网关、DNS和HTTP，保持MPSS running、WPA COMPLETED、DRM存在、taint0，显示underrun0。每次双向4MiB的宿主/手机SHA256一致。公网ICMP三个阶段均失败，不能称公网ping通过。地址/类型组合可能对应同一物理设备，不能把这些数字作为唯一设备数。

NFC GET_DEVICE、DEV_UP、再查询powered=1、DEV_DOWN四个响应成功；无标签，RF/读卡/eSE未验收。本轮未发出蓝牙配对/连接指令。旧测试工具曾打开connectable/bondable标志，收尾时将严格扫描工具两者设为0，READ_INFO验证后仍扫描到16个地址/类型组合；显示vsync29025→29334、underrun0，随后SET_POWERED=0确认关闭。旧工具的私人二进制/源码与记录保留，后续使用严格扫描版本。

| 产物 | SHA256 |
|---|---|
| Image #95 | `617ad170734ce6f1eed226f1852ecf92e7f5f4758273530f87d3df5f8faf2b2f` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `1e0960a137b81b8f1c63ea86141af582d82752fef4e6e6526a27189d6af57e01` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722` |
| 完整boot备份 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 完整logdump备份 | `f69091aa4dde55bee83f639ee1442ba567190ca52fa3baf2216f0eae84da4fe5` |
| 阶段95现场/失败记录 | `0f2c2706db7537ced585100416c10fe0fd0061176a1e39b94bcccc7e64bc8d4a` |
| 主checkpoint（141文件） | `21d07c8fa945d522be0cf8f46ab35cd71d7c975466872c22e7ce5af65f51b517` |
| 严格扫描补充（14文件） | `d8200daec6af70ff4d0fbde2d831f525e5f5fd6e1599030936263c7891dc0d39` |

刷前74个文件、主现场141个文件、补充14个文件逐一校验；6个原NV哈希跨启动一致，persist不变，boot/logdump/三个模块/init/蓝牙服务和测试工具读回通过。F1回执后EIO是断开，仍按独立fastboot枚举决定刷写。新启动最初EUD尚未枚举、SSH路由尚未就绪的错误保留；正常com-up后取得15秒247帧EUD片段并释放owner，完整启动日志依据同次启动SSH副本，不把片段当全文。

首次连接脚本在新wpa_supplicant控制socket创建前立即查询，因set-e退出；初次共存因debugfs未挂载退出，流量监听尚未创建因DHCP缺失退出。分别保留原日志，补充debugfs和有界socket等待后继续成功；没有改写失败记录。后续完整测试脚本已包含这两项前提。

当前同次启动MPSS running、5GHz COMPLETED、taint0、显示刷新/underrun0；BT已关闭，驱动和RAM本机地址保留，NFC已DEV_DOWN。EUD Windows/Shared、未Attached，reader/隐藏keepalive均关闭。固件、库、MAC/周边设备身份、PSK、密钥和完整日志仅在私人kernel96目录。

仍有8次BT Frame reassembly -84、1次波特率重试，以及旧peer密钥移除-110和regulatory downgrade；不能屏蔽日志代替修复。冷启动/真实失败路径、地址自动供应、UART重初始化、休眠/长期共存、宽信道/吞吐、配对传输、NFC实物和其它硬件继续待办。只刷boot/logdump，Android/数据/GPT/原NV/persist/SSH身份与显示85–88快照保留；不改其它线程rootfs/F2FS工作，不写充电配置，不跑旧OEM探针。本轮无提交/推送，整体goal仍active。
