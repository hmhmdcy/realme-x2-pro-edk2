
---

## 19. 内核命令行进了 boot option 的 LoadOptions（2026-10-07 14:4x）

### 19.0 TL;DR

内核命令行现在**同时**存在于两个地方：设备树的 `/chosen/bootargs`（原来就有）和
"Linux (mainline samurai)" 这个 boot option 的 **LoadOptions**（本次新增）。两者逐字
相同，正常路径下行为不变；设备树万一没带上 bootargs，内核仍然拿得到 `console=` 和
`earlycon=`，不会变成"选了启动项、黑屏、EUD 里 0 字节"。

新产物（**尚未上真机**——手机当前没有连接：adb 无设备，Windows 上也没有 VID_05C6）：

| 文件 | 大小 | sha256 |
|---|---|---|
| `E:\edk2-samurai-out\boot-samurai-linux-cmdline.img` | 15,185,920 | `b9fb2064e10f9fa8b77c04c5e5062ac1ba6362051a2390e1d4783b3c01900619` |
| `E:\edk2-samurai-out\SM8150_UEFI-samurai-linux-cmdline.fd` | 20,971,520 | `b02b55a1c8fd6bb6295fa559af99e3a3bdd22381ac8af0ac52c7d3861f3eb4ad` |

EDK2 提交 `c2a3697`，已 push 到 fork `hmhmdcy/edk2-realme-x2-pro` 的 master。

### 19.1 为什么这不是"顺手加固"，而是必修

`update_fdt()`（`drivers/firmware/efi/libstub/fdt.c`）里只有一句：

    if (cmdline_ptr != NULL && strlen(cmdline_ptr) > 0)
            fdt_setprop(fdt, node, "bootargs", cmdline_ptr, strlen(cmdline_ptr) + 1);

即 **EFI 命令行非空时，它整段替换设备树的 `/chosen/bootargs`**。而修改前
`PlatformRegisterFvBootOption()` 根本没有 OptionalData → LoadOptions 恒为空 →
内核 100% 依赖设备树的 bootargs。这就是单点故障：设备树这一环出任何问题（DTB 没装上、
`chosen` 被裁掉），`console=tty0` 和 `earlycon=eud,mmio,0x88e0000` 会一起消失，现象与
§18.3 B.2 描述的一模一样。现在这条备胎补上了，`console=` / `earlycon=` 不再只有
一个来源。

### 19.2 必须记住的坑：LoadOptions 是 UTF-16，不是 ASCII

libstub 的 `efi_convert_cmdline()` 把 LoadOptions 当 **UTF-16** 读（`efi_char16_t *`，
最后用 `snprintf(..., "%.*ls", ...)` 转成 ASCII）。按 ASCII 塞进去的后果是：

- 每两个 ASCII 字节被当成一个 UTF-16 码元 → 解出一串乱码；
- 这段乱码**非空**，于是按 19.1 的逻辑**覆盖**掉设备树里本来正确的 bootargs；
- 正好亲手制造出它要防的那个故障（黑屏、EUD 无输出）。

所以 `PlatformBm.c` 里用 `STATIC CHAR16 mSamuraiLinuxCmdLine[] = L"…"`，不是 `CHAR8`。
`verify-cmdline-firmware.py` 专门有一条检查："FVMAIN 里唯一的 ASCII 副本必须落在设备树
内部"——代码侧只允许出现 UTF-16。

### 19.3 改了什么

`Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c`：

- `PlatformRegisterFvBootOption()` 增加第 4 个参数 `CHAR16 *CommandLine OPTIONAL`；
  非空时 `OptionalDataSize = (StrLen(CommandLine) + 1) * sizeof(CHAR16)`，作为
  `EfiBootManagerInitializeLoadOption()` 的 OptionalData。BDS 会原样把它当
  `LoadOptions` 传给 `LoadImage()`，`EfiBootManagerInitializeLoadOption()` 自己会复制
  一份缓冲区，所以传静态数组是安全的；
