# 普通USB网络与SSH（session72）

> 2026-11-13 当前 boot 重新暴露了一个独立的枚举故障：手机 UDC 停在
> `default`/high-speed，主机未完成 SET_CONFIGURATION，Windows 没有
> present 的 `0525:a4a1` 实例。Wi‑Fi SSH 正常；`usb-signaller` 不再
> 因 10 秒超时降级到 charging-only，恢复服务也可做有界软重连/DWC3
> 重绑，但两次尝试后主机仍未 configured。这不是 NCM/OTG 验收通过，
> 证据和剩余判别步骤见
> [USB-ENUM-RECOVERY-20261113](USB-ENUM-RECOVERY-20261113.md)。

> 2026-11-12 当前运行时已切换到 postmarketOS 标准 `usb-signaller` +
> NetworkManager + `unudhcpd` + `umtprd` 栈：默认 Developer 地址是
> `172.16.42.1/16`（DHCP 客户端 `172.16.42.2`），模式由
> `com.meego.usb_moded` D-Bus 管理；历史 `samurai-usb` 的
> `169.254.42.1` 和 `10.42.0.1` 内容仅用于理解旧路径。当前证据和
> 未验收边界见 [PMOS-USB-20261112](PMOS-USB-20261112.md)。

当前诊断initramfs自动提供CDC NCM和公钥SSH。手机169.254.42.1/16，Windows系统
UsbNcm自动绑定并使用APIPA地址；无需改主机默认路由。独立重启后无需host com-up
也能认证SSH。EUD仍可用于早期日志和F1，两条路径共存。

本机专用密钥/known_hosts在E:\edk2-samurai-out\kernel72。使用
reference/kernel72/usb-ssh.ps1执行命令、scp-usb.ps1传文件（显式-O）。
SSH端口22只绑定USB地址，密码认证已在编译和运行时禁用。主机密钥是手机唯一密钥，
仅保留在本地实际initramfs/构建产物，客户端私钥只留主机；两者不进入Git。

## 2026-11-09 当前结论（直连 USB）

把手机从 Genesys `05e3:0610` 扩展 Hub 的端口 3 改接到笔记本主板直连口
后，Windows 重新枚举出手机的 NCM 和 fastboot，`VID_0000&PID_0001`
Code 43 只保留为旧 Hub 端口的历史状态，不再是当前故障。

直连后仍发现第二个独立问题：连续 4 MiB device-to-host 传输偶发停顿
约 15–31 秒，随后 `Broken pipe` 或 SSH 超时；失败时 UDC 始终
`configured`、DWC3 link `On`、runtime PM `active`，手机 `usb0` TX
停止增长后会自行恢复。根因是 NCM 在途请求队列过浅，Windows UsbNcm
短暂停止 bulk-IN 轮询。`samurai-platform` 5-r21 在标准 configfs
`ncm.usb0` 上设置 `qmult=20`，不引入私有传输层；普通重启后由
`/usr/sbin/samurai-usb` 自动写入，当前 boot 的 UDC、carrier 和
`qmult` 均正确。最终长测结果见下方“NCM 稳定性现状”。

r21 同 boot 最终结果：双向 `64K/256K/1M/4M` 各 3 轮 24/24、
0 失败，心跳 1798.828 秒（798 个 2 秒样本），NCM verdict
`010be162…`；同一 boot 的 Wi‑Fi 独立 1810 样本/1820.51 秒，最大
采样间隔 1.01 秒，verdict `b3dd4e29…`。普通重启后的启动脚本自动
恢复 `qmult=20`，不是手工热改；真正断电冷启动和 Linux 主机仍待验证。

## 2026-11-11 UDC 卡住与 Windows Code 43

USBIN 唤醒实验后出现过一次真正的手机侧控制器卡住：充电口仍报告
`online=1`，但 UDC 是 `not attached`、DWC3 link 是 `Disconnected`；
Windows 连续 reset 后把设备停掉，报 Code 43
`请求 USB 设备描述符失败`。仅执行 UDC `soft_connect=connect` 或
`rc-service samurai-usb restart` 没有恢复。

完整控制器重绑后恢复：

```sh
echo a600000.usb > /sys/bus/platform/drivers/dwc3-qcom/unbind
sleep 1
echo a600000.usb > /sys/bus/platform/drivers/dwc3-qcom/bind
sleep 3
rc-service samurai-usb restart
```

恢复后的实际门禁：

```text
UDC configured, high-speed
link On
Windows 0525:a4a1 / UsbNcm Host Device: OK, Problem 0
Windows NCM DHCP 10.42.0.2
usb0 carrier 1, qmult 20
30 s 状态采样无重新枚举
USB NCM SSH 到 10.42.0.1 成功
```

因此这类 Code 43 不能只清 Windows phantom 设备。先看手机 UDC 和 link：
如果 UDC 不是 `configured`，必须重绑 DWC3；只重连 gadget 不足以清掉
controller 内部状态。USBIN 测试脚本已改成结束时强制重绑 DWC3 并重启
`samurai-usb`，避免把测试态留给主机。

## 2026-11-12 postmarketOS 自动恢复

当前运行时由标准 `usb-signaller 0.4.3-r4` 管理 gadget 和模式，
`unudhcpd 0.5.0-r2` 提供 DHCP，`samurai-platform` 6-r3 及之后的
6-r5/6-r6 只保留
SM8150 DWC3 的有界恢复：

- 只有本次电缆会话曾达到 `UDC=configured` 且 `usb0 carrier=1` 才武装；
- `online=1` 但链路持续丢失 12 秒时，执行一次 DWC3 unbind/bind；
- 曾成功枚举过且 VBUS 0 -> 1 后 20 秒仍未配置时，执行一次
  `reason=reattach` 的 DWC3 unbind/bind；
