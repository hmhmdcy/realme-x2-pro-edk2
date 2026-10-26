// SAMURAI: where the mainline Linux kernel lives on a file system.  It used to be
// an FFS file in this firmware volume; see SamuraiRegisterKernelBootOption() for why
// that cannot work with a 30 MB kernel.  The name is 8.3 friendly on purpose, so the
// volume does not depend on VFAT long name support.
//
#define SAMURAI_KERNEL_FILE  L"\\Image"

//
// SAMURAI: same string as /chosen/bootargs of the device tree in
// FdtBlob/samurai/.  It is passed as the LoadOptions of the boot option so
// the log channel survives even if the device tree reaches the kernel
// without bootargs.  CHAR16 on purpose: the EFI stub reads LoadOptions as
// UTF-16 and an ASCII buffer would be decoded into garbage that *replaces*
// the device tree's bootargs.
//
STATIC CHAR16  mSamuraiLinuxCmdLine[] =
  L"earlycon=eud,mmio,0x88e0000 console=tty0 console=eud loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused";

/**
  SAMURAI: register the mainline Linux kernel that lives on a file system.

  The kernel is a plain EFI application (CONFIG_EFI_STUB), so this is a normal
  LoadImage - no loader stub is needed.  The device tree does not have to sit
  next to it either: DtPlatformDxe already installed FdtBlob/samurai/ as the EFI
  configuration table and the stub takes the device tree from there.

  Keeping the kernel out of the firmware volume is deliberate:
    - an FFS file cannot exceed 16 MiB because the size field is 24 bit, and the
      kernel is 30 MB, so embedding it silently truncated the file and
      corrupted FVMAIN;
    - that volume decompressed to 62 MB, which does not fit in the PrePi/DXE
      memory pool (PcdUefiMemPoolSize), so the DXE core was never loaded.

  On this handset the kernel sits on the FAT16 "logdump" partition, a 64 MiB
  Qualcomm log partition that the Android ROM never mounts.
**/
