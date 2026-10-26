# EDK2/UEFI for realme X2 Pro (RMX1931 / "samurai")

Status: **boots to the UEFI Boot Manager and EFI Shell on real hardware**
(PEI -> DXE -> BDS -> Boot Manager -> Shell, UFS partitions enumerated).

## Hardware
- Qualcomm SM8150-AC (msmnile), 8 GiB RAM
- UFS storage, no persistent UEFI variable store (variables are lost on reboot)
- 1080x2400 AMOLED panel; the framebuffer is left initialised by ABL/XBL

## Required local files (NOT part of this repository)
The device-specific DXE drivers are dumped from the stock `xbl.img` and must be
placed under `Platform/EFI_Binaries/Drivers/Devices/samurai/`:

    DALSys/DALSys.efi, DALSys/DALSys.depex
    ButtonsDxe/ButtonsDxe.efi, ButtonsDxe/ButtonsDxe.depex   (not used, see gotcha 4)
    UsbPwrCtrlDxe/UsbPwrCtrlDxe.efi, UsbPwrCtrlDxe/UsbPwrCtrlDxe.depex

`ConfigParameters`/memory map reference: the factory `uefiplat.cfg` (Project-Aloha/UEFIFirmwareBackup, `realme-rmx1931`).

## Building

    cd edk2-msm
    ./build.sh -d samurai --toolchain GCC5

Output: `boot-samurai.img` (flashable Android boot image) and
`workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd`.

Host toolchain note: on very new GCC (e.g. GCC 15) BaseTools/Pccts need
`-std=gnu17`; append it to `GCC_AARCH64_CC_FLAGS` in `tools/tools_def.txt`
(the file is copied into `Common/edk2/Conf/` by `build.sh`).

## Flashing / testing
ABL on this device does **not** implement `fastboot boot`, so the image has to
be flashed:

    fastboot flash boot boot-samurai.img
    # rollback (keep a verified backup!):
    fastboot flash boot boot_stock_RMX1931.img

## Key findings / gotchas
1. The boot image must use the project default layout:
   `header v1 + gzip(BootShim.bin + SM8150_UEFI.fd) + appended FdtBlob_compat/<device>.dtb`.
   Do **not** override `platform_build_kernel`/`platform_build_bootimg` in a
   device `*.sh.inc` (an uncompressed payload, a header v2 with a separate dtb
   section or a missing appended DTB make ABL return to fastboot or hang).
2. `gQcomTokenSpaceGuid.PcdMipiFrameBufferAddress` **must be `0x9D000000`** on
   samurai (the platform default `0x9C000000` is the Xiaomi/OnePlus layout).
   With the default `USE_UART=0` the platform uses
   `Silicon/Qualcomm/QcomPkg/Library/FrameBufferSerialPortLib`, which renders
   *all* DEBUG output into the framebuffer. With a wrong address nothing is
   visible and the boot looks exactly like a hang at the bootloader logo.
3. `-DHAS_MLVM` must be defined: the 8 GiB memory map branch then reserves
   `0xA0000000..0xBBB00000`, which matches the `no-map` carveouts
   (`qseecom_region`, `cdsp_sec_regions`) of the device DTB.
4. `ButtonsDxe` must be taken from the shared `Drivers/sm8150/ButtonsDxe`.
   The vendor-extracted `ButtonsDxe` never comes up in this environment (it
   additionally requires vendor TLMM handling), and with it the volume keys do
   nothing. (Known issue: the shared driver reads Volume-Down through the PMIC
   PON real-time IRQ while on samurai the key is wired to a GPIO, so
   Volume-Down does not work - only Volume-Up/Power.)
5. `FdtBlob/<device>/<device>.dtb` is the **mainline** DTB which is handed to
   Linux through the EFI configuration table, while
   `FdtBlob_compat/<device>.dtb` is the Android/vendor DTB appended to the boot
   image. Do not swap them: with a vendor DTB the built-in
   `LinuxSimpleMassStorage` kernel falls back to `usb_nop_phy` and USB never
   comes up.
6. The `USB Attached SCSI (UAS) Storage` boot option is BigfootACA's
   `linux-simple-mass-storage` kernel: it turns the phone into a USB mass
   storage device exposing the **raw UFS LUNs**. Handle with care - never let
   the host OS initialise or format those disks.

## Open items
- Volume-Down key (see gotcha 4).
- `ACPI/DSDT.aml` is currently borrowed from cepheus; Windows needs a
  samurai-specific DSDT.
- Optional display driver (`USE_DISPLAYDXE` + factory panel XML) for a
  graphical console.

## Credits
- [edk2-msm](https://github.com/edk2-porting/edk2-msm) (Renegade Project) and SimpleInit
- [linux-simple-mass-storage](https://github.com/BigfootACA/linux-simple-mass-storage)
- [Project-Aloha/UEFIFirmwareBackup](https://github.com/Project-Aloha/UEFIFirmwareBackup) for the factory DXE set / uefiplat.cfg
