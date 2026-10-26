# 蓝牙原厂依据与可复用实现（2026-10-23）

本目录仅静态研究；未连接手机、未占用 SDK、未改变共用源码/recipe/检查点。现有185脉冲过滤、204唤醒DT和234诊断证据直接复用。配对/ACL/HID/音频/外部唤醒均不能由旧扫描结果推定通过。

## 可直接使用的结论

1. 保留本机 `crnv21.bin`、`crbtfw21.tlv` 和 DMS→MGMT 地址供应。原厂 NVM 不是待猜测的单层 tag 表；解析必须识别 type4 外壳、type2 BT 与 type3 第二组。BT 内无 tag44，不应用 Rome 的 PCM tag44 修改法。
2. 185解决有限 power-pulse 窗口的 NUL，不解决 phase5/3.2Mbps/firstff。234 H4真实函数已证明 `partial=0` 不能说明没有帧状态；吞 `ff`、补 `04` 会破坏解析语义。
3. 下一项可实现的底层改动是 GENI `set_termios` 完成 flow mode 变化后同步 RFR；应在真实端口锁/IRQ 契约中实现，并保留 console/RS485/PM 行为。234模型已给出2/16反例，但没有证明历史 phase5 根因；不能把模型通过写成手机修复。
4. 当前音频设计是 PulseAudio。版本匹配的 PA17原生后端已经有HFP/CVSD/mSBC控制协议；A2DP通过ACL无需先移植原厂 DSP offload。HFP是否能收发SCO仍需控制器/路由证据。
5. 185原始缓存四个初始化窗均声明SCO buffer60B×8、Enhanced Setup/Accept同步连接命令可用，见[脱敏解析](cached-sco-summary.json)。先尝试标准HCI data_path0/CVSD并确认真实SCO TX/RX；不能仅凭二手文章认定本机必须非HCI。原厂匹配19781板另有**第二个** SLIM NGD→WCN3990 音频通道，作为有来源的后备实现路线。

## 本机固件与地址

原始文件复用私人 `E:/edk2-samurai-out/kernel92/bluetooth-firmware.tar`，不复制原件到公开目录；[结构摘要](nvm-summary.json)隐藏地址与非传输payload，[解析器](inspect-oem-nvm.py)可复核。

| 文件/字段 | 已核对内容 |
| --- | --- |
| crnv21.bin | 4710B，SHA256 `148255b19bce3b7a048da461279dff908f97365140bd93c18cec32691cf0057c` |
| crbtfw21.tlv | 229812B，SHA256 `46a09f53f93c4e6e0d03cac8e69b3653216b2f1df86de0dbed62fc003e61a6f7` |
| NVM包装 | type4长度4706；type2 BT长度3627；type3长度1071 |
| BT tag17 | 长9，`82 01 11 08 04 14 28 02 15`；原厂IBS已置位，rate=0x11对应3.2Mbps |
| BT tag27 | 长1，`01`；deep sleep已置位 |
| BT tag44 | 不存在；第二组中的同号tag不属于BT transport配置 |
| 地址 | 130已证DMS GET_MAC BT→MGMT RAM配置和读回，保留本机NV/persist与既有配对；不公开地址/keys |

主线 `btqca.c:qca_tlv_check_data()`处理type4后只解析第一type2组，启IBS/写user baud及deep sleep；下载的是工作副本，原厂文件不应重写。当前DT显式指定21系列避免ROM0x1001自动派生缺失01文件；四供电及3.2Mbps均为既有配置。

## UART问题对应的真实代码

当前 canonical `/home/cy122/pmos-samurai-kernel136/kernel` HEAD在只读时为 `58d7652b4e2674b67fd283a061a0cc94907b6466`。GENI基线来自Linux v7.3-rc6，不能因文件含更新代码就推定设备已经换内核；234已核对保留183 Image实际函数。

