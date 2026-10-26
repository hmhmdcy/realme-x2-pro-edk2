# 下一阶段：地址供应、真实启动失败路径与UART恢复（session96）

继续完整Realme X2 Pro Linux全硬件目标，优先Wi-Fi、蓝牙和NFC。用户最新范围：蓝牙只扫描附近设备，暂不配对/连接；NFC无标签，先验证控制器。充电阶段收尾；其余硬件待办和历史显示快照保留。整体goal仍active，不因本轮通过而标记全硬件完成。

先读[sessions/96](../../sessions/96-wifi-msa-lifecycle-and-provisioned-addresses.md)、[reference/kernel96](README.md)，以及私人`E:/edk2-samurai-out/kernel96/checkpoint-validation-with-scan-policy.json`；必要时回看阶段94–95。重新获取boot ID、uptime、驱动/服务状态、路由和输出目录，不能重放旧boot ID、PID、哈希守卫或输出前缀。目录中的历史实验脚本有旧现场限制，不可盲跑。

当前部署Linux #95，逻辑阶段96。内核相对阶段95仅修改ath10k qmi.c/qmi.h，CPIO仅修改init和`samurai-bluetooth`；配置、DTB、三个BT模块字节与boot不变。只刷logdump，完整备份、候选审计和部署读回通过。实际DTB来自EDK2内嵌，FAT里的DTB不能替代固件DTB部署。

Wi-Fi worker将实际退出状态原子写入`/run/samurai-wifi/boot-finished`；蓝牙`boot`等此次尝试结束，成功/失败均可继续。240秒没有结束记录就拒绝重叠启动；保留最早60秒、最多30秒显示等待和10秒安静窗口。`start/stop/status`支持独立幂等操作、RAM锁拒绝并发，无强制卸载。服务只注册驱动，不自动设置地址、扫描或连接。阶段95人为失败标记只验证dispatch，真实冷启动Wi-Fi失败、worker被杀/超时等分支尚未验证。

阶段95主动解绑ath10k后，MSA权限未回收导致重新映射SCM -22、MPSS running但没有wlan0。阶段96补丁按区域记录实际成功授予的权限，在QMI handle和工作停止后随deinit回收，保留SCM错误、范围和fixed-perm原语义。一次相同完整热循环已恢复wlan0、认证、DHCP及双向流量，无MSA map/unmap错误；不能视为所有启停/恢复情形完成。

阶段94–96三次受控暖重启首次MPSS和显示成功，#95自动BT加载无TLV tx timeout。DRM/fb0存在，三个90秒共存窗口vsync增长、underrun0；固定后本次启动没有frame-done timeout。阶段95离线生命周期实验有一次frame-done timeout，失败现场保留。断电冷启动、休眠和长期可靠性仍未验收，保留CTL reset/SMMU切换保护，不隐藏错误。

当前Wi-Fi 5GHz（5180MHz）WPA COMPLETED，MPSS running、taint0。初始2.4GHz、热恢复后的2.4GHz、5GHz均通过认证、DHCP、网关、DNS、HTTP和双向各4MiB TCP，各90秒/45样本BT扫描共存通过；公网ICMP仍失败。三个扫描阶段分别15/16/16个地址/类型组合，可能属于相同物理设备，不作唯一设备计数。

蓝牙在MPSS停止时重新初始化并扫描17个地址/类型组合，使用此前MPSS启动后保存于RAM的本机地址。最终严格工具关闭connectable/bondable，READ_INFO核对后仍扫描16个组合，随后SET_POWERED=0成功；没有发出配对/连接指令。旧工具曾开放接入/配对标志，私人旧源码、二进制与日志保留。后续使用`bt-mgmt-probe-scan-only`，不恢复旧标志。当前BT关闭、驱动和RAM地址保留，NFC已DEV_DOWN；NFC GET/up/NCI初始化/powered=1/down通过，RF/tag/eSE未验收。

本机WLAN/BT地址来源为只读DMS service2/v1/instance0、GET_MAC 0x005c，设备类型WLAN=0、BT=1。工具核对唯一端点、源/事务/消息长度、TLV/result/error、6字节全局单播地址，只写0600 RAM文件，不向stdout打印身份。成功的libqrtr发送返回0，不能按字节数检查。当前安装的同机cnss-daemon检查数组最后字节低两位并反转WLAN地址，BT HAL的DMS函数复制原数组；MGMT使用LE数组。不能按首字节检查这份LE回复，也不能盲套其它机型。查询数据跨暖启动一致，实际netdev/READ_INFO地址已核对。

