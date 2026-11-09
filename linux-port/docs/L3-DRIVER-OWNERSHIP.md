# L3 驱动 Ownership 清单（草案）

整理日期：2026-11-09。

本文是 [L2-L4 收敛计划](LAYER-CONVERGENCE-PLAN.md) 的 L3-01 交付物。
它只盘点“哪个驱动组归谁、使用什么公共接口、当前有什么调试债”，
不修改内核、不刷写、不证明功能已经验收。

## 1. 使用规则

- 模块名、release 和哈希以当前部署 manifest/源码锁为准；本文的模块名
  只是检索入口，不是跨启动的身份。
- 通用 SoC 驱动与板级数据分开：板级接线应回到 DTS/板级数据，通用
  驱动只保留通用资源模型。
- `sensor-power`、面板复位等已知交叉项先标出，不在 L3-01 阶段删除。
- 任何行为变化都走 G2；需要改 `boot`/DTB 的走 G3，不能混在同一轮。

## 2. Ownership 表

| 驱动组 | 当前入口/证据 | 公共 UAPI | 板级部分 | 首轮动作 |
| --- | --- | --- | --- | --- |
| CPU/GPU | DRM MSM、Adreno A6xx、Mesa 用户态；270 审计记录 GPU/相机故障边界 | DRM/KMS、drm fd、标准 GPU ioctl | SoC OPP/电源、GPU carveout | 只记录当前模块/固件版本；不先改 GPU 频率或电源 |
| 启动/UEFI | EDK2 BDS、Linux EFI stub、标准 `\EFI\BOOT\BOOTAA64.EFI`/GRUB 候选 | UEFI LoadImage/StartImage、EFI stub、标准 EFI removable-media path | BootShim、BDS 直启回退、DTB FFS、面板 handoff/EUD 关闭 | 候选已离线构建但未刷入；持久 UEFI 变量仍未实现 |
| 显示/DSI | MDSS/DSI、`samsung,sofef03f-m` 面板、背光 class；60/90 Hz 补丁 0016/0017 | DRM/KMS mode、backlight class | 面板时序、DSI lane、背光 GPIO/rail | 保持 60/90 模式不变，把面板/背光板级数据列成 DTS→驱动的资源表 |
| UFS/存储 | UFS LUN、GPT、4 KiB 逻辑扇区；UFS 电源继承/板级覆盖 | block、UFS/SCSI、GPT | UFS rail、PCIe/PHY 资源、LUN 使用 | 只读记录 LUN/GPT/容量/模块；不先改 UFS 电源或分区 |
| 输入/按键 | `syna,rmi4-i2c` 触摸、PM8150 GPIO 按键、evdev | input evdev、`KEY_*` | 触摸 reset/IRQ/VIO、按键 GPIO/pinctrl | 记录设备名、event 节点和唤醒属性；不改键值 |
| USB gadget | DWC3/UDC、configfs、CDC NCM；主线 `tx-fifo-resize` + `qmult=20`；`samurai-usb`；官方 `sleep-inhibitor` | USB gadget/configfs、net device、UDC class、DWC3 device property | UDC 名、USB PHY、串号来源 | `samurai-platform` 5-r21 已安装；5-r23 候选删除调试用 sleep guard。主板直连口上双向 24/24、1798.828 秒 NCM 心跳、1810 样本 Wi‑Fi 心跳和完整 runtime 通过；旧 Genesys Hub、Linux 主机、OTG、多次冷启动和长期空闲仍待 |
| Wi-Fi | WCN3990/cfg80211、NetworkManager；板级 Wi-Fi helper/firmware 服务 | cfg80211、rfkill、net device | 固件路径、NV/MAC、供电/时钟 | 区分通用无线栈和板级 helper；不先重排 firmware load 顺序。r21 boot 1810 样本心跳通过；固件仍报 invalid permanent MAC，板级 helper 在关联前应用同机 DMS 地址 `PRIVATE_WIFI_MAC`，未写永久 MAC |
| 蓝牙 | WCN3990 BT UART、BlueZ、HCI；主线 `BNEP/UHID/uinput` 模块候选 | BlueZ/HCI、rfkill、UART、BNEP socket、UHID/uinput 字符设备 | UART pins、firmware、MAC | `samurai-bluetooth-host 0.1.0-r0` 两构逐字节一致、两轮隔离安装和符号/ABI 检查通过；设备安装、autoload、PAN/HID 对端、重启和冷启动仍待 |
| 音频 | ASoC machine driver `realme,samurai-audio`、Q6AFE/Q6ASM/Q6ADM、MAX98937、ALSA UCM | ALSA PCM/control、UCM、jack | machine driver、speaker amp、mic/headset GPIO | 保留 machine driver；把 UCM/路由和桌面策略分开 |
| 传感器 | SSC/FastRPC、SensorProxy、IIO 用户入口、`sensor-power` | remoteproc prepare/unprepare、IIO（若使用）、iio-sensor-proxy D-Bus | `sensor-power` 电压顺序、SLPI/FastRPC 资源 | genpd 方案已否决；极薄 `rproc_subdev` sequencer 已在真机 `#2` 通过启动/停止、readiness 和冷启动；SensorProxy 现为 SSC 软依赖，保留旧 `state` 只读兼容 |
| 振动 | AW8697 输入/反馈、feedbackd udev | input/ff、feedbackd D-Bus | I2C/GPIO/供电、机型识别 | 保留 udev 规则；只记录振幅/时长接口，不改手感参数 |
| 充电/电池 | `mps,mp2650`/`mp2650_charger`、`ti,bq28z610`/`bq27xxx`、标准 `power_supply`；历史 `samurai-*` 仅为显式 opt-in | power_supply、thermal、USB Type-C | charger/OTG/APSD、电阻/温度、fuel gauge | 标准绑定已通过；先统一只读属性清单，充电状态机和高压策略留到后续 |
| 相机 | CAMSS、CCI、CSIPHY/CSID/VFE、四路 sensor/镜头模块、libcamera/IPA | V4L2、media controller、V4L2 subdev、Selection API、videobuf2、libcamera | CCI/CSI endpoints、PM8008、sensor probe/power、MMCX 性能态 | 四路 RAW 标准路径已在最终 boot 的三个周期通过；Selection API 和 V4L2 flash 链接已收口，v4l2 final boot 的普通重启后完整 runtime/RAW 门禁再次通过；断电冷启动与 ISP/画质仍待 |
| 闪光灯 | PM8150L `leds-qcom-flash`；flash0+flash1 合成白色 emitter | LED flash class、V4L2 flash subdevice | 仅 DTS `led-0` 的通道/电流/超时与 S5KGW1 `flash-leds` 链接；无私有驱动 | Linux 侧 boot/FAT 成对写入、24 资源 contract、774 模块 runtime gate、200 mA torch 光学 RAW、faults 0 和普通重启均通过；冷启动与长时间热升待验 |
| modem/GNSS | MPSS remoteproc、QRTR/QMI、IPA、ModemManager/GeoClue | QRTR、QMI、WWAN、GNSS/GeoClue | modem firmware/MCFG、QRTR 地址、GNSS 服务 | 保留服务顺序；先区分通用 QMI/QRTR 和板级 helper |
| NFC | NCI 控制器初始化、上电/关闭；Alpine `neard` 用户态候选 | NFC/NCI 字符设备/协议栈、`org.neard` D-Bus | I2C/IRQ/供电、eSE | 5-r22 包离线签名和探针已准备；设备安装、`nfc0`、服务状态和真实读卡仍待 |
| 指纹 | 尚无 Linux 功能验收 | 未建立 | SPI/供电/安全环境/认证链 | 不纳入 L3 首轮；另立安全/驱动任务 |

