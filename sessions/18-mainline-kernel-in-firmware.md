---
<!-- from HANDOVER-NEXT.md, section 18 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 18. 主线 Linux：内核已进固件，等真机验证（2026-10-07 14:3x）

### 18.0 TL;DR

固件里**第一次有了能用的主线 Linux 内核，和这台机器自己的设备树**。
之前 `FdtBlob/samurai/sm8150-realme-samurai.dtb` 其实是小米 9（cepheus）的设备树，
而固件里除了别人编的 pmOS 6.1 内核外没有任何可启动的内核。

现在刷 `E:\edk2-samurai-out\boot-samurai-linux.img`，UEFI 菜单里会多出
**"Linux (mainline samurai)"**，选中后内核经 EUD earlycon 打日志（同时 simpledrm
把日志打到手机屏）。**这一步尚未上真机**——下一个会话第一件事就是它。

### 18.1 本会话（Linux 主线）做了什么

工作区 `E:\RealmeX2Pro edk2\linux-port`；WSL 源码树 `~/x2pro-linux/linux`
（Linux v7.3-rc6 `a90ee4305c4a`，无 remote，本地两个提交）。

1. **EUD earlycon**（提交 `e4858b30a`，补丁 `linux-port/patches/0001-*.patch`）：
   `drivers/tty/serial/eud_earlycon.c`，命令行 `earlycon=eud,mmio,0x88e0000`。
   **本会话修掉一个会直接崩机的 bug**：earlycon 框架对 `mmio` 形式只映射 64 字节
   （即 FIFO 所在那一页），而 `CSR_EUD_EN` 在 `+0x1014`，属于**下一页**——照原样写会
   缺页，内核还没输出就死。改为自己 `ioremap(mapbase + 0x1014, 4)` 再写；映射失败
   也不影响 console 注册。
2. **samurai 主线设备树**（提交 `0450fd895`，源 `linux-port/dts/sm8150-samurai.dts`）：
   以 `sm8150-mtp.dts` 为底（本机原厂基础 DTB 本身就是 MTP 派生），按实机重写
   21 个 reserved-memory、音量键（`pm8150_gpios` 6/7、`bias-disable`、
   `power-source = <1>`）、UFS 供电（保持 MTP 的 `vreg_s4a_1p8`）；GPU/WiFi/四个
   remoteproc/uart2/pon_resin 保持 `disabled`。`make dtbs` 通过，DTB
   `1c760ec9cf74389c246e1b64a032c52910f6437dab29772371a506ead5d67b81`（94,623 B）。
   `/memory` 故意保持 `0x80000000 + 0`：Android 链由 ABL 修补，EDK2/EFI 链的 RAM
   来自 EFI memory map（已核对 `drivers/firmware/efi/efi-init.c`）。
3. **旧工程核实**（报告 `linux-port/docs/OLD-PROJECT-VERIFICATION.md`）：
   它的补丁可复现（重编 DTB 与产物同哈希 `f0c3a820…`），但 **3 处勿抄**：
   UFS `vccq2` 是 `&vreg_s4a_1p8`（S4A）不是 L7A；音量键 pin 是 `bias-disable` +
   `power-source = <1>`；ramoops 不要 `devinfo-size`（主线不解析）。其文档只记了
   4 轮主线盲刷，实际是 6 轮（1-4/7/8），第 8 轮完全没有结果文件。
4. **诊断内核 Image**（`linux-port/scripts/build-image.sh`）：以旧工程
   `bringup.config` 为配置基线（补上它缺的 `CONFIG_EFI` / `EFI_STUB` /
   `EFI_ARMSTUB_DTB_LOADER`），另开 EFI GOP 帧缓冲控制台（`SYSFB_SIMPLEFB` +
   `DRM_SIMPLEDRM` + `FRAMEBUFFER_CONSOLE`，日志同时上屏）、`SERIAL_EUD_EARLYCON=y`、
   `PSTORE_RAM=y`，内置 busybox 诊断 initramfs。`Image` 30,116,352 B，
   sha256 `3d5665ab…`，`kernelrelease = 7.3.0-rc6-rmx1931-samurai+`。
