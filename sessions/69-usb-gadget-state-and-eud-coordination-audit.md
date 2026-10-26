# 69. USB 功能未配置，EUD 共存边界只读核对（2026-10-10）

**COM14 当前归 Windows；Linux 正常在 initramfs shell，但普通 USB 功能尚未配置。**
手机端保存的新 dmesg 69499 字节完整导出，设备 SHA256、gzip CRC 和长度均通过。
本轮只读设备状态/日志和源码，没有配置或绑定 gadget、切换 EUD、刷机或修改内核。
Android 上 EUD 与 ADB 只能二选一是用户提供的实际线索，本轮未启动 Android 重测。
它不能自动扩大为 Linux 或 EUD 硬件的必然限制。

证据及离线核对：[reference/kernel69](../reference/kernel69/README.md)。

## 69.1 当前连接与设备状态

先核实三节点 9501/9500/9505 均 OK，9505/COM14 位于 6-5，usbipd 显示 Shared，
未 Attached；上一 owner 的退出0和 Closed COM14 已收到，才用既有 Windows 终端。
全程单一 owner，每次 finally Close/Dispose。没有 USBIP attach、控制节点写入、
com-up/com-off、reset、掩码、ZLP、节奏或 Windows 驱动变更。

五份设备侧保存/压缩副本均有完整起止标记、设备 SHA256 和 gzip CRC：

| 保存文件 | gzip 字节 | 原始字节 | 结果 |
|---|---:|---:|---|
| /tmp/K69U：USB/configfs 基线 | 282 | 547 | 通过 |
| /tmp/K69V：UDC 状态 | 112 | 153 | 通过 |
| /tmp/K69L：完整 dmesg | 15676 | 69499 | 通过；手机 wc 长度一致 |
| /tmp/K69D：运行模式/设备树/初次绑定查询 | 277 | 411 | 通过；其中 readlink 用法错误保留 |
| /tmp/K69R：逐条驱动绑定查询 | 84 | 115 | 通过 |

K69L gzip SHA256：`28ad635dfebf39904397cff93a588aaa70eac1de3f18ed68dacb428f8d7d2dda`；
解压 SHA256：`6e93b2d0c10668edc31eb18eb4e80ffba0f5759dddd681778d74cd49a6521f64`。
保存文件仍在手机 tmpfs，后续可直接导出同一原件，没有给残缺的实时前缀补字。

boot_id 仍为 afbbf870-b998-43d8-ab3d-42b3c68c0122，taint=0，#60 未重启。
UDC a600000.usb 已注册，state=not attached、current_speed=UNKNOWN；maximum_speed
为 super-speed-plus，这只是配置上限，不是实测协商速度。configfs 已挂载，但
/sys/kernel/config/usb_gadget 为空。USB role/Type-C 类目录为空。
实际 DT 的 dr_mode=peripheral，USB_DWC3_GADGET=y、DUAL_ROLE/HOST 未开；
不能把空 role-switch/Type-C 目录视为新的内核失败，OTG/host 仍未实现/验收。

## 69.2 EUD 与普通 USB 的边界