- `qcom_geni_serial_set_mctrl()`在 `manual_flow && !RTS && !suspended` 时写 `UART_MANUAL_RFR_EN|UART_RFR_NOT_READY`，否则写0。
- `qcom_geni_serial_set_termios()`按CRTSCTS改变 `manual_flow`，但不重算RFR寄存器。
- `uart_update_mctrl()`在请求值等于缓存值时不调用底层set_mctrl。因而仅改变termios后再设置相同RTS可能保留旧RFR。
- `hci_uart_set_flow_control()`的serdev分支依次调用set_flow_control和set_rts；这条真实调用链应进入修复模型。
- 官方[0b1837c04d2335ec50b9a55b0282dcde7bc12439](https://github.com/torvalds/linux/commit/0b1837c04d2335ec50b9a55b0282dcde7bc12439)引入manual_flow以修正自动流控被手动RTS覆盖。当前源码**已经包含**，不能再当待移植新修复。
- 原厂 `msm_geni_serial_set_mctrl()`按RTS改变manual_flow并在寄存器写后执行mb；原厂termios先在端口锁中stop_rx，再改时钟/格式并start_rx。这说明硬件切换顺序有原厂依据，但其PM/DMA框架与主线不同，不能整段照搬。

已有234可用初始化轨迹两次phase5均是完整vendor event+command-complete共12B，UART与HCI字节一致、无剩余skb；未复现历史错误。后续仅在具体错误窗口保留完整前后状态/GENI IRQ/串口字节，不因未复现重复扫描。

## 原厂SCO/A2DP音频通道

固定官方R提交 `23172a1571bd91156032cc9fef16284a82b63d2c`，文件原文及SHA见 [manifest](public-sources/manifest.json)。下载仅补本地缺少的R版本文件。

| 原厂源 | 可复用事实 |
| --- | --- |
| [19781/sm8150.dtsi](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/arch/arm64/boot/dts/19781/sm8150.dtsi#L3549) | slim_qca@17240000，NGD寄存器17240000/2c000、17204000/20000，IRQs291/292；WCN PGD EA `[00 01 20 02 17 02]`、IFD `[00 00 20 02 17 02]` |
| [19781/sm8150-audio-overlay.dtsi](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/arch/arm64/boot/dts/19781/sm8150-audio-overlay.dtsi#L64) | snd_934x启qcom,wcn-btfm=1；本机9340族与9360候选分别有对应节点 |
| [btfm_slim_codec.c](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/bluetooth/btfm_slim_codec.c) | SCO TX capture和SCO/A2DP RX playback DAI、采样率/声道和prepare/shutdown生命周期 |
| [btfm_slim_wcn3990.h](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/bluetooth/btfm_slim_wcn3990.h#L78) | SCO TX port0、SCO RX port16、A2DP RX17；WCN寄存器偏移0x800 |

更早官方Q提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 已在本地 `/home/cy122/work/realme-stock`，提供同族btfm寄存器编程。R19781连接已经单独核对，不能把18115板源直接当本机。

当前主线hci_qca虽支持H4_RECV_SCO，但该解析入口**不能证明WCN3990正在使用SCO-over-HCI**。额外解析185已保存的真实monitor：原模块scan-before-v2、185 scan-after、suspend后、postresume四个初始化窗，ReadBufferSize均status0/ACL1024×7/SCO60×8；SupportedCommands第29字节的Enhanced Setup/Accept bits3/4均置位。缓存没有SCO TX/RX，因为当时只扫描；buffer声明仍不能替代实际SCO流验证。此结果使直接断言“不支持SCO-over-HCI”缺乏依据，也无需再为这些只读能力发新命令。[解析脚本](read-cached-sco.py)

WCN3990 socdata未声明WIDEBAND_SPEECH/HFP_HW_OFFLOAD；不能照抄WCN3991或QCA2066的capability，也不能由该flag缺失推出所有CVSD/HCI音频不可用。当前主线的 `qca_configure_hfp_offload()`设置非HCI data_path_id=1且无需ConfigureDataPath，仅在其他已声明capability的芯片调用，不是WCN3990非HCI适配已经完成的证据。

AOSP旧Cherokee `libbt-vendor` 的 `BT_VND_OP_SCO_CFG`只回报dummy success；没有通用可拷贝的“切HCI”命令。[固定源码](https://android.googlesource.com/platform/hardware/qcom/bt/+/20f50076d30e7d1c55c2d8206e01534f2df9112b/msmcobalt/libbt-vendor/src/bt_vendor_qcom.c)。AOSP标准enhanced eSCO结构定义data_path0=HCI、1=PCM，默认CVSD/mSBC均设1；这是标准路由字段，不证明本机控制器支持所有值。[结构](https://android.googlesource.com/platform/system/bt/+/ea7ab70a711e642653dd5922b83aa04a53af9e0e/device/include/esco_parameters.h)、[默认参数](https://android.googlesource.com/platform/system/bt/+/android-8.1.0_r33/device/src/esco_parameters.cc)。

尚缺：本机vendor蓝牙HAL/stack的SCO初始化和实际路由。现存kernel96 stock-vendor.tar只有init rc/libbtnv.so；238归档没有BT HAL。主会话可在已协调窗口只读提取真实HAL、BT配置与音频SCO XML后静态匹配；此子任务没有自行读取设备。网上“不支持SCO-over-HCI”的断言仅有二手文章，不作为已确认事实。

## 用户态依赖与防止双重接管

旧rootfs115作为已有软件包证据（不是当前现场快照）：BlueZ5.87-r0、PA17.0-r7及pulseaudio-bluez均已安装；default.pa自动加载module-bluetooth-policy/discover。pulseaudio-wireplumber的`51-pulseaudio.conf`将main profile的hardware.audio和hardware.bluetooth置disabled，PipeWire/WirePlumber用于相机而不抢PA蓝牙。

- [PA17 module-bluez5-discover](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/module-bluez5-discover.c) 支持native/ofono/auto、enable_msbc、enable_native_hsp_hs、enable_native_hfp_hf；默认mSBC=true。
- [PA17 backend-native](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/backend-native.c) 默认native后端注册本机HFP AG（手机）以服务对端HF（耳机），源码中的`HFP_HF`枚举和`enable_native_hfp_hf`指对端角色；SCO通过BTPROTO_SCO socket收发。不能误写为native同时默认注册本机HFP HF；本机AG→耳机HF无需因旧PA网页而强加oFono。
- [WirePlumber0.5.18文档](https://github.com/PipeWire/wireplumber/blob/81606cbb32d29df20147d1b68b662c1082654d81/docs/rst/daemon/configuration/bluetooth.rst)适合未来offload方案的接口依据；当前不应为了蓝牙音频同时打开第二套音频owner。
- BlueZ5.87固定提交 `65d11edee469c24dcc8d075b8be9c040cebaaf98`；Adapter/Device/Profile/Media接口按该版本复用。配对agent、信任和重连是用户态策略，不应通过修改固件默认自动接受附近设备。

下一次设备baseline应只确认当前实际PA server、loaded bluez modules、51-pulseaudio配置、BlueZ Media/Profile endpoint和已授权对端条件；SCO MTU/Enhanced Sync能力直接复用上述缓存，不重发初始化。优先标准HFP CVSD，在btmon确认Enhanced Setup/Accept的input/output data_path0，以及真实SCO TX/RX；没有数据再对比本机HAL路由，必要时实现原厂SLIM路径。不要重复既有三模式扫描，仅profile注册/创建sink-source不等于音频数据成功。

当前Linux源码已核对：`sco.c:625-629`默认CVSD/data_path0；`hci_conn.c:385-386`复制给Enhanced Setup input/output；WCN3990未安装offload override。PA本机AG→耳机HF的注册与角色方向、强制CVSD所需临时模块参数、最短命令和恢复条件见[原生CVSD验收](NATIVE-CVSD-ACCEPTANCE.md)。该文是待设备窗口执行的操作依据，没有执行或完成验收。

## 外部同机vendor来源范围

只读取同机设备树文件列表与属性，没有下载整ROM或二进制HAL。HyperTeam固定设备树提交：Android10/lineage17.1 `9b3542960d9c4297edfe9f01d694023990e4607c`，Android11/lineage18.1 `5691782f540b35be8eea349273ac49674b1b80c6`。两份`proprietary-files.txt`均列有：

- `vendor/lib64/hw/android.hardware.bluetooth@1.0-impl-qti.so`及32bit对应件；
- `vendor/bin/hw/android.hardware.bluetooth@1.0-service-qti`、对应init rc；
- `libbt-hidlclient.so`、`libbtnv.so`；
- A2DP的`audio.bluetooth_qti.default.so`、`vendor.qti.hardware.bluetooth_audio@2.0-impl.so`和`libbluetooth_audio_session_qti.so`。

17.1属性指定Cherokee、modem_nv_support和splitA2DP；18.1亦指定Cherokee、splitA2DP并增加不同codec/offload属性。这些用于定位实际本机HAL及版本匹配，不能冒认与手机当前vendor完全相同，Android属性不能直接当Linux驱动参数。文件已移到私人research-scratch，不需要公开镜像；固定来源与哈希见[source-lock](source-lock.json)。TheMuppets聚合仓库的lineage17.1固定`4aecaaac1b0547ff5bf6e4c2edb0df5212978643`根目录只有RMX1801，未找到samurai；猜测的独立vendor仓库未能取得。没有可供静态反汇编的同机替代HAL，本轮不再扩大搜索。

## 公开方案适用范围

同SM8150 Hotdog [b12bfb8c42f98d08475fe6aaf684c2b4fbe230ad证据](https://github.com/Sr-0w/hotdog-linux-bringup/blob/b12bfb8c42f98d08475fe6aaf684c2b4fbe230ad/docs/evidence/2026-08-04-mainline616-bluetooth.md)使用21系列固件/UART13/四供电，验证真实HID连接和普通断开；音频及PM仍开放。可复用连接/固件选择契约，不能当HFP已运行实现。

Firecrawl已优先使用。精确WCN3990/GENI检索多次返回无关芯片，已逐次反馈；之后用官方代码和版本固定的primary source补齐。GitHub匿名REST查询触发403速率限制，原厂固定raw文件仍成功取得，不以API失败阻塞本地研究。

## 本轮交付与下一步

本轮完成静态原厂/公开方案收敛、既有SCO能力缓存解析和有界待执行验收步骤。源码、包、设备均未部署改动。手机交回后先按该文做PA原生CVSD/HCI数据试验；UART功能候选由负责代理按真实锁契约推进，phase5根因仍未关闭；SLIM保留备选。

文档镜像只需本目录README、NATIVE-CVSD-ACCEPTANCE、cached-sco-summary/read-cached-sco.py、nvm-summary/inspect-oem-nvm.py、source-lock、fetch-public.py、public-sources的manifest和四个GPL源文件。一次探索脚本、外部vendor列表/属性已移到 `E:/edk2-samurai-out/bluetooth-oem-20261023/research-scratch`保留，不需镜像。无私人数据/二进制HAL/原始HCI payload需公开镜像。
