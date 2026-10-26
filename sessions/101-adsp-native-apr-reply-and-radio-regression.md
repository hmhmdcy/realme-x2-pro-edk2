# 101：ADSP真实版本回复、振动人工验证暂缓及无线基线

2026-10-11。本轮已构建并真实刷入Linux #100和重建的EDK2；本机ADSP自动运行、APR原生版本回复AFE API7/ASM API2通过。ALSA仍无声卡，音频输出/录音未验收。一次有界恢复后MPSS/ADSP running、5GHz可通信、蓝牙关闭；首次MPSS40秒fatal与2.4GHz掉线仍未解决。全硬件goal仍active。

用户明确无人测试振动，要求按日志与代码静态分析后继续下一个。复查ID检查、异步I2C、低强度连续模式、关闭/故障停振和1秒保护，未发现需要立即修改的问题。保留阶段99三次20%150ms电气与close/SIGKILL/1.02秒保护测试；Shipping API28核对通过；机械效果未人工确认且已暂缓，无新增播放、没有待答的触感问题。

## 本机资源与候选

预检在#99当前启动下完成，vendor ext4只读noload、modem vfat只读，均已卸载。40文件预检包SHA `3ad010286b3f33597ab8c6a387a559fd9581cd6421ebf88c745686d42af6a368`。本机17个ADSP拆分签名文件共12,420,754字节，ELF32/EM_HEXAGON164，load段可重定位跨度30MiB，与保留的 `0x9b200000/0x1e00000/no-map` 完全相符。签名内容/OEM XML/JSN只在私人目录。

本轮只修改ADSP status/firmware-name，新增APR/core两节点，domain4/channel apr_audio_svc；固件JSN核对avs/audio、msm/adsp/audio_pd。SOUND/QDSP6/APR及PDR内建；QDSP6其它服务的代码没有相应DT设备。codec/功放/机器声卡仍未启用；SLPI/CDSP禁用。原init、已有模块/驱动、保留区及其它DT节点保持；GPU zap同目录文件保持。两次构建的登录PATH导致8项Rust编译器检测元数据差异已逐项审计，CONFIG_RUST始终关闭，没有新增Rust运行代码。

公开19781资源来自 [Realme官方内核仓库](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)。[hotdog维护者ADSP记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-05-mainline616-adsp.md)提供同SoC分步验证的参考；本机签名固件和实际结果单独核对。下一步音频契约仍需本机原厂DT选择和活动vendor配置确认，公开overlay提示WCD934x/Maxim并非已验收芯片结论。

新增无线helper严格核对唯一MPSS的name/compatible/DT真实路径/firmware；两个无线服务不依赖remoteproc0。此次实机MPSS0/ADSP1，但下次编号不能当契约。两个服务内容与新增helper之外，CPIO只新增17个私有ADSP文件；原SSH身份/模块/初始化/振动全部保持。

## 实际DSP查询

只读samurai_api只对本机创建，调用原生GET_FWK_VERSION及必要时legacy fallback；单次100ms等待与原生一次缓存。sentinel拒绝没有真实服务条目的“成功”返回，不走默认timeout亦ready的接口。回复解析先检查固定header与变长条目长度，避免无界num_services读取。

ADSP18.900281秒up，初次102.64秒现场与恢复后只读查询均回复AFE API7/ASM API2，内核taint0、ADSP fatal0。没有打开PCM、设置功放增益或声学测试；/proc/asound/cards为空，不能把版本回复当声音可用。

## 刷入、首次失败与单次恢复

当前boot/logdump完整新备份，80个2MiB块8192Kbit/s全部逐块/合并SHA通过，本轮无传输超时。真实EDK2重建只DTB FFS/压缩容器变化，其它执行字节、兼容DTB、shim/header/ramdisk/EUD核心源保持。F1 receipt后出现设备消失/EIO，保留原日志；独立fastboot核对私有身份、msmnile与两分区大小，通过后只刷boot/logdump。

首次EUD设置时控制设备尚未枚举，失败保留；控制设备出现后正常com-up/一次reader重试通过并释放owner。NCM重新枚举后第一次SSH尚无可用地址，空启动ID文件保留，再读真实新boot ID并检查#100/taint0。EUD读取4587帧，原包仅私人。

