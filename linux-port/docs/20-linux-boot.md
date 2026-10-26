
---

## 20. 主线 Linux 真机启动成功：内核改放 FAT 分区（2026-10-07 16:0x）

### 20.0 TL;DR

**这台 realme X2 Pro 第一次真正跑起了主线 Linux。** EUD 上抓到了

```
Linux version ...  Machine model: Realme ...
earlycon ... 0x88e0000
efi: SMBIOS=... MEM...
OF: reserved memory: memory@85700000 ... 0xb7e00000 (ramoops) ... cma ...
PSCI v1.1 ... Zone ... Detected CPU ... init: SLUB ... RCU ... GIC ... IPIs
```

关键改变：**内核不再放进固件卷**，而是放在 `logdump` 分区（64 MiB，FAT16）；固件在打开 EUD 之后直接启动它。

### 20.1 为什么必须搬出来：两个硬根因

1. **FFS 文件装不下 30 MB 内核。** `EFI_FFS_FILE_HEADER.Size` 只有 3 字节（最大 16 MiB），`GenFfs` 把
   `0x1CB8A62` 截成了 `0x00CB8A62`——FVMAIN 里的内核文件结构是坏的，PE32 section 头同理。
2. **未压缩 FVMAIN 撑爆 PrePi 内存池。** 加了内核后 FVMAIN 从约 32 MB 涨到 **62.5 MB**，而
   `PcdUefiMemPoolSize=0x04230000`（66.2 MiB），`PrePiLib` 的 `InternalAllocatePages` 是**从池顶往下分配**的，
   解压 FVMAIN 占掉 94%，DXE 核加载失败。RELEASE 构建里 `ASSERT` 是空操作，于是**静默挂死在
   `LoadDxeCoreFromFv In`**（屏幕最后一行）。
   → FD 从 20 MiB 改回 7 MiB、FVMAIN 回到 31 MB 后，PEI/DXE/BDS 全部正常。

### 20.2 内核放在哪：`logdump`

这台机的分区表（从 9008 包的 GPT 和实机 live GPT 双向核对，两者一致）：

| 分区 | 索引 | 起始 LBA | 大小 | 类型 GUID | unique GUID |
|---|---|---|---|---|---|
| `modem` | 4 | 0xC86 | 0x10000 (256 MiB) | 标准高通 | 934CA8ED-C69D-9755-BA9A-6C9411CDC27F |
| `logfs` | 30 | 0x31570 | 0x800 (8 MiB) | BC0330EB-... | 09969439-057F-289A-5729-CE302330C1CA |
| **`logdump`** | 32 | 0x31F70 | 0x4000 (**64 MiB**) | 5AF80809-AABB-4943-9168-CDFC38742598 | 6458791A-5CBF-649C-B221-7A804460E308 |

选它的安全依据（全部逐项验证过）：

- **内容全是 0**（抽 0 / 4 KiB / 32 MiB 三处），没有任何数据可丢；
- 工厂 9008 包 `rawprogram*.xml` 里 `logdump` **没有 filename**，`patch*.xml` 只改 GPT 里 `userdata` 的
  last LBA，**出厂流程根本不写它**；
- 实机 `fstab` / SELinux 里 `logdump` **只作为块设备标签**出现，ROM 既不挂载也不格式化它；
- LineageOS 在 Nokia msm8998 / 小米 beryllium / 一加 sdm845-common 上直接把 `logdump` 改成了 `/metadata`，
  提交信息明说"生产机上该分区无用"——**复用有先例**；
- **不动 GPT**：只写分区内容，名字/大小/类型 GUID/偏移全不变；
- 上机前做了完整备份：`E:\edk2-samurai-out\backup\{logdump_stock.bin (64 MiB, md5 E97EA65C…),
  gpt_lun0_live.bin, gpt_lun4_live.bin}`。

格式化与写入（安卓 root 下）：

```sh
newfs_msdos -F 16 -c 1 -S 4096 -L KERNEL /dev/block/by-name/logdump   # 必须 4096，UFS 逻辑扇区是 4K
mount -t vfat -o rw /dev/block/by-name/logdump /mnt/kernel
cp /sdcard/Image /mnt/kernel/Image            # 30,116,352 B, sha256 3d5665ab…
cp /sdcard/samurai.dtb /mnt/kernel/samurai.dtb
umount /mnt/kernel
```

文件名用 `Image` / `samurai.dtb`（都是 8.3 兼容），不依赖 VFAT 长文件名支持。

### 20.3 固件怎么找到并启动它

