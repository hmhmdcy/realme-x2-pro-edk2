# 阶段97：自动本机地址供应与双频回归（2026-10-11）

手机已部署Linux #96，逻辑阶段97。Wi-Fi和蓝牙在本次暖启动中自动读取、验证并应用本机DMS地址；双频认证、DHCP、网关、DNS、HTTP和双向各4MiB TCP校验通过。首次2.4GHz扫描共存出现一次非主动掉线并自动重连，同时有三次显示帧完成超时，原因未解决；后续两个90秒扫描共存窗口通过，不能覆盖首次失败。蓝牙仅扫描，没有配对或连接，最终电源和接入/配对标志均关闭。完整全硬件goal仍active。

## 实现和部署边界

[自有源码与审计脚本](../reference/kernel97/README.md)只改启动服务并增加两个静态工具。内核驱动源码、配置、DTB和三个BT模块与阶段96一致；阶段96的ath10k MSA权限回收补丁保留。CPIO仅修改`samurai-wifi`、`samurai-bluetooth`，增加`samurai-radio-address`、`samurai-dms-mac-read`、`samurai-bt-address`；init、其它文件、模式和符号链接保持。重新构建产生#96 Image。复用已验证boot，只刷logdump中的Image，FAT DTB字节保持；实际DTB仍由EDK2内嵌提供。

`samurai-radio-address`使用只读DMS service2/v1/instance0的GET_MAC 0x005c，WLAN类型0、BT类型1。查询工具校验唯一端点、来源、事务、消息/TLV长度、result/error和6字节全局单播地址，输出只写root的0600 RAM文件，目录0700，不打印身份。WLAN按本机已验证的同机cnss-daemon语义反转LE数组，在netdev关闭时设置；已匹配则幂等返回，不改活动接口。原NV始终只有RAM COW，原分区不写。

蓝牙工具通过MGMT设置public address，要求控制器关闭且缺少的配置选项仅为public address。它等待初始化、动态重查正常索引，核对完整READ_INFO地址和状态；READ_INFO包含3字节ClassOfDevice，载荷280字节。地址已正确时只验证；冲突或不安全状态拒绝，不强制reset。关闭connectable/discoverable/bondable；不含扫描、配对、连接或原始HCI写入功能。启动服务仍等Wi-Fi本次实际尝试结束、显示注册和安静窗口，独立幂等启停及并发锁保留。

当前缓存一次查询WLAN和BT，两者成功才发布共同`current`。这在本机成功路径已验证，但结构上仍使BT查询依赖WLAN查询成功。下一步必须拆成按无线设备独立查询/缓存，再测试真实Wi-Fi首次失败分支。MPSS首次失败时没有已验证的全新离线身份来源；阶段96的MPSS停止后扫描使用的是此前RAM缓存，不能替代该验收。

## 实机结果和未解决失败

刷前先在#95 RAM中测试幂等地址应用、BT停止/重开、扫描与最终关闭，保留第一次READ_INFO长度误判的失败工具/日志后修正，再用新前缀通过。此次#96启动在uptime47.53秒完成DMS查询、47.56秒验证WLAN地址；BT驱动105.04秒注册、109.11秒完成地址验证。原始开机日志、RAM缓存、实际netdev地址和MGMT READ_INFO均在手动调用服务前保存并核对。跨暖启动地址一致。热点凭据之后才从私人RAM配置加入；本轮证明自动本机地址供应，不证明自动连接热点。

| 本轮测试 | 结果 |
|---|---|
| 初次2.4GHz扫描共存 | 仅两个成功样本后掉线，WPA reason7，随后自动重连；此阶段失败 |
| BT关闭对照 | 90秒/45样本保持WPA COMPLETED、MPSS running、taint0 |
| 重连后2.4GHz | 认证/DHCP、网关/DNS/HTTP及双向各4MiB通过；90秒/45样本扫描共存通过，13个地址/类型组合 |
| 5GHz 5180MHz | 认证/DHCP、网关/DNS/HTTP及双向各4MiB通过；90秒/45样本扫描共存通过，16个地址/类型组合 |
| 公网ICMP | 两个完成的网络验证均失败；不能以HTTP通过覆盖 |
| 蓝牙 | 开机自动地址、幂等调用、严格扫描和最终关闭通过；未配对/连接 |
| NFC | 本轮未重测；保留阶段96控制器初始化/开关证据，无标签/RF/eSE验收 |

