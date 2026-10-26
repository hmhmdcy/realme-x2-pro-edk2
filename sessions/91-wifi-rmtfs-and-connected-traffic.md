# Session91：Wi-Fi 服务链路、WPA2 与真实双向流量

2026-10-11，Asia/Shanghai。包含 session89–91 尚未交接的部署与验证。

实机 Wi-Fi 的 2.4GHz 已可用：授权热点完成 WPA2-PSK/CCMP 四次握手，DHCP、网关、DNS、公网 HTTP 和双向各 4MiB TCP 数据通过。两端 SHA256 一致，TCP 连接明确绑定两端 Wi-Fi 地址；USB NCM 只用于控制和取日志。公网 ICMP 未回应。5GHz 能扫描，早期曾关联并接收握手 M1，但更正凭据后的测试停在认证超时，尚未验收。

## 已部署与修复

手机实际内核 `7.3.0-rc6-rmx1931-samurai+ #90`，boot ID `dfe8e722-f6b7-4ce8-85cc-17dfba80f69d`。实际 Linux DT 来自 EDK2 内嵌 DTB。仅刷写已授权的 boot/logdump；Android、数据、GPT 与其余分区保留。原 initramfs 字节不变。

MPSS 最初在启动约40秒后崩溃，日志显示 RMTFS 服务缺失。Realme 原厂使用动态2MiB共享区，不能照抄 MTP 固定地址。增量 DTS 为2MiB区加两端4KiB保护页，限定在普通 DRAM 内分配；`CONFIG_QCOM_RMTFS_MEM` 从模块改为内建。实机分配外区 `0xefdfe000`、驱动可用区 `0xefdff000`，client1/VMID15 与尺寸通过校验。

RMTFS 增量只接受六个固定的原厂 NV 普通文件快照，源分区只读；固件写入保存在 RAM COW 中。地址、长度、句柄、调用节点及路径检查通过本地和 AArch64 实机测试。共享内存仅使用内核 RMTFS 字符设备，不使用 `/dev/mem`、UIO 或远程启动自动化。

TFTP 固件反复 WRQ `/readwrite/server_check.txt`，完全拒写导致重试阻塞 WLAN 加载。只给这个固定名字提供最大4096字节 memfd 探针，其它 WRQ 拒绝，路径翻译仍拒绝逃逸/符号链接。处理实际协商的7680字节块、窗口10和未知传输长度后，本机 `wlanmdsp.mbn` 成功加载，WLFW 服务出现。WLFW 是 **0x45（十进制69）**，不是十进制45。

实际 chip ID `0x30224`、board ID `0xff`。Realme 原厂 CNSS 在 board ff 时选择 `bdwlan.bin`，因此使用本机同一文件作为 `board.bin`，26328字节、XOR16=`0xffff`，未改变校准内容。官方 linux-firmware API5 文件只有60字节元数据，不包含替代固件代码。运行的是本机 `WLAN.HL.3.0.c8-00232-QCAHLSWMTPLZ-1.355769.1.365081.1`；api5、HTT3.70、TLV WMI/HTT。

## 启动与扫描边界

首次成功运行超过1120秒，三次扫描分别24、16、24个BSS，含2.4GHz/5GHz。另两次新服务进程、MPSS停启、ath10k解绑/重绑，分别完成扫描23、22个BSS，并超过原来的40秒故障窗口。QRTR独立 trace 实例保留，未清空显示故障实例。第一轮 trace 无丢失/覆盖，服务14/4096在MPSS HELLO前公布，随后收到WLFW69。

更早的手动重启仍有偶发40秒崩溃及服务未进入的情况，不能据两次通过宣称启动竞态已解决。当前固件/服务仍临时部署在RAM；尚未证明重启后自动可用。接下来应把已验证的受限启动顺序接入 initramfs，再做重新启动验证。

## 认证与流量

首次提供的凭据有误；两频段的失败日志到 M1/M2，用户随后更正密码。独立 PTK/MIC 检查验证了此前19个M2与当时给定PMK一致，这不能证明密码匹配AP。15秒 HTT诊断出现3个NOACK，当时不能据此判断DMA或TX格式缺陷。更正后2.4GHz正常握手和双向流量已证明基本发送通路可用，没有据此前错误凭据日志修改驱动。

配置重载后 network ID 从0变为1，应查询实际ID。静态 wpa_supplicant 2.12 使用 OpenSSL 3.5.9；官方OpenSSL签名/校验及已知PBKDF2向量通过，nl80211/control interface实机通过。这个构建没有可选 `-f` 日志支持；前台进程置于nohup后写入私人日志。`CONFIG_NO_CONFIG_WRITE` 下不配置 `update_config`。凭据、SSID、MAC、NV、完整日志和二进制均在本机私人目录，未进入公开工作区。

实际TCP下载4MiB约0.56秒、上传约0.28秒，仅为单次小文件观察，不是稳定吞吐基准。checkpoint uptime3506.51秒、taint0；本次MPSS运行约25分钟。六个NV源分区、六个普通文件快照与modem分区哈希均保持。

## 复核产物

| 私人产物 | SHA256 |
|---|---|
| Image-rmtfs，39164416字节 | `5d76bac9c960838a35946cb279d67ced09b87e35dbfe60647225a22884783e50` |
| 实际内嵌DTB，97138字节 | `e7f217554f09f4614feff7e7b1317e9313b68ed0a773a4a0d8cd930f06374ded` |
| boot-k91-rmtfs.img | `6c2ee20360acd9a535004cef05c2d6d7ab207936cec56038746d87e6ca16cd23` |
| logdump-k91-rmtfs.img | `37ea81b0c2dbc678ed090048fcad8160acd089f1b7189eddbf0d0c873698ac36` |
| 扫描/服务归档 wifi-ready.tar | `17d4779c812a01b8f3957a50a6dc350371969c50a46eab53c5fd70b42b2b4e56` |
| 连接/流量现场 connected.tar | `ff4a253d85bc9fc5e62318c25f847c4c8e9551b1ea9b7ddd85ffa65bb6f704ad` |

复核脚本见 `reference/kernel91/verify-connected.py`，现场采集见 `collect-connected.sh`，有界双向传输见 `wifi-traffic-server.c`/`wifi-traffic-client.ps1`。完整现场留在 `E:/edk2-samurai-out/kernel91`。

显示先前故障仍开放；#90当前下溢0不能代替候选全面验收。充电阶段保持收尾和既有边界。用户新优先级为Wi-Fi、蓝牙、NFC等连接，接着核对本机UART/I²C/供电，推进蓝牙/NFC。

来源：[Realme原厂CNSS](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/net/wireless/cnss2/qmi.c)、[rmtfs](https://github.com/linux-msm/rmtfs)、[tqftpserv](https://github.com/linux-msm/tqftpserv)、[wpa_supplicant发布](https://w1.fi/releases/)、[OpenSSL发布](https://openssl-library.org/source/)。新近WCN3990被动扫描补丁测试的是HL3.2，而本机HL3.0已经发现5GHz；目前没有移植这个未证明匹配的补丁。
