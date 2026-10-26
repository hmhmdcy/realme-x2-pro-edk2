# 下一阶段：首次共存掉线、地址依赖拆分与UART/显示恢复（session97）

继续完整Realme X2 Pro Linux全硬件目标，优先Wi-Fi、蓝牙和NFC。用户蓝牙只扫描，暂不配对/连接；NFC无标签，先控制器。充电阶段收尾，15组硬件待办和历史显示快照保留，整体goal仍active。

先读[sessions/97](../../sessions/97-automatic-radio-addresses-and-boot-regression.md)、[reference/kernel97](README.md)，以及私人`E:/edk2-samurai-out/kernel97/checkpoint-validation.json`。重新获取boot ID、uptime、驱动/服务、路由及输出目录，不能重放旧boot ID、PID、哈希守卫或前缀；历史脚本均有现场和构建限制。

当前Linux #96，逻辑阶段97。本轮内核驱动源码/配置/DTB/三个BT模块不变，阶段96 ath10k MSA权限回收补丁保留。CPIO仅改Wi-Fi和BT服务，增加无线地址服务/两个静态工具；init、其它文件、模式和符号链接保留。复用boot，只刷logdump，完整备份/候选审计/部署读回通过。实际DTB来自EDK2内嵌，FAT DTB不能替代固件部署。

已完成本机WLAN/BT自动开机地址供应：本次暖启动47.53秒DMS查询、47.56秒WLAN地址验证，105.04秒BT注册、109.11秒BT地址就绪。原始日志/实际netdev/MGMT READ_INFO/RAM缓存在手动调用前保存，跨暖启动地址一致。热点认证使用随后加入的私人RAM配置；未实现/宣称自动连接热点。

只读DMS service2/v1/instance0 GET_MAC0x005c，类型WLAN0/BT1，验证唯一端点、来源/事务/长度/TLV/result/error与6字节全局单播。WLAN反转已验证本机LE数组，仅接口关闭时设置；BT通过MGMT在关闭时设置public address、动态重新查询索引并核对280字节READ_INFO（包含3字节ClassOfDevice），不自动power on，不reset冲突状态。libqrtr send返回0表示成功。地址与原始回复仅root0700目录/0600文件RAM存放，原NV/persist不写，不打印身份。

**仍有地址依赖**：当前`samurai-radio-address refresh`先查WLAN再查BT，两者成功才发布共同缓存；BT路径在空缓存时也走此流程。需拆成按无线设备独立查询/缓存，验证WLAN失败而BT查询成功、锁/部分失败与幂等行为。尚无全新冷启动MPSS失败时的离线BT身份来源，不能猜地址、复制其它设备或发布到CPIO。阶段96的MPSS停止时BT扫描用此前缓存，仅证明缓存复用。

Wi-Fi服务原子写本次实际结束状态；BT boot等待成功/失败结束记录，240秒无记录就拒绝重叠。保留最早60秒/最多30秒显示等待/10秒安静窗口、独立幂等start/stop/status和RAM锁。阶段95人为失败标记只验证dispatch，真实首次Wi-Fi失败、worker被杀/超时和断电冷启动分支仍未实测。

当前Wi-Fi 5GHz5180MHz WPA COMPLETED，MPSS running、taint0，BT已关闭、接入/配对/可发现标志0。2.4GHz重连后和5GHz认证/DHCP、网关、DNS、HTTP及每方向4MiB TCP校验通过；公网ICMP两个阶段均失败。BT关闭90秒/45样本对照、2.4/5GHz各90秒/45样本扫描共存通过，扫描13/16个地址/类型组合，不作物理设备数量。NFC本轮未重测，保留阶段96四条控制器命令通过的证据，RF/标签/eSE未验收。

**首次共存失败未解决**：初次2.4GHz只有两个成功样本，WPA reason7（CLASS3_FRAME_FROM_NONASSOC_STA）掉线后自动重连，随后key操作-110。通用ath10k告警覆盖SET/DISABLE，不能凭该告警认定密钥安装根因。首次完整日志和失败阶段保持原样，后续通过不覆盖。当前WLAN MAC更新在实际mac80211/ath10k代码中会同步vif/bss_conf地址，未发现明显软件更新遗漏；不凭猜测改校准、国家码或固件。

**显示同期失败**：326.298、330.456、370.872秒三次frame-done timeout，首次两次邻近Wi-Fi掉线，尚无因果证据。之后BT关闭/双频扫描窗口没有新增超时，vsync17799→20488、23233→25896、27887→30585，underrun0；最终frame_done_cnt3。保留CTL/SMMU保护、旧85–88快照，不以持续刷新宣称超时已修复。

本次BT Frame reassembly -84共4次（108.099、110.106、255.729、817.395秒），波特率重试0、无TLV tx timeout。发生在初始化/重新上电附近，继续定位H4边界/波特率事件，不屏蔽错误或无限重试。#95此前8次帧错误/1次波特率重试证据保留；本轮刷前RAM模块重启又增加2次，不与新启动计数混合。阶段94–97四次受控暖重启首次MPSS/显示注册成功，仅证明这些暖启动，不能当断电冷启动或运行期无显示故障。

