# Reference and decisions (formerly HANDOVER-NEXT sections 8-11)

当前操作规则：[WORKING-BOUNDARIES](../WORKING-BOUNDARIES.md)。用户已撤销其余临时禁令；下方历史中的GPU禁测、固定时序、只读、禁复用及禁提交推送等条款不再适用。硬件状态和既有失败记录仍保留。

> Extracted verbatim from HANDOVER-NEXT.md on 2026-10-08.  The living handover is
> HANDOVER-NEXT.md; the session logs are in `sessions/`.

## 8. Linux boot path and persistent variables - decision (2026-10-07)

Both items are OFF the firmware critical path.  Community practice and the
reasoning are recorded here so this does not get re-analysed every session.

### What the firmware already provides

* Disk stack is in the FV: DiskIoDxe, PartitionDxe, EnhancedFatDxe,
  FvSimpleFileSystem (Apriori.fdf.inc:109-124), so UEFI can read FAT partitions
  and load an EFI application from \EFI\BOOT\BOOTAA64.EFI.
* UFS through the vendor UFSDxe (Shell map/blk shows all six LUNs).
* The platform already runs a Linux kernel as a UEFI application
  (LinuxSimpleMassStorage, MODULE_TYPE = UEFI_APPLICATION).
* The mainline DTB is handed to Linux through the EFI configuration table
  (FdtBlob/<device>/); FdtBlob_compat/<device>.dtb is the vendor DTB appended
  to the boot image so ABL can build the runtime DTB.

### How other phone ports do it (references)

* Renegade / edk2-msm: SimpleInit is only a boot manager - the OS is loaded by
  GRUB or Windows Boot Manager as an EFI application.  Boot menu settings live
  in a config file on a partition (e.g. simpleinit.static.uefi.cfg on the logfs
  partition), NOT in UEFI variables.
    https://renegade-project.tech/en/config/bootmenu
    https://github.com/edk2-porting/edk2-msm
    https://github.com/edk2-porting/renegade-project.org/blob/master/en/multiboot.md
* postmarketOS dual boot on SDM845-class phones: repartition with TWRP/sgdisk,
  create an ESP (set N esp on), pmbootstrap install --split, then boot through
  Renegade UEFI + GRUB.
    https://wiki.postmarketos.org/wiki/Dual_Booting
    https://gist.github.com/raihan2000/70dd18a4022cab8f3411e5665fea5902
* Phones with an SD card slot can boot entirely from SD with no GPT changes;
  the X2 Pro has no card slot, so that escape hatch does not exist here.

### Decision

* initrd / distro boot: NOT implemented in firmware, on purpose.  initrd and
  DTB handoff are the OS loader's job (GRUB publishes LINUX_EFI_INITRD_MEDIA_GUID
  and passes the DTB via devicetree or the EFI config table).  The firmware
  prerequisite - loading an EFI application from a FAT partition - already works.
* Persistent UEFI variables: NOT implemented; accepted as optional.  Variables
  stay emulated (PcdEmuVariableNvModeEnable=TRUE, QcomCommonDsc.inc:92) and are
  lost on reboot.  This only matters for Windows/WoA installers; for the Boot
  Manager / Shell / UFS / EUD-debug goals it is irrelevant.
* Do NOT repartition the phone just to tick the checklist.  If a distro is ever
  wanted, a full GPT backup plus a verified EDL/9008 rescue path must come first.

### If someone wants it later (deferred plan)

1. Back up the GPT (sgdisk --backup) and the partition headers; confirm an
   EDL/9008 rescue path.
2. Shrink userdata with TWRP and create a FAT32 ESP (512 MB - 1 GB), optionally
   a Linux rootfs partition.  Never touch modem / persist / op1 / op2 / super.
