# EDK2 / UEFI firmware for the realme X2 Pro (RMX1931 · "samurai")

Unofficial EDK2/UEFI port for the **realme X2 Pro (RMX1931 / RMX1931CN)**, Qualcomm
**Snapdragon 855+ (SM8150-AC)**, platform **msmnile**, codename **"samurai"**.

This repository is a fork of [edk2-porting/edk2-msm](https://github.com/edk2-porting/edk2-msm)
with a device package for *samurai* (`Platform/Realme/sm8150/`, `configs/devices/samurai.conf`).
Everything below is specific to this phone - the generic framework documentation lives in the
upstream project.

> 中文简介见文末。

---

## Status

Boot verified on real hardware (2026-10): **PEI → DXE → BDS → Boot Manager → EFI Shell**.

| Feature | Status | Notes |
|---|---|---|
| UEFI boot (Boot Manager / EFI Shell) | ✅ works | reaches the shell, `map`/`blk` show all UFS partitions |
| Display | ✅ works | framebuffer text console, 5x12 font (`FrameBufferSerialPortLib`), 1080x2400 |
| Volume-Up button | ✅ works | `SCAN_UP` |
| Power button | ✅ works | |
| **Volume-Down button** | ❌ **broken** | shared `ButtonsDxe` polls it through the PMIC PON RT IRQ, but on samurai it is wired to a GPIO (see Known issues) |
| UFS / block devices | ✅ works | 6 LUNs, GPT, `BLK*` devices in the shell |
| USB mass storage mode (phone as a USB disk) | ✅ works | via the built-in `LinuxSimpleMassStorage` kernel (see below) |
| USB keyboard / host mode | ❓ untested | no OTG device was available during development |
| Persistent UEFI variables | ❌ not implemented | no variable store partition configured, variables are lost on reboot |
| Windows (WoA) | ❌ not ready | DSDT is currently borrowed from a Xiaomi Mi 9 (cepheus); a samurai-specific DSDT is required |
| Mainline Linux | ⚠️ partially | the built-in mass-storage kernel runs; a full distro needs a mainline DTB + rootfs |

---

## The device

| | |
|---|---|
| Model | realme X2 Pro (RMX1931 / RMX1931CN) |
| Codename | **samurai** |
| SoC | Qualcomm **Snapdragon 855+** (SM8150-AC), msmnile |
| PMICs | PM8150 / PM8150L / PM8150B (SPMI) |
| RAM | 6 / 8 / 12 GiB SKUs; project hardware evidence is on an 8 GiB unit |
| Storage | 64 GB UFS 2.1; 128/256 GB UFS 3.0; 6 LUNs, GPT observed on the project unit |
| Display | 6.5" 1080x2400 Super AMOLED, 90 Hz (Samsung `sofef03f_m`) |
| Bootloader | realme/OPPO ABL (XBL). Unlocked bootloader required. **No `fastboot boot` support** - the image has to be flashed. |

---

## What this fork changes

```
configs/devices/samurai.conf                     device config (mkbootimg: header v1)
Platform/Realme/sm8150/samurai.dsc               platform DSC (PCDs, build options)
Platform/Realme/sm8150/samurai.fdf.inc           per-device FFS components (DXE drivers, ACPI, DTB)
Platform/Realme/sm8150/FdtBlob/samurai/*.dtb     mainline DTB  -> handed to Linux via the EFI configuration table
Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb vendor DTB   -> appended to the boot image (ABL builds the runtime DTB from it)
Platform/Realme/sm8150/AcpiTables/samurai/DSDT.aml  (currently borrowed from cepheus)
Platform/Realme/sm8150/README.md                 device-level notes
```

Nothing else in the upstream tree is modified - no patches to PEI/DXE core, no BootShim changes.

### Device-specific files you must supply yourself

The per-device DXE drivers are Qualcomm/realme firmware and are **not** included here.
Dump them from your own stock `xbl.img` and place them in
`Platform/EFI_Binaries/Drivers/Devices/samurai/` (that directory is part of the
`Platform/EFI_Binaries` submodule):

```
DALSys/DALSys.efi            DALSys/DALSys.depex
UsbPwrCtrlDxe/UsbPwrCtrlDxe.efi   UsbPwrCtrlDxe/UsbPwrCtrlDxe.depex
ButtonsDxe/ButtonsDxe.efi    ButtonsDxe/ButtonsDxe.depex      (not used, see gotcha 4)
```

Useful references:
- [Project-Aloha/UEFIFirmwareBackup — `realme-rmx1931`](https://github.com/Project-Aloha/UEFIFirmwareBackup/tree/main/realme-rmx1931)
  (factory XBL dump, `Binaries/RawFiles/uefiplat.cfg`, panel XMLs)
- the factory `uefiplat.cfg` for the memory map / `ConfigParameters` reference

---

## Building

```bash
git clone --recursive https://github.com/hmhmdcy/edk2-realme-x2-pro.git
cd edk2-realme-x2-pro
./build.sh -d samurai --toolchain GCC5
```

Output:
- `boot-samurai.img` - flashable Android boot image
- `workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd` - raw firmware volume

Host notes (Ubuntu, no sudo needed):
- On very new host GCC (e.g. GCC 15) BaseTools/Pccts fail with the default C23
  standard: append `-std=gnu17` to `GCC_AARCH64_CC_FLAGS` in `tools/tools_def.txt`
  (`build.sh` copies that file into `Common/edk2/Conf/`).
- `BaseTools` must be built once: `make -C Common/edk2/BaseTools -j$(nproc) BUILD_CC="gcc -std=gnu17"`.
- `uuid-dev` and `msgfmt` may have to be provided locally if you have no root.

---

## Flashing / testing

```bash
# ALWAYS keep a verified backup of your stock boot partition first:
fastboot flash boot boot_stock_RMX1931.img     # rollback

# flash the port:
fastboot flash boot boot-samurai.img
```

The realme/OPPO ABL does **not** implement `fastboot boot` (`FAILED (remote: 'unknown command')`),
so a temporary boot is not possible - you have to flash, and keep a backup for rollback.

To enter fastboot when the phone is stuck: hold **Power** for ~15 s to force power off, then hold
**Volume-Down + Power**.

---

## How the port works (porting notes for other SM8150 devices)

1. **Boot chain.** ABL loads the boot image "kernel" (which is `BootShim.bin` followed by the
   concatenated UEFI FD), jumps to it with `x0` = DTB, and BootShim copies the FD to
   `FD_BASE = 0xCE000000` and jumps into UEFI. PEI reads the runtime DTB from the address stored in
   `PcdDeviceTreeStore` (`0x9E000000`) to decide the memory size (4/6/8/10/12 GiB) and therefore
   which branch of the platform memory map is used.
2. **The boot image must keep the project default layout**:
   `header v1 + gzip(BootShim.bin + SM8150_UEFI.fd) + appended FdtBlob_compat/samurai.dtb`.
   Deviating (uncompressed payload, header v2 with a separate dtb section, or no appended DTB)
   makes ABL return to fastboot or hang. Do not override `platform_build_kernel` /
   `platform_build_bootimg` in a device `*.sh.inc`.
3. **Framebuffer console - the `0x9D000000` trap.** With `USE_UART=0` (default) the platform uses
   `Silicon/Qualcomm/QcomPkg/Library/FrameBufferSerialPortLib`, which draws *all* DEBUG output
   into the framebuffer with a 5x12 font. It uses `PcdMipiFrameBufferAddress`, whose platform
   default is `0x9C000000` (Xiaomi/OnePlus layout). On samurai the live framebuffer is at
   **`0x9D000000`**, so with the default value the log is written into invisible memory: the
   screen keeps showing the bootloader logo and the boot looks exactly like a hang.
   `samurai.dsc` therefore sets `PcdMipiFrameBufferAddress|0x9D000000`.
4. **`ButtonsDxe`.** Use the shared `Drivers/sm8150/ButtonsDxe` (same as cepheus). The vendor
   extracted `ButtonsDxe` has a satisfiable DEPEX but fails during initialisation here
   (it additionally needs vendor TLMM handling) and is unloaded - with it no key works at all.
5. **DTB roles.** `FdtBlob/<device>/<device>.dtb` is the **mainline** DTB (published to the OS
   through the EFI configuration table); `FdtBlob_compat/<device>.dtb` is the **vendor/Android**
   DTB appended to the boot image. Do not swap them: with a vendor DTB in `FdtBlob`, the built-in
   `LinuxSimpleMassStorage` kernel falls back to `usb_nop_phy` and USB never comes up.
6. **Memory map / MLVM.** `samurai.dsc` builds with `-DHAS_MLVM`: for the 8 GiB branch this
   reserves `0xA0000000..0xBBB00000`, matching the `no-map` carveouts of the device DTB
   (`qseecom_region` at `0xA0000000+0x1400000`, `cdsp_sec_regions` at `0xA4C00000+0xC00000`).
   Without it UEFI may allocate memory inside protected regions.

---

## USB mass storage mode (phone as a USB disk)

The firmware contains BigfootACA's [linux-simple-mass-storage](https://github.com/BigfootACA/linux-simple-mass-storage)
kernel (`Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.efi`,
registered as the boot option **"USB Attached SCSI (UAS) Storage"**). Selecting it boots a small
Linux 6.1 kernel which exposes the phone's **raw UFS LUNs** to a host PC as UAS mass storage.

Verified: Windows enumerates `USB Attached SCSI (UAS) Mass Storage Device` plus 6 disks
(`Qualcomm sda` = 118 GB userdata, `sdb`..`sdf`), and a FAT partition (`op1`, containing
`simpleinit.uefi.cfg`) becomes mountable - a convenient way to copy files to/from the phone
without reflashing.

**Warning:** this exposes *raw partitions*. Never let the host OS initialise, repartition or
format those disks - that destroys data or bricks the firmware. When not needed, do not boot
this option. (On Windows you can protect yourself with
`Set-Disk -Number <n> -IsOffline $true`.)

---

## Known issues / TODO

- **Volume-Down does not work.** The shared `ButtonsDxe` reads `VOL-` through the PMIC PON
  real-time IRQ; on samurai the key is wired to a GPIO.
  (Details: the vendor `ButtonsDxe` maps `VOL+`/`VOL-` through GPIO, which is correct for this
  board, but it fails to initialise even after adding the vendor `TLMMDxe` - the actual error
  still has to be captured from the framebuffer log.)
- No letter input: the EFI Shell cannot be typed into with the volume keys alone; a USB keyboard
  (host mode) is untested.
- A samurai-specific DSDT is required for Windows-on-ARM.
- Persistent UEFI variables (a variable store) are not configured.
- Optional: enable `USE_DISPLAYDXE` + the factory panel XML for a graphical console.

---

## Safety

- Only ever flash the `boot` partition; keep a verified backup
  (the stock image used during development has sha256
  `dfe18875661164e7cb64eba7942b856e80ffe20abb537aec815da4bf43995cdd`).
- Do not touch the partition table or any other partition (`xbl`, `abl`, `modem`, `persist`,
  `super`, `userdata`, ...).
- The U-disk mode described above exposes raw partitions - see the warning there.

---

## Credits

- [edk2-porting/edk2-msm](https://github.com/edk2-porting/edk2-msm) (Renegade Project) - the framework this port is built on, and SimpleInit
- [BigfootACA/linux-simple-mass-storage](https://github.com/BigfootACA/linux-simple-mass-storage) - the built-in mass-storage kernel
- [Project-Aloha/UEFIFirmwareBackup](https://github.com/Project-Aloha/UEFIFirmwareBackup) - factory firmware dumps (`realme-rmx1931`)
- [edk2-porting/edk2-msm device sources](https://github.com/edk2-porting/edk2-msm/tree/master/Platform) - cepheus (Mi 9) was used as the working SM8150 reference

## License

Same as upstream edk2-msm (BSD-2-Clause-Patent for EDK2 code). Device firmware blobs
(vendor DXE, DTBs, ACPI) are **not** distributed here - obtain them from your own device.

---

## 中文简介

**realme X2 Pro（RMX1931 / 代号 samurai）的 EDK2/UEFI 移植**，基于 `edk2-porting/edk2-msm`。

已在真机验证：UEFI 可启动到 Boot Manager 与 EFI Shell，framebuffer 文本控制台、音量上/电源键、
UFS 分区枚举、以及"把手机当 U 盘"的 USB 大容量存储模式都可用。**已知缺陷：音量下键无效**；
Windows 化还需专属 DSDT。

关键坑（详见上文）：
1. boot 镜像必须保持项目默认布局（v1 + gzip(BootShim+FD) + 尾部追加 `FdtBlob_compat` 的安卓 DTB）；
2. `PcdMipiFrameBufferAddress` 必须改成 **0x9D000000**，否则 edk2 日志"静默"、看起来就是卡死；
3. 按键驱动要用共享版 `Drivers/sm8150/ButtonsDxe`；
4. `FdtBlob` 放主线 DTB、`FdtBlob_compat` 放安卓 DTB，别放反（放反会导致 U 盘模式失效）。

⚠️ **安全**：只刷 `boot` 分区，先备份；U 盘模式会暴露原始分区，切勿让 PC 端格式化/初始化。
