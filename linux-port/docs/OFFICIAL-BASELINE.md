# 官方基线审计：postmarketOS 与 realme RMX1931

审计日期：2026-11-08。范围是 postmarketOS 官方 `pmaports` 的
`main` 与当前发布分支 `v26.06`，以及 realme 官方
`realmeX2Pro-kernel-source`。本文只记录可追溯的官方设计与本地差异；
没有把 Android vendor 私有接口当成主线 API，也没有把一次在线会话
当成冷启动验收。

## 1. 来源、版本、许可证和适用性

| 来源 | 版本/提交 | 日期 | 许可证 | 适用层 | 结论 |
| --- | --- | --- | --- | --- | --- |
| postmarketOS pmaports `main` | `b5810eb2f3b24ce380a00c54569236f5559f78b1` | 2026-11-08 | GPL-3.0；`LICENSE` SHA-256 `53927bd0b739d38c87a0a82236fd9b070c2dfff11c0c119be50372005d5047ad` | L5–L7 | 当前服务边界和 `unudhcpd`/sleep-inhibitor 设计的主参考 |
| postmarketOS pmaports `v26.06` | `2a8621d64d91647f7362eac59e7cdc091ff2bba8` | 2026-10-23 | GPL-3.0 | L5–L7 | 当前发布分支；服务文件与 main 大体一致，但 `postmarketos-base`/UI 版本较旧 |
| postmarketOS pmaports `v25.12` | `70624fdb1b26e77ef1e2c1ced074c91e9e0c1dff` | 2026-08-05 | GPL-3.0 | L5–L7 | 上一发布分支，仅记录分支尖端；本轮未把其包内容当成当前基线 |
| realme X2 Pro kernel source | `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` | 2020-02-20 | 根 `COPYING` 为 GPLv2；文件含 GPL-2.0 SPDX；GitHub metadata 为 Other/NOASSERTION | L2–L3 | Android vendor `4.14.83` 内核，只作板级配置和硬件事实参考 |

pmaports 远端会重定向到 `gitlab.nura.eco`；提交和文件内容以本地
`b5810eb2…` 校验为准。realme 仓库的根 Makefile 是
`4.14.83`，不是当前的 `7.3.1-rmx1931-samurai-v731` 主线移植。
realme 仓库的 `COPYING` SHA-256 为
`af8067302947c01fd9eee72befa54c7e3ef8a48fecde7fd71277f2290b2bf0f7`。
仓库 metadata 的 `Other/NOASSERTION` 不等于根许可证文本；发布和再分发
时必须保留根 GPLv2 通知，并逐文件检查 SPDX/copyright。

### RMX1931 对应目录

`arch/arm64/boot/dts/Makefile` 列出多个 project 目录。当前证据把
`arch/arm64/boot/dts/19688/` 作为 RMX1931 的高可信匹配：

- `sm8150-sdx50m-mtp-overlay.dts` 和 `sm8150-mtp-overlay.dts` 都写着
  `oppo,prjversion = <1 19688>`；
- `19688` 目录包含本机实际使用的 Samsung `SOFEF03F_M`
  `1080x2400@90fps` 面板 DTSI；
- `19371` 目录不包含该面板选择；
- 内核 DTS 没有直接写 `RMX1931` 产品字符串，所以这是“项目号 + 面板 +
  SM8150 平台”的交叉匹配，不应说成厂商字符串已经直接确认。

关键文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `arch/arm64/boot/dts/Makefile` | `b47e02d37e109167ebccc2427fff65099c9f42c82a6f2eaacb56a54de8d24f10` |
| `arch/arm64/boot/dts/19688/Makefile` | `f8f96e3184e769a5ab9dce0a2d4b3534dcfed77d92e7828f2e1c3c4643a939e2` |
| `19688/sm8150-sdx50m-mtp-overlay.dts` | `897df693386d400005e837deb7d5c7d1a19543d7595b6f8ce5b6032b24ee4b53` |
| `19688/sm8150-mtp-overlay.dts` | `af3d9ce2afb1031e89f1586b309b6aa9d4be85bee631e2499abefbf9ca4b4418` |
| `19688/sm8150-usb.dtsi` | `7a0cfb877e91bce2118b0a650acc2bde3377bc7e410e9ad0c2147735691d8dab` |
| `19688/sm8150-pmic-overlay.dtsi` | `9e2a55af50741c585098b8feaaa6f0d2e6518be5160ef2c3f66a1d63705d628a` |
| `19688/...SOFEF03F...90fps-cmd.dtsi` | `b3c5992ff79ab430a7117153e86121bded5d64401b94a54faa323ee22b1bfe90` |

