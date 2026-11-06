# L3 驱动 Ownership 清单（草案）

整理日期：2026-11-05。

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
| 显示/DSI | MDSS/DSI、`samsung,sofef03f-m` 面板、背光 class；60/90 Hz 补丁 0016/0017 | DRM/KMS mode、backlight class | 面板时序、DSI lane、背光 GPIO/rail | 保持 60/90 模式不变，把面板/背光板级数据列成 DTS→驱动的资源表 |
| UFS/存储 | UFS LUN、GPT、4 KiB 逻辑扇区；UFS 电源继承/板级覆盖 | block、UFS/SCSI、GPT | UFS rail、PCIe/PHY 资源、LUN 使用 | 只读记录 LUN/GPT/容量/模块；不先改 UFS 电源或分区 |
| 输入/按键 | `syna,rmi4-i2c` 触摸、PM8150 GPIO 按键、evdev | input evdev、`KEY_*` | 触摸 reset/IRQ/VIO、按键 GPIO/pinctrl | 记录设备名、event 节点和唤醒属性；不改键值 |
| USB gadget | DWC3/UDC、configfs、CDC NCM；`samurai-usb`/sleep guard | USB gadget/configfs、net device、UDC class | UDC 名、USB PHY、串号来源 | UDC 发现已通过源级离线测试；保持现有 gadget 身份和 `MaxPower=500`，包安装/运行态待 G4 |
| Wi-Fi | WCN3990/cfg80211、NetworkManager；板级 Wi-Fi helper/firmware 服务 | cfg80211、rfkill、net device | 固件路径、NV/MAC、供电/时钟 | 区分通用无线栈和板级 helper；不先重排 firmware load 顺序 |
| 蓝牙 | WCN3990 BT UART、BlueZ、HCI；板级蓝牙 helper/firmware | BlueZ/HCI、rfkill、UART | UART pins、firmware、MAC | 记录 HCI/固件/服务入口；不改 power sequence |
| 音频 | ASoC machine driver `realme,samurai-audio`、Q6AFE/Q6ASM/Q6ADM、MAX98937、ALSA UCM | ALSA PCM/control、UCM、jack | machine driver、speaker amp、mic/headset GPIO | 保留 machine driver；把 UCM/路由和桌面策略分开 |
| 传感器 | SSC/FastRPC、SensorProxy、IIO 用户入口、`sensor-power` | remoteproc prepare/unprepare、IIO（若使用）、iio-sensor-proxy D-Bus | `sensor-power` 电压顺序、SLPI/FastRPC 资源 | genpd 方案已否决；极薄 `rproc_subdev` sequencer 已在真机 `#2` 通过启动/停止、readiness 和冷启动；保留旧 `state` 只读兼容 |
| 振动 | AW8697 输入/反馈、feedbackd udev | input/ff、feedbackd D-Bus | I2C/GPIO/供电、机型识别 | 保留 udev 规则；只记录振幅/时长接口，不改手感参数 |
| 充电/电池 | `samurai-mp2650`、`samurai-usb-input`、`samurai-gauge-protection`、BQ28Z610、power_supply | power_supply、thermal、USB Type-C | charger/OTG/APSD、电阻/温度、fuel gauge | 先统一只读属性清单；充电状态机和高压策略留到后续 |
| 相机 | CAMSS、CCI、CSIPHY/CSID/VFE、sensor 模块、libcamera/IPA | V4L2、media controller、V4L2 subdev、libcamera | CCI/CSI endpoints、PM8008、sensor probe/power | 只整理通用/板级边界；不把 ISP/画质工作混入本轮 |
| modem/GNSS | MPSS remoteproc、QRTR/QMI、IPA、ModemManager/GeoClue | QRTR、QMI、WWAN、GNSS/GeoClue | modem firmware/MCFG、QRTR 地址、GNSS 服务 | 保留服务顺序；先区分通用 QMI/QRTR 和板级 helper |
| NFC | NCI 控制器初始化、上电/关闭；尚无真实读卡 | NFC/NCI 字符设备/协议栈 | I2C/IRQ/供电、eSE | 维持现状；先补消费者和真实读卡证据 |
| 指纹 | 尚无 Linux 功能验收 | 未建立 | SPI/供电/安全环境/认证链 | 不纳入 L3 首轮；另立安全/驱动任务 |

## 3. 相机模块的当前身份

[相机源码锁](../camera/kernel/source-lock.json) 是当前最具体的模块清单，
包含：

- `qcom_camss`、`i2c_qcom_cci`、`v4l2_cci`；
- `s5k3m5`、`s5kgw1`、`imx319`、`imx471`、`lc898219xi`；
- `qcom_pm8008`、`qcom_pm8008_regulator`；
- `qcom_camss_icp_a5_core`、`camss_icp_a5_m2m`、`v4l2_mem2mem`、
  `videobuf2_dma_sg`。

这些名称只对该锁定的 source stage/release 生效。任何 L3 改动都必须
同时记录 source-lock、实际 release、模块哈希和部署状态；不能只拿
一个 `.ko` 文件名判断兼容。

## 4. 充电模块的历史身份与当前边界

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

## 5. 已知跨层项

以下项目在 L3 表中出现，但需要 L2 或 L4 协同：

| 项目 | 当前问题 | 迁移条件 |
| --- | --- | --- |
| 面板 GPIO6 reset | 公共 pinctrl 与板级复位逻辑交叉 | 面板节点/DTS 资源表稳定后再动 |
| `sensor-power` | 私有 platform sysfs + C 内默认电压策略 | 标准化阶梯见 [L3-02 边界](L3-SENSOR-POWER-BOUNDARY.md)；genpd 真机失败后改用 `qcom,rproc` + `rproc_subdev`，旧 `state` 降为只读兼容；真机 `#2` 已通过，规范 OS DTB 仍需 G3 |
| UDC `a600000.usb` | 标准 class 但旧脚本只看一个名字 | 已改为列表发现/单 UDC 回退，源级 7 用例通过；旧名仍优先兼容，包安装待 G4 |
| bring-up flags | `clk_ignore_unused` 等仍可能掩盖资源依赖 | 最后逐项删除，每项单独冷启动和回退 |

## 6. L3 验收入口

L3-01 完成时，每个驱动组至少要有：

- 实际模块/源文件或明确的源码锁；
- 使用的公共 UAPI；
- 板级资源列表；
- 当前调试开关/参数；
- 当前证据链接和未验收范围；
- 一个可以单独回退的候选范围。

没有这些信息，不应进入 L3-02 的行为修改。