首次MPSS43.886772秒up、83.873343秒fatal without message，间隔39.986571秒。源准备成功但无WLAN身份成功标记，自动Wi-Fi exit1；原boot-finished=1/自动日志与首次失败包保持。上轮无ADSP时已经有约40秒问题，不能据新增ADSP归因。原生同一句fatal包含SMEM错误/零长度/空首字节路径，仍需有限诊断。

自动BT worker已经退出/锁释放后，单次受控停BT/解绑ath10k/停崩溃MPSS/重绑/启动，复用已核验RAM COW与存活tftp/rmtfs。WLAN出现后45秒监测通过，独立WLAN/BT只读DMS成功，BT关闭；ADSP全程running，版本回复相同。原自动失败标记未改为0，也没有无限恢复。

## 网络与验收边界

初次误用早期freq_list2462的私有配置，2.4GHz认证成功但5GHz条件失败，原partial目录/配置不覆盖。这段期间又出现一条非主动reason7（此前阶段98已有两次）；之后主动换5GHzreason3/locally_generated1单独记录。重试改用阶段100已验证私有5GHz配置，认证/DHCP/路由/DNS/HTTP577字节通过；首轮网关3发2收33%丢包，后测5发5收0丢包。原丢包不被后测覆盖，2.4GHz、自动启动和长期稳定未解决。

最终113文件checkpoint SHA `e3f24622bbebe7de770fc9b0eeca136fffa9ba658a8520b9c3ebfd430a7c2354`，uptime586.99秒；原4个完整测试包与nested清单逐字节绑定，并保留初次错误频段partial目录。后测网关包SHA `bc4a18b43e0564583f6fd3b05f0acaaa68918a44f2eebf510df4bdf14906d7ca`，uptime646.07秒，同启动双DSPrunning/taint0。当前checkpoint显示超时0、三条BT Frame reassembly failed均phase2；没有开启本轮单播删除跟踪，不作删除等待修复结论。振动ID97/standby/starts0/error0；6NV与persist不变。

首次checkpoint collector遗漏nested清单的外层hash，原包保留，修改为只排除根SHA256SUMS，以checkpoint-retry1重采并全校验。初次原目录guard发现GPU已有固件而停止，私有前快照保留；核对只有两个无线服务和新helper的部分修改后有界续做，未覆盖GPU固件。所有工具/数据失败均有原件，不以日志删除改变验收。

## 产物与后续

| 产物 | SHA256 |
|---|---|
| Image #100 | `6edfea9d5c23bd55b623b8f57f21937f1f8c3e63467b0437ffe5021ae8aab19d` |
| DTB | `2fac32706a56743294f17d108e207937b237be0ef2d1a7c27bff5bcf8fe57f46` |
| CPIO | `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7` |
| boot（6680576字节） | `ea123f3aa112f477d979444f5d620b4b378ef09ef2f55c140658b65407b57cc0` |
| logdump（64MiB） | `2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe` |
| 完整boot读回 | `b71044d4cee6190e433878af8bc6be12e8179adcf1219981faeb4309c4406543` |

boot整分区与新前缀+原尾部的SHA相符，logdump整分区与候选完全相符，RAM服务/已有模块及实际ADSP DT节点与候选吻合。当前源码见 [reference/kernel101](../reference/kernel101/README.md)，下一项 [codec/SLIMbus/功放交接](../reference/kernel101/next-session.md)，15组 [硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。

保留Android、userdata/GPT、原NV/persist、SSH身份、显示85–88和rootfs01/F2FS；NV仅RAM COW，不跑旧充电探针。签名固件/镜像/二进制/OEM库/XML/原日志/身份/凭据不公开，无提交/推送。冷启动/休眠/长期稳定及全硬件仍待继续。

最后8文件只读状态在uptime 1081.81秒确认同一次#100启动：MPSS/ADSP running、5GHz COMPLETED、BT四标志关闭、振动standby/starts0、taint0、NV/persist不变；累计MPSS fatal1、ADSP fatal0、显示超时0、BT phase2错误3，无额外MPSS fatal。原包SHA `cbed4ee09724635e0bf36c512b2588dcf361b977e004d38e0a7e66ba07d6562f`，私人final-status-validation.json；版本为本次原生查询后的缓存，未重复发送查询。
