# RMX1931 Linux 硬件状态与未完成项目

目标更新（2026-11-09）：Wi‑Fi、CDC NCM 和 SSH 的持久化与最终验收已
完成，现继续适配其他硬件；主线正式版模型/API、极薄私有层、安全刷写和
不擦写 NV/persist/校准/userdata 的约束不变。

目标更新（2026-11-10）：活动块切换到 USB 标准平台适配。先只把
PM8150B Type-C/TCPM 作为 DTB-only sink 候选；DWC3 host/OTG 需要另建
`DWC3_DUAL_ROLE+xHCI` Image，USB3/DP 和 suspend wake 继续独立分层。

2026-11-10 电源键/显示最终结论：官方路径仍是 elogind
`HandlePowerKey=ignore`、KWin `DpmsInputEventFilter` 和 PowerDevil
移动端默认 `ToggleScreenOnOff`。实体键能到 KWin，DPMS wake trace 为
`phase=0 -> dpu_first_frame_backlight ret=0 -> phase=1`，但 1024 亮度
在旧驱动中没有 HBM 切换，物理面板黑屏。根因是 SOFEF03F
`0x53=0xe0/0x20` HBM 边界，不是 first-frame 时序或 KWin EBUSY。
`0009-arm64-panel-sofef03f-serialize-brightness.patch` 已刷入 boot
`12a652a5…`；10 轮 1024 DPMS 和真实触摸通过，用户确认不再黑屏。
新建树使用等价的 `0010-...-consolidated.patch`（收敛 0003/0005/0009，
与部署源码逐字节一致）。
`kwin-6.8.2-r3` 的 `TouchInputRedirection::cancel()` 和本地瞬时 EBUSY
重试仍保留，但后者不是本次根因。详见
[PANEL-HBM-20261110](PANEL-HBM-20261110.md)。

2026-11-09 网络检查点（当时）：`samurai-platform` 5-r21 已安装；普通重启
`d5cfa04f-5f4e-430a-8bc3-472567bd45f7` 后 UDC `configured`、
`usb0` carrier 1，标准 configfs `qmult=20` 由启动脚本自动写入。
刷前手机运行 camera-final boot `9b9be136…`；Wi‑Fi SSH
`root@192.168.0.114` 和 USB NCM SSH `root@10.42.0.1` 均使用严格
host-key 认证。原先 Genesys 扩展 Hub 的 `VID_0000&PID_0001` Code 43
在改接主板直连口后消失，fastboot 也已恢复；直连后剩余的 4 MiB
NCM 停顿由 `qmult=20` 处理。30 分钟 NCM/Wi‑Fi 结果见下一段。

2026-11-09 相机 Selection API 检查点：IMX471 的 `CROP` 改为报告当前
模式的模拟寄存器窗口，S5K3M5 补齐 active/try 的
`CROP/CROP_DEFAULT/CROP_BOUNDS`。两个 in-tree 模块替换后普通重启
boot `668b8d20-d22f-44d9-908c-68070eea0147`，42 秒恢复 Wi‑Fi SSH，
`taint=0`；`cam -l` 不再出现 `Unable to get rectangle`/EINVAL。
四路 RAW 各两帧仍为 100% 非零、0% 饱和，帧间变化
27.058–50.355%；libcamera 0.7.2 四路 640×480 RGB888 单帧全部成功。
抓取后 CAMSS `suspended`、MMCX 128；完整 runtime 门禁通过。新的
773 模块归档只替换 `imx471.ko` 与 `s5k3m5.ko`，其余 771 个模块
逐字节保持不变。这仍是普通重启，不是断电冷启动。

同一 boot 还完成两项只读硬件推进：内置麦克风经活动用户 PulseAudio
连续采集 61.98 秒，2,975,039 个样本、RMS 15.053、55.644% 非零、
0% 削顶、最长零段 29.604 ms、stderr 为空；原始音频未保留。时钟
审计得到 358 个时钟中有 55 个“硬件使能但无逻辑 consumer”，包含
`gcc_cpuss_rbcpr_clk`；这只是清单，不是逐项 critical 证明。
仍不在无人值守时测试无 `clk_ignore_unused` 启动。

2026-11-09 闪光灯/V4L2 最终验收：原厂 19781 相机 DTS 明确后置双 LED
使用 PM8150L flash0/flash1、torch0/torch1 和 switch3；主线使用现有
`qcom,pm8150l-flash-led`、LED flash class 和 V4L2 flash subdevice，
没有新增私有驱动。S5KGW1 通过标准 `flash-leds` phandle 加入 CAMSS
媒体图后，`white:flash` 实体和 V4L2 控制同时出现。最终 DTB
`b244b3f1…`、boot `5b4dd487…`、FAT `c99c690e…` 由运行中的 Linux
成对写入并回读，未使用 fastboot。200 mA torch 下 S5KGW1 宽幅 RAW
均值从 177.04 升到 407.147（+130%），0% 饱和，faults 0；774 模块
runtime gate、四路 RAW、thermal、Wi‑Fi/NCM/SSH 和 taint 0 在普通
重启前后均通过。随后安装蓝牙主机模块包，777 模块的 boot ID
`071abbb5…` 再次通过完整 gate；最近 NCM SSH 39.764 秒、Wi‑Fi SSH
64.487 秒。
拔除外部供电的物理按键冷启动、重复冷启动和长时间闪光灯热升仍未验收。

