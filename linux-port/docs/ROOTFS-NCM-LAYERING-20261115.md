# Rootfs NCM 分层修复（2026-11-15）

## 现象

切根成功、Windows 正常枚举 `USB\VID_0525&PID_A4A1`、
`UsbNcm Host Device` Problem 0、链路协商 426 Mbps，但：

| 观测 | 值 |
| --- | --- |
| Windows `ReceivedBytes` | 0 |
| Windows `SentBytes` | 1.2 MB |
| `ping 169.254.42.1` | 不可达 |
| DHCP | 超时，Windows 落到 APIPA |
| SSH | 不可达 |

主机能发、设备回零，说明 USB 描述符与枚举没问题，是设备侧
netdev 没有参与收发。

## 根因：分层职责缺了一格

initramfs 的 `samurai-usb` 无条件做了三件事：

```sh
dev_addr/host_addr 固定
ip link set usb0 up
ip addr add 169.254.42.1/16
```

切根后，这三件事的归属变了：

| 职责 | initramfs | rootfs 现状 |
| --- | --- | --- |
| gadget 创建 | `samurai-usb` 手写 configfs | `usb-signaller`（标准） |
| 链路 UP | 无条件 `ip link set up` | **无人负责** |
| 地址 | 脚本直接 add | NetworkManager profile |
| DHCP | dnsmasq | `unudhcpd.usb0` |

而 NetworkManager 只在 `carrier=1` 时激活以太网 profile
（`0009-usb-signaller-activate-only-with-carrier.patch`），
`carrier` 又由 `gether_connect()` 在端点使能后才置 1；
端点只有在 netdev 被 `eth_open()` 拉起、`eth_start()` 填 RX 队列后
才恢复。于是形成死锁：

```text
usb0 DOWN → carrier=0 → NM 不激活 profile → usb0 仍 DOWN
```

主机的 OUT 端点照常发送，设备 RX 队列从未填充，所以
`ReceivedBytes=0`。

旧 rootfs 后端（`samurai-platform` 的 `usr_sbin_samurai-usb`）
绕开了这个死锁：`nmcli device set usb0 managed no`，然后
`ip link set up` + `ip addr add` + dnsmasq。

## 修复：把这一格放回板级薄服务

新增 `samurai-usb-network`（OpenRC `supervise-daemon`，
`default` runlevel）：

- 等待 `usb0` 出现（最多 120 秒）；
- `nmcli device set usb0 managed no`，阻止 NM 撤掉地址；
- `ip link set usb0 up`；
- `ip addr add 169.254.42.1/16` 与 `172.16.42.1/24`；
- 重启 `unudhcpd.usb0`，因为它是 `boot` 服务，启动时 `usb0` 还不存在；
- 监控 netdev 世代（gadget 重绑会重建同名接口）并重新配置；
- 每 10 秒自检 `UP`/地址/载波，缺失即修复。

它**不**创建 gadget、不重置 UDC、不接管 SSH。gadget 仍由
`usb-signaller` 拥有，DHCP 仍是 `unudhcpd`，SSH 仍是发行版
`sshd`。

同时移除旧的 `samurai-ncm-fallback`：

它被同时放进 `boot` 和 `default`，而 `boot` 运行时 `usb0` 不存在，
服务返回成功后被 OpenRC 标记为已启动，`default` 的同名服务因此
不再执行 —— 从头到尾没有配置过接口。

## 分层归属（最终）

| 层 | 内容 |
| --- | --- |
| L2 DTS | DWC3、PHY、Type-C、VBUS 接线 |
| L3 驱动 | `qcom,sm8150-dwc3`、`f_ncm`/`u_ether`、`tx-fifo-resize` |
| L4 UAPI | configfs/UDC、netdev、`soft_connect` |
| L5 发行版 | NetworkManager、`unudhcpd.usb0`、`sshd` |
| L6 板级 | `usb-signaller` 描述符覆盖、`samurai-usb-network` 链路 glue |
| L7 桌面 | Plasma Mobile |
| initramfs | 仅诊断/救援；不参与正常运行链路 |