5. **内核进固件 + 换掉错误 DTB**（EDK2 提交 `47c3efb`，说明
   `linux-port/docs/EDK2-KERNEL-EMBED.md`）：
   - `FdtBlob/samurai/sm8150-realme-samurai.dtb` → 新的 samurai DTB；
   - 新增 `Platform/Realme/sm8150/LinuxKernel/{Image,SamuraiLinuxKernel.inf}`
     （`UEFI_APPLICATION`，GUID `7a3c1e42-9d55-4c8b-b621-0f8a442e913d`，写法照抄
     `LinuxSimpleMassStorage.inf`），`samurai.fdf.inc` 加 `INF` 行；
   - `PlatformBm.c` 在 `#ifdef SAMURAI_LINUX_KERNEL` 下注册启动项
     `"Linux (mainline samurai)"`，`samurai.dsc` 打开该宏；
   - **FD 从 7 MiB 涨到 20 MiB**（`configs/sm8150.conf` 的 `FD_SIZE=0x01400000`、
     `sm8150.fdf` 的 `NumBlocks=0x1400` 和 FD 区域 `0x01400000`），原因是内核
     压缩后约 11.7 MB，塞不进 7 MiB。
6. **离线逐字节验证**：FD = 20,971,520 B；boot.img 解出的 BootShim+FD 与之完全一致；
   FV 里内核 FFS 的 PE32 载荷与 `Image` **sha256 相同**；未压缩 `FVMAIN.Fv` 中
   `realme,samurai` 出现 1 次、`xiaomi,cepheus` **0 次**、`rmx1931-samurai` 7 次。

### 18.2 产物

| 文件 | 大小 | sha256 |
|---|---|---|
| `E:\edk2-samurai-out\boot-samurai-linux.img` | 15,185,920 | `0d1ec54656fed0550a90ac8453918a8d589d93ed890914959ffba31f2b0a3439` |
| `E:\edk2-samurai-out\SM8150_UEFI-samurai-linux.fd` | 20,971,520 | `f6a0664d6d4ce402c668fdd46fef9d49bd8e3bbabe901e55fb550c7843d58f4b` |
| `E:\edk2-samurai-out\Image-rmx1931-samurai` | 30,116,352 | `3d5665abcf53b1b97ee5b2c32b4aaaee45265a4c45af99463b4d3c2b35427ba3` |
| 回滚用 | — | `backup\boot_stock_RMX1931.img`（`dfe18875…`） |

EDK2 提交：`47c3efb`（内核进固件）+ `0ccd325`（本文档），**已 push 到 fork
`hmhmdcy/edk2-realme-x2-pro` 的 master**。内核补丁在 `linux-port/patches/`，
设备树源在 `linux-port/dts/`。

⚠️ **复现注意**：`Platform/Realme/sm8150/LinuxKernel/Image` 是构建产物，**没有进
git**（30 MB）。全新 clone 后必须先把它放回去——`E:\edk2-samurai-out\Image-rmx1931-samurai`
或 `linux-port\artifacts\Image-rmx1931-samurai`（sha256 `3d5665ab…`），或自己按
`linux-port/scripts/build-image.sh` 重编——否则 `./build.sh -d samurai --toolchain GCC5`
会因为 INF 找不到 `Image` 而直接失败。

### 18.3 下一步（按顺序）

**A. 真机验证（最高优先；手机接上就能做）**

```powershell
# 1) 先备好 EUD 日志通道：重启后约 3.5 s 出现 9501，那时执行
E:\eud-host\eudtool.exe com-up
E:\eud-host\comlog.exe COM14 600 E:\eud-host\samurai-linux.log
# 2) 刷入并重启
fastboot flash boot E:\edk2-samurai-out\boot-samurai-linux.img
fastboot reboot
# 3) 屏幕出现 UEFI 菜单后：音量键选 "Linux (mainline samurai)"，电源键确认
```

验收：`samurai-linux.log` 里出现 `Booting Linux on physical CPU`、8 核、内存、
UFS、initramfs 横幅；屏幕上同时能看到内核日志。

回滚：EUD 开着时 USB 被占用，**先长按电源 15 s 彻底断电**，再 音量下+电源 进
fastboot，`fastboot flash boot E:\edk2-samurai-out\backup\boot_stock_RMX1931.img`。

