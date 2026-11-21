# 切根失败的原因与修复（2026-11-15）

## 现象

刷入 `userdata` 成功、内核正常启动，但设备始终停在诊断
initramfs：NCM 可用、`169.254.42.1` 可 ping，SSH banner 是
`SSH-2.0-dropbear_2026.94`，`user`/root 均 `Permission denied
(publickey)`。看起来像“rootfs 刷坏了”，实际是**从未切根**。

## 原因

内核内嵌的 initramfs（`Image` 中，`CONFIG_INITRAMFS_SOURCE`
指向的 `baseline-initramfs.cpio.gz`）里的 `/init` 会执行：

```sh
. /usr/sbin/samurai-rootfs || echo "[rootfs] retaining diagnostic initramfs"
```

`/usr/sbin/samurai-rootfs` 在切根前做一串严格校验：

1. 按 `PARTNAME=userdata`、PARTUUID
   `fce252a8-deb1-7d74-0dbc-bfdabfa3710a`、232486808 扇区、
   4096 字节逻辑块找到分区；
2. F2FS UUID 必须是 `32dd1191-5c73-4eb7-8d45-2213af0f2001`；
3. `ro,norecovery` 挂载后，**`/etc/samurai-rootfs-release` 必须含
   `ROOTFS_ID=samurai-f2fs-rootfs01`**，且 `/sbin/init` 可执行；
4. 之后再 `rw` 挂载并 `switch_root`。

我们刷入的 rootfs 缺第 3 项：`/etc/samurai-rootfs-release` 不存在，
于是每次都打印 `[rootfs] userspace identity/init validation failed`
并回落到诊断 initramfs 的 `while true; sleep 3600`。

同样缺的第 4 项前置是内核模块：rootfs 里没有 `/lib/modules`，
切根后 `samurai-bluetooth` 找不到 `hci_uart.ko`、Wi‑Fi 相关
`modprobe` 全部失败。

## 为什么会漏

- `samurai/finalize-rootfs.py:63` 会写这个标记，但 Plasma 路径用的是
  `finalize-plasma.py`，它没有对应代码；
- 内核 `kernel=none`，模块由打包流程之外单独提供，rootfs 生成脚本
  从未把它们装进去。

## 修复

已对 `samurai-rootfs-f2fs-partuuid.raw.img` 执行：

1. `linux-port/scripts/mark-rootfs-release.sh` 写入
   `/etc/samurai-rootfs-release`：
   ```
   ROOTFS_ID=samurai-f2fs-rootfs01
   BUILD_PROFILE=github-pmaports-samurai-userspace
   ```
2. `linux-port/scripts/install-modules-into-rootfs.sh` 装入
   `7.3.1-rmx1931-samurai-v731`（766 个 `.ko`，`modules.dep` 齐全，
   排除 `build/`、`source/` 悬空链接）。`modinfo vermagic` 为
   `7.3.1-rmx1931-samurai-v731 SMP preempt mod_unload aarch64`，与运行
   内核一致。
3. 重新生成 sparse 镜像并逐字节校验（simg → raw 哈希相同）。

同时把缺失的一步补回生成脚本：
`linux-port/scripts/patch-finalize-plasma.py` 给 `finalize-plasma.py`
加了 marker 写入，避免下次重建复发。

## 校验

`linux-port/scripts/inspect-rootfs.py` 新增切根前置检查，当前全部通过：

```
switch_root preconditions:
  OK      /etc/samurai-rootfs-release
  OK      /sbin/init -> bin/busybox
  OK      /etc/inittab runs OpenRC
  OK      kernel modules 7.3.1-rmx1931-samurai-v731
```

21 个必需包、6 个必需命令也全部 `OK`；`fsck.f2fs --dry-run` 无错误。

## 镜像

| 产物 | 大小 | SHA-256 |
| --- | --- | --- |
| `samurai-rootfs-f2fs-partuuid.simg` | 2,780,972,604 | `bff95419b11f50962a8fb943ef735e8bd7f19735c2975d93f7e3d01cdc4600c8` |