## 离线校验

镜像内检查全部通过：

```text
switch_root preconditions:
  OK      /etc/samurai-rootfs-release
  OK      /sbin/init -> bin/busybox
  OK      /etc/inittab runs OpenRC
  OK      kernel modules 7.3.1-rmx1931-samurai-v731
  OK      /etc/init.d/samurai-usb-network (default, supervised)
  OK      /etc/init.d/unudhcpd.usb0
```

sparse 镜像逐块与 raw 比对：

```text
sparse: 11802 chunks, block_size=4096, blocks=29060851,
        data=119033245696 bytes
OK: sparse payload is byte-identical to the raw image
```

## 镜像

| 项 | 值 |
| --- | --- |
| sparse 大小 | 2,784,523,032 字节 |
| SHA-256 | `563f208caf0b7c33ac3c664387eaacd5b57325f2b20074a272e0e0243057d1d8` |
| 展开大小 | 119,033,245,696 字节（与 `userdata` 等长） |

## 一次必须记录的自我失误

第一版 glue 服务的 init 脚本里写着：

```text
command="/usr/sbin/samurai-ncm-watchdog"
```

但安装脚本只放了 `/usr/sbin/samurai-usb-network-watchdog`，并且
删掉了旧的 `samurai-ncm-watchdog`。结果 `supervise-daemon` 会一直在
“启动一个不存在的二进制 → 立刻退出 → respawn”里循环，服务永远
显示 started 却什么都不做，链接仍然不会被拉起。

这类错误在磁盘上完全看不出来（符号链接、runlevel、文件名都对），
所以现在 `apply-rootfs-ncm-layer-fix.sh` 会解析 init 脚本的
`command=` 并在镜像内断言该路径可执行；`inspect-rootfs.py` 也加了
同一检查，并做过正/负向测试（缺失时返回 False，存在时返回 True）。

教训：init 脚本里的 `command=` 与服务实际安装的路径必须由同一个
来源生成，不能两处各写一遍。

## 实机验收（待补）

开机后按顺序检查：

1. `USB\VID_0525&PID_A4A1` 枚举正常，网卡状态 `Up`；
2. Windows `ReceivedBytes > 0`；
3. `ping 169.254.42.1` 可达；
4. DHCP 取得 `172.16.42.2/24`；
5. `ssh user@172.16.42.1` banner 为 `OpenSSH`；
6. `/var/log/samurai/usb-network.log` 出现 `configured usb0`。

## pmaports 落地（2026-11-15 23:25）

这一层已进入 `device/testing/samurai-platform`，不再只是镜像手改：

| 项 | 内容 |
| --- | --- |
| `source=` | `usr_sbin_samurai-usb-network-watchdog`、`etc_init.d_samurai-usb-network` |
| `package()` | 安装到 `/usr/sbin/samurai-usb-network-watchdog`、`/etc/init.d/samurai-usb-network` |
| `post-install` | 删除旧的 `samurai-ncm-fallback` 链接与脚本，`rc-update add samurai-usb-network default` |
| 构建产物 | `samurai-platform-6-r18.apk`，29,121 字节 |

构建验证：

```text
=> edge/samurai-platform: Building package (cross compiling: cross-native2)
=> edge/samurai-platform: Done!
```

镜像内两个文件的 SHA-256 与该 APK 内的副本完全一致
（`MATCH usr/sbin/samurai-usb-network-watchdog`、
`MATCH etc/init.d/samurai-usb-network`），因此刷入的镜像与
pmaports 包是同源的，不是两套各自维护的副本。

### 构建环境里踩到的三个真实缺陷

这三个都会让“看起来只是构建失败”掩盖真正的包错误：