## 2. L2–L7 提取结果

| 层 | 官方做法 | 本地实现 | 差异/取舍 | 证据 |
| --- | --- | --- | --- | --- |
| L2 板级描述 | realme DTS 给出 PM8150B、PM8008、CCI、CSI PHY、panel、pinctrl、regulator、充电和外设接线 | `linux-port/dts/v731/sm8150-samurai.dts` 用主线 DTS 描述同一组板级事实 | 只采用可验证的寄存器/电源/GPIO/panel/camera事实；不复制 `qcom,msm-bus`、Android extcon 或厂商私有节点 | realme `19688` 文件哈希；本地 DTB contract |
| L3 内核驱动 | vendor 4.14 使用 `qcom,dwc-usb3-msm`、厂商 camera/充电和 Android extcon 路径 | 主线 `qcom,sm8150-dwc3`、CAMSS/CCI、V4L2、power_supply、DRM、input、netdev | vendor 只作为 board facts；底层接口必须是主线已有模型/API；板级 glue 只保留真实硬件差异 | `L3-*` 文档、补丁、真机 runtime |
| L4 UAPI | Android HAL/ioctl 不能作为通用平台 ABI | UDC/configfs、media controller、V4L2、netdev、DRM/KMS、power_supply、evdev、sysfs | 不导出私有 ioctl；用标准 class/device property 发现设备 | DTB contract、media/video/power_supply 运行时证据 |
| L5 服务 | pmaports `postmarketos-base` 管 `sshd`、`unudhcpd.usb0`、boot/default runlevel；base-ui 管 NetworkManager、wpa_supplicant、BlueZ、ModemManager、SensorProxy、tinydm、sleep-inhibitor | `samurai-radio`、`samurai-usb`、`samurai-ssc` 是板级薄服务；NetworkManager/sshd 独立启动；电源策略使用官方 `sleep-inhibitor` | 本地保留板级 radio/USB 启动和 DHCP，但不再安装或替换通用睡眠策略 | `postmarketos-base-openrc.post-install`、`check-settings-provenance.sh` |
| L6 包与配置 | pmaports 的 base/base-ui 子包负责发行版边界；tinydm 默认没有可选硬件 `rc_need` | `samurai-platform 5-r24`、`samurai-desktop 4-r15` 已安装；`4-r16` 候选删除 `samurai-powerkey` 桥 | 包名本地化，服务边界与官方对齐；调试策略移出正式包 | APK、manifest、install hook、来源检查 |
| L7 桌面/交互 | Plasma Mobile 使用 tinydm、KWin、KScreen、PowerDevil、标准 portal；elogind `HandlePowerKey=ignore`，PowerDevil 移动端默认 `ToggleScreenOnOff` | `samurai-desktop` 只保留 tinydm 会话配置和旧 cgroup 清理；电源键/DPMS 交回 KWin/PowerDevil | 不把桌面栈写进 L3；只保留 SOFEF03F 面板亮度时序薄层 | Plasma Mobile check、KWin/KScreen 运行态、KWin 包反汇编 |

### 2.1 OpenRC、Wi‑Fi、NCM 与 SSH 边界

pmaports `main` 的 `postmarketos-base-openrc.post-install`：

- 创建 `/etc/init.d/unudhcpd.usb0` 并加入 `boot`；
- 将 `sshd` 加入 `default`；
- 将 `udev`/`udev-trigger`/`udev-settle` 加入 `sysinit`；
- 将 `logbookd`、`hwclock`、`bootmisc` 等加入启动级。

本地设备当前 `rc-status -a` 显示 `sshd` 在 `boot`，而不是官方
`default`。这是本地为了尽早提供 SSH 的排序选择，不改变 TLS/密钥/端口
语义；NetworkManager 和 sshd 都不依赖 `samurai-radio`/`samurai-usb`
硬启动。

pmaports `main` 的 rootfs `unudhcpd` init 默认：

```text
server 172.16.41.1
client 172.16.42.2
```

initramfs 阶段的默认是 `172.16.42.1/172.16.42.2`。本板当前仍使用
`10.42.0.1/24` 和保留的 `169.254.42.1/16`，因为已有主机
`known_hosts`、路由、脚本和测试依赖这些地址。没有把它们和设备离线
时的服务边界修改混在一起；迁移必须作为单独候选，在设备在线时验证
主机路由、首次 SSH 身份和回滚。

