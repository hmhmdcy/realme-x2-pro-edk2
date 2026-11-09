# 蓝牙 PAN/HID 主线模块候选

整理日期：2026-11-09。

Wi‑Fi、CDC NCM、SSH 已作为回归门禁保留；本候选属于后续硬件适配，
只补 Linux v7.3.1 已存在但当前未编译的三条主线路径：

- `CONFIG_BT_BNEP=m`：Bluetooth PAN/BNEP；
- `CONFIG_UHID=m`：BlueZ 用户态 HID 传输；
- `CONFIG_INPUT_UINPUT=m`：BlueZ HID 使用的用户态 input 注入。

没有新增板级驱动、私有 ioctl、Android HAL、Binder 入口、服务脚本或
安装 hook。签名包已安装，三条模块在普通重启后由标准启动路径自动加载，
BNEP socket、`/dev/uhid`、`/dev/uinput` 和 BlueZ `hci0` 均通过。
没有外部 PAN/HID 对端，不能据此声称 PAN 或 HID 业务已验收。

## 候选收据

主目录：
`E:/edk2-samurai-out/standard-arm64-v731/bluetooth-host-20261109/`

| 产物 | SHA-256 |
| --- | --- |
| `samurai-bluetooth-host-0.1.0-r0.apk` | `a4cbe10a1a7a5b6e13ba01bf2a27e64663a0e290c2fd168c54e2b17f44a4be5e` |
| `packages.adb` | `5d4f43e3f99eabb74d9eff60e94402df05608c1d1065f420a24408fb251c34ae` |
| `package-manifest.json` | `7a12f03f21b03a538448fa5a6bbc1cab8d82f5a00c3c345aa0ae5ad9eae1fbf3` |
| `verification.json` | `32497f8daf5d624afeac860650f0b007808d1b615fe9e06f56460c1dff85cddb` |
| `samurai-linux-203.rsa.pub` | `dbfa32c3c97d5624e558547ec6e47725f77a1f4f0569455288f79ca66269bbc3` |

模块载荷：

| 模块 | 字节 | SHA-256 | 用途 |
| --- | ---: | --- | --- |
| `bnep.ko` | 26696 | `aa2e7affa0bc7238a61a0bdfc190be533f6382ea21eaebf88b3419301a412b74` | Bluetooth PAN |
| `uhid.ko` | 18232 | `a5e72e3ed257c978e35fe12dcb18784d790f96c059c37cc09576b813d57ceea0` | BlueZ HOG/用户态 HID |
| `uinput.ko` | 22896 | `d5a94b699e33aef2835a0ba5e2f419574f7da3c643ade9d8f2ed4be781029bbb` | 用户态 input |

三者均为 AArch64 `ET_REL`、`intree=Y`、空依赖，vermagic 为：

```text
7.3.1-rmx1931-samurai-v731 SMP preempt mod_unload aarch64
```

构建基线为提交
`824dc0a56143d8bf1cc1d20adb877abced48b336`，使用已部署 v7.3.1
构建树的 `Module.symvers`
`77338912db077834f4e7762ed49638a64fe5e15defdc9cccc0482f1396cd2583`。
配置语义差异只有上述三项 `n -> m`；BNEP 两个默认关闭的 filter 仍为
`n`，没有其他配置变化。模块以 `W=1 KCFLAGS=-Werror` 重编，日志无
warning/error，所有导入符号都在该符号表中存在。

两份独立构建目录
`bluetooth-host-20261109/` 与 `bluetooth-host-20261109-r2/` 的 APK、
索引、manifest 和公钥逐字节一致；两份 `verification.json` 也逐字节
一致。

## 官方用户态边界

Alpine 官方 `bluez` APKBUILD 把 `modules-load.conf` 安装为
`/usr/lib/modules-load.d/bluez.conf`，内容为 `uinput`、`uhid`：

- APKBUILD：
  `https://gitlab.alpinelinux.org/alpine/aports/-/raw/master/main/bluez/APKBUILD`
  SHA-256 `5be80828b55c4c025dbaae70b5730cbc34e20a45d8443bf6aa97e9a2cd86ebfd`；
- modules-load.conf：
  `https://gitlab.alpinelinux.org/alpine/aports/-/raw/master/main/bluez/modules-load.conf`
  SHA-256
  `cd595ebf65d1a45b0007dde6343a60b6d34e123ee27f291ce3111c7606d249f7`。

因此候选不复制 `bluez.conf`，也不新增 modules-load 文件。`bnep` 在
主线 `net/bluetooth/bnep/core.c` 中带 `MODULE_ALIAS("bt-proto-4")`，
BlueZ 建立 PAN 协议 socket 时可走标准模块别名加载。实际 kmod
`modules.order`/`modules.dep` 是否在当前 rootfs 正确更新，仍需设备
在线后只读确认。

## 构建与独立验证

构建器和独立 verifier 在仓库中：

- `linux-port/scripts/build-bluetooth-host-package.py`
  SHA-256 `b60488a53337bdbd6ba9ffe48f8b16fc136e336ae5d6f27b4c882d80cf140466`；
