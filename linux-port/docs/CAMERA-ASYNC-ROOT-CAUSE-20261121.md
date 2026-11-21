# 相机 media graph 无链接：根因与修复（2026-11-21）

## 现象

`/dev/media0` 有 27 个实体，`qcom-camss` probe 正常，4 个 sensor 驱动全部 bound，
但每个 sensor 的 `links` 都是 0：

| 实体 | pads | links |
|---|---|---|
| `msm_csiphy0..3` | 2 | 2（只连 csid） |
| `msm_csid0/1` | 5 | 8 |
| `msm_vfe*` | 2 | 1 |
| `s5kgw1 6-0010` | 1 | **0** |
| `imx319 7-0010` | 1 | **0** |
| `s5k3m5 8-002d` | 1 | **0** |
| `imx471 9-0010` | 1 | **0** |
| `lc898219xi 6-0072` | 0 | 0 |

工具：`linux-port/scripts/media-links.py`（`MEDIA_IOC_ENUM_LINKS`，指针式
`struct media_links_enum`）。

## 三条被推翻的假设（记录以免重犯）

### 1. 不是 `bus-type` 缺失

`v4l2_fwnode_endpoint_parse()` 在缺 `bus-type` 时会把 `vep->bus_type`
兜底成 `V4L2_MBUS_CSI2_DPHY`（`v4l2-fwnode.c:237-238`），不报错。
而且唯一带 `bus-type` 的 `s5kgw1` 同样 `links=0`，直接证伪。

### 2. 不是 `camss_parse_ports()` 失败

它只遍历 camss 自己的 `ports/port@N/endpoint`（4 个都带 `bus-type`）；
失败会 `goto err_v4l2_device_unregister` 让 probe 整体失败，
而实机 probe 成功、`media0` 存在。

### 3. 不是"`flash-leds` 指向另一个 v4l2_device 所以永远匹配不上"

这个推断一度看起来成立，但检查 `leds-qcom-flash.c` 后发现
`qcom_flash_v4l2_init()` 收到的是 `led-0` 自己的 fwnode，而
`v4l2_flash_init()` 里 `v4l2_async_register_subdev()` 会按 fwnode 正常
参与匹配。只要该编译分支存在，`flash-leds` 就能被匹配上。

**所以 DTS 里的 `flash-leds` 是正确的，不该删。**

## 真正根因

```
$ grep CONFIG_V4L2_FLASH_LED_CLASS linux/.config
# CONFIG_V4L2_FLASH_LED_CLASS is not set        ← 而仓库规范是 =m
```

`CONFIG_V4L2_FLASH_LED_CLASS` 关闭时，`drivers/leds/flash/leds-qcom-flash.c`
编译的是 `#else` 分支的空实现：

```c
#else
static int
qcom_flash_v4l2_init(struct device *dev, struct qcom_flash_led *led,
                     struct fwnode_handle *fwnode)
{
	return 0;          /* 不注册任何 v4l2_flash 子设备 */
}
#endif
```

于是在 v4l2-async 看来：

```
sensor 子 notifier 里 flash-leds 这条连接 → 永远没有对应的 subdev 可以匹配
                                          → waiting_list 永久非空
                                          → v4l2_async_nf_can_complete() = false
                                          → camss_subdev_notifier_complete() 不执行
                                          → media_create_pad_link(sensor → csiphy) 从未调用
                                          → 4 个 sensor 全部 links=0
```

### 二进制层面证实

```
$ aarch64-linux-gnu-nm -u drivers/leds/flash/leds-qcom-flash.ko | grep v4l2_flash
  (空)                          ← 旧 .ko：stub 路径
```

重编后：

```
$ aarch64-linux-gnu-nm -u ... | grep v4l2_flash
                 U v4l2_flash_init
                 U v4l2_flash_release      ← 真实路径
```

### 为什么仓库规范配置里有、实际内核没有

| 符号 | 运行内核 | 仓库 `samurai-standard.config` |
|---|---|---|
| `CONFIG_V4L2_FLASH_LED_CLASS` | **n** | `m` |
| `CONFIG_MFD_SPMI_PMIC` | 缺失 | `y` |
| `CONFIG_LEDS_QCOM_FLASH` | `m` | `m` |
| `CONFIG_ARCH_QCOM` | 缺失 | `y` |