- 从 `host_mode` 或其他非 NCM 模式切回 Developer/Tethering 后，
  若 UDC 已 `configured` 但主机没有拉起 carrier，等待 10 秒后执行
  一次 `reason=mode_transition` 的同一有界恢复；
- 6-r6 按 configfs gadget generation 识别短 `host_mode` 会话，并把
  恢复自身重建的 generation 写回基线，避免尝试预算被自己无限复位；
- 每会话最多连续两次，成功后通过 usb-moded D-Bus 恢复原模式，并
  重启对应的标准模式服务；
- 最后写入公开 UDC `soft_connect` 的 `disconnect`/`connect`，让主机
  重新枚举并重新执行 DHCP；
- 链路稳定 300 秒后刷新尝试预算；
- 只插充电器、从未枚举的会话不会触发无意义重绑。

日志：`/var/log/samurai/usb-recover.log`；状态：
`/run/samurai-usb-recover/`。

实测人为 `ip link set usb0 down` 后：

```text
13:51:17 LINK_LOST state=configured carrier=
13:51:29 RECOVER_BEGIN attempt=1 reason=link_lost ...
13:51:36 RECOVER_OK attempt=1 reason=link_lost state=configured carrier=1
```

boot ID 不变；Windows 在 `13:51:32` 重新取得 DHCP
`172.16.42.2/24`，DHCP server `172.16.42.1`，
`USB\VID_0525&PID_A4A1` 和 `UsbNcm Host Device #5` 均为
Problem 0。该路径解决的是控制器恢复后的主机旧 NCM/DHCP 状态，
不表示 suspend 期间链路保持在线。

### 5-r30 历史

`samurai-platform 5-r30` 已把上述人工重绑改成有界自动恢复：

- 原先只重启板级 `samurai-usb`；
- 6-r1 起改为 usb-moded D-Bus + 标准 usb-signaller 模式服务；
- 6-r2 起增加恢复后的 UDC `soft_connect` 重枚举。

标准 Type-C + USB 唤醒部署后已完成 3×15 秒、1×60 秒和追加
8×15 秒 `s2idle`。每次 resume 后 Windows 重新枚举，UDC/NCM
在 12–20 秒内恢复；8×15 秒 soak 的 `suspend.success` 为 18→26，
主机自行重枚举，没有触发强制重绑，Windows
`USB\VID_0525&PID_A4A1\62BC28A1` 保持 Problem Code 0。物理拔线
唤醒和长期反复插拔仍未验收，见
[`USB-TYPEC-WAKE-20261112.md`](USB-TYPEC-WAKE-20261112.md)。

随后追加 16×30 秒 `s2idle`：16/16 轮睡满 32 秒，
`suspend.success` 28→44，UDC/carrier 每轮恢复，恢复服务没有触发
强制重绑。另做 20 轮保持 VBUS 的 UDC `soft_connect`
disconnect/connect：20/20 在 3–4 秒内恢复；主机以
`CM_Get_DevNode_Status` 每 100 ms 采样 1629 次，所有 present
样本均为 `problem=0`，设备节点恰好出现 20 次消失/重建，没有
Code 43，也没有 `RECOVER_BEGIN`。
测试后 32 MiB NCM 上传 1.146 秒并通过哈希。该测试不能替代物理
Type-C 插拔唤醒。

## 2026-11-08 历史失败分层

当前 boot `849bdfb8-1adf-420f-ba1c-bcded615f25b` 的失败点不在
NetworkManager、`unudhcpd`/`dnsmasq`、`sshd` 或 NCM 地址层：
`mp2650-input` 报告 `online=1`（约 4.475 V / 200 mA），但
`usb0` 没有 carrier，DWC3 UDC 状态是 `default`，debugfs link state 是
`Suspend`。Windows 48 小时系统事件中没有新的手机 USB attach；当前
`1A40` Hub 的端口 3/4 分别是音频设备和 IR 摄像头，不是手机。一次受控的
`dwc3-qcom` unbind/bind 也没有改变 `default`/`Suspend`。因此这一次首先
是主机枚举前链路或物理接线问题，不能归因于 NCM 网络服务。

历史上至少有三个独立故障类别，不能合并成一个“USB 坏了”：

1. **ABL 暖启动枚举失败**：从 Linux 热重启进 fastboot 时，Windows 偶发
   看到 `USB\VID_0000&PID_0001` + Code 43 / Port Reset Failed。根因在
   ABL 的暖启动 USB 路径，干净解绑 NCM 后再 `RESTART2` 是待硬件重复
   验证的 workaround；重新进一次 fastboot 会重新初始化控制器/PHY。
2. **NCM 大传输中断**：旧 DTB 在 4 MiB device-to-host 传输后出现
   `Broken pipe` 或短时 SSH 超时。主线 DWC3 `tx-fifo-resize` 属性修复
   了该路径，并已在普通重启后的 30 分钟双向矩阵中通过；这不是 USB3
   问题，当前链路是 USB 2.0 high-speed。
3. **空闲 suspend 断链**：DWC3 在系统 suspend 时撤销 gadget pull-up，
   主机无法唤醒一个没有活跃 SSH 会话的 USB NCM 链路。5-r20 按官方
   sleep-inhibitor 边界只让 `ssh-session-open` 默认持锁；仅充电连接允许
   suspend。长时无人值守 NCM/SSH 矩阵应使用标准
   `elogind-inhibit --what=sleep --mode=block`；板级 carrier guard 只在
   确实需要无 SSH 活动的 USB 维护时显式启用。不能把系统 suspend
   误判成 KDE 或 NCM 的随机掉线。

当前故障需要先用**主板直连 USB 口 + 已知数据线**复测，并保留 Windows
PnP/USBHub 端口状态；只有直连仍持续出现 `default`/`Suspend`，才继续
追查手机 USB-C 座、DWC3 PHY 或 QSCRATCH 复位路径。若直连正常，则优先
检查旧 Hub、线材和热重启交接，而不是改动主线 USB API。