下一优先：

1. 保存当前失败日志后，围绕首次reason7掉线、key SET/DISABLE操作和三次显示超时增加有界诊断，复现实验用新前缀。先拆按无线设备独立地址查询/缓存，再测真实Wi-Fi失败/worker异常分支；不掩盖两项故障或盲加无限MPSS重试。
2. 定位BT UART初始化/重新上电的4次Frame reassembly -84，继续仅扫描、connectable/bondable/discoverable关闭。配对/连接待用户恢复测试。
3. 断电冷启动、真实MPSS失败时只读离线身份来源、多次独立Wi-Fi/MPSS热循环、休眠/唤醒和长期共存。阶段96 MSA回收热恢复通过，当前没有新热循环验收。旧key操作-110/regulatory downgrade、宽信道/吞吐和公网ICMP仍待办。
4. NFC只控制器；音频/摄像头/传感器/指纹/振动/GNSS/蜂窝、显示90Hz/亮度、USB外设及充电未完成项保留，见[15组硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
5. 每轮刷前新现场和完整boot/logdump备份，审计CPIO/配置/模块/固件及真实嵌入DTB。DTB不变可复用boot，只替换FAT Image；DTB改变须重建真实EDK2。停止顺序：WPA退出→BT off/卸载→ath10k解绑（MPSS仍运行）→MPSS stop；F1确认后独立fastboot枚举核对私人身份/产品/大小后才写。

| 当前产物/证据 | SHA256 |
|---|---|
| Image #96 | `3869fb26eb3597f9487b023ab05839ede1b317028ae8378180ee9fe22c604ab7` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `14a80922bc6870d117706440df2cf32c9e2beb24725093020a108aba82a0ab3e` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| 新logdump | `935141253c61f2b9bb4ab92103217adaa45800a00894215326e1dac0d955718a` |
| 完整boot备份/读回 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 完整旧logdump备份 | `226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722` |
| 刷前RAM重试25文件 | `9e8afc738b467de9dcaf9e61de1f38b1e6c0ed5c8b31f8ff091e830df62e8bd2` |
| 刷前60文件 | `8ac1a8d13e21b319647574a847d87046513e2cb08491ff28e58be21b025369cf` |
| 最终131文件checkpoint | `b009f782efd2fe1035918190c9f457cf31fd7e62219daf4d8fd7dfe22187df82` |

131文件逐一校验包含嵌套清单，boot/logdump/init/服务/工具/模块读回通过，6个原NV跨启动哈希一致、persist整分区不变。私人`checkpoint-validation.json`包含首次共存失败和显示超时、`goal_complete=false`，不以证据校验通过代替全功能通过。

刷前第一次64MiB SCP在末尾16KiB终止，手机仍可SSH/Wi-Fi；保留部分文件，设备前缀/尾部校验后补齐，整分区SHA一致。第一次根清单排除嵌套清单错误，保留旧tar后用新目录修正。初次RAM READ_INFO长度误判、初次共存掉线、首次网络前提失败和5GHz切换/DHCP脚本尚未完成就检查的调度错误均有私人原记录。后者待完成后新前缀通过。

EUD当前Windows/Shared未Attached，本轮reader/USBIPD owner/隐藏keepalive释放。15秒4623帧辅助观察不等于无损完整日志；以同次启动SSH设备保存副本和SHA为准。F1确认后的断开EIO与首次SSH/NCM未就绪记录保留。序列号来自私人`fastboot-identity.json`，大分区限速`reference/kernel97/scp-private.ps1`，SSH身份沿用kernel72。

Linux `/home/cy122/x2pro-linux/linux`，HEAD `e42788eafb0bb9d8dfce319c71ca54c5207b2295`；initramfs `/home/cy122/x2pro-linux/initramfs`；EDK2 `/home/cy122/edk2-samurai/repo`；私人`E:/edk2-samurai-out/kernel94`至kernel97。内核全树已有其它显示/EUD/触摸/电源差异，本轮构建前后差异一致，不重置或顺手改其它补丁。三个BT模块沿用94，实机taint0。本轮无提交/推送。

仅boot/logdump可刷，原Android、userdata/GPT、原NV/persist、密钥和历史显示85–88快照保持。公开仅自有代码/patch/脱敏摘要；固件/镜像/二进制/OEM库/原日志/地址/周边身份/凭据及SSH身份不入Git。vendor是当前安装的同机分区，不能称未经修改OEM；只ro,noload，旧探针不跑。另一线程rootfs/F2FS头部与`E:/edk2-samurai-out/rootfs01`不改。充电不写配置/解封/NVM/OTP/FET/OTG/GPIO/MCU，不用I2C_FORCE；旧显示故障快照不清空/重武装。