内核树里的 `.config` 只有 2348 行且缺 `ARCH_QCOM`，是个被打坏的半截文件；
真正的上次构建配置在 `include/config/auto.conf`（2894 行，含
`ARCH_QCOM=y` / `MFD_SPMI_PMIC=y` / `LEDS_QCOM_FLASH=m`，但同样**没有**
`V4L2_FLASH_LED_CLASS`）。

### `-usbwake-otg` 是故意的，不是野构建

`build-kernel-regdb.sh` 明确设置了 `FLAVOR=-usbwake-otg`：

```
# make's LOCALVERSION is *appended* to CONFIG_LOCALVERSION, so passing it
# here yields 7.3.1-rmx1931-samurai-v731-usbwake-otg
FLAVOR=-usbwake-otg
```

那次构建用的正是仓库的 `configs/v7.3.1/samurai.config`，
而该文件**确实写着** `CONFIG_V4L2_FLASH_LED_CLASS=m`。

### 所以丢在哪一步

重放验证（用仓库配置 + 当前工具链）：

```
cp samurai.config .config
make olddefconfig
→ CONFIG_V4L2_FLASH_LED_CLASS=m     仍保留
→ CONFIG_ARCH_QCOM=y / MFD_SPMI_PMIC=y / LEDS_QCOM_FLASH=m  仍保留
```

即 `olddefconfig` 不会关掉它。结论：**那次构建用的 `.config` 在进入
`make` 之前就已经缺这一项**（构建脚本只校验了 `INITRAMFS_SOURCE`，
没有校验这条链路，所以静默通过）。

这正是"清洁构建"要堵的洞：把断言加到构建脚本里。

## 修复

不碰 DTS。用仓库规范配置重建，并补上 vermagic：

```sh
cp linux-port/configs/v7.3.1/samurai-standard.config  linux/.config
scripts/config --set-str LOCALVERSION "-rmx1931-samurai-v731-usbwake-otg"
make syncconfig
make -j8 modules
```

`LOCALVERSION` 取 `-rmx1931-samurai-v731-usbwake-otg` 是因为**当前跑着的**
内核 vermagic 就是它；仓库配置里的 `-rmx1931-samurai-v731` 是干净基线值。
在没重刷 boot 之前，模块 vermagic 必须跟运行内核一致，否则 `insmod` 拒绝。

产出三个模块（vermagic 已核对为
`7.3.1-rmx1931-samurai-v731-usbwake-otg SMP preempt mod_unload aarch64`）：

| 模块 | 作用 |
|---|---|
| `drivers/leds/led-class-flash.ko` | `led_set_flash_*` 符号提供者 |
| `drivers/media/v4l2-core/v4l2-flash-led-class.ko` | `v4l2_flash_init()` 提供者 |
| `drivers/leds/flash/leds-qcom-flash.ko` | 真正注册 flash 子设备 |

## 验证方法（必须实机）

```sh
python3 linux-port/scripts/media-links.py /dev/media0
```

判定标准：

1. 出现 flash 实体（`MEDIA_ENT_F_FLASH`，名字含 `white:flash`）
2. 4 个 sensor 的 `links` 从 0 变 1
3. 出现 `sensor[p] -> msm_csiphy[n][0]` 且 flags 含
   `MEDIA_LNK_FL_IMMUTABLE | MEDIA_LNK_FL_ENABLED`

## 交付物

### 修复后的 rootfs 镜像

```
E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261121-camflash\
    samurai-stable-f2fs-partuuid.simg

bytes   3,644,494,976
sha256  42dfdf9f06cb8e446f56f53d34d21fa228b7917b78c0ce78e09fc4d6c2f4185d
```

基线是 `rootfs-stable-20261119-clean`（`5e69d0ae…`，3,644,249,048 B）。
只改动了 `lib/modules/7.3.1-rmx1931-samurai-v731-usbwake-otg/`：