**B. 如果没输出，按这三个分支排查**

1. 菜单里根本没有 "Linux (mainline samurai)" → 确认 `INF` 真的编进去了
   （grep `workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.inf`）以及
   `-DSAMURAI_LINUX_KERNEL` 生效。
2. 选了之后立刻黑屏/回菜单，EUD 里什么都没有 → 最可能是内核没拿到 DTB/命令行
   （console 与 earlycon 都来自 DTB 的 `chosen/bootargs`）。加固：给
   `PlatformRegisterFvBootOption` 增加一个可选命令行参数，把
   `earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7` 作为 LoadOptions 传进去
   （EFI stub 会用 EFI 命令行覆盖 DTB 的 bootargs，两者内容一致，无副作用）。
3. 连 UEFI 菜单都起不来 → 第一嫌疑是 FD 7 → 20 MiB 的改动。回退：把
   `configs/sm8150.conf`、`Platform/Qualcomm/sm8150/sm8150.fdf` 三个尺寸改回
   `0x700000`，或先把内核精简（非必需驱动改模块）再重编。

**C. 起来之后**

- 用 `linux-port/refs/19781/`（Android 源）继续做：面板 SOFEF03F_M（806 行 init
  序列已存）、触控 S3706（`i2c17`/`i2c@c80000` 地址 0x20、IRQ TLMM 122、reset
  TLMM 54、2.8 V `pm8150_l17`、1.8 V 使能 `pm8150l_gpios 5`）、WCN3990、充电、
  传感器；
- 决定 30 MB `Image` 怎么管：建议放二进制子模块或用脚本生成，**不要提交进父仓**；
- 把 EDK2 提交 push 到 `hmhmdcy/edk2-realme-x2-pro`（网络不稳，通常要重试 2-3 次）。

### 18.4 不要重新推导的事实

- `PcdDefaultDtPref` 默认 **TRUE**（`EmbeddedPkg.dec`，本平台没有覆盖成 FALSE）
  → `DtPlatformDxe` 选 DT 分支，把 `FdtBlob/samurai` 通过
  `InstallConfigurationTable(gFdtTableGuid, …)` 装进 EFI 配置表；arm64 EFI stub
  从配置表取 DTB、从 `chosen/bootargs` 取命令行。
- 实机 `/memory` 三段：`0x80000000 + 0x3BB00000`、`0x1_80000000 + 0x1_00000000`、
  `0xC0000000 + 0xC0000000`；EDK2 `Mem8G` 表里 `0xC0300000 + 0x7FD00000` 是 `Conv`
  → FD 在 `0xCE000000` 扩到 20 MiB 仍在映射范围内。
- earlycon 框架给外设只映射 64 字节（一页）；**跨页寄存器必须自己 ioremap**。
- Android 设备树源码就在本机：下游克隆
  `E:\Realme X2 Pro移植主线Linux\sources\realme-downstream.git` →
  `arch/arm64/boot/dts/19781/`（`19781` = 本机 `oppo,dtsi_no`），关键文件已复制到
  `linux-port/refs/19781/`；可用性评估见 `linux-port/docs/ANDROID-DT-REFERENCE.md`。
  仓库本身无需联网即可 `git ls-tree` / `cat-file` 读取。
- 旧工程 3 处错误与 6 轮盲刷记录见 §18.1 第 3 点与核实报告。

### 18.5 本会话新增文档索引

| 文档 | 内容 |
|---|---|
| `linux-port/README.md` | Linux 主线进度总览 + 真机测试步骤 |
| `linux-port/docs/EDK2-KERNEL-EMBED.md` | 第 2 步改动清单、DTB 链路证据、风险 |
| `linux-port/docs/OLD-PROJECT-VERIFICATION.md` | 旧工程核实：可复现、3 处错误、轮次漏记 |
| `linux-port/docs/ANDROID-DT-REFERENCE.md` | Android 设备树可用性与映射表、坑 |
| `linux-port/scripts/*.sh` | 可复跑脚本（编 Image、装内核进固件、核实旧工程、抓实机真值） |
---