2026-11-09 的端口级复查把范围进一步缩小了：

- Windows 上历史上正常的手机 NCM
  `USB\VID_0525&PID_A4A1\62BC28A1` 与当前失败的
  `USB\VID_0000&PID_0001\7&3B715170&0&3` 都位于同一个
  Genesys `05e3:0610` Hub 的 3 号口；前者已变成 phantom，后者仍是
  Code 43。
- 直接向该 Hub 查询端口状态，3 号口返回
  `USB_CONNECTION_STATUS=2 (DeviceFailedEnumeration)`；Hub 描述符为
  4 口、自供电，当前 `HubIsBusPowered=0`，不是整个 Hub 掉电。
- 手机侧 UDC 仍绑定 `a600000.usb`，`state=default`、
  `current_speed=high-speed`；DWC3 已 active，USB2 link state 为
  `U3/Suspend`。本轮启动的 dmesg 中没有主机完成
  `SET_CONFIGURATION`，5 秒采样中 DWC3 IRQ 计数也不增长。
- 因此失败发生在 NCM 网卡、DHCP、sshd 和 NetworkManager 之前，属于
  主机端口把手机判为“已连接但枚举失败”。这个 Hub 端口状态不会因为
  手机 Linux 重启而自行清除；宿主普通重启也未必给下游 Hub 断电。

当前能复现的是“首次枚举失败后，端口长期停在失败态”的机制；最早一次
触发究竟是 ABL 暖启动、线材/接口瞬断，还是主机 Hub 端口的单次复位
异常，仍必须用直连主板口和已知数据线做对照。不能把
`DeviceFailedEnumeration` 直接写成某个内核 USB 驱动的 bug：手机侧
根本没有走到 NCM 配置阶段。

rootfs 中 `/usr/sbin/samurai-usb start` 由
`/etc/init.d/samurai-usb` 异步调用；`status` 可查看 UDC、USB 状态和
`usb0` 地址。脚本等待主线 UDC 就绪，创建设备串号来自
`/sys/devices/soc0/serial_number` 的单一 NCM 函数，再启用 `usb0`。
rootfs 不再启动 Dropbear，SSH 由发行版 `sshd.pam` 提供；当前
`169.254.42.1:22` 只绑定 USB NCM。

`samurai-platform` 5-r17 已包含这一 rootfs 版本（NCM/sleep guard 沿用
5-r16），并保留 `MaxPower=500`
重新绑定修复；它同时保留 `169.254.42.1/16` 调试地址，并用标准 `dnsmasq`
在 `10.42.0.1/24` 提供 DHCP 与保留旧链路本地路由的 classless option 121。
历史 initramfs 仍使用独立的 devpts/Dropbear 路径，两者不要混装到同一个启动阶段。

官方 pmaports `postmarketos-base-openrc` 的做法是使用
`unudhcpd.usb0`（boot runlevel），不依赖本板的 `dnsmasq`。地址要区分
启动阶段：pmOS initramfs 的 `unudhcpd_host_ip`/client 默认是
`172.16.42.1`/`172.16.42.2`，而 rootfs 的 Alpine `unudhcpd` init
脚本默认是 `172.16.41.1`/`172.16.42.2`，可由
`UNUDHCPD_SERVER`/`UNUDHCPD_CLIENT` 覆盖；不能把它简化成单一的
`172.16.42.1/24`。本板暂时保留 `10.42.0.1/24` 与
`169.254.42.1/16`，是为了兼容已经写入主机 `known_hosts`、路由和测试
脚本的地址；切换到 `unudhcpd` 会同时改变主机地址和首次 SSH 身份，
必须在设备在线时作为单独候选迁移并重新做主机侧验收，不能和设备离线
时的启动策略修改混在同一个包内。

2026-11-12 的运行时已完成该迁移：rootfs 使用 `unudhcpd 0.5.0-r2`
和 `172.16.42.1/16`。该本地包只增加 RFC 2131 BROADCAST flag
处理；Windows NCM 在 gadget 重枚举后若请求广播回复，OFFER/ACK
会发往 `255.255.255.255:68`，否则保留原有单播/ARP 路径。

`samurai-platform` 5-r24 起正式包不再安装 carrier-only guard，也不再
安装 `samurai-sleep-inhibitor`。正式系统直接使用 postmarketOS 官方的
`/etc/sleep-inhibitor.conf` 和官方 `sleep-inhibitor` 服务：有活跃 SSH
会话时 `ssh-session-open` 持有 `sleep` 锁；仅插着 USB 充电线不会永久
阻止 suspend。需要无 SSH 活动的 USB 维护时，使用
`linux-port/debug/sleep-policy/` 里的手动 helper，且测试结束立即释放。
5-r20 同时移除了 `sshd -> samurai-usb` 和
`NetworkManager -> samurai-radio` 的启动门控，避免 NCM/radio 准备
拖慢已经可用的 Wi‑Fi SSH；这一点必须用新的普通重启时间线验收，不能
只凭源码改动宣称首连已修复。
这不是新增 USB 转发层：使用的仍是 sysfs、configfs、上游
`sleep-inhibitor` 二进制和 `elogind-inhibit` 公共接口。正式配置就是
官方 `/etc/sleep-inhibitor.conf`；不再有板级配置文件或独立服务。
2026-11-05 的 carrier-only guard 空闲约 5 分钟、不保持 SSH 会话时
30/30 链路探测成功，这只能证明旧策略下 guard 生效，不能作为 r20 默认
策略的验收。
Windows显示426Mbps是驱动链路报告，实测协商high-speed；没有USB3/OTG验收。
NCM枚举刚出现时服务/主机地址可能还没就绪，要以实际SSH回执确认连接。