`PlatformBm.c`（EDK2 提交见下）：

- `SamuraiRegisterKernelBootOption()` 枚举**所有** `EFI_SIMPLE_FILE_SYSTEM_PROTOCOL`，找根目录下的
  `\Image`；**必须校验文件内容以 `MZ` 开头**（PE 签名）才认，否则跳过；
- 用 `FileDevicePath()` 生成设备路径，`EfiBootManagerInitializeLoadOption()` 注册成
  `Linux (mainline samurai)`，OptionalData 就是内核命令行（UTF-16）；
- **注册完立刻 `EfiBootManagerBoot(&NewOption)`**，放在 `PlatformBootManagerAfterConsole()` 的最后、
  EUD 打开之后，绕开整个 boot order。
- `samurai.fdf.inc` 里删掉 `INF …SamuraiLinuxKernel.inf`；`LinuxKernel/SamuraiLinuxKernel.inf` 顶部加了
  "DO NOT ADD THIS BACK" 警告。

两个踩到的坑（都已修）：

1. **`modem` 分区被固件的 FAT 驱动误判成 FAT 卷**，而且"里面"也有个 `\Image`。只检查"文件能打开"就会选它，
   BDS 去那里读 PE 失败 → `BdsDxe` 报致命错误（`ERROR: C40000002… I0 6D33944A-…`，`6D33944A` 就是
   `MdeModulePkg/Universal/BdsDxe/BdsDxe.inf`）→ 复位。**必须校验 `MZ`。**
2. **SimpleInit 会复位**：这台机的 boot manager 是 SimpleInit，它的内置条目 `Continue Boot` 是
   `BOOT_EXIT`（`boot.c:40`），也就是"退出 SimpleInit 让固件继续"；之后 BDS 继续走却撞上上面那个坏设备路径，
   于是每 ~10 秒复位一轮。所以固件改成**直接启动内核**，不再把控制权交给它。

### 20.4 日志通道：EUD

- 固件在 BDS 开 EUD（`SAMURAI_ENABLE_EUD`），主机 `E:\eud-host\eudtool.exe com-up` 让 9505 变成
  `COM14`，再 `comlog.exe COM14 600 <log>` 录制。
- **`earlycon` 是 boot console，真 console 注册后会被注销**，所以最初只录到 1.2 秒的日志就断了。
  cmdline 里加 **`keep_bootcon`** 后 boot console 不再注销，EUD 就能拿到整个启动过程的日志
  （代价：EUD 是分小帧轮询发送，日志多时启动会变慢）。
- comlog 的帧重组不完美，日志会花；真正干净的做法是把 `eud_earlycon.c` 升级成**真正的 console 驱动**
  （注册 `struct console`，`console=eud`），下游 4.14 的 `drivers/soc/qcom/eud.c`（`ttyEUD`）就是这套思路。
- 兜底：DTB 里有 `ramoops@0xb7e00000`（4 MB），内核 panic 后进安卓
  `su -c cat /sys/fs/pstore/console-ramoops` 可以读到上次的日志。

### 20.5 产物与脚本

| 文件 | 说明 |
|---|---|
| `E:\edk2-samurai-out\boot-samurai-linux-console.img` | 加 `keep_bootcon`，sha256 `e461a8a2…`（本轮最新） |
| `E:\edk2-samurai-out\boot-samurai-linux-mz.img` | 首次真机跑起内核的那版，sha256 `aed239e3…` |
| `E:\edk2-samurai-out\boot-samurai-linux-fs.img` | 只注册启动项、不自动启动，sha256 `35fd18ee…` |
| `linux-port\scripts\move-kernel-out-of-fv.py` | 把内核移出 FV + 改 FD 尺寸 |
| `linux-port\scripts\boot-kernel-directly.py` | 在 AfterConsole 末尾直接启动内核 |
| `linux-port\scripts\require-pe-magic.py` | 加 `MZ` 校验，修掉 modem 误选 |
| `linux-port\scripts\verify-kernel-on-fs.py` | 离线校验（扫描器字符串、内核已移出、FD 尺寸） |

### 20.6 下一步

1. 读完整日志（`E:\eud-host\samurai-console.log`），看内核跑到哪里、卡在什么驱动；
2. 把 `eud_earlycon.c` 升级成真正的 console 驱动（`console=eud`），日志就能在 cmdline 里切换、不必每次重刷固件；
3. 然后按 §18.3 C 继续：面板 SOFEF03F_M、触控 S3706、WCN3990、充电、传感器。