1. **pmbootstrap 依赖解析忽略 pkgrel**
   `pmb/helpers/pmaports.py` 用 `apkbuild["pkgver"]` 去比较
   `>=0.5.0-r2`，于是本地 `unudhcpd 0.5.0-r2` 永远判定不满足。
   已改为 `pkgver-pkgrel`（`fix-pmbootstrap-version-constraint.py`）。
2. **sha512sums 位置必须与 source 顺序一致**
   abuild 的 `default_fetch()` 每个 `$source` 项消费两个
   `$sha512sums` 词；把新校验和追加到块尾会让之后每一项错位，
   报错却只指向最后一个文件。因此新增
   `check-sum-order.py` 与 `normalize-apkbuild-sums.py`。
3. **`sha512sums="` 后不能有空行**
   空行会被当成一个空条目，abuild 报
   “1 of 1 computed checksums did NOT match”。
   插入脚本现已在写入前做顺序重排与空行防护。

### 复现命令

```sh
python3 linux-port/scripts/normalize-apkbuild-sums.py \
  <aports>/device/testing/samurai-platform/APKBUILD
python3 linux-port/scripts/check-sum-order.py \
  <aports>/device/testing/samurai-platform/APKBUILD
python3 linux-port/scripts/verify-apkbuild-sources.py \
  <aports>/device/testing/samurai-platform/APKBUILD
```

## 刷入后设备按键断电流程

这个 bootloader 在约 2.6 GB 写入之后，USB 命令通道会失效。之前只看到
`usb_read failed (31)`，2026-11-15 23:4x 又出现新的失败形态：

```text
getvar:product  FAILED (AdbWriteEndpointSync failed: 信号灯超时时间已到 (121))
continue        FAILED (AdbWriteEndpointSync failed: 121)
reboot bootloader FAILED (AdbWriteEndpointSync failed: 121)
```

这一轮是**刚刷完、进入 bootloader 时通道本来是正常**的全新会话，
`fastboot reboot` 仍然把通道弄坏。因此：

- `fastboot reboot` / `continue` 都不可靠，不能作为刷写后的正常出口；
- 写入本身始终成功，`userdata` 已完整落盘；
- 唯一可靠的退出方式是长按电源约 15 秒强制断电，再正常开机。

`flash-plasma-rootfs.ps1` 已按此改写：默认不 reboot，`-Reboot` 失败时
只提示断电，不抛出误导性的“刷写失败”。

## 本轮镜像记录

| 项 | 值 |
| --- | --- |
| sparse 大小 | 2,785,477,428 字节 |
| SHA-256 | `94af4c106a8b71677ff465adf785287b05adbc4977d5d98f85c9405cf8ac52c3` |
| 逐块校验 | 11806 chunks，29,060,851 blocks，与 raw 完全一致 |
| 已刷入 | 是（`userdata`） |

`samurai-usb-network-watchdog` 在镜像内的 SHA-256 为
`c158ac52c04736b77ae9a91e3559289eba9c202d8c5e44d1f46fefba6ad50d36`，
与 `linux-port/scripts/samurai-ncm-watchdog.sh` 相同。

## 模式归属（tethering 修复）

第一版 glue 无条件把 `usb0` 设成 NetworkManager 不管理，并在上面强加
`172.16.42.1/24`。这会**直接破坏 tethering**，因为该模式依赖
`nmcli ... ipv4.method=shared`（`10.42.0.1/24` + dnsmasq）。

现在按当前绑定的 configfs gadget 分派：

| 模式 | glue 做什么 |
| --- | --- |
| `developer` | `managed no`、`ip link up`、`169.254.42.1/16`、`172.16.42.1/24`、重启 `unudhcpd.usb0` |
| `tethering` / `mtp` / 其他 | 仅保证链路 `UP`（carrier 的前提），地址与 DHCP 全归 NetworkManager |
| developer → 其他 | 显式 `managed yes` 交还设备，并强制重新配置 |