同一组合状态的 NFC 检查点：`samurai-platform 5-r22`、
`neard-openrc 0.20-r0` 和 `neard 0.20-r0` 已安装；普通重启 boot ID
`3331ca80-078d-4dda-935a-902d271cbea1` 后 `nfc0` 存在，`neard`
自动启动，`org.freedesktop.DBus.Properties`、电源开关、
`StartPollLoop`/`StopPollLoop` 和清理全部通过。无实体标签，
`tag_seen=false`，不能声称读卡。777 模块的蓝牙/闪光灯/四路相机/网络
完整 gate 同时通过；最近 NCM SSH 34.688 秒、Wi‑Fi SSH 55.178 秒。
一次前台 NCM NFC 探针出现瞬时 `Connection reset`，Wi‑Fi 同时正常，
随后两者恢复，后台 NCM 探针通过；该主机/USB 瞬态仍未闭环。

同日的私有层审计覆盖 14 个 C/H 逻辑文件和 11 个 DTS/数据文件，未发现
私有 ioctl、用户态拷贝、Android/Binder 入口，平台补丁 96 个变更文件
的新增 C/H 行同样为零；MAX98937 与 AW8697 的
自定义只读 `status` sysfs 已被 0004 补丁删除，并已编入最终 Image
`f8d89621…` 和只替换 `/Image` 的 FAT `1f4bbb30…`；boot
`5b4dd487…` 与 flash/V4L2 DTB `b244b3f1…` 保持不变。Linux 侧成对
刷入后，两次普通重启均通过 777 模块完整门禁；两个 MAX98937 和一个
AW8697 的 `status` 节点均消失，标准 ALSA playback/capture 和 AW8697
input/FF 仍在，`taint=0`。唯一保留的旧只读兼容面是
`sensor-power/state`，仅用于门禁核对两路 rail。

同一 Image 的一次 suspend 尝试未通过：使用 detached `loginctl suspend`
和直接 sysfs RTC wakealarm 后，NCM/Wi‑Fi 在 140 秒内未恢复，Windows
USB 与 fastboot 也未枚举。该失败不能归因于 thin-private 代码，也绝不能
写成 suspend 已通过；需要先物理唤醒，保存
`/tmp/samurai-suspend-test.log`、`suspend_stats` 和 `dmesg`，再用此前
已通过过的 `rtcwake -m mem -s 30` 方法复测。

同日的 NFC 标准化不修改内核：主线 `nxp,nxp-nci-i2c` 节点继续使用
`drivers/nfc/nxp-nci`，用户态选择 Alpine 官方 `neard 0.20` 及其
OpenRC 服务。`samurai-platform 5-r22` 只新增 `neard-openrc` 依赖并把
上游 `neard` 放入默认 runlevel，不在安装事务中启动或重启活动 daemon。
离线 APK、索引、manifest、依赖和签名已通过独立 verifier；设备安装、
`nfc0` firmware/probe、`org.neard` D-Bus 和实体标签读写仍待验收。
无标签时只记录 adapter，不能把控制器绑定或服务存在写成读卡成功。

同日的蓝牙 PAN/HID 标准化只启用主线已有模块：
`CONFIG_BT_BNEP=m`、`CONFIG_UHID=m`、`CONFIG_INPUT_UINPUT=m`。
签名包 `samurai-bluetooth-host 0.1.0-r0` 只含 `bnep.ko`、`uhid.ko`、
`uinput.ko`，三项均为 AArch64 `ET_REL`、`intree=Y`、空依赖，vermagic
精确匹配 `7.3.1-rmx1931-samurai-v731`；配置语义差异只有三项 `n->m`，
且全部导入符号存在于已部署 `Module.symvers`。两次独立构建的 APK、
索引、manifest 和公钥逐字节一致，两轮隔离 APK 安装、owner/version、
文件模式和数据块校验通过。没有新增服务、modules-load 覆盖、私有驱动
或安装 hook；Alpine 官方 `bluez` 包已自带 `uinput/uhid` 加载配置，
`bnep` 使用主线 `bt-proto-4` 别名。设备安装、depmod/autoload、
BNEP socket、`/dev/uhid`、`/dev/uinput`、外部 PAN/HID 对端、普通重启
和冷启动仍未验收，不能把离线包写成蓝牙业务已通过。详见
[BLUETOOTH-HOST-MODULES](BLUETOOTH-HOST-MODULES.md)。

网络 boot `d5cfa04f…` 的最终结果：NCM 双向 `64K/256K/1M/4M` 各三轮，
24/24、0 失败，1798.828 秒心跳（798 个样本），独立 verdict
`010be162…`；Wi‑Fi SSH 独立 1810 样本、1820.51 秒、最大采样间隔
1.01 秒，verdict `b3dd4e29…`。`camera-r21-final` runtime JSON
`d0e8d605…` 显示四路相机各两张 RAW、100% 非零、0% 饱和、帧间变化
26.256–47.325%，抓取后 CAMSS `suspended`、taint 0；随后稳定到
MMCX 128。libcamera 0.7.2 `simple` 已枚举并抓取四路 640×480
RGB888 单帧，内置麦克风 3 秒采样非空；这些只是下一硬件阶段的
只读预检，不是画质/音频质量验收。