展开后 29,060,851×4096 = 119,033,245,696 字节，与 `userdata`
分区完全等长，不会溢出。`flash-plasma-rootfs.ps1` 默认哈希/尺寸已更新。

## 未完成

- **尚未刷入**：设备当前运行在 Linux（NCM 在线、`169.254.42.1`
  可 ping），但主机无法进入该系统——SSH 只接受 publickey 且该
  dropbear 实例的 `authorized_keys` 与本地私钥不匹配，也没有 adb。
  需要设备重启进 fastboot 才能执行刷写。
- 刷入后仍要验证：是否真的 `switch_root`、Plasma 首启、SSH
  （新系统是 `openssh`，密钥在 `user` 账号且属主 10000）、NCM
  DHCP 是否拿到 `172.16.42.2`。

## 第二次刷入后的状态（2026-11-15 18:0x）

切根校验已通过：USB 从调试 ramdisk 的实例变成了 rootfs 的
`0525:a4a1`（`USB\VID_0525&PID_A4A1\REALME-SAMURAI`），说明
`switch_root` 成功，系统已进入发行版。

但 NCM 仍然不通：

| 观测 | 值 |
| --- | --- |
| Windows 网卡 | `以太网 10`，`Disconnected`，`0 bps` |
| 收发字节 | `ReceivedBytes=0`、`SentBytes=0` |
| ping `169.254.42.1` / `172.16.42.1` / `10.42.0.1` | 全部超时 |
| 重启网卡、等待 2 分钟 | 无变化 |

不是 IP 配错：链路层就是 0 字节，host 从未收到任何以太网帧。

### 设备端原因

`community/usb-signaller` 的 `0009-usb-signaller-activate-only-with-carrier.patch`
让 developer-mode 脚本只在 `carrier=1` 时才激活 NetworkManager 连接：

```sh
if carrier_is_up; then
    activate_connection
else
    echo "NetworkManager will activate $IFACE when carrier appears"
fi
```

而 `0005` 让 gadget 在 host 只做了 address、未做
`SET_CONFIGURATION` 时保持模式（不降级），此时 `usb0` 的
carrier 一直是 0。于是：

1. `usb-signaller` 建好 gadget，host 枚举出 NCM 接口；
2. carrier 不升，developer-mode 不激活连接；
3. `usb0` 没有地址、也没有 `ip link set up`；
4. host 侧看到 `0 bps / 0 bytes`。

另外 `usb-signaller-developer-mode` 声明 `need net`，而 rootfs 里
没有名为 `net` 的独立服务（只有 `networking` / `networkmanager`
以 `provide net` 提供），启动时序也可能让该服务整体失败。

### 修复（已写入新镜像）

新增 `samurai-ncm-fallback`（`linux-port/scripts/samurai-ncm-fallback.initd`）：

- `after usb-signaller`、`before unudhcpd.usb0`；
- 等 `usb0` 出现后无条件 `ip link set usb0 up`；
- 补上 `169.254.42.1/16` 与 `172.16.42.1/24` 两个地址；
- 不依赖 NetworkManager / nmcli，也不与它抢管理权。

安装脚本 `linux-port/scripts/install-ncm-fallback.sh`：

- 装 initd、加入 `boot` 与 `default` runlevel；
- 在 apk 数据库登记包信息与 3 个文件条目，保持与磁盘一致。

镜像：`2,781,005,596` 字节，SHA-256
`b64ae5fa99106cd85cdcc887403fc02bbbb061b24ebfaa43f6577267bdf041f1`。
`fsck.f2fs --dry-run` 无错误，1091 个包。

### 一次性和常驻的区别（2026-11-15 18:5x）

首次尝试的兜底服务是一次性的，放在 boot runlevel。`usb-signaller`
在 boot 服务之后才创建 gadget，所以该服务启动时 `usb0` 还不存在，
直接返回成功；同名服务在 default runlevel 也不会再跑一次。因此
`usb0` 从头到尾没有被配置过。

改为常驻 watchdog（`samurai-ncm-watchdog`，由 `supervise-daemon` 托管）：