pmaports `v26.06` 的 `postmarketos-base-openrc.post-install` 仍是旧的
initramfs/USB 网络路径，没有 main 的 `unudhcpd.usb0` 注册。因此不能
把 `v26.06` 的地址和 main 的 rootfs 地址混写成一个“官方默认”。

### 2.2 sleep-inhibitor

pmaports main 的默认 `/etc/sleep-inhibitor.conf` 只有：

- `ssh-session-open`；
- `apk-running`。

5-r24 起，正式系统直接使用这份官方 `/etc/sleep-inhibitor.conf` 和
官方 `sleep-inhibitor` 服务，不再安装 `/etc/samurai/sleep-inhibitor.conf`
或 `samurai-sleep-inhibitor`。`samurai-usb-sleep-guard` 已移到
`linux-port/debug/sleep-policy/`，只在显式调试时手动挂载，不作为
OpenRC 服务。这样正式系统的自动休眠语义与 postmarketOS 基线一致。

5-r20 仍然保留的部分是：`NetworkManager`、`sshd`、ModemManager 不硬
依赖板级 `samurai-radio`/`samurai-usb`。这是为了避免一次 USB/radio
失败拖垮整个桌面和 SSH；不代表 USB NCM 在系统 suspend 后仍然保持
链路。活跃 SSH 仍由官方 `ssh-session-open` 插件保护；手动
`loginctl suspend` 不属于官方策略。

### 2.3 tinydm / Plasma Mobile

pmaports 的 `rootfs-etc-conf.d-tinydm` 只提供：

```text
rc_cgroup_cleanup="yes"
AUTOLOGIN_UID=10000
```

没有 `rc_need`/`rc_after` 指向 ModemManager、Bluetooth 或
`iio-sensor-proxy`。4-r16 起本地不再写这份文件，只清理历史
4-r7..4-r10 注入的精确旧值；正式配置由 `postmarketos-base-ui` 拥有。

历史 4-r10 曾留下 `rc_need="dbus elogind"` 和
`rc_use="iio-sensor-proxy samurai-sleep-inhibitor"`；4-r16 会删除这些
板级调试依赖。官方 tinydm 自己的 init 脚本已经使用
`need localmount`、`want dbus elogind`，不需要本地再补硬依赖。

### 2.4 realme vendor 的可用边界

realme `19688` 的 USB 节点仍以 `qcom,dwc-usb3-msm`、`extcon =
<&pm8150b_pdphy>, <&eud>` 和厂商 bus scaling 为主；摄像头节点使用
厂商 CCI/CSI/电源私有属性。可用的信息是：

- SM8150 USB 控制器/PHY 的基址、时钟和板级 GPIO；
- PM8150B/PM8008 regulator 和 VBUS/充电接线；
- SOFEF03F panel 的时序、DSC 和背光事实；
- camera CCI/CSI/供电和模组 GPIO；
- NFC、触摸、马达等板级 pinmux。

不可直接复用：

- Android `ioctl`、HAL、vendor extcon 状态机；
- vendor camera/充电节点作为主线 UAPI；
- Android bus/regulator 私有属性替代主线 provider；
- `4.14.83` 的驱动 ABI 替代 `7.3.1` 主线 API。

## 3. 本地实现与官方基线的差异

| 项目 | 官方基线 | 本地当前 | 取舍 |
| --- | --- | --- | --- |
| USB 网络 | main rootfs `unudhcpd`，`v26.06` initramfs 路径，地址阶段不同 | `dnsmasq` `10.42.0.1/24`，保留 `169.254.42.1/16` | 保持 known_hosts/路由兼容；迁移另立候选 |
| SSH 启动 | `sshd default` + 发行版 OpenSSH | `sshd default`，独立于 USB/radio | 与官方 runlevel 对齐，未引入私有协议 |
| NCM 传输 | 主线 DWC3 模型 | 主线 `tx-fifo-resize`；无 OOT 模块 | 修复 4 MiB 传输失败；未把 FIFO 当私有传输层 |
| USB 睡眠 | 官方默认只有 SSH/apk sleep lock | 5-r24 起同官方；carrier-only guard 仅 debug 外部脚本 | 空闲允许 suspend；长期 USB 维护用测试进程持有的临时锁 |
| Wi‑Fi | base-ui 选择 wpa_supplicant，NetworkManager 管设备 | wpa_supplicant/NetworkManager + 板级 `samurai-radio` 启动固件/TFTP/RMTFS | 固件/NV 启动保留板级，网络管理仍是发行版服务 |
| 桌面 | base-ui、Plasma Mobile/tinydm | 同名 tinydm/Plasma，加 90Hz panel 亮度时序 quirk | 电源键/DPMS 已交回 KWin/PowerDevil；桌面元包和会话接口保持标准 |