## suspend 与“按电源键才恢复”

DWC3 在系统 suspend 的 gadget 路径会执行 soft-disconnect，撤掉 USB
pull-up；主机随后看到的是一次拔出。此时主机即使继续发 NCM 数据包，
也没有可恢复的 USB 设备，必须等手机被电源键或其它系统唤醒源唤醒。
因此“UDC state=configured”或 Windows 网卡仍为 Up 不能证明空口链路
可唤醒。

正式策略是：活跃 SSH 或 SCP 会话持有标准 `sleep` 锁，屏幕仍可由
KWin 做 DPMS 关闭；仅保留 USB 线但无 SSH 活动时允许系统 suspend。
长时无人值守测试由脚本创建额外的标准 elogind block 锁，测试结束释放。
carrier-only guard 只存在于 debug 目录，不进入正式配置。

**suspend 验收不能用直接 sysfs `since_epoch + 延迟`。** 2026-11-09
在 thin-private boot `2b17a67a…` 上用该方法布防后执行
`loginctl suspend`，手机 140 秒内没有恢复，USB/fastboot 也未枚举。
本机 PMIC RTC 当时显示 1970 年域，而系统 wall clock 是 2026 年；
直接写 `wakealarm` 与 `rtcwake` 的 offset 处理不等价。后续必须使用
`SAMURAI_ALLOW_SUSPEND=1 linux-port/scripts/test-suspend-rtcwake.sh 30`
（或串口确认的等效路径），并在有人工唤醒条件时单独测试；不能把
`test-usb-ncm-stability.py` 的 sleep 锁和 suspend 测试混在同一轮。

### postmarketOS 休眠模型与 USB 唤醒边界（2026-11-10）

本内核启用了 `CONFIG_PM_SLEEP`/`CONFIG_SUSPEND`，但没有启用
`CONFIG_PM_AUTOSLEEP` 和 `CONFIG_PM_WAKELOCKS`。因此这里不使用
Android 式的 `/sys/power/autosleep` 或 `wake_lock`；系统睡眠由 KDE
PowerDevil 通过 logind/elogind 发起，`sleep-inhibitor` 使用
`elogind-inhibit --what=sleep` 持锁。

postmarketOS 官方默认把 `sleep-inhibitor` 加入 OpenRC `default`
runlevel，配置只包含 `ssh-session-open` 和 `apk-running` 两个插件；
`ssh-session-open` 的匹配式是
`sshd(-session)?(\.[^:]+)?:.*pts`，因此它依赖一个带 PTY 的交互式
SSH 会话。自动化的 `BatchMode` 命令如果没有 `-t`，不应当被当成
可靠的休眠保护；无人值守测试仍应显式持有
`elogind-inhibit --what=sleep --mode=block`。该插件的检查周期是
6 秒，刚连上时也存在短窗口，不能代替测试脚本的锁。

USB 唤醒要分两种方向：

- USB gadget 的 remote wakeup 是“手机唤醒主机”，由 `u_ether` 在
  NCM 发包时调用 `usb_gadget_wakeup()`；它不能让主机在手机已经
  suspend 后把手机唤醒。
- 主机侧数据包、magic packet 或一次 SSH SYN 都不是手机唤醒源。
  当前 DWC3 gadget 路径在 suspend 时执行 soft-disconnect，撤掉
  pull-up，主机看到的是 USB 拔出，随后没有任何 NCM 设备可以接收
  数据包。

真正可能的标准唤醒源是电源键、RTC、已布防的 USB/充电器 IRQ 或
Qualcomm PDC wakeirq。当前 RMX1931 设备树没有给
`usb_1_dwc3` 加 `wakeup-source`，且 `dwc3-qcom.c` 只在 host role
下布防 USB PHY wake IRQ；本板的 `dr_mode` 是 `peripheral`，所以
单纯加一个 `wakeup-source` 属性并不会自动得到 USB 数据唤醒。
PM8150B Type-C 节点当前未启用，MP2650 驱动也只有 I2C 状态轮询，
没有 charger/VBUS 唤醒中断。因此当前正式配置没有可靠的“插拔 USB
线唤醒手机”路径。

如果以后要把它做成标准能力，优先考虑上游已有的通用模型：
`usb-conn-gpio` + 真实的 VBUS/ID GPIO + `wakeup-source`，或补齐
PM8150B Type-C/充电器 IRQ 的 `enable_irq_wake()` 支持；不应在板级
私有驱动里伪造一条 USB 数据唤醒路径。任何 suspend 试验都必须保留
电源键或串口恢复路径；RTC 只能作为有恢复手段时的定时唤醒测试。

> **2026-11-11 撤回**：GPIO10 extcon 的假设已被真机否定（厂商 DTS
> 注释掉 `vbus-gpio` 和消费者，实测 GPIO10 不跟随 VBUS、IRQ 120 始终
> 为 0）。overlay、udev 规则和包条目已删除，keep-connect 也已关闭。
> 详见 [USB-REMOTE-WAKE-20261111](USB-REMOTE-WAKE-20261111.md)。

