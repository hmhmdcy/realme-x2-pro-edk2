# 卡在 EDK2 进不去 Linux：boot 分区 DTB 被替换（2026-11-21）

## 结论

设备停在固件界面、无 SSH、无 NCM，**不是内核或 rootfs 坏了**，而是
`boot` 分区（`/dev/block/sde11`）里的 DTB 被换成了另一份不完整的设备树。

原版 boot 与本轮误刷的 boot **只有 DTB 一个文件不同**，其余 100 个 FFS
文件与整个 BootShim/FV 容器逐字节一致。

## 证据链

### 1. 分区内容

| 分区 | 大小 | md5 | 结论 |
|---|---|---|---|
| `boot`（`/dev/block/sde11`） | 100,663,296 B | `c8088b065b59f29b84b816704ca61094` | **= 本地 `boot-fixed.img`（误刷的那份）** |
| 原版 boot（`boot-cur.img`） | 100,663,296 B | `84476cf0d61cdb7358064ab9d154ec07` | 与 `realme-x2-pro-releases-assets-20261114` 里的 `boot-eud-production-off.img` 完全相同 |
| `logdump`（`/dev/block/sde32`） | 67,108,864 B | sha256 `56c8379b…` | 与本地 `logdump-candidate-20261120.img` 完全相同 |

对应 sha256：

```
boot-cur.img      4520915183bbdf91bf606c1f2c711097a7a686c5e4666298e8bd1665a44036f1
boot-fixed.img    46c94d33f9c8b18a74c919f7d6df0168ca44a226e7481838c0db77baa1506524
logdump-dev.img   56c8379be00d5a1678f736a18af488a15b05bb3cc398120b2c1c34cb7949a0a0
logdump-live       125436109e7bb950bf608610ffc3dca656638764e695f52eda843eaf16d70dbb
```

### 2. 逐文件比对（`compare-fv-files.py`）

```
外层 FV：  3 个文件   -> 相同 2，不同 1（FVMAIN 容器）
内层 FV：101 个文件 -> 相同 100，不同 1（DTB）
                          DIFF 25462cda-221f-47df-ac1d-259cfaa4e326
```

即：固件、BootShim、BdsDxe、UiApp、SMBIOS 全都没变。

### 3. logdump 侧完好

`logdump` 里只有两个文件，都是 11-20 验证过能启动的那一份：

| 文件 | 大小 | sha256 |
|---|---|---|
| `/Image` | 58,673,664 B | `7b98edbcb6e31ebb9bc4df2f0713409c9cedcf3b9ad4620a97daeec575b9144e` |
| `/samurai.dtb` | 114,928 B | `9ca1d2f9b170ebc4913d8dd0ea16442bef0556b76f9d18b3d0393870d1167162` |

`Image` 头部 `arm64 magic = 0x644d5241`、`image_size = 60,293,120`
（< 64 MiB 分区上限），内嵌 15,068,393 B gzip initramfs（含
`regulatory.db`），版本串 `7.3.1-rmx1931-samurai-v731-usbwake-otg`。
这份 Image 在 11-20 实机验证过：`iw phy phy0 reg get` 为
`country US`、`systemctl --failed` 为 0。

### 4. rootfs 完好

recovery 内直接可见 F2FS `userdata`（`/dev/block/sda16`，119,033,245,696 B）：

```
/data/sbin/init              -> ../lib/systemd/systemd
/data/etc/os-release         -> ../usr/lib/os-release
/data/etc/samurai-rootfs-release   存在（80 B，2026-11-17）
/data/boot                   不存在（启动链不依赖 rootfs 里的 /boot）
```

最后一次正常关机由 journal 记录：

```
systemd-shutdown, "Journal stopped", SYSLOG_TIMESTAMP=Nov 21 03:02:43
```

之后每次重启都没有再进入系统。

## 设备 DTB 与原版 DTB 的差异

两个 DTB 解出后转 DTS 比对（忽略 phandle 重编号）：