2026-11-08 当前部署（历史）：标准 rootfs 的 `boot`+`logdump` 已配对携带主线
DWC3 `tx-fifo-resize` DTB。`samurai-platform` 5-r20 /
`samurai-desktop` 4-r10 已安装，普通重启 boot ID 为
`849bdfb8-1adf-420f-ba1c-bcded615f25b`、`taint=0`，Wi‑Fi SSH 约
52.8 秒恢复；服务边界、runtime、desktop 和 Plasma Mobile 检查除
USB UDC/carrier 外通过。当时 USB NCM 未枚举（`usb0` 无 carrier，
UDC `default`），需要直插主板 USB 口和已知数据线复测；断电冷启动仍待验。
boot `7f8d7a65…`、kernel FAT `1f3a40f4…`、Image `5069b1b4…`、DTB
`c9f948cd…` 均经分区/文件回读确认。F2FS `userdata` 为根、`/sbin/init`
为 PID1；CAMSS/CCI/四 sensor/镜头/PM8008、三路 remoteproc、sensor-power、
UDC、DSI、Plasma、Wi‑Fi 与 NCM SSH 均正常，启动边界和
`--usb-fifo` 完整运行时门禁全绿；四路相机各两张 RAW 均完整、100%
非零、无饱和且帧间有变化。
`samurai-platform` 5-r20 已安装；r17 曾把 `samurai-wifi` 的固定 45 秒
启动等待改成有界 MPSS `running` 轮询。普通重启请求到 SSH 就绪：Wi‑Fi
约 57 秒（内核后约 26 秒），NCM 约 37 秒（内核后约 7 秒）；修复前
Wi‑Fi 约 101 秒。r17 的 5 分钟 NCM 24/24 和 Wi‑Fi 300 样本回归通过。
`samurai-ssc` 的固定 20 秒 readiness 等待也已移除，改为标准 QRTR SSC
服务 400 加真实 sensor probe 重试；当前 boot 的 `default` runlevel
约 26 秒，FastRPC 到首个 sensor probe 约 5.7 秒，边界和 skip-camera
运行时门禁通过。主机侧近期 Wi‑Fi 首连曾波动到 87 至 117 秒，设备
`WIFI_READY` 仍在约 18.8 秒，AP/DHCP/主机链路仍未闭环。
服务依赖修复现由 `samurai-platform` 5-r20 和 `samurai-desktop` 4-r10
承载：radio/USB/SSC 使用有界等待和有序软依赖，NetworkManager、sshd 和
tinydm 不再被单一硬件服务失败连带拒绝；r20/r10 已跨普通重启验证。
`usb0` 保留 `169.254.42.1/16` 并提供标准 DHCP `10.42.0.1/24`。
历史记录中的 `samurai-platform` 5-r20 / `samurai-desktop` 4-r10 是
当时实装版本；当前已升级到 5-r24 / 4-r15，4-r16 是删除电源键桥的
正式候选。候选按 postmarketOS/Nura 官方边界进一步
删除本地电源策略：tinydm 回到官方配置，不再写
`rc_need`/`rc_use`；正式包只使用官方 `/etc/sleep-inhibitor.conf`
和官方 `sleep-inhibitor`，删除 `samurai-sleep-inhibitor` 与
`samurai-usb-sleep-guard`；USB carrier guard 只留在 debug 目录。
`ssh-session-open` 仍是活跃 SSH 的官方 sleep 锁。5-r20 已移除
`sshd -> samurai-usb` 和 `NetworkManager -> samurai-radio` 门控。
候选包尚未在恢复后的设备上安装验收，不能写成已通过。
r16 旧生产 DTB 曾在 4 MiB device-to-host 路径复现 `Broken pipe`；加入
主线 `tx-fifo-resize` 后，30 分钟矩阵 24/24 通过、心跳 1800.598 秒，
Wi‑Fi 同时完成 1800 个样本/1810 秒心跳；其中 DSI 已 `DPMS=Off` 时
SSH 仍持续。部署后的第二个 30 分钟 NCM 窗口也以 24/24、
1800.169 秒心跳通过；同一新 boot 的 Wi‑Fi 第二轮为 1800 样本/1811 秒，
最大采样间隔 2 秒。真正拔除外部供电的手动冷启动、多次冷启动、
更长空闲和 Linux 主机仍未验收；当前剩余的平台级启动约束是
`clk_ignore_unused`。
进一步还有一个**未刷入**的标准 UEFI 启动候选：BdsDxe 优先启动
`\EFI\BOOT\BOOTAA64.EFI`，由 GRUB standalone 加载 `/Image`、
`/samurai.dtb` 并设置 root 命令行；boot `c5e856d5…`、FAT `7c326ad4…`。
GRUB 按 `/Image` 文件发现卷，不依赖 `KERNEL` 卷标。它同样只能成对
刷写，真机 GRUB/root 挂载尚未验收。
第三个候选去掉 `clk_ignore_unused`，只给 `gcc_cpuss_rbcpr_clk`
加 `CLK_IS_CRITICAL`：Image `9d50f464…`、GRUB `81fba992…`、FAT
`3e788ccb…`；干净源码对象重建证明 flags 从 `0x0000` 变为 `0x0800`，
已离线验证但未刷入。无 flag live-FDT kexec 预检虽加载成功并武装了
watchdog，设备超过 255 秒未回 Wi‑Fi/NCM/fastboot，持久 boot/FAT 未改
但需要物理断电重启；该路径不能无人在场重试。
fastboot 暖启动未知 USB 的 workaround 见 [USB-NCM-SSH](USB-NCM-SSH.md)。历史私有充电
长测条目保留为旧组合证据，不再代表当前内核加载路径。源锁和边界见
[STANDARD-ARM64-V731](STANDARD-ARM64-V731.md)。

2026-10-25充电离线交接：[完整接手单](../../reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)。额度消费者38例/单KO、ADC5单位8例、PD/APSD 3708断言/156故障点、5V合同退出34生产函数与6对象W1均通过离线检查；完整probe未整合，高压采用未就绪，均未部署。506长测最近累计8643/36000秒、31%、26.2℃、AUTO/Good、fault0，继续占用手机。用户报告EUD tty打开失败；只读复查确认节点/getty/reader未就绪，无当前日志，不改桌面。

2026-10-24历史：USB IRQ唤醒配置已装机并通过[一次RTC待机恢复](../../reference/charging-management-20261023/usb-irq-wake-rtc001-result.json)。当时504/USB13f41/97c/f6bef/服务83469/manifest5ef4、boot4e325；真实驻留15.019秒，success+1/fail0，前后12门、USB挂起恢复回调0、原key/NCM自动恢复与SDP500保持，无新fault，alarm/trace清理。原驱动未配置IRQ wake的缺口已补；真实USB插拔唤醒仍待现场，窗口只prepare未启动。前boot的2719完整8帧证据保留，新boot MACv2/p1实例0/0未重查。该组合USB两文件逆向0c6a6恢复ebfcb/8c5b7后冷启；更早回退属于不同范围。下面旧组合/未加载描述按历史范围读取。