- 新增 `STATIC CHAR16 mSamuraiLinuxCmdLine[]`，内容与设备树 bootargs 逐字相同：
  `earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 ignore_loglevel panic=15`
  `clk_ignore_unused pd_ignore_unused regulator_ignore_unused`；
- 其余 4 个调用点（SimpleInit / Shell / UAS / SwitchSlots）补 `NULL`，行为不变。

### 19.4 离线验证（全部通过）

脚本 `linux-port/scripts/verify-cmdline-firmware.py`，直接读构建树，可重跑：

- FD = `0x1400000`（20 MiB），带 FV 头 `_FVH`；sha256 与改动前不同（`f6a0664d…` → `b02b55a1…`）；
- 未压缩 `FVMAIN.Fv` 里有 UTF-16 命令行（offset 16231800）和 UTF-16 的
  `Linux (mainline samurai)` 启动项描述；
- 全文唯一的 ASCII 命令行副本在 offset 32279672，落在 mainline 设备树内部
  （`d0 0d fe ed` @ 32279380，totalsize 94623）→ 代码侧确实只有 UTF-16；
- `realme,samurai` 在、`xiaomi,cepheus` 不在；
- `boot-samurai.img` 解出的 BootShim+FD 与构建目录的 FD **逐字节相同**；
- 尾部追加的是 `FdtBlob_compat/samurai.dtb` 本身（450,826 B，逐字节比对）。

### 19.5 本会话新增脚本

| 脚本 | 用途 |
|---|---|
| `linux-port/scripts/patch-bootmanager-cmdline.py` | 幂等地打 §19.3 那个 PlatformBm.c 改动 |
| `linux-port/scripts/build-cmdline-firmware.sh` | WSL 里重编 samurai 固件（后台 + 日志） |
| `linux-port/scripts/verify-cmdline-firmware.py` | §19.4 的全部检查 |
| `linux-port/scripts/archive-cmdline-firmware.sh` | 归档产物到 `E:\edk2-samurai-out\` 并提交 |

### 19.6 下一步：仍然只有真机验证

手机接上后刷的是 **`boot-samurai-linux-cmdline.img`**（不是 §18 里的
`boot-samurai-linux.img`），其余步骤与 §18.3 A 完全相同：

```powershell
E:\eud-host\eudtool.exe com-up
E:\eud-host\comlog.exe COM14 600 E:\eud-host\samurai-linux.log
# 重启后 9501 出现时执行上面两行，再：
fastboot flash boot E:\edk2-samurai-out\boot-samurai-linux-cmdline.img
fastboot reboot
# 菜单里音量键选 "Linux (mainline samurai)"，电源键确认
```

本轮之所以没做：手机没有连接（`adb devices` 为空，Windows 上没有 `VID_05C6`）。
`boot-samurai-linux.img`（`0d1ec546…`）保持原样未删，两个都能刷，新的是超集。

### 19.7 没做但该记一笔：linux-port 还没进版本库

`E:\RealmeX2Pro edk2\linux-port\` 里的内核补丁、设备树源、脚本和文档目前**只在
Windows 上**，本地没有 git 仓库；WSL 的 `~/x2pro-linux/linux` 也没有 remote（只有
两个本地提交 + `~/x2pro-linux/patches/` 里的 format-patch 产物）。EDK2 仓库这边只有
`HANDOVER-NEXT.md` / `README.md` 里的引用，`linux-port/...` 这个路径在没有那份工作区
的机器上是断的。

建议（下一次做）：把 `linux-port/{README.md,docs,patches,dts,scripts,refs}` 这几个小
目录（合计约 300 KB，不含 30 MB 的 `Image` 和 `artifacts/`）镜像进
`Platform/Realme/sm8150/linux-port/`，保持引用路径可解。本轮没动，因为它会改变仓库
结构，先留给人确认。