| 属性 | 原版 DTB | 手机当前 DTB |
|---|---|---|
| `typec@1500` | `status = "okay"` | **`status = "disabled"`** |
| `typec@1500/connector` | 存在（`usb-c-connector`、`power-role=dual`、`data-role=dual`、`vbus-supply`） | **整个节点不存在** |
| `usb@a600000` | `dr_mode="otg"` + `usb-role-switch` + `role-switch-default-mode="peripheral"` | `dr_mode="peripheral"`，无 role-switch |
| `cci/i2c-bus@0/camera@10` | 有 `flash-leds` | 无 `flash-leds` |
| `soc@0/ethernet@20000` | 无 | 多出该节点（`status="disabled"`） |
| `pmic@2/pon@800` | `okay` | `disabled` |

### 为什么会生成这样一份 DTB

本轮排查时用**内核树当前状态**重新编译 DTS（`build-fixed-dtb.sh` →
`apply-camera-fix.py` → `dtc`），得到的正是这份“缺 typec connector、
`dr_mode=peripheral`”的 DTB。根因在于：

- 内核树 `/home/cy122/x2pro-linux/linux/arch/arm64/boot/dts/qcom/pm8150b.dtsi`
  里 `pm8150b_typec` 默认就是 `status = "disabled"`；
- `sm8150-samurai-common.dtsi` 里**没有** typec / usb 的 board overlay
  （`grep pm8150b_typec|typec@1500|usb-role-switch|dr_mode` 均为空）；
- 原版可启动 DTB 是历史会话**逐点打补丁**生成的，不是这棵源码树的直接产物。

所以“用源码树重编译整份 DTB”这个动作本身就会丢掉 typec/usb 的板级描述。
本轮把它误当成“只删了 flash-leds”，实际是整份 DTB 被换成了另一个版本。

## 修复

只还原 boot，不动 logdump、不动 userdata：

```sh
# 设备（recovery，root）
dd if=/dev/block/sde11 of=/data/boot-broken-20261121.img bs=1M   # 先留证
# 主机把 boot-cur.img push 到 /data，然后
dd if=/data/boot-cur.img of=/dev/block/sde11 bs=1M conv=fsync
sync
md5sum /dev/block/sde11     # 期望 84476cf0d61cdb7358064ab9d154ec07
```

本地镜像：

```
E:\wsl-recover\work\boot-cur.img
  md5    84476cf0d61cdb7358064ab9d154ec07
  sha256 4520915183bbdf91bf606c1f2c711097a7a686c5e4666298e8bd1665a44036f1
  大小   100,663,296 B（与分区逐字节等长）
```

## 排查工具（本轮新增，`E:\wsl-recover\work\`）

| 脚本 | 用途 |
|---|---|
| `dtb-diff-20261121.sh` | 从两份 boot 里提取 DTB |
| `dtb-decompile-20261121.sh` | dtb → dts |
| `dtb-sem3.py` | 按节点路径比对，phandle 解析为节点路径后忽略重编号 |
| `dtb-typec-orig.sh` / `dtb-typec-dev.sh` | 打印两侧 typec 节点 |
| `logdump-inspect-20261121.sh` | 只读挂载 logdump，列文件与哈希 |
| `logdump-image-inspect.sh` | 校验 `Image` 的 arm64 头与 initramfs |
| `fv-kernel-20261121.sh` | 校验 FV 层文件与内核 FFS 是否变化 |
| `kern-tree-dts-check.sh` | 核对内核树里 DTS 的当前状态（确认源码已被改） |

## 仍未做

1. **尚未执行还原**。本轮只做到了定位与取证；设备目前在 recovery。
2. 还原 boot 后需要再确认一次能否进 Linux；如果仍不行，再用
   `logdump-live-20261120.img`（sha256 `125436109e7b…`）做对照。
3. 相机 flash 的模块修复已在新镜像里（见 `DELIVERY-20261121.md`），
   但实机验证仍未做。