2026-10-25充电最新：[508合测与回退通过](../../reference/charging-oem-audit-20261023/tcpm-usb-budget-candidate/phone-trial-r2-result.json)：默认Rp预算500、软件共同0→500/原key恢复、实际关机取消释放锁。已自动回正式506 boot82d6，两载体/原充电文件/三note/PD双0核验。[预充03原1299条复核通过](../../reference/charging-management-20261023/precharge-live506-r3-recovered-result.json)。[真实计时观察已启动](../../reference/charging-management-20261023/timeout-live506-start-result.json)，初期587→885与实耗相符，低SOC零实验负载；36000秒到期/AUTO锁存尚未验收。物理USB唤醒、温界、完整PD/APSD共存、高功率等仍待完成。

用途：按功能查询已证明能力与缺口。整理日期：2026-10-23；最后部署见[检查点](../../NEXT-SESSION.md)，操作与验证范围见[当前规则](../../WORKING-BOUNDARIES.md)和[适配工作流](PORTING-WORKFLOW.md)。按本轮功能读对应行，无需每轮通读或回归全部硬件。历史部署、帧数与过程从[会话索引](../../sessions/INDEX.md)定位，各阶段原文与失败证据保留。

## 2026-11-08 标准化审计

只列仍未完全标准化的部分；“已用主线 API”不代表上游已经接收，只代表
当前镜像不再走厂商私有调用路径。

| 功能 | 已用主线模型/API | 仍保留的板级薄层 | 当前证据与缺口 |
| --- | --- | --- | --- |
| 相机 | CAMSS、CCI、V4L2 subdev、Selection API、videobuf2、media controller、libcamera simple | sensor/lens 接线、PM8008 双地址、CAMSS 资源表与 MMCX 投票 | 四路 RAW 三周期、r21 boot 和 Selection API 修复后的普通重启均通过；IMX471/S5K3M5 的 crop/default/bounds ioctl 全部成功，libcamera 0.7.2 枚举无 EINVAL 并四路各抓一帧 640×480 RGB888。暗场景单帧不代表画质；AF/AWB/LSC、录像、多摄、热功耗和校准仍待 |
| 闪光灯 | PM8150L 3 通道 flash、标准 LED flash class、V4L2 flash subdevice | 仅 DTS 启用双通道、声明白色 emitter 并链接到 S5KGW1；无私有驱动 | Linux 侧 boot/FAT 成对写入、24 资源 contract、200 mA torch 光学 RAW、faults 0 和普通重启均通过；安装蓝牙包后 777 模块 gate 仍通过，冷启动与长时间热升待验 |
| 显示 | DRM/KMS、DSI PHY、标准背光 | sofef03f 面板时序/接线 | 60/90Hz 与短时 s2idle 通过；deep sleep、冷启动黑屏时长和长期稳定性开放 |
| 音频 | ASoC、ALSA、UCM、标准 DAPM、PulseAudio | MAX98937 与 samurai ASoC glue | 播放/录音和短 PM 通过；Selection-fix boot 的内置麦克风连续采集 61.98 秒，0% 削顶、stderr 空、最长零段 29.6 ms。耳机/耳麦、watchdog、音质与长稳开放；私有 `status` sysfs 已从部署 Image `f8d89621…` 删除，标准 ALSA playback/capture 在两次 thin-private 普通重启后仍存在 |
| 传感器 | remoteproc、IIO、SensorProxy、标准 claim/release | `sensor-power` 板级 subdevice/电顺序 | readiness、旋转和短 PM 通过；SSR、freezer 竞态、精度与长期跨 boot 开放 |
| 蜂窝 | `qcom_q6v5_pas`、QRTR/QMI、IPA、ModemManager | 板级 MCFG 目录/配置复制 | modem 可 running；真实 SIM、数据、通话、短信和 UIM 未验收 |
| Wi-Fi/蓝牙 | cfg80211/mac80211、hci_uart、btqca、BlueZ | 板级校准/固件与上电顺序、同机 DMS MAC 查询 | Wi‑Fi 当前 boot 1810 样本/1820.51 秒 SSH 心跳通过；WCN3990 仍记录 invalid MAC，但启动脚本在关联前应用 DMS 地址 `PRIVATE_WIFI_MAC`（BT `PRIVATE_BT_MAC`），多次启动一致；BT 音频/连接、冷启动和长稳开放 |
| USB | `qcom,sm8150-dwc3`/`qcom,snps-dwc3`、UDC、configfs NCM；PM8150B Type-C/TCPM 候选 | 无私有 USB 传输层，只有板级 NCM 配置脚本；stock 无 FSA4480 证据 | 5-r21 网络基线通过；标准 `tx-fifo-resize` + `qmult=20`。2026-11-11 撤回 PM8150 GPIO10 extcon（厂商 DTS 注释掉 `vbus-gpio`/consumer，实测不跟随 VBUS）和 keep-connect opt-in（拔线时 `dp_hs_phy_irq` 伪唤醒，插线 resume 曾致 Windows Code 43）。标准 suspend/resume 已验证：插线 20 s、拔线 30 s（实测 32 s），boot ID 不变。USB wake 未支持，下一步走 PM8150B Type-C/TCPM；当前内核仍是 `DWC3_GADGET`，dual-role host 需新 Image。见 [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md) |
| 充电 | `bq28z610`、`mp2650`、标准 `power_supply` | 板级阈值/保护参数 | 标准绑定和短测通过；高压、完整 PD/APSD、长期计时与温界未验收 |
| NFC | NXP NCI I2C 标准控制器、Alpine `neard 0.20`、`org.neard` D-Bus | 板级供电/接线；`samurai-platform 5-r22` 只增加 `neard-openrc` 默认 runlevel | `neard-openrc` + `neard` 和 5-r22 已安装；普通重启后 `nfc0`、neard 默认 runlevel、D-Bus 属性、电源和轮询启停通过；无实体标签，TagFound/读写/eSE 未验收 |
| 指纹 | 尚无功能主线驱动 | 传感器/SPI/供电/TEE/用户态认证链 | 未做功能验收，是当前最大的未标准化硬件块 |
| 触觉 | input/ff、标准 feedbackd D-Bus | AW8697 板级驱动 | 按键反馈通过；振幅、时长和长稳未由用户确认；私有 `status` sysfs 已从部署 Image `f8d89621…` 删除，AW8697 input/FF 在两次 thin-private 普通重启后仍存在 |
| 定位 | GNSS、GeoClue、标准电源管理 | 板级 RF/天线接线 | 室外定位通过；室内、冷启、PM、长稳和绝对精度开放 |
| 启动/UEFI | EDK2、Linux EFI stub、标准 `\EFI\BOOT\BOOTAA64.EFI`/GRUB 候选 | 私有 BootShim/BDS 直启回退、DTB FFS、EUD 关闭策略 | 标准启动器候选未刷入，GRUB 与 root 挂载未真机验收；标准 ESP/BDS 回退和持久变量未实现；已建立 358 时钟只读审计与 55 个无 consumer 候选清单，`clk_ignore_unused` 逐项根因仍未验收 |