扫描计数是地址/类型组合，不能作为不同物理设备数量。TCP下载/上传每方向4194304字节，设备和主机文件SHA256一致；它证明数据通路，不代表最大吞吐。最初网络检查失败保留：2.4GHz处于首次掉线后阶段；5GHz第一次检查在切换/DHCP脚本尚未完成时启动，属于测试调度失误，待脚本完成后用独立前缀通过。

首次WPA reason7对应CLASS3_FRAME_FROM_NONASSOC_STA。随后ath10k报告key操作-110；源码通用告警同时覆盖SET和DISABLE，不能仅凭时间顺序断言密钥安装是掉线根因。没有按猜测修改固件、校准、国家码、MAC逻辑或驱动发送通路。

显示在uptime326.298、330.456、370.872秒发生三次frame-done timeout，前两次邻近首次掉线；因果未证明。后续BT关闭和两个扫描共存窗口均无新增超时，vsync分别17799→20488、23233→25896、27887→30585，underrun0；不能因此撤回早期故障。保留原显示保护及85–88故障快照。当前启动有4次BT Frame reassembly -84，分布于初始化/重新上电，波特率重试0、无TLV tx timeout；UART错误仍未修复。阶段94–97四次受控暖重启首次MPSS/显示注册成功，断电冷启动、休眠和长期可靠性未验收。

## 备份、校验和失败记录

刷前完整96MiB boot和64MiB logdump备份。logdump第一次SCP在最后16KiB终止；手机SSH和Wi-Fi仍可用，不能称为手机崩溃。保留原部分文件，读取设备前缀/尾部哈希并补齐16KiB，重组文件与原整分区SHA一致。第一次根SHA清单误排除了嵌套清单，包装审计拒绝；保留旧tar，重新生成只排除根清单的完整清单后逐文件通过。F1回执后断开、首次SSH未就绪记录保留；独立fastboot身份/产品/分区大小核对后只写logdump。EUD15秒辅助片段4623帧，reader/USBIPD owner最后释放；完整日志以设备SSH快照和哈希为准。

刷前60个私人文件、最终131个私人文件均逐一验证；部署读回核对boot头、完整boot/logdump、init、三个服务、两个地址工具和三个BT模块。6个原NV跨启动哈希一致，persist整分区不变。最终taint0、MPSS running、DRM/fb0、5GHz WPA COMPLETED，BT关闭。校验结果在私人`E:/edk2-samurai-out/kernel97/checkpoint-validation.json`，`goal_complete=false`。

| 产物 | SHA256 |
|---|---|
| Image #96 | `3869fb26eb3597f9487b023ab05839ede1b317028ae8378180ee9fe22c604ab7` |
| CPIO | `14a80922bc6870d117706440df2cf32c9e2beb24725093020a108aba82a0ab3e` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| 复用boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| 新logdump | `935141253c61f2b9bb4ab92103217adaa45800a00894215326e1dac0d955718a` |
| 完整boot备份/读回 | `a89b44d65f6615fd7d820b7631a495becf15a28bfa0a33f1b240772c66f5bef7` |
| 旧logdump备份 | `226c4da4c28953c394e9677af069e48c3cad0f036f922ea47712b762761c8722` |
| 最终checkpoint | `b009f782efd2fe1035918190c9f457cf31fd7e62219daf4d8fd7dfe22187df82` |

MGMT布局/地址语义核对[BlueZ官方协议](https://github.com/bluez/bluez/blob/master/doc/mgmt-protocol.rst)，DMS字段核对[libqmi官方定义](https://github.com/linux-mobile-broadband/libqmi/blob/main/data/qmi-service-dms.json)，MAC更新和QCA UART行为核对实际内核源码。公开仅自有源码和脱敏说明；私人固件、镜像、日志、凭据、地址/周边身份及密钥不入Git。本轮无提交/推送，不改另一线程rootfs/F2FS；充电阶段保持收尾。下一步见[交接](../NEXT-SESSION.md)和[15组硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