3. Put grubaa64.efi as EFI/BOOT/BOOTAA64.EFI plus kernel, initrd, DTB and
   grub.cfg on the ESP:

       menuentry "Linux" {
         devicetree /samurai.dtb
         linux     /kernel.efi console=tty0 root=PARTUUID=<rootfs> rw
         initrd    /initrd.img
       }

   SimpleInit will discover it; if not, register a boot option in PlatformBm.c
   the same way the UAS entry is registered.
4. Minimal proof without a distro: put kernel.efi + initrd.img + startup.nsh on
   the ESP and run it from the Shell (the Shell has no letter input, so
   startup.nsh is mandatory):

       fs0:\kernel.efi console=tty0 initrdfile=fs0:\initrd.img

   (older kernels accept initrd= instead of initrdfile=)
5. A file-backed variable store already exists in the tree if ever needed:
   Common/edk2/OvmfPkg/Library/NvVarsFileLib (OVMF model: keep emulated mode,
   read \NvVars early, save it at ExitBootServices).  Not needed now.

---
## 9. Port checklist status (2026-10-07)

| Item | Status | Note |
|---|---|---|
| Stable boot | ✅ | PEI -> DXE -> BDS -> Boot Manager -> EFI Shell, verified on hardware |
| Memory | ✅ | 8 GiB profile: -DHAS_MLVM + ABL-patched runtime DTB |
| GOP / display | ✅ | framebuffer text console 1080x2400; optional DisplayDxe not enabled |
| Buttons | ✅ | Vol-Up / Vol-Down / Power (factory ButtonsDxe + OppoProject + ResetRuntimeDxe) |
| Select / load Linux | 🟡 | delegated: SimpleInit + GRUB.  Firmware can load EFI apps; no distro installed |
| DTB passed | ✅ | mainline DTB via EFI configuration table; vendor DTB appended for ABL |
| initrd passed | 🟡 | delegated to GRUB; firmware side intentionally not implemented |
| UFS | ✅ | six LUNs, GPT, Shell map/blk; raw LUNs via the UAS boot option |
| USB for debugging | ✅ | EUD CTL + EUD COM + DEBUG over EUD (host qcser driver needed); SWD/JTAG not yet |
| Persistent variables | ❌ | not implemented, optional; only needed for Windows/WoA |
| Windows on Arm | ❌ | DSDT still borrowed from cepheus |﻿
---

---
## 10. Linux porting paths and when a partition change is really needed (2026-10-07)

A first Linux bring-up on this phone does NOT require touching the partition
table.  Do not repartition unless one of the cases in the last table applies.

### Paths that need NO GPT change