| 文件 | 改前 | 改后 |
|---|---|---|
| `kernel/drivers/leds/flash/leds-qcom-flash.ko` | 18,456 B（stub 路径） | 104,824 B（真实路径） |
| `kernel/drivers/leds/led-class-flash.ko` | 16,208 B | 69,736 B |
| `kernel/drivers/media/v4l2-core/v4l2-flash-led-class.ko` | **缺失** | 90,824 B |
| `modules.dep` | 无 v4l2 依赖 | 补上 `v4l2-flash-led-class.ko` 依赖 |

离线验收：

- 三个 `.ko` vermagic 均为 `7.3.1-rmx1931-samurai-v731-usbwake-otg SMP preempt mod_unload aarch64`
- `nm -u leds-qcom-flash.ko` 可见 `U v4l2_flash_init` / `U v4l2_flash_release`
- `/etc/os-release` 仍是 `postMarketOS v26.06`
- 镜像内 `modules.dep` 已含 `leds-qcom-flash.ko: led-class-flash.ko v4l2-flash-led-class.ko`

注意：镜像里同时存在 `7.3.1-rmx1931-samurai-v731` 与
`…-usbwake-otg` 两套 modules 目录；运行内核是后者，所以只改了后者。
前者是仓库基线配置的目录，等重刷 boot 换成基线内核后才需要同步。

### boot 侧：必须恢复原镜像

早前把一个"删掉 flash-leds"的 DTB 打进 boot 镜像属于**误判**，
而且那次写入已经把 `boot` 分区覆盖了。真正修复在 rootfs 的模块里，
boot 不需要任何改动，必须刷回原镜像：

```
设备上备份: /root/boot-backup-20261121.img
md5        84476cf0d61cdb7358064ab9d154ec07   ← 与原始 boot 一致
分区       /dev/sde11 (100 663 296 B)
```

恢复命令（设备可达时）：

```sh
printf '12345678\n' | sudo -S -p '' sh -c \
  'dd if=/root/boot-backup-20261121.img of=/dev/sde11 bs=1M conv=fsync && sync'
```

`linux-port/dts/split-ba61/s5kgw1-samurai.dtsi` 与
`linux-port/patches/v7.3.1/0002-…camera-stack.patch` 里的 `flash-leds`
都已回滚到原状（补丁 136 hunk 自洽）。

## 新增门禁

`linux-port/scripts/_wsl-samurai/check-flash-modules.sh IMG`：

- 只校验与部署内核匹配的那套 `<release>-usbwake-otg` modules 目录
- 要求 `leds-qcom-flash.ko`、`v4l2-flash-led-class.ko` 同时存在
- 要求 `leds-qcom-flash.ko` 内含 `v4l2_flash_init` 引用（非 stub）

实测：旧镜像 FAIL、新镜像 PASS。

`check-rootfs.py` 也加了同样的断言（在文件末尾，需 `--packages` 指向真实
构建产物才能跑到那一步）。

`build-kernel-regdb.sh` 新增配置链路断言：`olddefconfig` 之后必须同时满足

```
CONFIG_V4L2_FLASH_LED_CLASS  = m|y
CONFIG_LEDS_CLASS_FLASH      = m|y
CONFIG_LEDS_QCOM_FLASH       = m|y
CONFIG_MFD_SPMI_PMIC         = m|y
CONFIG_ARCH_QCOM             = m|y
```

任一不满足即 `exit 1`，不再让缺 flash 子设备的内核静默产出。
实测：仓库 `samurai.config` 通过，去掉 `V4L2_FLASH_LED_CLASS` 的副本会中止。

## 镜像改动审计（boot 侧）

早前把一个"删掉 flash-leds"的 DTB 打进 boot 镜像属于**误判**。
该改动已回滚：`s5kgw1-samurai.dtsi` 与 `0002` 补丁都恢复 `flash-leds`。

若最终仍需重刷 boot，可复用
`linux-port/scripts/_wsl-samurai/patch-boot-dtb.py`；它对两份 boot 镜像做过
逐文件比对（`compare-fv-files.py`）：

```
outer: 3 files  → identical 2, differ 1 (FVMAIN 容器)
inner: 101 files → identical 100, differ 1 (DTB)
```