官方参考：
[`sleep-inhibitor` 配置](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/main/main/postmarketos-base-ui/rootfs-etc-sleep-inhibitor.conf)、
[`elogind` 配置](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/blob/main/main/postmarketos-base-ui/rootfs-usr-lib-elogind-logind.conf)、
[pmOS 电源管理](https://wiki.postmarketos.org/wiki/Power_management)、
[pmOS opportunistic sleep](https://wiki.postmarketos.org/wiki/Opportunistic_Sleep)、
[SDM845/SDM850 wakeups](https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_(SDM845/SDM850)#Wakeups)。

### USB 平台适配覆盖矩阵（2026-11-10）

`NCM 能连`只覆盖了表中的第一行和 gadget/configfs 子集，不能据此认为
整个 USB-C 平台已经完成适配。

| 能力 | 当前状态 | 证据/边界 |
| --- | --- | --- |
| USB2 high-speed device mode | 已验证 | DWC3 UDC、NCM、SSH/SCP 可用；传输问题由 `tx-fifo-resize` 和 `qmult=20` 修复 |
| configfs gadget/UDC | 已验证 | NCM 生命周期和普通重启可工作 |
| DWC3 runtime PM | 已验证 | 空闲时 runtime suspend，活跃时恢复 |
| NCM 大传输 | 已验证 | 双向 64K/256K/1M/4M 矩阵通过 |
| 热重启进 ABL fastboot | 部分/有 workaround | 曾出现 `VID_0000&PID_0001` Code 43；干净解绑 UDC 可降低概率，但根因在 ABL 暖启动 |
| 系统 suspend 后的 USB 插拔唤醒 | **未支持** | GPIO10 extcon 被否定并删除；没有可信 VBUS/attach 源。下一步走 PM8150B Type-C/TCPM |
| 同线主机发给手机的 USB resume | **未支持** | keep-connect 已禁用（拔线时 `dp_hs_phy_irq` 伪唤醒，插线 resume 曾致 Code 43）；标准路径不保留 U3 链路 |
| VBUS/充电器检测 | 部分 | MP2650 只做 I2C `power_supply` 轮询，没有 IRQ/wakeup 布防 |
| Type-C CC/PD 与 role switch | sink 已验证；OTG dual-role 已部署 | 当前运行内核为 `dr_mode = "otg"`、`usb-role-switch` 和 PM8150B Type-C/TCPM；role=device，物理 host 选择待验收 |
| OTG/host mode | device 与 synthetic host 已验证，物理外设待验收 | `...-usbwake-otg` Image/DTB/boot/logdump/772 模块包已部署；synthetic host 注册 xHCI root bus 并自动回到 device。U 盘/键盘、自动 Type-C host、反插和 VBUS source 未验收，见 [USB-OTG-20261112](USB-OTG-20261112.md) |
| USB3 SuperSpeed | 未启用 | `usb_1_qmpphy` disabled，`maximum-speed = "high-speed"` |
| DisplayPort alt mode | 未实现 | 同一 QMP PHY/DP 路径未接入 |
| 充电控制/输入限流/watchdog | 未实现 | MP2650 驱动明确只读，避免未验证的保护链被改写 |

因此这里更准确的说法不是“USB 驱动坏了”，而是“USB2 NCM 的最小数据
路径已经打通，USB-C 的角色、供电、充电器事件、唤醒和高速/DP 能力
仍是分层的未完成项”。这些能力应作为独立的候选逐项接入；不能用一个
NCM 连通测试代替 USB 平台验收。

### USB2 Type-C 分层候选（2026-11-10）

本轮把 USB 适配拆成两个 DTB 候选，避免把“启用 TCPM”和“启用 host”
混成一次改动：

- `usb2-typec-sink`：只启用 PM8150B Type-C/TCPM，connector 固定
  `power-role=sink`/`data-role=device`，DWC3 保持当前
  `dr_mode="peripheral"`，不添加 role-switch 或 HS graph。它与当前
  gadget-only 内核配置兼容，是首个可安全上机的 DTB-only 候选。
- `usb2-typec-dual`：标准 OTG + `usb-role-switch` + connector graph，
  source 先限制为 5 V / 500 mA。当前生产内核缺
  `CONFIG_USB_DWC3_DUAL_ROLE`、`CONFIG_USB_XHCI_HCD` 和
  `CONFIG_USB_XHCI_PLATFORM`，所以它必须配新的 Image，不能只替换 DTB。

离线产物和哈希：

```text
E:/edk2-samurai-out/standard-arm64-v731/usb-typec-20261110/manifest.json
sink DTB      b18da56255f82ecf9fa2095f7eddd4d0041fbb1a8162162007f1b55c657bd792
dual DTB      ef8e40ba6dca4f344918b7be9a6d1c6145c0b4d2670d58336cd3ee4086c4d164
dual config   524cc7e476b2c7ad1e35dd1fb339d95f60f0cb29f4e1f3b44d105180d30ec3e6
```

构建、配置解析、候选边界和上游参考见
[`USB-TYPEC-20261110.md`](USB-TYPEC-20261110.md)。这两个 DTB 尚未刷入；
设备本轮在 SSH 握手前即关闭连接，不能把离线构建当作运行时通过。

rootfs 源码脚本为
[`samurai-platform/usr_sbin_samurai-usb`](../packages/samurai-platform/usr_sbin_samurai-usb)；
历史 initramfs 脚本为 `linux-port/scripts/samurai-usb.sh` 与
`build-dropbear-usb.sh`。
构建Dropbear用固定2026.94官方tar和SHA，输出静态ARM64 multicall，包含
dropbear/dropbearkey/scp；许可证在refs/dropbear-2026.94-LICENSE。
实际initramfs是/home/cy122/x2pro-linux/initramfs，原EUD/init逻辑保留。
kernel72-initramfs.config把本地UID/GID1000映射成包内root；更换构建用户时按
实际源文件所有权配置并验证CPIO，不能把固定1000当通用发行配置。
历史安装/构建/部署和验证代码在reference/kernel72，可按当前布局复用；
处理一次性安装步骤，将所需修改合入现有init/initramfs并保留回退。

本轮只刷一次logdump，boot固件与DTB未改；直接回退kernel71/logdump-k71-touch.img。
日志可保留在手机后SCP下载，也可流式采集；按用途核验完整性。
72阶段文件传输采用手机SHA256、gzip CRC和长度校验。
双向4MiB SHA、PTY、自动SSH、EUD保留及原始失败记录详见sessions/72。

## fastboot 暖启动时的未知 USB

从 Linux 热重启进入 ABL fastboot 时，Windows 偶发把手机显示为
`USB\VID_0000&PID_0001` + Code 43。它是“USB 已接上但没有有效描述符”的
占位设备，不是新外设，也不是 Windows 驱动问题；重新进一次 fastboot
会重新初始化 ABL 的 USB 控制器/PHY，通常立即恢复 `62bc28a1`。
2026-11-08 复查时当前设备扫描没有 problem node；注册表仍保留同一
Hub 端口的历史 `VID_0000&PID_0001`/`PID_0002` 记录，分别标记
“Port Reset Failed”和“Device Descriptor Request Failed”。这进一步说明
它是手机同一次失败的 USB 枚举残留，而不是额外的 USB 外设。

可在重启前用标准 configfs/UDC 生命周期做一次干净交接：

```sh
python3 linux-port/scripts/restart-bootloader-clean.py --inspect
python3 linux-port/scripts/restart-bootloader-clean.py
```

脚本解绑 `/sys/kernel/config/usb_gadget/samurai/UDC`，等待解绑完成，
`sync` 后调用 `RESTART2("bootloader")`。只跑 `--inspect` 不会断开 USB。
因为实跑会先撤掉 NCM gadget，必须从 Wi-Fi SSH 执行，或先
`nohup`/`setsid` 再执行；USB SSH 会在解绑时断开。

这仍是 workaround；根因在 ABL 的暖启动 USB 路径。只有在多次热重启对照
中稳定恢复 `fastboot devices` 后，才能把它写成正式修复。

## NCM 稳定性现状

结论：旧生产 DTB 在 r16 标准 rootfs 上仍会于 4 MiB device-to-host
传输后出现 `Broken pipe` 和短暂 SSH 超时。只增加主线 DWC3
`tx-fifo-resize` 属性后，候选 boot 先通过 24/24 双向传输、5 分钟
心跳和 30 分钟矩阵；该属性现已写回生产 DTS，boot 与 logdump FAT
已配对部署，并在新普通重启周期 `f26c6cdc…` 通过运行时门禁。
这不是 USB3 问题：整机 Type-C 按 USB 2.0 使用，NCM 协商 high-speed；
Windows 显示的 426Mbps 只是链路报告。

已有证据：

- 190 出现 USB 归档尾部中断和双向 IPv6 探测失败，单次 gadget 重绑后
  恢复，但没有取得重绑修复根因的正向证据；
- 203 大 SCP 停顿后，同一 boot 的 Wi-Fi 取得完整候选；
- 213 的 1MiB 分块传输截断，随后 USB 小 SSH 超时；当时没有盲目复位；
- 214 在同一 boot 用原密钥重新连回，改用 64KiB 分块完成了 227+167
  个成员的归档核对；这只证明 64KiB 路径可恢复，不证明大传输已修复；
- 2026-11-05 的旧 carrier-only guard 在空闲约 5 分钟、不保持 SSH 会话
  时 30/30 链路探测成功；r20 默认改用 `ssh-session-open`，仅充电连接
  允许 suspend，DWC3 在 suspend 时仍会 soft-disconnect；
- 2026-11-08 当前 boot `6df4a965…` 的 30 分钟矩阵通过：双向
  `64K/256K/1M/4M` 各 3 次、共 24 次传输，所有字节和 SHA-256 匹配，
  0 失败；随后 1800 秒每秒 SSH 心跳通过，`taint` 前后均为 0。独立
  验证器输出 `ncm-baseline-verdict.json`，SHA-256
  `7fd449305cdc084f8735f44d75948ac1ac40f09fdc9ff0bbbb3af6a4ac63c31a`。
- 2026-11-08 r16 标准 rootfs 在同一矩阵复现 4 MiB device-to-host
  `Broken pipe`：3 次失败、后续约 17 秒 SSH 超时；加入
  `tx-fifo-resize` 的候选 boot `7f8d7a65…` 随后 24/24 通过，5 分钟
  心跳通过，独立 verdict SHA-256 为
  `c8524d1d43d401a9ed58949bc8395d678798ef8517124ff7ead00c39addc4ff2`。
- FIFO 候选的完整 30 分钟矩阵随后通过：双向 `64K/256K/1M/4M`
  共 24/24，心跳 1800.598 秒，前后 `taint=0`、同一 boot ID；结果
  SHA-256 `e2eda19639dec2dc6767b0f0f3c713ad2524adee0152ef8460d39671d506d70a`，
  独立 verdict SHA-256
  `0eef880c9ebb8fbdc72dbf83df1157154fc2cf2899aca4d4c6a09342deddcb16`。
- 同一窗口的 Wi‑Fi SSH 连续心跳为 1800 个样本、1810 秒、最大采样间隔
  2 秒；独立 verdict SHA-256
  `95e063fbbebfaa9556b0f16f5bd6ad96e20e3b737f000a328450e881e346b972`。
- boot `7f8d7a65…` 与 64 MiB logdump FAT `1f3a40f4…` 已配对一致，
  普通重启进入 `f26c6cdc-275c-451b-b7fc-65c93741e63e`；新 boot 的
  skip-camera 总门禁全绿，运行时 JSON SHA-256
  `8de57ab47aef1e28c8e3794901ad4b94d83dd68b0c1a56099e8c57bbb7bf6096`。
- 部署后的新 boot 又完成一轮 30 分钟 NCM：24/24、心跳 1800.169 秒、
  前后 `taint=0`、UDC `configured`、carrier 1；结果 SHA-256
  `0365acda3af83f744bda5393fd48cc7bc2c13e84bfdf3275c1eb82fe84c74afc`，
  独立 verdict SHA-256
  `4df827354eff27e83f06731302ff77638f9cafe3ae01a840b1d757c82dc72729`。
- 同一新 boot 的 Wi‑Fi SSH 第二轮也完成 1800 个样本、1811 秒，最大采样
  间隔 2 秒；日志 SHA-256
  `5b773411c906380c445eb111951f1f118a07a57cc215d3c608e5bf734bf06dd2`，
  独立 verdict SHA-256
  `87edf0a2e5e79778fbd26a4a93ede99bc7f96f8086c58dfdaed4189b2f7521d`。
- `samurai-platform` 5-r17 又把 `samurai-wifi` 的固定 45 秒等待替换为
  有界 MPSS `running` 轮询。包升级后的普通重启从请求到首次 SSH：
  Wi‑Fi 约 57 秒（内核启动后约 26 秒），NCM 约 37 秒（内核启动后约
  7 秒）；修复前 Wi‑Fi 约 101 秒。r17 下的 5 分钟回归为 NCM 24/24、
  Wi‑Fi 300 样本/301 秒，`taint=0`。

这次结果把“当前 boot、当前 Windows 主机、NCM 与 Wi‑Fi 各两轮 30 分钟
窗口”从开放项变成通过项，但不等于长期稳定。多次冷启动、更长空闲、
不同 USB 主机/线材和更大的持续传输仍需单独验收。

2026-11-09 的 r21 检查点进一步把 `qmult=20` 写入标准 configfs
启动路径：普通重启 `d5cfa04f…` 后双向 24/24、心跳 1798.828 秒，
Wi‑Fi 1810 样本/1820.51 秒，两个独立 verdict 均通过；同一 boot
的完整 runtime/CAMSS/RAW 门禁也通过。当前剩余的是外部断电冷启动、
多次冷启动、Linux 主机和更大传输，而不是 NCM 队列深度或旧 Hub
枚举问题。

## 启动期依赖故障

2026-11-08 的一次重启前，屏幕上看到的 NetworkManager 错误不是 WiFi
认证失败，而是 OpenRC 的依赖链故障。持久化的 `/var/log/rc.log` 显示：

```text
ERROR: samurai-radio failed to start
ERROR: cannot start networkmanager as samurai-radio would not start
ERROR: cannot start bluetooth as samurai-radio would not start
ERROR: cannot start modemmanager as samurai-radio would not start
ERROR: cannot start routewrangler as samurai-radio would not start
Could not find a wireless interface
No SDSP FastRPC device
ERROR: samurai-usb failed to start
cat: can't open '/sys/devices/soc0/serial_number': No such file or directory
ERROR: cannot start sshd as samurai-usb would not start
ERROR: samurai-ssc failed to start
ERROR: cannot start iio-sensor-proxy as samurai-ssc would not start
ERROR: cannot start tinydm as samurai-ssc would not start
```

这说明一次启动周期内无线/调制解调器和 USB gadget 的初始化没有在
OpenRC 依赖窗口内完成，随后依赖服务被拒绝启动；KDE 电源策略和 SSH
daemon 本身都不是这个错误的原因。重启后当前 boot ID
`6df4a965-4ca2-4a1b-97c5-35b60dac14c3` 已恢复：

- `samurai-radio`、`samurai-usb`、`samurai-ssc` 和 `networkmanager`
  都已启动；
- Wi‑Fi `wlan0` 为 `192.168.0.114`，`usb0` 为
  `169.254.42.1`，UDC `configured`、carrier 为 1；
- USB NCM 严格主机密钥 SSH 已恢复；但主机侧首次 ARP 可能需要
  数十秒，期间会出现暂时超时；
- `qrtr0` 当前仍记录
  `error setting IPv4 forwarding to '0': No error information`，
  这是没有 SIM 时 ModemManager/NM 的警告，不应拿它解释同一启动周期
  的 Wi‑Fi 断连。

该依赖链已按“硬件就绪等待 + 可选服务软依赖”处理，而不是继续靠重启
碰运气：

- `samurai-usb` 先按需加载标准 `socinfo`，再对
  `/sys/devices/soc0/serial_number` 做 60 秒有界等待和数字校验；
- `samurai-wifi` 对 UFS/radio 来源和 `wlan0` 枚举分别做 120 秒有界
  等待，失败原因保存到 `/var/log/samurai/wifi-boot-failure.log`；
- NetworkManager 的 `samurai-radio` 从 `rc_need` 改成
  `rc_use + rc_after`；sshd 的 `samurai-usb` 同样改成软依赖，因此
  Wi‑Fi SSH 不再被 NCM gadget 的失败连带拒绝；
- SensorProxy 对 `samurai-ssc` 使用软依赖；SLPI 最多等 30 秒，
  FastRPC 设备最多等 90 秒；
- `tinydm` 把 `iio-sensor-proxy` 作为有顺序的可选服务，SSC 暂时失败
  不再阻塞 Plasma。

对应的 `samurai-platform 5-r16`（SHA-256
`a8be746614bb5dad3fd773ac109f042b260b48d13d027cdf08724ccdf8d4c923`）
和 `samurai-desktop 4-r8`（SHA-256
`48730e82a72f7e9047069a1b9fd908282639b72fbe422be882d5f1145aa2675d`）
已安装到当前 rootfs；APK 签名验证、`samurai-usb start` 幂等冒烟、
服务状态和桌面边界检查通过。**这仍不是冷启动验收**：
必须再经历多次完整断电/启动，确认即使 `samurai-radio` 或
`samurai-ssc` 返回失败，NetworkManager、sshd 和 tinydm 仍能启动。
冷启动后可直接运行只读门禁
[`check-boot-service-boundaries.sh`](../scripts/check-boot-service-boundaries.sh)；
当前运行态已经返回
`RESULT: boot service boundary check passed`。

恢复后的标准测试矩阵：

1. 直连主板 USB 口与经过 hub 两种接法各测一轮，并更换数据线；
2. 64KiB、256KiB、1MiB、4MiB 四种分块，双向 SCP，各自至少 3 次，
   每次做手机端 SHA-256 与主机端校验；
3. 30 分钟每秒一次的小 SSH 心跳 + ping，记录首次失败时间和恢复方式；
4. 同时采集手机 `dmesg`、UDC `state`/`carrier`、`ip -s link`，以及
   Windows USB/PnP 事件；
5. 用 Linux 主机复测同一镜像，区分 Windows NCM 主机驱动和手机 DWC3/
   NCM gadget 侧问题；
6. 不把单次大文件成功当作修复；只有多轮、双向、长时测试全部通过，
   才能把 NCM 大传输从开放项移除。

已提升为标准生产 DTS 属性：
[`patches/experiments/0001-arm64-dts-samurai-usb-tx-fifo-resize.patch`](../patches/experiments/0001-arm64-dts-samurai-usb-tx-fifo-resize.patch)
保留了最初的实验记录。`tx-fifo-resize` 是主线
`Documentation/devicetree/bindings/usb/snps,dwc3-common.yaml`
定义的布尔属性，由 `drivers/usb/dwc3/core.c` 用
`device_property_read_bool()` 读取；高速 bulk IN 时可动态分配 TX FIFO。
这不是板级私有 USB 传输层。
正式 DTB 已从生产源重建为
`E:/edk2-samurai-out/standard-arm64-v731/usb-fifo-production-source-20261108/sm8150-samurai.dtb`
（`c9f948cdac6e58b23ba5bd9bb29137d6266154ce22540fb4d585e24826649fc5`）；
源文件 SHA-256 为
`d6e75f92cb900e779467bee2698bff25d7e89d6d57f1c9bec44ff3a48776b83d`。
2026-11-08 从标准 rootfs boot `e1cccd9d…` 重新打包的 boot
`7f8d7a65…` 中，BdsDxe、PlatformSmbiosDxe、UiApp 和其余 100 个 main
FFS 逐字节不变，只替换了 DTB FFS。
boot 的受控刷写入口是
[`flash-v731-usb-fifo.ps1`](../scripts/flash-v731-usb-fifo.ps1)，默认
dry-run，只接受固定串号、`msmnile`、候选 boot 的精确大小和 SHA-256；
不加 `-Flash` 不会写入任何分区，`-Reboot` 也不是默认行为。
配对入口为
[`flash-v731-usb-fifo-pair.ps1`](../scripts/flash-v731-usb-fifo-pair.ps1)，
拒绝只写 boot 或只写 logdump。
本次无人值守部署时 boot 已是同一 `7f8d7a65…`，因此只把 64 MiB
logdump 镜像经 Wi‑Fi SSH 送入手机，先校验镜像、分区大小、旧分区哈希和
“未挂载”状态，再用 `dd conv=fsync` 写入 `/dev/disk/by-partlabel/logdump`；
写后回读必须等于 `1f3a40f4…`，`fsck.vfat -n` 通过，随后普通重启。
这是一次性分区写入方法，不允许对已挂载分区执行；有现场时仍优先使用
上面的 fastboot 配对 helper。

## 无人值守稳定性矩阵

[`test-usb-ncm-stability.py`](../scripts/test-usb-ncm-stability.py) 把上面的
矩阵做成可重复运行的本机脚本。默认使用严格 known_hosts、BatchMode、
连接/活动超时和双向 SCP；每次传输都在主机和手机两端校验字节数与
SHA-256，并在失败时保存 UDC、carrier、`ip -s link` 和 `dmesg` 片段。
脚本默认在手机侧持有 7200 秒的
`elogind-inhibit --what=sleep --mode=block`，结束后释放；报告中的
`sleep_inhibit`/`sleep_inhibit_release` 可审计。只有明确传
`--no-sleep-inhibit` 才允许无锁运行。
脚本不会自动重绑、重启或刷写设备，因此 NCM 失联时不会扩大故障范围。
`--host-snapshot` 另存 `host-snapshot-pre/post.json`：当前 USB PnP 的
`Problem`/中文描述、Win32 `ConfigManagerErrorCode`、NCM 网卡计数、
IPv4/link-local 邻居，以及最近两小时 USB/PnP 系统事件；下一次出现
`VID_0000&PID_0001` Code 43 时可直接留下主机侧证据。

生产 DTB 基线：

```powershell
python .\linux-port\scripts\test-usb-ncm-stability.py `
  --host 10.42.0.1 `
  --identity E:\edk2-samurai-out\kernel72\id_ed25519 `
  --known-hosts E:\edk2-samurai-out\kernel72\known_hosts `
  --iterations 3 --heartbeat-seconds 1800 --host-snapshot `
  --output-dir E:\edk2-samurai-out\standard-arm64-v731\ncm-baseline-20261108
```

完成后不要只看脚本退出码，再用
[`verify-usb-ncm-result.py`](../scripts/verify-usb-ncm-result.py) 做独立门禁：

```powershell
python .\linux-port\scripts\verify-usb-ncm-result.py `
  E:\edk2-samurai-out\standard-arm64-v731\ncm-baseline-20261108 `
  --min-iterations 3 --heartbeat-seconds 1800 `
  --output E:\edk2-samurai-out\standard-arm64-v731\ncm-baseline-verdict.json
```

验证器要求双向四个尺寸各三轮、完整 SHA/字节回读、`taint=0`、同一 boot
ID、UDC `configured`、carrier 1 和至少 30 分钟心跳；dry-run、缺项、
超时或任一端哈希不符都会判失败。

旧生产 DTB 的 30 分钟基线曾在 `6df4a965…` 通过，但 r16 标准 rootfs
上仍复现了 4 MiB 失败；FIFO 生产 DTB 已完成完整 30 分钟对照，部署后
又在新普通重启完成第二轮 30 分钟。多次冷启动、更长空闲、Linux 主机、
不同线材和更大持续传输仍未验收。