[Qualcomm 官方主机库](https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/src/ctl_api.cpp)
明确描述 eud_connect_usb/eud_spoof_attach：芯片软件处理 VBUS attach 通知后，
MSM 普通 USB 经 EUD 连接 PC。[Qualcomm binding](https://android.googlesource.com/kernel/msm/+/f382bd87e7398d1d55b1b84211de3d44ae88cf11/Documentation/devicetree/bindings/soc/qcom/qcom,msm-eud.txt)
描述片内 mini hub 与 extcon 通知客户端。因此没有依据认定硬件天然必须与 ADB 互斥。
这只是设计/软件流程依据，不是本机同时传输的实测。

同机型原厂公开树固定在 9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，
drivers/soc/qcom/eud.c 转发 VBUS/extcon，dwc3-msm.c 接收对应 USB 通知。
当前自定义 tty eud.c 保留 RX53 方法并仅启用 RX，不转发 VBUS/charger。
主线 qcom_eud.c 使用 USB role switch，当前 CONFIG_USB_QCOM_EUD=m，实际 initramfs
没有加载它；不能在同一 CSR/IRQ 上并行加载控制驱动来尝试“修复”。

**实际运行的是 dwc3-qcom-legacy。** 当前 DT 的 qcom,dwc3 匹配 legacy，
逐条 readlink 独立确认父设备绑定 dwc3-qcom-legacy、子设备绑定 dwc3。
legacy 读取子节点 dr_mode；非 host 模式主动启用 VBUS override，且支持可选 extcon。
初始审查 dwc3-qcom.c 的新 glue 路径已纠正；新文件只匹配 qcom,snps-dwc3。
因此“缺少 EUD VBUS 转发”尚不是已证实根因，固定 peripheral/override 的影响需一并考虑。

Linux 上存在类似互斥表象的可能性，当前最确定的是没有配置普通 USB 功能。
未绑定 gadget 时没有普通 USB 枚举，不能证明 PHY 损坏、EUD 抢占或共存失败。
原计划临时 CDC ACM 功能验证在用户提出 Android 线索后暂缓，未创建 configfs 对象。
本轮按用户的日志读取范围收束，不关闭 EUD 或新增 EUD 实验。

## 69.3 当前异常与优先级

| 优先级 | 校验后的证据 | 处理范围 |
|---|---|---|
| P1 | configfs 已挂载、UDC 存在，但没有 gadget；普通 USB 流量/共存未验 | 确认可保存日志和回退的普通 USB 功能路径，不因无枚举直接改内核 |
| P2 | PM8009 ldo2 无 ldof2 cmd-db 地址 | 对照本机原厂 PMIC/固件资源，不删除节点静音 |
| P2 | RPMh 读回 ret=-95；QMP data-lanes 无方向/模式；aux_bridge=-ENODEV | 区分固件不支持读回、继承的 USB3/DP 图与本机接线，不能当显示全面不可用 |
| P3 | PSCI PC mode=-3、无 KASLR seed、初始 console 警告和 init tail EINVAL | 保留影响边界；随后 EUD shell/用户态成功，不是 panic 证据 |

完整 dmesg 从0秒开始，有6个 UFS SCSI disk，未见 panic/Oops、旧映射 WARN 或 CPU7
2956800 的 Voltage update failed。CPU7 修复证据仍见 session68；本轮未进行高频负载测试。
燃料计/充电/原生面板/触摸/GPU/Wi-Fi 仍须本机证据，不能由这份日志宣称完成。

## 69.4 手机 Linux 的 USB 调试方式

postmarketOS 通常使用 USB 网络加 SSH，电脑看到网络接口，通过 TCP/IP 登录，
传文件使用 SCP/SFTP。2025-12-28 的[官方 USB 框架说明](https://postmarketos.org/edge/2025/12/28/USB-framework-rework/)
介绍 GNOME Mobile/Phosh/Plasma Mobile 的 usb-moded：默认仅充电，用户选择合适模式后
才能使用网络/SSH/MTP；并非插线就必定提供调试访问。SSH 服务也须启用。
传统 USB 网络地址常为手机172.16.42.1、电脑172.16.42.2，见
[项目的 USB 网络实现说明](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/3819)。
地址和 UI 模式须以实际镜像为准。

SSH 提供日常 shell/文件/端口转发；Linux 日志用 dmesg 和实际日志系统读取。
启动早期尚无网络时，initramfs debug shell、串口/EUD 等另有用途。
ADB 是 Android 的独立协议/服务，当前诊断 initramfs 未提供 adbd/sshd 或 gadget。
后续普通 USB 网络/SSH 适合作为常用通道，EUD 保留早期排查能力；这不是当前已实现状态。
USB_Network/SSH wiki 页面遇站点保护，记录读取限制，未绕过；官方公告和项目实现说明可读。

## 69.5 失败记录、保存与提交

BusyBox readlink 只接受单一 FILE，第一次多路径调用打印 usage；不是驱动未绑定。
保留 K69D 原件，再逐条查询保存 K69R，才获得真实绑定。源代码查找的不存在文件/
通配路径错误、公开 GitHub 本地项目 commit 的404与 lore 的403均不算硬件错误。
十次有界 owner 的原始帧/文本/发送事件逐字节核对；每次仅 startup Ctrl-U 重试一次，
数据帧全部只发一次，实际 END 和 shell 提示符出现后完成关闭。没有新增 EUD 传输工具。

末次三节点 OK、COM14 Windows/Shared/not Attached、无已知采集 owner/临时日志/ETW。
原 Windows 驱动/终端/eudtool、Image/config/init、EUD/earlycon 源码和回退哈希保持。
TOP_CFG0x11、整帧、RX53 console/IRQ、F1、原生/兼容终端保留；F1 本轮未触发。
不刷任何分区，Android 和全部数据保留；rootfs 限制继续以 ROOTFS-PRESERVE-ANDROID 为准。
本轮为日志/功能前提和来源审查进展，不是新内核修复或共存通过。证据和交接只推 fork/master。