vendor/persist仅ro,noload读取，前后完整哈希相同，persist隐藏`.bt_nv.bin`不存在。所读vendor是当前安装的同机Android分区，不能仅凭采集脚本名宣称其为未经修改的OEM镜像；未执行OEM库/探针。原NV仅RAM COW、原分区不写。地址当前只在RAM手动应用，尚未接入自动开机流程；全新冷启动MPSS失败时尚无经过验证的离线地址供应。

下一优先：

1. 将经过验证的本机只读DMS地址供应接入开机流程，严格校验回复和字节序、保留私人权限与启动隔离边界。研究首次MPSS失败时的只读离线BT身份来源；不能猜地址、复制其它设备、写原NV/persist或放入公开CPIO。
2. 实测Wi-Fi首次失败后BT启动、worker异常/超时、断电冷启动和后续暖启动，明确独立地址来源是否成立；人工失败标记不能代替真实场景，不能盲加无限MPSS重试。
3. 定位8次BT Frame reassembly -84与1次波特率切换重试，继续有界UART重初始化测试；BT保持仅扫描、connectable/bondable关闭。不要用忽略错误或无限重试宣称修复。
4. 新变化后验证多次Wi-Fi/MPSS独立热循环、休眠/唤醒和长期扫描共存；旧peer key remove -110、regulatory downgrade、宽信道/吞吐保留待办，不无证据改国家码或校准。
5. NFC无标签继续控制器范围。音频、摄像头、传感器、指纹、振动、GNSS、蜂窝、显示90Hz/亮度、USB外设及充电未完成项保留，见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
6. 刷机前新现场、完整boot/logdump备份、配置/CPIO/模块/固件审计。DTB不变时可复用已验证boot，只替换FAT Image；DTB变化必须重建真实EDK2嵌入。受控停止：wpa退出→BT off/卸载→ath10k解绑（MPSS仍运行）→MPSS stop；再F1确认与独立fastboot枚举，核对私人身份/产品/分区大小后才写。

| 当前产物/证据 | SHA256 |
|---|---|
| Image #95 | `617ad170734ce6f1eed226f1852ecf92e7f5f4758273530f87d3df5f8faf2b2f` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `1e0960a137b81b8f1c63ea86141af582d82752fef4e6e6526a27189d6af57e01` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722` |
| 完整boot备份 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 完整旧logdump备份（阶段95） | `f69091aa4dde55bee83f639ee1442ba567190ca52fa3baf2216f0eae84da4fe5` |
| 刷前74文件现场/失败记录 | `0f2c2706db7537ced585100416c10fe0fd0061176a1e39b94bcccc7e64bc8d4a` |
| 主checkpoint（141文件） | `21d07c8fa945d522be0cf8f46ab35cd71d7c975466872c22e7ce5af65f51b517` |
| 严格扫描补充（14文件） | `d8200daec6af70ff4d0fbde2d831f525e5f5fd6e1599030936263c7891dc0d39` |

刷前74个、主现场141个和补充14个私人文件逐一校验，部署读回通过，6个原NV跨启动哈希相同、persist不变。当前验证报告`checkpoint-validation-with-scan-policy.json`的`goal_complete=false`；主报告`checkpoint-validation.json`仍保留。初次DMS返回值/地址顺序/执行权限失败、控制socket/debugfs前提失败、初次EUD枚举/SSH路由未就绪均有原记录，不覆盖失败输出。

EUD当前Windows/Shared未Attached，所有本轮reader/USBIPD owner/隐藏keepalive释放。15秒247帧EUD片段仅辅助观察，完整日志来自同次启动SSH设备副本并校验。F1回执后的断开EIO不等于失败，但必须等待独立fastboot枚举。序列号从私人`fastboot-identity.json`读取，不硬编码进新公开脚本；大分区备份用限速`reference/kernel96/scp-private.ps1`，保留原SSH身份。

Linux `/home/cy122/x2pro-linux/linux`（基线`e42788eafb0bb9d8dfce319c71ca54c5207b2295`）；initramfs `/home/cy122/x2pro-linux/initramfs`；EDK2 `/home/cy122/edk2-samurai/repo`；私人 `E:/edk2-samurai-out/kernel94`、kernel95、kernel96。三个BT模块沿用kernel94字节，uname构建号改变不改变vermagic，实机taint0。作用域内qmi差异检查通过；全树有既存EUD尾部空格，不顺手改其它补丁。本轮无提交/推送。

只刷boot/logdump，原Android、userdata、GPT、原NV、persist、密钥与历史显示85–88快照保持。公开仅自有代码/patch/脱敏摘要，固件/镜像/二进制/OEM库/完整日志/地址/周边身份/凭据和SSH身份不入Git。另一线程rootfs/F2FS头部和`E:/edk2-samurai-out/rootfs01`不改。充电不写配置/解封/NVM/OTP/FET/OTG/GPIO/MCU，不跑旧OEM探针、不用I2C_FORCE；旧显示故障快照不清空/重武装。