模式判定用 `linux-port/scripts/test-ncm-mode-logic.sh` 在模拟 configfs
上验证，4 种绑定状态与 2 项所有权断言全部通过。

## 实机验证（2026-11-16）

分层修复在真机上成立。以下都是实测，不是离线推断：

### 首次连上

| 检查 | 结果 |
| --- | --- |
| 枚举 | `USB\VID_0525&PID_A4A1&MI_00` Problem 0 |
| 链路 | Up / 426.0 Mbps |
| 设备回包 | `ReceivedBytes` 从 **0** 变为 702 |
| ARP | `Reachable 6A-4D-2F-B1-4F-77` |
| ICMP | `ping 172.16.42.1` 通 |
| DHCP | 主机取得 `172.16.42.2` |
| SSH | `SSH-2.0-OpenSSH_10.6`（发行版 sshd，非 dropbear） |

设备日志即为根因证据：

```text
08:00:12 new netdev generation ... (mode=developer)
08:00:12 configured usb0
08:00:12 carrier=0
08:00:22 carrier=1
```

### 冷启动验证（关键）

重启后 boot id 由 `772aa26f…` 变为 `708ac0f5…`，NCM 在 30 秒内自行恢复，
日志再次出现 `configured usb0` → `carrier=0` → `carrier=1`。

这证明 rootfs **自己**重建 gadget 与链路，不依赖诊断 initramfs。
重启后 8 项验收再次全绿。

### 服务归属

```text
usb-signaller        started   (default)   建 configfs gadget
samurai-usb-network  started   (default)   链路 glue（本修复新增）
unudhcpd.usb0        started   (boot)      DHCP
sshd                 started   (default)   SSH
```

## 两次自己造成的故障（已修复并加了门禁）

### 1. apk 数据库被写坏

退役的 `install-ncm-fallback.sh` 曾手工向 `lib/apk/db/installed` 追加记录，
导致设备上 `apk` 全部命令报：

```text
ERROR: Unable to read database: v2 database format error
```

即包管理器完全不可用。

处理：

- `repair-apkdb.py` 从镜像移除该记录（1091 → 1090）；
- `repair-device-apkdb.sh` 在**运行中的设备**上完成同样修复，
  设备端 `apk info -e samurai-platform` 恢复正常；
- 用真实 `apk-tools 3.0.9` 二进制验证改写后的数据库可读；
- `install-ncm-fallback.sh` 已改为直接报错退出，指向正确脚本；
- `inspect-rootfs.py` 增加 apk 数据库与 `etc/apk/world` 门禁。

### 2. tethering 切换把设备变成不可达

为“让 tethering 更干净”，我先让 glue 在 tethering 下只做 `ip link up`
并把 `usb0` 留给 NetworkManager。实测结果：

```text
ReceivedBytes : 0
dhcp-lease    : APIPA / none
ping          : 不可达
SSH           : Connection closed
```

设备在 tethering 模式下既无地址也无数据，**唯一的远程维护通道消失**。
这比原本要修的“美观问题”严重得多。

修正后的 tethering 行为：

| 动作 | 归属 |
| --- | --- |
| `ip link set usb0 up` | glue（carrier 的前提，不可省） |
| `169.254.42.1/16` | glue（**保底维护通道，任何模式都保留**） |
| `nmcli device set usb0 managed yes` | glue（交还 NM） |
| `10.42.0.1/24` + dnsmasq + 转发 | NetworkManager shared profile |
| `172.16.42.1/24` + `unudhcpd.usb0` | 仅 developer 模式 |

新增 `verify-mode-switch-keeps-access.sh` 作为硬门禁：它实跑模式分派并断言
两种模式都保留可寻址的 `usb0`，另加强 5 条静态不变量。

### 教训

`usb0` 的 link-local 地址不是“开发者模式的便利”，而是**带外维护通道**。
任何模式都不应把它当作可牺牲的配置；拿掉它等于把设备变成砖。

## tethering 的最终归属（板级自管）