明确不进入标准镜像的私有部分：相机 ICP userspace、已删除的 APSD 死
Kconfig、私有 USB-input、旧 managed-charging KO、生产 EUD serial、
vendor 根属性和 `samurai_diag` trace 依赖。它们不能以“能跑”为由重新
混入标准平台。

**149已复现的A640 CCU故障修复保持；240新增Snapshot默认Vulkan负载的GPU fault，需独立继续定位。** 147修复旧式GLES地址对齐，149修复Vulkan自动VM_BIND地址对齐。149完成185次像素读回零差异、36次Settings面板打开及PM、稀疏重绑定、旧地址重放、Vulkan/GLES并发验收。151同启动六次被动观察中无新增fault，taint0，桌面保持。150无Mesa补丁的降级候选未部署；它的验证不能混入149系统驱动的验收。

211新增相机GPU ISP退出时的`__arm_lpae_unmap`告警，保存日志可见349条、taint512；它不属于此前CCU像素读回验收。212默认CPU ISP跨启动取流没有新增告警，最终taint/fault0；GPU路径仍未修复。这个结论限定此前已复现故障和已测负载。所有Vulkan扩展、长时间压力及跨启动GPU回归仍需验收；显示交接白屏/花屏及已测开关屏已通过本轮验收，冷启动、休眠和长期显示稳定性仍开放。普通Mesa包更新可能覆盖本地修复，旧rootfs132镜像不含该库更新。

## 当前功能与待办

“未完成”包括仍有真实缺陷、功能尚未接入，以及仅做过部分验收；不能将这三类都写成完全不能用。

