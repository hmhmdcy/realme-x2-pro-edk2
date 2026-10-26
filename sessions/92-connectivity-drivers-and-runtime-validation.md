# Wi-Fi、蓝牙扫描与 NFC 控制器实测（2026-10-11，session92）

本轮延续全硬件目标，优先连接功能。用户后来明确要求蓝牙只扫描附近设备，暂不配对/连接；NFC 没有标签，先验证控制器。

## 实机结果

部署 Linux #91 与相应 EDK2 内嵌 DTB，仅刷 boot/logdump。完整原分区及现场已保存私人目录；Android、userdata、GPT、原机 NV 均未写入。

Wi-Fi 自动启动发现了真实时序缺陷：`resolve` 在 UFS 尚未枚举时被条件语句调用，shell 的 `set -e` 不会阻止其最后一个 `printf` 返回成功，导致空分区名被接受。对分区存在、大小、型号、唯一性检查添加显式 `return 1` 后，RAM 修正版成功启动 MPSS/WLFW/ath10k，并完成 45 秒稳定检查。这个修复尚需下一版开机验收。

2.4 GHz WPA2/CCMP、DHCP、网关 ping、DNS、HTTP 均通过。公网 ICMP 未通过，因此不声称公网 ping 可用。Wi-Fi 绑定手机 DHCP 地址和宿主 WLAN 地址，双向各 4 MiB TCP 的双方 SHA256 一致，USB 仅负责启动与取证。5 GHz 扫描已有证据；认证、DHCP及流量仍待完成。

| 本轮成功流量 | SHA256 |
|---|---|
| 手机发送 4 MiB / 宿主接收 | `0fdb13bbcf3b9f84abb6fc3b81c8f0ce2bade8b1c6d89f90d683b4143d2f2084` |
| 宿主发送 4 MiB / 手机接收 | `fe1ae07b02bd439cb10154953665909a7c34a7e724230a373cefcb9e0e504d7d` |

蓝牙 UART13、hci0 和 NFC I2C9、nfc0 已注册。蓝牙实际响应 product `0x0a`、SOC `0x40010224`、ROM `0x1001`、patch `0x6699`。通用算法请求缺失的 revision-01 文件；原机提供 revision-21 文件。先以 ROM 固件完成 31 次发现事件，再对同机 `crbtfw21.tlv` / `crnv21.bin` 进行 RAM 别名诊断，日志确认 QCA UART setup completed。匹配参考来自 [Hotdog 作者实测](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-04-mainline616-bluetooth.md)，原机文件来源及哈希独立验证，未使用他机二进制。主线 `firmware-name` 双字符串绑定允许显式指定 NVM 和 rampatch；下一版采用真实文件名，取消 RAM 别名。

加载 NVM 后控制器需要有效蓝牙地址。persist 分区以 ext4 `ro,noload` 检查，未找到通用 bt_nv/bdaddr 文件，前后全分区哈希一致。本轮用仅保存于 RAM 的随机临时本地地址完成 MGMT 配置、上电和 17 次发现事件；没有配对、连接或远端数据操作。出厂地址接入、配对、传输、音频和休眠仍未验收。发现事件数不是独立设备数；详细地址/邻近设备名称留私人目录。

NFC generic netlink GET_DEVICE / DEV_UP / GET_DEVICE / DEV_DOWN 全部成功，状态由 powered=0 变为 1 后关闭，再重复三次均成功。DEV_UP 包含实际 NCI 初始化命令/响应路径，证明数字控制器通路。未发送固件下载、eSE、标签轮询或数据交换操作；射频、CLKREQ GPIO113 与读卡须后续验证。VEN 使用本机 GPIO36，未复制 Hotdog 的 GPIO41。

本轮最后一次连接快照 uptime=623.84 秒、taint=0、MPSS running；6 个原 NV 分区和 persist 前后校验通过。停止顺序改为 wpa terminate → BT off → ath10k unbind → MPSS stop，在同一启动周期成功结束，未触发重启。解绑期间仍出现 key removal -110，不能称停止流程已完全可靠。

## 私人证据和镜像

私人目录 `E:/edk2-samurai-out/kernel92`；完整日志、地址、密钥、网络配置、固件及可执行程序不发布。

| 产物 | SHA256 |
|---|---|
| #91 Image | `64b8228773263076f36ff817205571ef6f9043c961d35dcbb7cf7b1a2081261b` |
| DTB | `cb33d8059a4d09ed2ff9201be447f64eb2583e7a1b2b89ad8e0d7dd620863ff9` |
| boot-k92-connectivity.img | `35f6fe338f2fb21ec15702e5c532d742dd6dafd90d11d5cbed8ded2348b1885c` |
| logdump-k92-connectivity.img | `7972dae9d5f3c709fd41f8b0e577417e1f6278930afa04762bae70dbb85ace86` |
| 新启动刷前完整日志/备份归档 | `0942072f30879fb9e45e84c0e310e980bfa939f78fa5e8a77fd86f4c21b1c575` |
| 本轮成功连接、蓝牙/NFC现场归档（kernel93/preflash.tar） | `b16c67e7ed39f52a6d26989b02fda54a142becc6a75bb74cd43dd43e0e40d9c3` |

初次流量测试缺少手机发送样本、随后端口复用被拒绝，保留失败输出；最终独立端口和完整样本的两方向校验通过。静态测试工具源码在 reference/kernel92。

旧 MPSS stop-first 预测试曾导致重启，pstore 最后记录止于 modem stopped，无 panic 栈，根因未证明。#91 启动后曾短暂 USB/EUD 断开，之后恢复并完整测试；不将这种恢复当长期启动可靠性证明。显示、充电和其它硬件待办仍保留，目标未完成。