第二次修正尝试时发现设备已经有完整的 tethering 基础设施，无需借用
NetworkManager：

| 文件 | 内容 |
| --- | --- |
| `/etc/samurai/usb-dhcp.conf` | `interface=usb0`、`dhcp-range=10.42.0.2,10.42.0.10`、`dhcp-option=121` |
| `/etc/nftables.d/10_dhcp.nft` | 放行 `usb*` 上的 bootps |
| `/etc/nftables.d/51_usb_inet.nft` | usb 接口转发规则 |

因此 tethering 改为：

- glue 添加 `10.42.0.1/24` 与 `169.254.42.1/16`；
- glue 直接以 `/etc/samurai/usb-dhcp.conf` 启动 dnsmasq
  （`/run/samurai-tether-dnsmasq.pid`，租约在
  `/var/lib/misc/dnsmasq-usb.leases`）；
- `nmcli device set usb0 managed no`，避免 NetworkManager 的
  carrier 门控再次把接口拉下；
- 不触碰 `unudhcpd.usb0`（那是 developer 模式的 172.16.42.x 服务）。

之所以不沿用 `nmcli ... ipv4.method=shared`：该 profile 与 developer
profile 一样要等 `carrier=1` 才激活，而 carrier 又要求 netdev 已 UP，
形成死锁。板级配置没有这个依赖。

`verify-mode-switch-keeps-access.sh` 现在是硬门禁，包含 7 条断言：

```text
OK   link is raised
OK   link-local kept for maintenance
OK   tethering subnet published
OK   developer address not added
OK   NetworkManager kept out of the way
OK   no unudhcpd restart
OK   board takes over after developer
```

## 待完成的实机项

- 断电恢复后，在**新镜像**上复测 tethering → developer 往返，
  确认切换后 SSH 仍可用（这是上一轮失败的直接触发条件）；
- 复测冷启动；
- 记录最终镜像哈希。

## 当前阻塞（2026-11-16 02:xx）

设备在 tethering 模式下 **`ReceivedBytes = 0`、无 IPv4 地址、SSH 拒绝**，
即上一轮那版有缺陷的 glue 把设备变成不可达。三次目标轮次尝试后仍是同一
状态。

主机侧已穷尽的手段（均为实测失败）：

| 手段 | 结果 |
| --- | --- |
| SSH `172.16.42.1` | `Connection closed` |
| `ping 169.254.42.1` / `10.42.0.1` / `ping -6 ff02::1%6` | 不可达，RX 不增长 |
| fastboot | 无设备（不是 bootloader） |
| PnP `Disable/Enable-PnpDevice` | “常规故障” |
| `pnputil /restart-device` 根集线器 | **Access is denied**（需要管理员） |
| EUD / EDL | 无 `VID_05C6`，`eudtool` 不存在 |
| 局域网 192.168.0.x 扫描 | 无设备（未保存 Wi‑Fi 凭据） |

`samurai-usb-recover` 也不会自愈：它明确把“`configured` + `carrier=0`”
当作正常空闲（`docs/USB-ENUM-RECOVERY-20261113.md`），因此不会介入。

**唯一恢复路径：长按电源约 15 秒强制断电，再正常开机。**

恢复后应执行：

```powershell
E:\RealmeX2Pro edk2\linux-port\scripts\verify-mode-round-trip.ps1 `
  -Password '<current-user-password>'
