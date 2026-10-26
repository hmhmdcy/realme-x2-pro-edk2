# 把主线内核装进 EDK2 固件（第 2 步）

> 2026-10-07。EDK2 仓库（WSL `~/edk2-samurai/repo`）提交 **`47c3efb`**。
> 目标：让固件在 BDS 里就把 EUD 打开、并把这台机器的**正确设备树**和
> **主线内核**一起交给内核，从而第一次拿到可用的主线启动日志。

## 1. 为什么要改

改之前这台机器的固件有两个硬伤：

1. **`FdtBlob/samurai/sm8150-realme-samurai.dtb` 其实是小米 9（cepheus）的设备树**
   （`model = "Xiaomi Mi 9"`, `compatible = "xiaomi,cepheus"`）。`DtPlatformDxe`
   会把它装进 EFI 配置表交给内核，等于给 Linux 发错硬件描述。
2. **固件里没有任何可用的主线内核**：`LinuxSimpleMassStorage.efi` 是别人编译的
   6.1 内核（pmOS 大容量存储用途），不能用来做本机 bring-up。

## 2. 改了什么（6 个文件）

| 文件 | 改动 |
|---|---|
| `Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb` | 换成 samurai 主线 DTB（sha256 `1c760ec9…`，来自 [../dts/sm8150-samurai.dts](../dts/sm8150-samurai.dts)） |
| `Platform/Realme/sm8150/LinuxKernel/Image` | 主线内核 Image（EFI stub + 内置诊断 initramfs + EUD earlycon，sha256 `3d5665ab…`）。**未入 git**（30 MB 构建产物） |
| `Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf` | 把它声明成 `UEFI_APPLICATION`，GUID `7a3c1e42-9d55-4c8b-b621-0f8a442e913d`，照抄 `LinuxSimpleMassStorage.inf` 的写法 |
| `Platform/Realme/sm8150/samurai.fdf.inc` | 加一行 `INF …SamuraiLinuxKernel.inf`，把内核放进 FVMAIN |
| `Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c` | `#ifdef SAMURAI_LINUX_KERNEL` 下注册启动项 **"Linux (mainline samurai)"**（用现成的 `PlatformRegisterFvBootOption`） |
| `Platform/Realme/sm8150/samurai.dsc` | BuildOptions 加 `-DSAMURAI_LINUX_KERNEL` |
| `Platform/Qualcomm/sm8150/sm8150.fdf` + `configs/sm8150.conf` | FD 从 **7 MiB 涨到 20 MiB**（内核压缩后约 11.7 MB，装不下 7 MB）：`FD_SIZE=0x01400000`、`NumBlocks=0x1400`、FD 区域 `0x00000000\|0x01400000` |

## 3. 为什么这样能成（已核对过的链路）

* **内核怎么被启动**：BDS 从 FV 里按 device path 找到我们的文件（与 `LinuxSimpleMassStorage`
  同一机制，那个文件本身就是一份 Linux Image），`LoadImage` + `StartImage`。
* **DTB 怎么到内核**：`DtPlatformDxe`（在 FV 里）→ `DtPlatformLoadDtb` 按
  `gDtPlatformDefaultDtbFileGuid` 读 `FdtBlob` → 没有持久变量可读 → 回落到
  `PcdDefaultDtPref`，而 EmbeddedPkg 默认 **TRUE** → 走 DT 分支 →
  `gBS->InstallConfigurationTable (&gFdtTableGuid, Dtb)`。arm64 EFI stub 会从配置表取
  DTB，并从 `chosen/bootargs` 取命令行（我们的 DTB 里就带着
  `earlycon=eud,mmio,0x88e0000 console=tty0 …`）。
* **日志为什么不会丢**：BDS 在进菜单前已开 EUD（`SAMURAI_ENABLE_EUD`），主机可以
  先 `eudtool com-up` 把 COM14 准备好，再选内核启动 → 内核第一条 earlycon 就有地方去。
* **20 MiB 放在 0xCE000000 安全吗**：实机 `/memory` 有第三段 `0xC0000000 + 0xC0000000`
  （3 GiB），EDK2 的 `Mem8G` 表里 `0xC0300000 + 0x7FD00000` 也是 `Conv`，两边都覆盖
  0xCE000000…0xCF400000 ✓。

## 4. 已做的验证（离线，逐字节）

* FD = `0x1400000` = 20,971,520 字节；boot.img 里 BootShim + FD 解压后与之逐字节一致。
* FV 里内核的 FFS 文件 `7a3c1e42-….ffs` 中的 PE32 载荷与 `Image` **sha256 完全相同**
  （都是 `3d5665ab…`）。
* 未压缩 `FVMAIN.Fv`：`realme,samurai` 出现 1 次，`xiaomi,cepheus` **0 次**，
  `rmx1931-samurai`（内核版本串）7 次 → 新 DTB 与内核确实都在里面。
* `DtPlatformDxe` 在 FV 里；`PcdDefaultDtPref=TRUE`（EmbeddedPkg.dec 默认值，本平台
  没有覆盖成 FALSE）。

## 5. 产物

| 文件 | 大小 | sha256 |
|---|---|---|
| `E:\edk2-samurai-out\boot-samurai-linux.img` | 15,185,920 | `0d1ec54656fed0550a90ac8453918a8d589d93ed890914959ffba31f2b0a3439` |
| `E:\edk2-samurai-out\SM8150_UEFI-samurai-linux.fd` | 20,971,520 | `f6a0664d6d4ce402c668fdd46fef9d49bd8e3bbabe901e55fb550c7843d58f4b` |
| `E:\edk2-samurai-out\Image-rmx1931-samurai` | 30,116,352 | `3d5665abcf53b1b97ee5b2c32b4aaaee45265a4c45af99463b4d3c2b35427ba3` |

## 6. 已知风险 / 未验证（真机待验）

1. **FD 从 7 MiB 涨到 20 MiB**：内存映射两边都核对过，但没有真机跑过；如果
   BootShim 之后固件起不来，这就是第一嫌疑。
2. **启动项要手动选**：不会自动进内核；如果选之前没做 `com-up`，主机的 9501 会
   出现但 COM 没打开，内核早期日志仍会丢（这正是 EDK2 日志环那条经验）。
3. **如果 DTB 那条链路任何一环失败，内核拿不到命令行**（console/earlycon 都来自
   DTB 的 `chosen/bootargs`），表现会是"选了启动项，黑屏无输出"。备选加固：把
   `earlycon=… console=tty0` 作为 LoadOptions 传给启动项（需要给
   `PlatformRegisterFvBootOption` 加一个可选参数，尚未做）。
4. **30 MB 内核** 会让 BDS 的 `LoadImage` 拷贝 30 MB 到内存；若失败，退路是精简配置
   （把非必需驱动改成模块）重编。

## 7. 复现

```bash
# 内核侧（WSL）
bash linux-port/scripts/build-image.sh          # 配置 + initramfs + make Image
# 固件侧（WSL）
bash linux-port/scripts/install-kernel-into-edk2.sh   # 换 DTB、装内核、注册启动项、改 FD 尺寸
cd ~/edk2-samurai/repo && ./build.sh -d samurai --toolchain GCC5
```