- `linux-port/scripts/verify-bluetooth-host-package.py`
  SHA-256 `05309d406bb5817d9079b064473621dd42f3763b80be4d16db83b1acad7ee6d6`；
- 设备运行时探针 `linux-port/scripts/test-bluetooth-host.py`
  SHA-256 `e753ade318f011f00bf3648b921f6541e160109c055905245989cba7aa12cf9d`。

独立 verifier 重新验签 APK 与索引、解析 APKv3 数据块、逐字节比对
三个模块、在全新隔离 APK 根中安装，并核对文件模式、root 所有权、
owner、版本和失败标志。两轮均 `passed=true`。

离线签名/载荷/隔离安装验证之外，2026-11-09 已在手机上完成安装和
普通重启后的加载验证。没有证明外部 BlueZ 对端、PAN 路由、HID 配对、
冷启动或休眠恢复。

## 设备安装与普通重启验收

实际安装与探针结果：

- `apk verify`：OK，使用手机已有 `samurai-linux-203` 公钥；
- `apk add --no-network`：只安装 `samurai-bluetooth-host-0.1.0-r0`，
  没有升级无关包；模块总数从 774 变为 777；
- 安装后第一次 `modprobe` 前需要标准 `depmod -A` 刷新
  `modules.dep`；`modloop` 在启动早期已经执行该步骤，所以普通重启后
  不需要手工 depmod；
- 普通重启 boot ID `071abbb5-88bd-4c8a-879a-ab9906387617`；
- `bnep`、`uhid`、`uinput` 均自动加载；
- `/dev/uhid`、`/dev/uinput` 可打开，BNEP socket family 4 可创建；
- BlueZ 暴露 `hci0` / `PRIVATE_BT_MAC`，重启后 `Powered=false`
  只是在没有业务时的默认省电状态；
- NCM SSH 39.764 秒、Wi-Fi SSH 64.487 秒恢复；
- `flash-led-v4l2 + bluetooth-host` 完整 gate 通过：777 模块、四路
  相机、闪光灯、thermal、网络、服务、CAMSS/MMCX 空闲和 `taint=0`。

早期探针曾把 `modprobe bnep uhid uinput` 作为一个命令调用，BusyBox
`modprobe` 会把后两个名字当作 `bnep` 参数；现已改为逐模块调用。这个
问题只影响探针，不影响官方启动路径。

## 单变量验收命令

先确认 Wi‑Fi/NCM/SSH 回归门禁、当前 boot ID、`taint=0` 和分区回读
未变。安装不能与闪光灯、私有层或其他内核候选混成一轮。

```sh
# 仅在 /etc/apk/keys/samurai-linux-203.rsa.pub 已存在时安装
apk add --no-network /path/to/samurai-bluetooth-host-0.1.0-r0.apk
apk info -L samurai-bluetooth-host
sha256sum /usr/lib/modules/7.3.1-rmx1931-samurai-v731/kernel/net/bluetooth/bnep/bnep.ko
sha256sum /usr/lib/modules/7.3.1-rmx1931-samurai-v731/kernel/drivers/hid/uhid.ko
sha256sum /usr/lib/modules/7.3.1-rmx1931-samurai-v731/kernel/drivers/input/misc/uinput.ko
```

预期只新增三个模块，不升级其他包。然后经 SSH stdin 运行探针，避免
依赖设备端预先存在的脚本：

```powershell
ssh root@192.168.0.114 'python3 - --load --output /tmp/bluetooth-host.json' `
  < linux-port/scripts/test-bluetooth-host.py
```

探针只验证：

- release、模块文件、vermagic、`intree=Y`、空依赖；
- `/dev/uhid`、`/dev/uinput` 可打开；
- BNEP socket family 可创建；
- `/usr/lib/modules-load.d/bluez.conf` 存在；
- BlueZ adapter 存在。

没有配对、PAN peer 或 HID peer 时，`Scope` 明确写“未声称业务”。
普通重启后运行不带 `--load` 的探针，确认官方 `bluez.conf` 已在启动时
加载 `uinput/uhid`；BNEP 可在需要时由别名加载。实际结果同时记录了
Wi‑Fi/NCM/SSH、四路 RAW、`taint=0` 和无新 WARN/Oops。

真正的 PAN 对端、BLE HID 对端、路由/输入回退、外部事件唤醒和拔电
冷启动是独立验收项；没有对端证据时不能写成“蓝牙 PAN/HID 已通过”。

## 回退

本包不改 `boot`、DTB、Image、NV、persist、校准或 userdata。设备侧
回退只删除安装包：

```sh
apk del samurai-bluetooth-host
```

模块正在被 BlueZ 或用户态占用时不要强制 `rmmod`；普通删除包后由下一次
重启清除加载状态。若安装后出现新的网络回归，应先停止安装/加载、
保留 dmesg，再按 `samurai-platform` 既有回退流程恢复，不与闪光灯或
私有层候选混测。