## 4. 当前验收证据（2026-11-08）

已完成的实机链路：

- 签名包 `samurai-platform-5-r20.apk`
  SHA-256 `c7481c502cfb0b59dbb9fbeb64a37914b6edace0aad32a4d86a01d24d7a4dcdc`；
- 签名包 `samurai-desktop-4-r10.apk`
  SHA-256 `931ccbdde64d5e25ce735fbb7750de57f88f66ad85e70728560b23092c129043`；
- 手机端 `apk verify` 通过，`apk add --no-network` 安装成功；
- 普通重启后 boot ID `849bdfb8-1adf-420f-ba1c-bcded615f25b`，
  `taint=0`；Wi‑Fi `22/tcp` 在主机侧约 52.8 秒恢复；
- `check-boot-service-boundaries.sh` 所有非 USB 检查通过；仅
  `UDC state` 和 `usb0 carrier` 失败；
- `verify-v731-final-runtime.py --usb-fifo --skip-camera` 仅
  `udc_configured` 失败；内核 release、boot/FAT 哈希、模块布局、
  CAMSS idle、NFC、power_supply、DSI、Wi‑Fi 和 OpenRC 服务通过；
- `check-plasma-mobile.sh` 通过，包括单 KWin/Plasma、电源键、Wayland、
  KScreen、portal、ModemManager、BlueZ、GeoClue、SensorProxy 和
  sleep-inhibitor 边界；
- `check-desktop-boundaries.sh` 通过，确认 USB idle guard 默认不持有
  sleep lock。

尚未完成：

- USB NCM 当前没有主机枚举；Windows 没有新的手机 USB attach，
  `usb0` 无 carrier，UDC `default`/link `Suspend`。一次
  `dwc3-qcom` unbind/bind 没有恢复；需要直插主板 USB 口和已知数据线
  复测；
- 真正的断电冷启动尚未执行；普通 `reboot` 不能替代外部断电；
- 最终 camera-final boot 尚未刷入；当前运行的是
  `usb-fifo-standard-rootfs` 组合；
- 多次冷启动、不同主机/线材、长期 USB 空闲和 suspend 恢复仍是开放项；
- 主机侧 NCM 的 30 分钟矩阵只能证明历史 FIFO 路径，不证明当前这次
  无枚举故障。

## 5. 可复现检查

```sh
apk verify /tmp/samurai-platform-5-r20.apk
apk verify /tmp/samurai-desktop-4-r10.apk
apk add --no-network /tmp/samurai-platform-5-r20.apk \
  /tmp/samurai-desktop-4-r10.apk
sh linux-port/scripts/check-boot-service-boundaries.sh
sh linux-port/scripts/collect-network-startup-timeline.sh
python3 linux-port/scripts/verify-v731-final-runtime.py \
  --usb-fifo --skip-camera
sh linux-port/scripts/check-plasma-mobile.sh
```

这些命令在 USB 未接入时，边界检查会故意报告 UDC/carrier 失败；不能
把该失败算成 NetworkManager 或 SSH 失败。需要 NCM 验收时，先把
USB 直插到主板端口并确认 Windows 出现 `0525:a4a1`，再运行 NCM
稳定性矩阵。

## 6. 未决事项

1. 直插 USB 后重新采集 Windows PnP/USBHub 端口状态，确认是 Hub/线材
   还是手机 DWC3/PHY 路径；不要先改主线 USB API。
2. 通过 fastboot 或受控分区路径刷入最终 camera-final boot，完成 boot
   回读和普通重启/断电冷启动；当前没有可用 fastboot 设备。
3. 在设备在线时把 `unudhcpd` 迁移做成独立候选，先保留旧
   `10.42.0.1/24`/known_hosts，再验证地址、DHCP、SSH 和回滚，不能和
   r20/r10 服务变更合并。
4. 把本轮 r20/r10 包、源码归档、启动时间线和运行时证据写入
   `source-lock.json`，并更新 `00-INDEX.md`。