```

> 该示例原先写着一次性的 bring-up 临时密码；本机账号密码在
> 2026-11-16 改过一次，脚本不再硬编码任何真实口令。运行时传入当前密码。

它会 developer → tethering → developer 往返，并在任一步失联时自动回滚。

### 已就绪的待刷镜像

| 项 | 值 |
| --- | --- |
| sparse 大小 | 2,785,928,452 字节 |
| SHA-256 | `7d4a52a91b393669cef4ccec2512500db69f08250be39c2ce249f4cdcc022174` |
| 逐块校验 | 11839 chunks，与 raw 完全一致 |
| watchdog 哈希 | `44e205d1bf32567df1fcaea1c013424435e23188e45bc08d2d39bd21ce4dbc80` |

该镜像修复了三个问题：NCM 链路 glue（含 tethering 板级自管）、
apk 数据库（1090 条，v3 校验通过）、以及 tethering 下的 link-local 保底。

## tethering 的 dnsmasq 启动方式（QEMU 实测）

新方案不再依赖 OpenRC 的 `dnsmasq.<iface>` 模板（镜像里**没有**这个实例），
而是由 glue 直接以 `/etc/samurai/usb-dhcp.conf` 启动 dnsmasq。为确认这不是
“看起来对”，用宿主机上的 `qemu-aarch64` 真跑了镜像里的 aarch64 dnsmasq：

```text
Dnsmasq version 2.93
Compile time options: ... DHCP ...        # DHCP 已编译进二进制

$ dnsmasq --conf-file=usb-dhcp.conf --test
dnsmasq: syntax check OK.

$ dnsmasq --conf-file=usb-dhcp.conf --keep-in-foreground &
$ ss -lun | grep :67
UNCONN 0 0 0.0.0.0%usb0:67 0.0.0.0:*
```

即 10.42.0.1 上确实会监听 DHCP。第一次尝试失败的原因是缺少
`/etc/passwd`（`unknown user or group: dnsmasq`）；镜像里
`dnsmasq:x:102:104` 存在，所以设备上不会遇到该问题。

`port=0` 关闭 DNS，只保留 DHCP，符合 tethering 的需要。

## 顺带修正的记录错误

`SWITCH-ROOT-20261115.md` 曾写「`ncm_qmult = 20` 从未生效」。
这个结论基于**上游未打补丁的源码树**，是错的：本地
`0001-gadget-support-board-descriptor-overrides.patch` 确实新增了
`GadgetConfiguration` 并在 `create_with_options` 中写入
`functions/ncm.*/qmult`。该 TOML 字段自 r11 起真实生效。

另一个记录错误是把 `retry` 写成 `command_background`；本板实际
使用 OpenRC 0.63 的 `supervisor=supervise-daemon`，脚本必须以
前台方式运行，`command_background` 会被忽略。

## 2026-11-16 刷入记录

镜像 `rootfs-plasma-20261115/samurai-rootfs-f2fs-partuuid.simg` 已写入
`userdata`。刷写前校验通过：

```text
size    2785928452 bytes
sha256  7d4a52a91b393669cef4ccec2512500db69f08250be39c2ce249f4cdcc022174
```

`max-download-size` 为 805306368，故使用 `-S 767M` 分块。fastboot 返回
exit 0 并回显 `flash complete; userdata written.`，即分区写入成功。

写入完成后 USB 命令通道按预期瘫痪：`fastboot devices` 仍列出条目，
但串号退化为 `????????????`，`getvar product` 在 3 分钟后仍无返回，
只能终止进程。这与本文档此前记录的 2.6 GB 写入后 `AdbWriteEndpointSync
failed (121)` 一致，属于 bootloader 通道问题，不是镜像问题。

因此本次**没有**执行 `fastboot reboot`。设备需长按电源约 15 秒强制断电
后重新开机。此前的 initramfs 阶段与 rootfs 首轮验证中，NCM 链路与 SSH
在开机后均能恢复，故刷写本身不改变 L2/L3/L4 层。

开机后待完成的门禁（尚未执行，不能视为通过）：

1. `verify-ncm-rootfs-link.ps1` 期望 8/8，含 `SSH-2.0-OpenSSH`。
2. `verify-mode-round-trip.ps1` developer -> tethering -> developer，
   每步保持可达。
3. `apk info -e samurai-platform`，确认 apk 数据库仍可读。
4. 再次冷启动，确认 boot_id 变化且 NCM 自愈。