| 功能组 | 已证明的能力 | 尚未修复或验收 |
| --- | --- | --- |
| GPU | 149已复现GLES/Vulkan CCU修复及原像素回归保持；240停止故障Snapshot后及CPU mmap两轮新增fault0/taint0 | 240 Snapshot默认Vulkan新增GPUfault480/VK_ERROR_DEVICE_LOST，CPU回退未修GPU根因。211 GPU ISP退出IOMMU WARN另案保留；Mesa可复现包/rootfs、完整扩展和长稳待完成 |
| 原生显示 | 用户实屏确认EDK2之后无白屏/花屏，黑屏等待后显示命令行；此前165的DPMS/首帧门控/稳态软件验收通过。最终v7.3.1 boot已通过KWin/KMS `1080x2400@60`与`@90`双向切换，切换窗口无WARN/timeout/fault；15秒RTC s2idle唤醒后同一boot、DPMS On、桌面与四路相机均恢复。PowerDevil/KScreen标准亮度接口实测15%→sysfs 308、50%→1024 | 冷启动黑屏等待时长、实体电源键长按菜单复测、deep sleep、更长休眠/长期稳定性仍开放。164首启音频WARN及157重启原因仍未知。亮度需等下一次KWin合成帧才写硬件，自动亮度默认关闭 |
| Plasma Mobile | tinydm自动登录Plasma Mobile，当前用户UID10000/Wayland-1；KWin、plasmashell、PowerDevil、KScreen、portal-kde、Calls/Chatty/mmsd服务已接入。最终boot的s2idle唤醒后tinydm/KWin/Plasma保持同一PID，桌面无需重启；只读检查脚本全绿：单KWin/plasmashell实例、Wayland/KScreen、两个portal、Modem Manager对象、NetworkManager、BlueZ、传感器、音频、USB守护和OpenRC服务均通过。`samurai-desktop` 4-r15 已安装并通过普通重启；4-r16 候选删除 `samurai-powerkey` 桥并保留官方 tinydm/PowerDevil 路径。设置来源见[SETTINGS-PROVENANCE.md](SETTINGS-PROVENANCE.md) | 4-r16 尚未实机安装；人工拔电冷启动和实体电源键短按已通过；长按电源键官方路径存在，本机 `PowerDown` 曾为 `none`，已恢复；D-Bus 与 event0 1.2 秒 `KEY_POWER` 注入均实测菜单，实体手感待用户确认；deep sleep和长期行为待验；真实SIM业务受未插卡阻塞；无SIM时ModemManager自动枚举约需30秒，不把D-Bus存在等同于通话/短信/数据通过；旧 Genesys Hub 的 USB 枚举失败已由主板直连口规避，r21 qmult=20 网络长测通过 |
| 电源键/DPMS | 官方路径已确认：elogind `HandlePowerKey=ignore`、KWin `DpmsInputEventFilter`、PowerDevil 移动端默认 `ToggleScreenOnOff`。实体键能到 KWin；DPMS wake 的 `phase=0`、`dpu_first_frame_backlight ret=0`、`phase=1` 均出现，KWin 截图是完整锁屏。安装的 `kwin-6.8.2-r3` 含 `TouchInputRedirection::cancel()` 和 `0103-retry-transient-ebusy-commits.patch`；4-r16 候选删除 `samurai-powerkey` 桥。2026-11-10 最终定位锁屏触摸黑屏为 SOFEF03F HBM 边界：亮度 >1023 必须先写 `0x53=0xe0` 进入 HBM，离开时写 `0x53=0x20`；旧驱动直接写 1024 导致物理黑屏，KWin EBUSY 是独立问题 | `0009-arm64-panel-sofef03f-serialize-brightness.patch` 已刷入 boot `12a652a5`；10 轮 DPMS off/on（brightness 1024）全部 On/enabled/1024/`bl_power=0`，HBM/亮度错误 0、KWin EBUSY 0；真实上滑多次用户确认不再黑屏。2026-11-11 拔电冷启动（boot `f70fcefd…`）和冷启动后电源键唤醒通过；长按电源键走 KWin 1 秒合成 `PowerDown` + PowerDevil `PromptLogoutDialog`，本机曾因 `kglobalshortcutsrc` 的 `PowerDown=none` 不触发，已恢复；D-Bus 与 event0 1.2 秒 `KEY_POWER` 注入均出现菜单。截图证据 `panel-hbm-20261110/powerdown-menu-20261111.png`。 |
| 音频 | 171人工双组滴声；183识别离线传输并清理WCD流，活跃双工合成crash原客户端恢复、2旧FD EIO、18项0，匹配左右相关0.9119/0.9312。两次s2idle实际45.33/87.04秒、success2/fail0、PM callbacks全err0；醒后原生/桌面左右通过。1473秒taint0、20项全boot0，PCM关、功放23/23与22/22静音、16控件恢复、五consumer各1/两map/一MCLK；新 boot 内置麦克风连续采集61.98秒、0%削顶、stderr空 | 耳机/耳麦/按钮、实际watchdog、跨启动/更长可靠性和音质/瞬态/保护开放，用户暂无耳机。新发现181活跃STOP −107/ASoC3及旧178/180失败、183首轮脚本mute假设错误均保留，不改成通过 |
| 电池与充电 | 508短测默认Rp500、软件0→500及关机取消通过，已回506/5c8d/b29e，boot82d6原件/三note/PD双0重核。USB161b/chargerbef4/保护f6bef/服务83469/manifest8b402。预充1299条、phase1→连续phase2/正净流及负载收尾通过。506两RTC、旧回满/停充计时及[基础容量查询](../../reference/charging-management-20261023/gauge-basic-capacity506-result.json)保留 | 真实36000秒观察运行中，最近只读累计8643秒；手机归该长测。PM后新连接/FLOAT/APSD、物理USB唤醒、2719/TCA语义、温界、低电到Full/恒流精度、高功率/快充与长稳待验。离线候选与后续整合顺序见[充电交接](../../reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)。旧逆向按组合。[当前进度](../../reference/charging-management-20261023/PROGRESS.md)、[完整要求](../../reference/charging-management-20261023/ADAPTATION-REQUIREMENTS.md) |
| 摄像头 | Linux v7.3.1 标准 V4L2/CAMSS/CCI 路径已刷入并通过三个最终启动周期：IMX471 前摄、IMX319 后摄、S5K3M5 长焦、S5KGW1 主摄均自动 probe；每周期四路各抓到两张完整、非全零、无饱和且帧间有变化的私有 RAW，共 24 帧。r21 最终 boot `d5cfa04f…` 再次通过四路各两张 RAW。Selection API 修复后的 boot `668b8d20…` 中 IMX471/S5K3M5 的 crop/default/bounds 全部成功，`cam -l` 无 EINVAL，四路 RAW 与 libcamera 四路单帧再次通过；抓完 CAMSS `suspended`、MMCX 128、`taint=0` | `poweroff` 再上电已通过，但拔除外部供电后手动电源键冷启动未验；绝对画质、LSC/AWB/AF、录像、热功耗、多摄同时流、长期共享 lease 和 camera ICP userspace 仍待。场景 RAW 与校准不公开；历史私有 stack 证据保留在 `reference/kernel*` |
| 其它传感器 | 204第二boot自动真实readiness及三个DSP/SensorProxy三Has通过，首轮文件服务就绪失败清理offline仍保留；200新boot三项Has与标准Claim/Release通过，早期门控后SLPI running；187 A.11实际三轴204/202/197及五种CLI通过；230真正树内2abde新启动taint0，实测保活1→2→1、五流67/44/9/10/1与活动Wayland用户Claim；189 FastRPC freezer等待修复与自动服务已部署，连续三轮驻留45.2至45.3秒、success3/fail0/RTC3，醒后四种CLI与原daemon身份保持；三轮后真实active Wayland UID10000 Claim/Release通过；2026-11-05 kernel `#2` 的 `sensor-power` `rproc_subdev` 已真机通过，start/stop、两路电顺序、SSC readiness、SensorProxy/桌面和冷启动均验证 | 188原PM崩溃保留；普通信号重试/freezer竞态、共享池stop/start/reclaim−22及SSR仍未解决。269板级安装矩阵及桌面重新发现传感器后，用户确认整屏自动旋转正常；首次整机启动顺序、3D安装/精度及更广运动回归仍待验。亮暗响应与绝对精度、接近日常、长期跨boot/多SKU/长稳仍开放；平放undefined/被动lux0至8不等于这些验收 |
| 后置闪光灯 | PM8150L flash0/flash1 双通道按一个白色 LED 暴露，使用主线 `leds-qcom-flash`、LED flash class 和 V4L2 flash；最终 DTB `b244b3f1…`、boot `5b4dd487…`、FAT `c99c690e…` 由 Linux 侧成对写入并回读。`white:flash` 实体和 V4L2 控制存在，亮度 26/255、torch 200 mA、faults 0；开灯 RAW 均值 +130%，0% 饱和，普通重启前后完整门禁和 taint 0 | 拔除外部供电的物理按键冷启动、重复冷启动、长时间热升和持续高负载功耗仍未验收；不要把普通重启写成冷启动 |
| 蜂窝通话与数据 | MPSS、QRTR/QMI、ModemManager/IPA基础接入；207两次普通启动modem running，原厂MCFG目录自动复制且mdtime可读；PDC活动平台/软件存在、无pending、1平台/25软件列表通过；用户确认未插SIM，当前Power1、failed/原因2与条件一致。2026-11-05修复Plasma启动期D-Bus自动激活与OpenRC重复拉起ModemManager的竞争；干净单实例启动后`qmicli`读取真实ID，`mmcli -L`自动出现Modem/0 | 269保存到一次modem watchdog并伴随整机意外重启，原因和与Snapshot的关联未明。mcfg.tmp仍零字节，整体配置初始化与真实SIM注册/数据/通话/SMS/UIM仍待验；221再次只读得到两槽no-atr/absent/active，与191相同，该历史结果不作为插卡故障证据，真实业务待有卡；电源策略/SSR/冷启/休眠开放 |
| GNSS定位 | [260](../../reference/kernel260/README.md) 普通桌面GNSS-only室外300秒280次更新，其中262次严格校验、时间戳新鲜且随更新变化，默认LOW、无额外HIGH客户端；GPS去重最多9颗TRACK/46.7dB-Hz，自动上线/LOW_POWER回收与设置恢复。[258](../../reference/kernel258/README.md) 原生287份SATELLITE坐标/286秒、去重12颗TRACK/44.4dB-Hz/PGA+2；原厂256去重10颗/45.5dB-Hz/PGA+2。GeoClue10项/电源14项回归及实机四轮开停通过 | 旧采集器拒绝Accuracy=0，18次余下更新未分类，不能直接计丢星或实测精度；本轮PGA未观测。259在OFFLINE下失败不能作ONLINE对照。完整5MiB连续内存/SCM provider、室内PGA/RF根因、冷启/PM/长稳/绝对精度仍开放。位置/启动/辅助未单变量控制，初始化未证明相同 |
| 指纹 | 无主线认证 API；Android 19781 源只有 `goodix_fp` 的电源/复位/中断和 `ldo7-supply`，没有 Linux 数据总线 | HAL 采集/匹配走签名 TEE applet 与 QSEECom；主线没有对应等效层 | 不在 OS DTB 暴露 vendor compatible，也不伪造 `spidev`/input 设备；功能认证链未验收，这是当前不可标准化的极薄硬件块 |
| NFC | NCI控制器初始化、上电查询、关闭和重复通过 | RF读卡/标签、时钟请求及eSE业务，尚无真实读卡验收 |
| 振动 | AW8697驱动与电气检查通过。`Realme X2 Pro AW8697 haptics`已由板级udev规则标记为`FEEDBACKD_TYPE=vibra`；标准feedbackd D-Bus `TriggerFeedback(button-pressed)`返回id2且`EndFeedback`成功 | 实际振幅、时长和桌面触感未由用户确认；跨启动和长稳待验 |
| 蓝牙 | 234实际RTS模型三变体16/2、16/0、16/2及H4回放8例通过；暂时诊断取得2个完整phase5回包/UART对应/1301事件无丢失，未复现错误。扫描因预上电属性Not Powered未完成，已恢复原185模块/config/helper/keys/787文件、最终健康0；裸RTS模型不满足真实锁契约，未部署功能补丁。[234](../../reference/kernel234/README.md)。205两次普通启动/8轮上下电/4次重注册未复现phase5，206已恢复原185模块/helper/BlueZ并核对keys；这不是phase5修复。204 RX wake/sleep已部署；首轮前9/45.14秒RTC PM后13、错误增量0，第二boot启动重组0，外部BT事件唤醒未验；首轮phase5仍1。200新boot startup及8秒只扫描发现10设备、退出恢复、重组增量0；185功率脉冲前导NUL及短写/flow修复保持；当时原扫描错误1/候选0、3模式响应及开启状态s2idle/延后扫描通过；189三个传感器PM窗内重组增量0、密钥保持。2026-11-09 `samurai-bluetooth-host 0.1.0-r0` 已安装；boot `071abbb5…` 上 `bnep/uhid/uinput` 自动加载，`/dev/uhid`、`/dev/uinput`、BNEP socket、BlueZ `hci0` 和 777 模块完整 gate 通过 | 189旧boot出现phase5/3.2Mbps/chunk13/partial0/firstff重组1，区别于旧phase2前导00，需继续修复。外部 PAN/HID 对端、配对/连接/音频、冷启动和带业务 suspend 未验收；没有对端证据时不能声称 PAN/HID 业务通过 |
| Wi-Fi | 200新boot自动connected，早期管理端点超时保留；2.4/5GHz通信已有回归；189三轮传感器PM的第1/3轮观察约5.33/0.53秒关联5180，最终5180，未手工重绑驱动；2026-11-08 当前 boot 5GHz/VHT 866.7 Mbit/s 连续关联约79分钟，beacon loss 0，power save off；2026-11-09 r21 boot 完成 1810 个 SSH 样本/1820.51 秒、最大间隔 1.01 秒，DMS 地址 `PRIVATE_WIFI_MAC` 在多次启动一致；原厂 decompiled DTB 的 WiFi 节点与蓝牙共用四个 PMIC regulator，当前 DTB 已绑定；ath10k 只把原厂未使用的 `vdd-3.3-ch1` 退回 dummy | 第2轮35秒窗内仍未关联，之后又执行第3轮PM，不能称第2轮自行恢复；185立即醒后2秒检查失败仍保留。冷启动、完整休眠通信恢复及长期稳定性仍开放；不能把 dummy ch1 直接当成断连根因 |
| 普通USB与OTG | USB 2.0 Type-C；2026-11-09 r21 boot 在主板直连口完成双向 `64K/256K/1M/4M` 各三轮 24/24、1798.828 秒 NCM 心跳；UDC `configured`、`usb0` carrier 1、`qmult=20`；严格 host-key Wi‑Fi/NCM SSH 和最终 runtime/Plasma 门禁通过。2026-11-10 的 sink DTB 和 dual DTB/config 已离线构建，语义差分只落在 PM8150B Type-C/DWC3 层 | 旧 Genesys 扩展 Hub 端口仍会停在 `VID_0000&PID_0001`/Code 43；当前 Image 缺 `DWC3_DUAL_ROLE`/xHCI，OTG host 尚未实现；Windows 网卡复位权限、USB 归档尾部中断、IPv6、EUD 接收/退出、Linux 主机、更长时间空闲和多次冷启动待验收。DWC3 suspend 仍会 soft-disconnect；默认由标准 `ssh-session-open` 持有 sleep 锁。设备本轮 SSH 握手前关闭，Type-C 候选尚未真机验证 |
| 触摸 | 用户确认可解锁、操作应用，原生驱动工作 | 边缘/方向/多触点与休眠后恢复、长稳 |

