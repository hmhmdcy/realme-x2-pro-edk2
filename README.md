# EDK2 / UEFI firmware for the realme X2 Pro (RMX1931 · "samurai")

用途：项目介绍、构建入口与移植说明。文档整理：2026-10-23；部署与实机状态以[当前检查点](NEXT-SESSION.md)的最后核对记录为准。

This fork brings EDK2/UEFI and mainline Linux to the realme X2 Pro. UEFI Boot Manager, EFI Shell, the framebuffer console, side buttons and UFS enumeration have historical hardware validation. Linux hardware acceptance and remaining work are maintained in the [hardware checklist](linux-port/docs/HARDWARE-STATUS.md).

## Start here

| Need | Document |
| --- | --- |
| Continue development; identify deployed images, sources and rollback | [NEXT-SESSION](NEXT-SESSION.md) |
| Fast porting workflow; factory data and incremental validation | [PORTING-WORKFLOW](linux-port/docs/PORTING-WORKFLOW.md) |
| Current operating boundaries | [WORKING-BOUNDARIES](WORKING-BOUNDARIES.md) |
| Hardware capabilities and acceptance gaps | [HARDWARE-STATUS](linux-port/docs/HARDWARE-STATUS.md) |
| Find documentation and maintenance commands | [DOCS-INDEX](DOCS-INDEX.md) |
| Linux source, patches and rootfs references | [Linux workspace](linux-port/README.md) |
| Experiments, rejected candidates and original evidence | [Session index](sessions/INDEX.md) |

## Scope

The Linux port has partial hardware acceptance. Passing a specific test does not establish complete daily-use reliability; cold boot, suspend/resume and remaining functional groups have their own acceptance gaps. Persistent UEFI variables and a board-specific Windows-on-ARM DSDT remain open work.

## The device

| | |
|---|---|
| Model | realme X2 Pro (RMX1931 / RMX1931CN) |
| Codename | **samurai** |
| SoC | Qualcomm **Snapdragon 855+** (SM8150-AC), msmnile |
| PMICs | PM8150 / PM8150L / PM8150B (SPMI) |
| RAM | 8 GiB (also sold with 12 GiB) |
| Storage | UFS 3.0, 6 LUNs, GPT |
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

The port also changes the shared BDS boot manager and selected libraries. Source and deployed-image differences are recorded in [NEXT-SESSION](NEXT-SESSION.md); device configuration alone does not describe the complete running build.

### Device blobs

The per-device DXE drivers are Qualcomm/realme firmware. They ship with this
fork: the `Platform/EFI_Binaries` submodule points at
`hmhmdcy/edk2-msm-binary` branch `samurai-blobs`, so a recursive clone is enough:

```bash
git clone --recursive https://github.com/hmhmdcy/edk2-realme-x2-pro.git
```

They live in `Platform/EFI_Binaries/Drivers/Devices/samurai/`:

```
DALSys/DALSys.{efi,depex}                 UsbPwrCtrlDxe/UsbPwrCtrlDxe.{efi,depex}
ButtonsDxe/ButtonsDxe.{efi,depex}         TLMMDxe/TLMMDxe.{efi,depex}
ResetRuntimeDxe/ResetRuntimeDxe.{efi,depex}
OcdtDxe/OppoProject.{efi,depex}
```

`Platform/Realme/sm8150/fetch-binaries.sh` can re-create the same set from public
mirrors if you prefer to extract them yourself; [BINARIES.md](BINARIES.md)
documents the sources and the required DEPEX patch.

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

## Testing and deployment

Identify the device, selected image and verified rollback before a deployment, using [NEXT-SESSION](NEXT-SESSION.md) and [WORKING-BOUNDARIES](WORKING-BOUNDARIES.md). The original `boot-samurai.img` build recipe does not by itself recreate the accepted Linux/firmware/rootfs combination. The compiled DTB, kernel store, modules and Mesa library must match the selected build evidence.

The realme/OPPO ABL rejected `fastboot boot` during bring-up. Historical flashing recipes are preserved in the [maintenance snapshot](archive/docs-before-maintenance-2026-10-14/README.md); select a deployment procedure against the current device and image receipts.

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
4. **`ButtonsDxe` needs three extra blobs.** The port uses the *factory* realme/OPPO
   `ButtonsDxe` (the only build with a correct key map for this board), but it is not
   self-contained: at run time it additionally wants `EFI_QCOM_TLMM_PROTOCOL` (`TLMMDxe`), the
   **OPPO project protocol** (`903C579D-...`, installed by `OcdtDxe/OppoProject.efi`) and the
   **reset-reason protocol** (`A022155A-...`, installed by `ResetRuntimeDxe`). It also reads the
   SMEM project entry (`Project:19781`) to select the per-project key map. Any missing piece makes
   it return `EFI_NOT_FOUND` and get unloaded - and then *no* side button works at all.
   Because it locates the OPPO project protocol only at run time (that GUID is not in its DEPEX),
   run `fix-buttons-depex.py` so the dispatcher guarantees `OppoProject` is installed first.
   See `Platform/Realme/sm8150/BINARIES.md`.
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

## Debugging and the test workflow

The working EUD COM/tty console and F1 bootloader command have hardware evidence. USB NCM/SSH/SCP and EUD coexistence have also been demonstrated; residual EUD reception/exit acceptance gaps remain in the hardware checklist.

- [EUD](EUD.md): device registers, CTL/COM protocol and firmware log ring history.
- [RX-CONSOLE](RX-CONSOLE.md): RX framing and Linux console investigation.
- [SWD-JTAG](SWD-JTAG.md): verified transport and unresolved AP DAP response.
- [FLYWHEEL](FLYWHEEL.md): build, deployment, observation and rollback workflow.

## Operating boundaries

Current rules are maintained in [WORKING-BOUNDARIES](WORKING-BOUNDARIES.md). USB mass storage exposes raw UFS partitions; preserve important data and calibration when using it.

## Credits

- [edk2-porting/edk2-msm](https://github.com/edk2-porting/edk2-msm) (Renegade Project) - the framework this port is built on, and SimpleInit
- [BigfootACA/linux-simple-mass-storage](https://github.com/BigfootACA/linux-simple-mass-storage) - the built-in mass-storage kernel
- [Project-Aloha/UEFIFirmwareBackup](https://github.com/Project-Aloha/UEFIFirmwareBackup) - factory firmware dumps (`realme-rmx1931`)
- [Project-Aloha/mu_aloha_platforms](https://github.com/Project-Aloha/mu_aloha_platforms) - source of the `OppoProject.efi` (OcdtDxe) blob
- [edk2-porting/edk2-msm device sources](https://github.com/edk2-porting/edk2-msm/tree/master/Platform) - cepheus (Mi 9) was used as the working SM8150 reference

## License and firmware provenance

EDK2 code follows the upstream BSD-2-Clause-Patent licensing. Vendor firmware keeps its original licensing and provenance; the fork's binary submodule and extraction sources are documented in [BINARIES](BINARIES.md).

## 中文阅读入口

这是realme X2 Pro的EDK2/UEFI与主线Linux移植项目。续作先读[检查点](NEXT-SESSION.md)、[操作边界](WORKING-BOUNDARIES.md)及[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。过程与失败记录见[会话索引](sessions/INDEX.md)；本次整理前的README和旧交接保存在[逐字快照](archive/docs-before-maintenance-2026-10-14/README.md)。