1. Android boot model, mainline kernel + built-in initramfs (recommended first
   step for a Linux port):
   - the repo already has the pieces: configs/devices/samurai.conf,
     tools/mkbootimg.py (header v1 + gzip payload + appended DTB) and the
     mainline DTB at Platform/Realme/sm8150/FdtBlob/samurai/*.dtb;
   - replace the UEFI FD payload with the Linux kernel + initramfs, build a
     boot.img, then:  fastboot flash boot boot-linux-bringup.img
   - the system runs from RAM (tmpfs); display / USB / UFS / buttons can be
     validated; going back to Android is just flashing the stock boot image.
2. EDK2/UEFI model, EFI-stub kernel embedded in the firmware as a UEFI
   application:
   - the platform already does exactly this with LinuxSimpleMassStorage
     (MODULE_TYPE = UEFI_APPLICATION, built-in initramfs, launched from the FV);
   - a bring-up kernel can be embedded the same way - no FAT partition and no
     GPT change; not suitable for a persistent distro.
3. Persistent rootfs without a GPT change: format userdata (ext4/f2fs) and use
   it as the rootfs.  Data is lost, but the partition table is untouched and
   Android can be restored at any time.

### Paths that DO need a GPT change

| Goal | Why |
|---|---|
| Android + Linux dual boot | must shrink userdata and create a second partition |
| Persistent distro while keeping Android data | same |
| EDK2/UEFI + GRUB distro | UEFI only reads FAT, so an ESP must exist |
| Windows on Arm | ESP + NTFS, same as the WoA community guides |

### Two distinctions that keep getting confused

* mkfs of an existing partition is NOT repartitioning.  Formatting userdata
  keeps the GPT intact; sgdisk/parted rewrite the GPT and are the real risk.
* Repartitioning itself needs neither EDL nor auth.  The community does it
  from TWRP with parted/gdisk on /dev/block/sda; userdata is the last
  partition, so the other partition offsets do not move.  EDL is only the
  rescue path for a hard brick (no fastboot, no recovery).

### Rules for the partition-touching cases (from the WoA community)

* partition names must not contain spaces and must not be empty - ABL fails
  otherwise; fix with parted, never with Windows diskpart/diskmgmt;
* back up the GPT and the partition headers before touching anything;
* keep QCN/EFS backed up - a full EDL flash erases IMEI.

---
## 11. EDL (9008) resources for RMX1931, and the auth question (2026-10-07)

The earlier assumption "realme has no public EDL package" was wrong - resources
exist (third-party mirrors, verify hashes and scan before use):

* firehose programmer (ELF/MBN) for RMX1931/SM8150:
    https://filewale.com/folders/rmx1931-realme-x2-pro-1/16100
* QFIL XML full firmware packages (rawprogram/patch XML + images):
    RMX1931EX-11-C.36-210310-XML-FIRMWARE-QFIL.rar (5.1 GB)
    RMX1931-11-F.10-210425-XML-FIRMWARE-QFIL.rar (3.8 GB)
    https://azrom.net/rom-realme-x2-pro-rmx1931-all-file-repair-firmware/
* tools / guides:
    https://github.com/salokrwhite/OplusEdlTool   (open source, OFP/OPS, backups)
    https://github.com/AdaUnlocked/OnePlus-9008-JiuZhuan-Guide
    https://github.com/kxob/OnePlus-9008-Unbrick-Guide
    ROM2box (XDA), "no auth" MSM Download Tool for RMX1931 (romprovider)
* Chinese 9008 line-flash packages:
    https://yun.daxiaamu.com/Realme_Roms/ (realme X2 Pro RMX1931 page)
* already on this machine:
    E:\RMX1931_11_OTA_1340_all_2QCxQYdkxpql.ozip          (3.19 GB, CN full OTA)
    E:\系统rom\RMX1931_11_OTA_1330_all_19781_downgrade.ozip (3.19 GB, downgrade)
    EDL reference scripts from the OnePlus 7T mainline work:
      E:\Realme X2 Pro移植主线Linux\sources\oneplus-reference\hotdog-linux-bringup\scripts\
      restore-boot-b-from-edl-firehose.sh, watch-edl-dump-critical.sh

Auth reality - do not rely on "no auth" being permanent:

* There is no real auth bypass.  "No auth" means leaked signed firehose files
  (devprg*.mbn plus digest/signature) reused by community tools.  It covers
  older models/firmware such as RMX1931, but OPPO has changed the scheme on
  newer firmware (the OnePlus 13 / Ace5 update went back to service-only auth,
  with no downgrade package).
* Consequence: do NOT update the firmware and do NOT re-lock the bootloader,
  otherwise the leaked files may stop working.
* A firehose file alone is not enough.  Four things are needed: a matching
  signed programmer (plus digest/signature if the device enforces auth), a
  matching firmware package (rawprogram/patch XML, or OFP/OPS), a tool that
  speaks the OPLUS protocol, and correct partition definitions for this exact
  model.  Plus a QCN/EFS backup because a full EDL flash erases IMEI.
* Safe rehearsal (zero risk): get into 9008, let the tool detect the device and
  load the firehose, then stop before flashing.  Only after that, and after the
  no-auth recovery path (fastboot images + QCN/EFS + ozip) is in place, should
  a GPT change even be considered.﻿
---