- 每 5 秒检查 `/sys/class/net/usb0`，出现就 `ip link set up`；
- 补 `169.254.42.1/16` 与 `172.16.42.1/24`；
- carrier 连续 25 秒为 0 时，对 UDC 做一次 `soft_connect`
  （`disconnect` → `connect`），每次 gadget 生命周期最多一次，
  避免 2026-11-13 那种 carrier 抖动引发的复位自激；
- 日志写入 `/var/log/samurai/ncm-watchdog.log`。

已确认的盲区：`samurai-usb-recover` 在文档和代码里都把
**“`state=configured` 且 `carrier=0`”** 当作正常链路空闲，
明确不触发任何恢复（`docs/USB-ENUM-RECOVERY-20261113.md` 记录过
这是为了防止 Windows 切换 NCM alt setting 导致复位循环）。所以
这个状态下没有任何现有服务会介入，必须由 watchdog 兜底。

### 另一个被忽略的配置项

`/etc/usb-signaller.d/90-samurai.toml` 里的 `ncm_qmult = 20` 从未
生效：`usb-signaller` 的 `Configuration` 结构只反序列化
`main.default_mode` 与 `mass_storage.storage_path`，没有 `gadget` 表。
历史上为解决 Windows NCM 批量传输停顿而加的 qmult 调优其实是空操作。

### 第三次刷入（2026-11-15 19:07）

写入完成：`flash complete`，镜像
`5997fa1e75c7e23530c319920603d13000e17dda983e4156073d7e4bc8b13123`
（2,781,058,816 字节）。随后 `fastboot reboot` 再次挂死：

```
fastboot -s 62bc28a1 reboot
Rebooting ... FAILED (usb_read failed: 连到系统上的设备没有发挥作用。 (31))
```

之后 4 分钟内设备一直枚举为 `Android Bootloader Interface`，
`fastboot devices` 串号是 `????????????`，`getvar` 返回
`AdbWriteEndpointSync failed (121)`。与第一次刷入后的现象一致：
**写入成功，但 bootloader 的 USB 通道在 2.7 GB 写完后挂死**。

这不是镜像问题：同一镜像本次也通过了哈希/尺寸/分区校验。需要现场
长按电源 15 秒强制断电再开机。

### 刷入后脚本改进（2026-11-15 19:2x）

`fastboot reboot` 已连续三次在 2.7 GB 写入后挂死这个 bootloader：

| 次数 | 现象 |
| --- | --- |
| 第 1 次 | `usb_read failed (31)`，设备停在 bootloader，`getvar` 全部 121 |
| 第 2 次 | 同上 |
| 第 3 次 | 同上 |

因此 `flash-plasma-rootfs.ps1` 改为**默认不自动 reboot**：写完后只提示
“长按电源 15 秒强制断电再开机”，需要时用 `-Reboot` 显式要求。写入本身
从未失败，失败的一直是可选的 reboot 步骤。

同时修了 watchdog 的一个真实缺陷：gadget 重绑会**重建同名 netdev**
（Windows 侧 `ifIndex` 从 31 变 6 就是证据），旧逻辑只在
`/sys/class/net/usb0` 消失时重置“已配置”标记，重建后不会重新配地址。
新逻辑用 `readlink -f /sys/class/net/usb0` 检测实例变化。

### 当前阻塞（2026-11-15 19:30）

设备停在 `Android Bootloader Interface`，持续约 25 分钟未恢复：

- `fastboot devices` → `???????????? fastboot`
- `getvar product` → `AdbWriteEndpointSync failed (121)`
- `fastboot continue` / `fastboot reboot` → 同样 121
- Windows `Disable-PnpDevice` / `Enable-PnpDevice` → “常规故障”
- EUD：`eudtool.exe` 报 `EUD not enabled`
- EDL：无 `VID_05C6`/`9000`/`9501` 设备

主机侧已无可用的唤醒手段，必须现场长按电源强制断电。

待刷镜像已就绪：`83822734f29d30cf94abc382056857b49a244577438b73bdceae56fa67001a52`
（2,781,058,872 字节，含增强版 watchdog 与 netdev 重建检测）。