已有基础还包括UFS访问、CPU调频表、PMIC温度与按键/EUD。CPU高频压力、UFS持续负载、整机功耗、冷启动及系统休眠唤醒仍需跨功能验收；不能以驱动注册或短窗口健康代替日用完成。

USB规格更正：用户指出此前误列USB3；[X2 Pro规格](https://www.gsmarena.com/realme_x2_pro-9904.php)标注USB Type-C 2.0。[厂商规格](https://www.realme.com/in/realme-x2-pro/specs)只标注Type-C接口，没有声明USB3；SoC具备更高速度控制器不代表整机接口支持该速度。

## 下一阶段顺序

2026-11-09 起，Wi‑Fi/NCM/SSH、相机 Selection API 和 PM8150L
闪光灯/V4L2 已从当前阻塞项转为已持久化基线；boot/FAT 由 Linux 侧
成对写入并回读，普通重启后的完整 runtime、四路 RAW、网络和闪光灯
控制/光学测试通过。蓝牙 `samurai-bluetooth-host 0.1.0-r0` 已安装并在
重启后自动加载，BNEP socket、UHID/uinput 和 777 模块 gate 通过；NFC
使用官方 `neard`/`neard-openrc` 与签名 `samurai-platform 5-r22`，
`nfc0`、服务、D-Bus 属性、电源和轮询启停通过。私有 `status` sysfs
删除已编入最终 Image `f8d89621…`/FAT `1f4bbb30…`，boot 和 DTB
保持不变；Linux 侧成对刷入后两次普通重启通过，ALSA、input/ff、
四路相机、flash/V4L2、蓝牙、NFC 和网络均未回归。当前设备在
一次 `loginctl` suspend 尝试后离线，不能用这次失败证明 thin-private
有回归；需先物理唤醒并保存日志，再用已通过的 `rtcwake` 方法复测。
音频、传感器、显示和相机 userspace 继续按无需现场附件的顺序推进；
NFC 标签、外部 PAN/HID 对端、指纹、SIM、高压充电和拔电冷启动保留为
有现场条件时的独立验收。

按当前用户目标和检查点选择下一功能；先复用原厂提取物与公开仓库实现，缺项再测量，不以所有功能完成为单项迭代的前置条件。显示交接白屏/花屏与已测开关屏已有验收证据；音频发声/拾音、停止和所测短时s2idle恢复也已通过。后续补音频SSR/重复长时PM、耳机和音质，同时推进充电控制保护、完整传感器、实体摄像头、蜂窝业务与GNSS冷启/PM/长稳；GNSS原生258及桌面260室外定位已通过。指纹、NFC读卡和外围设备功能保持待办。Wi-Fi/USB独立休眠告警保留，和触摸一起补稳定性；蓝牙继续区分已验收的扫描与尚未验收的连接/音频，整机冷启动和长期可靠性仍需验证。

参考证据：[显示140至145](../../sessions/145-dsi-deployment-and-session-closeout.md)、[SLIMbus139](../../sessions/139-slimbus-unsubmitted-tx-unwind-and-live-boot.md)、[DMIC104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md)、[充电132](../../sessions/132-persistent-mp2650-real-boot-and-complete-rootfs.md)、[充电138](../../sessions/138-readonly-charger-recharge-threshold.md)、[实体camera前的TPG126](../../sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md)、[传感器112](../../sessions/112-startup-sensor-registry-and-reboot.md)、[Wi-Fi128](../../sessions/128-wcn3990-pairwise-key-delete-and-5ghz.md)、[蓝牙130](../../sessions/130-standard-bluez-discovery-and-startup-integration.md)。

阶段151以前的完整状态记录已经移入[历史快照](../../archive/HARDWARE-STATUS-through150-2026-10-13.md)，不再把旧136 GPU故障或145设备状态写作当前待办。