## 3. 相机模块的当前身份

当前 v7.3.1 相机身份以
[v731 source-lock](../dts/v731/source-lock.json) 为准。旧的
[camera/kernel/source-lock.json](../camera/kernel/source-lock.json)
属于 k363/ICP 历史组合，不应拿来判断 v7.3.1 部署状态。

v7.3.1 标准候选包含：

- `qcom_camss`、`i2c_qcom_cci`、`v4l2_cci`；
- `s5k3m5`、`s5kgw1`、`imx319`、`imx471`、`lc898219xi`；
- `qcom_pm8008`、`qcom_pm8008_regulator`；
- 内核通用 `videobuf2` 与 V4L2 core。

历史 ICP 用户态/内核实验不属于该候选。

v7.3.1 标准候选进一步把四路 sensor 和镜头接入同一媒体图：
IMX471 前摄、IMX319 后摄、S5K3M5 长焦、S5KGW1 主摄和 LC898219XI
使用 V4L2 subdev、CCI 与标准运行时电源接口。最终相机 boot
`9b9be136...` 在 `c97a0a52-60e7-41fc-bf49-59c7ff0d3fc5` 和普通重启后的
`9b93d2c2-7bd9-45aa-90a2-1af71c32d6b3`，以及 `poweroff` 后的
`35915162-7912-4cb2-a766-88691cbd44bc` 三个周期中，每路各取得两张完整
RAW，共 24 帧；关流后 CAMSS `suspended`，MMCX 从 384 回落，`taint=0`。
证据与复现入口见
[STANDARD-ARM64-V731](STANDARD-ARM64-V731.md#camera-acceptance)。

后续 Selection API 收口把 IMX471 的模拟 crop 与 S5K3M5 的
`CROP/CROP_DEFAULT/CROP_BOUNDS` 补齐，`cam -l` 不再出现
`Unable to get rectangle` 或内核 `EINVAL`。两个 in-tree 模块替换后，
普通重启 boot `668b8d20-d22f-44d9-908c-68070eea0147` 通过四路 RAW、
libcamera 四路单帧和完整 runtime 门禁；773 模块归档中只有
`imx471.ko` 与 `s5k3m5.ko` 相对上一验收树发生变化。

蓝牙候选不修改 Image/DTB：只在同一 release 的隔离构建树启用
`BT_BNEP=m`、`UHID=m`、`INPUT_UINPUT=m`，并把三个 `intree=Y` 模块
放入 `samurai-bluetooth-host 0.1.0-r0`。包内没有服务、trigger、
modules-load 覆盖或私有接口；Alpine 官方 `bluez.conf` 继续负责
`uinput/uhid`，`bnep` 由主线 `bt-proto-4` 别名按需加载。离线证据见
[BLUETOOTH-HOST-MODULES](BLUETOOTH-HOST-MODULES.md)。

这些名称只对该锁定的 source stage/release 生效。任何 L3 改动都必须
同时记录 source-lock、实际 release、模块哈希和部署状态；不能只拿
一个 `.ko` 文件名判断兼容。

## 4. UEFI 启动候选的归属

[`source-lock.json`](../dts/v731/source-lock.json) 的
`uefi_standard_boot_candidate` 记录了一条离线构建链：
`BdsDxe -> \EFI\BOOT\BOOTAA64.EFI -> GRUB standalone -> Linux EFI stub`。
标准启动器负责设置 `root=PARTLABEL=userdata` 和 DTB；BDS 只保留
`\EFI\BOOT\BOOTAA64.EFI` 优先与 `/Image` 直启回退。

候选 boot `c5e856d5…`、FAT `7c326ad4…`、BDS `f5cf8a7e…`、
GRUB `97ef936d…`。GRUB 以 `search_fs_file` 按 `/Image` 发现卷，不依赖
`KERNEL` 卷标；卷标只为兼容既有工具保留。它尚未刷入，GRUB 在手机上的
执行、文件发现、root 挂载和回退均未验收；持久 UEFI 变量仍未实现。
离线验证脚本是
[`verify-uefi-standard-candidate.py`](../scripts/verify-uefi-standard-candidate.py)。

## 5. 私有新增文件边界

`git diff 09455be..824dc0a` 新增的运行时文件可以按下面分类。它们不是
“已经进入上游”的证明；保留它们是因为当前主线正式版没有可直接替代的
通用驱动或 SoC 数据。

| 新增文件 | 现阶段原因 | 归类 |
| --- | --- | --- |
| `drivers/power/supply/mp2650_charger.c` | 主线没有可直接匹配的 MP2650 充电器驱动；当前使用标准 `power_supply` 类 | 薄电源驱动，后续可尝试上游化 |
| `drivers/gpu/drm/panel/panel-samsung-sofef03f.c` | 本机面板时序/初始化；使用标准 DRM panel 模型 | 板级面板描述 |
| `drivers/input/misc/aw8697-samurai.c` | AW8697 触觉控制器；使用 input/ff 和 feedbackd UAPI | 薄板级输入驱动 |
| `sound/soc/codecs/max98937-samurai.c` | MAX98937 编解码器/功放；使用 ASoC/ALSA | 薄板级 codec |
| `sound/soc/qcom/samurai-audio.c` | machine driver、DAI link 和板级路由；使用 ASoC machine API | 板级 ASoC glue |
| `drivers/misc/samurai-sensor-power.c` 及其头文件 | SLPI sensor rail 的上电顺序；使用 regulator/remoteproc 公共接口 | 薄板级电源时序 |
| `drivers/net/ipa/data/ipa_data-v4.1.c`、`ipa_reg-v4.1.c` | SM8150 IPA v4.1 的 SoC 资源数据；不属于 RMX1931 私有硬件 | SoC 支持缺口，优先级高于手机私有层 |
| `drivers/media/i2c/lc898219xi.c`、`s5kgw1.c` 及 sensor 表头 | 当前主线没有完整匹配的镜头/传感器支持；使用 V4L2 subdev/CCI | 相机薄驱动，后续可上游化 |
| `drivers/phy/qualcomm/phy-qcom-snps-femto-v2-window.h` | SNPS Femto PHY 的窗口辅助定义；需与公共 PHY 驱动合并审查 | SoC PHY glue |
| `arch/arm64/boot/dts/qcom/sm8150-samurai*.dtsi`、`samurai-sensor-power-data.dtsi` | 板级 GPIO/regulator/CSI/CCI/panel 接线 | DTS 板级数据 |
| `Documentation/.../samsung,sofef03f-m.yaml`、`mps,mp2650.yaml` | 公共绑定文档，不是私有调用路径 | 可上游化文档 |
| `msm_dsi_trace.h`、`include/trace/events/drm_panel.h` | 显示诊断/trace，不改变硬件接口 | 诊断辅助 |

因此，当前私有层不是一个新的传输栈；它主要是 DTS、SoC 数据、板级
regulator/电源顺序和少数没有主线等价驱动的外设。NFC 使用主线 NXP NCI
驱动，指纹因缺少主线安全采集/匹配链而不伪装成标准设备。

2026-11-09 的静态审计把剩余私有层量化为 14 个 C/H 逻辑文件（116,007
字节）和 11 个 DTS/表文件（265,454 字节）；未发现私有 ioctl、
`copy_{to,from}_user`、Android/Binder 或自定义命令号。平台补丁
`09455be..824dc0a` 的 96 个变更文件中也没有新增此类入口。审计同时发现
MAX98937 和 AW8697 各自暴露了一个不属于 ASoC/input UAPI 的只读
`status` sysfs；对应删除补丁为
[`0004-samurai-remove-private-status-sysfs.patch`](../patches/v7.3.1/0004-samurai-remove-private-status-sysfs.patch)，
并已编入最终 Image `f8d89621…`/FAT `1f4bbb30…`；boot
`5b4dd487…` 和 flash/V4L2 DTB `b244b3f1…` 保持不变。Linux 侧成对
刷入后两次普通重启均通过 777 模块完整门禁，三处自定义 `status`
节点消失，标准 ALSA/input/ff、四路相机、闪光灯、蓝牙、NFC 和网络
均保持通过，`taint=0`。唯一明确保留的旧只读兼容面是
`samurai-sensor-power` 的 `state`，用于运行时门禁核对两路 rail，不能
作为新的私有写接口。`reference/` 中读取旧 `/status` 的脚本是历史证据
快照，不得在新 Image 上当作当前门禁重新执行。

## 6. 充电模块的历史身份与当前边界

Linux v7.3.1 标准镜像使用 DTS `mps,mp2650`、`ti,bq28z610` 和内核
`power_supply` 类，不加载下列私有模块。历史
[samurai-charging APKBUILD](../packages/samurai-charging/APKBUILD) 仅保留
为旧 k363 内核的显式 opt-in 实验：

- `samurai-mp2650.ko`；
- `samurai-usb-input.ko`；
- `samurai-gauge-protection.ko`；
- `/usr/sbin/samurai-charging` 和 OpenRC init。

它们与旧内核 release 绑定，不能把模块复制到 v7.3.1 后假设可用，也不由
`samurai-platform` 自动依赖或启动。
充电行为/温度/高压策略仍按 `HARDWARE-STATUS` 的未验收范围处理。

## 7. 已知跨层项

以下项目在 L3 表中出现，但需要 L2 或 L4 协同：

| 项目 | 当前问题 | 迁移条件 |
| --- | --- | --- |
| 面板 GPIO6 reset | 公共 pinctrl 与板级复位逻辑交叉 | 面板节点/DTS 资源表稳定后再动 |
| `sensor-power` | 私有 platform sysfs + C 内默认电压策略 | 标准化阶梯见 [L3-02 边界](L3-SENSOR-POWER-BOUNDARY.md)；genpd 真机失败后改用 `qcom,rproc` + `rproc_subdev`，旧 `state` 降为只读兼容；真机 `#2` 已通过，规范 OS DTB 仍需 G3 |
| UDC `a600000.usb` | 标准 class 但旧脚本只看一个名字 | 已改为列表发现/单 UDC 回退，源级 7 用例通过；旧名仍优先兼容，包安装待 G4 |
| bring-up flags | `clk_ignore_unused` 仍可能掩盖资源依赖 | 已生成只给 `gcc_cpuss_rbcpr_clk` 加 `CLK_IS_CRITICAL` 的完整离线候选，并用干净源码对象重建证明 flags 变化；未刷入，必须单独启动、运行时钟检查和回退 |

## 8. L3 验收入口

L3-01 完成时，每个驱动组至少要有：

- 实际模块/源文件或明确的源码锁；
- 使用的公共 UAPI；
- 板级资源列表；
- 当前调试开关/参数；
- 当前证据链接和未验收范围；
- 一个可以单独回退的候选范围。

没有这些信息，不应进入 L3-02 的行为修改。
