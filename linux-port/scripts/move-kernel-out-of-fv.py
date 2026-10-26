#!/usr/bin/env python3
"""Stop embedding the mainline kernel in the firmware volume.

A 30 MB kernel cannot live in an FFS file: the FFS header has a 24 bit size
field, so GenFfs silently wrote a truncated size and corrupted FVMAIN.  The
62 MB uncompressed volume that resulted also does not fit the PrePi/DXE memory
pool (PcdUefiMemPoolSize = 0x04230000).

The kernel now lives on the 64 MiB "logdump" FAT partition and PlatformBm just
looks for \Image on every file system it can see.
"""
import os
import sys

RK = "/home/cy122/edk2-samurai/repo"


def edit(path, pairs):
    p = os.path.join(RK, path)
    s = open(p, encoding="utf-8").read()
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            sys.exit("%s: anchor found %d times (want 1):\n%r" % (path, n, old[:160]))
        s = s.replace(old, new, 1)
    open(p, "w", encoding="utf-8").write(s)
    print("patched", path)


SCANNER = '''
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
STATIC
VOID
SamuraiRegisterKernelBootOption (
  VOID
  )
{
  EFI_STATUS                       Status;
  EFI_HANDLE                       *Handles;
  UINTN                            HandleCount;
  UINTN                            Index;
  EFI_SIMPLE_FILE_SYSTEM_PROTOCOL  *FileSystem;
  EFI_FILE_PROTOCOL                *Root;
  EFI_FILE_PROTOCOL                *File;
  EFI_DEVICE_PATH_PROTOCOL         *DevicePath;
  EFI_BOOT_MANAGER_LOAD_OPTION     NewOption;
  EFI_BOOT_MANAGER_LOAD_OPTION     *BootOptions;
  UINTN                            BootOptionCount;
  INTN                             OptionIndex;
  UINTN                            CmdLineSize;

  Status = gBS->LocateHandleBuffer (
                  ByProtocol,
                  &gEfiSimpleFileSystemProtocolGuid,
                  NULL,
                  &HandleCount,
                  &Handles
                  );
  if (EFI_ERROR (Status)) {
    Print (L"[SAMURAI] no file system to look for the kernel on\\n");
    return;
  }

  for (Index = 0; Index < HandleCount; Index++) {
    Status = gBS->HandleProtocol (
                    Handles[Index],
                    &gEfiSimpleFileSystemProtocolGuid,
                    (VOID **)&FileSystem
                    );
    if (EFI_ERROR (Status)) {
      continue;
    }

    Status = FileSystem->OpenVolume (FileSystem, &Root);
    if (EFI_ERROR (Status)) {
      continue;
    }

    Status = Root->Open (Root, &File, SAMURAI_KERNEL_FILE, EFI_FILE_MODE_READ, 0);
    Root->Close (Root);
    if (EFI_ERROR (Status)) {
      continue;
    }

    File->Close (File);
    DevicePath = FileDevicePath (Handles[Index], SAMURAI_KERNEL_FILE);
    if (DevicePath == NULL) {
      continue;
    }

    CmdLineSize = (StrLen (mSamuraiLinuxCmdLine) + 1) * sizeof (CHAR16);
    Status      = EfiBootManagerInitializeLoadOption (
                    &NewOption,
                    LoadOptionNumberUnassigned,
                    LoadOptionTypeBoot,
                    LOAD_OPTION_ACTIVE,
                    L"Linux (mainline samurai)",
                    DevicePath,
                    (UINT8 *)mSamuraiLinuxCmdLine,
                    (UINT32)CmdLineSize
                    );
    FreePool (DevicePath);
    if (EFI_ERROR (Status)) {
      break;
    }

    BootOptions = EfiBootManagerGetLoadOptions (&BootOptionCount, LoadOptionTypeBoot);
    OptionIndex = EfiBootManagerFindLoadOption (&NewOption, BootOptions, BootOptionCount);
    if (OptionIndex == -1) {
      EfiBootManagerAddLoadOptionVariable (&NewOption, MAX_UINTN);
      Print (L"[SAMURAI] kernel found, registered \\"Linux (mainline samurai)\\"\\n");
    } else {
      Print (L"[SAMURAI] kernel boot option is already present\\n");
    }

    EfiBootManagerFreeLoadOption (&NewOption);
    EfiBootManagerFreeLoadOptions (BootOptions, BootOptionCount);
    break;
  }

  if (Index == HandleCount) {
    Print (L"[SAMURAI] no \\\\Image on any file system - kernel not registered\\n");
  }

  FreePool (Handles);
}
'''

edit(
    "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c",
    [
        # includes
        ("#include <Protocol/PlatformBootManager.h>\n",
         "#include <Protocol/PlatformBootManager.h>\n"
         "#include <Protocol/SimpleFileSystem.h>\n"
         "\n"
         "#include <Library/MemoryAllocationLib.h>\n"),
        # the GUID becomes a file name
        ("//\n"
         "// SAMURAI: GUID of the mainline Linux kernel embedded in this firmware volume\n"
         "// (Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf).  Must match the\n"
         "// FILE_GUID there.\n"
         "//\n"
         "STATIC CONST EFI_GUID  mSamuraiLinuxKernelGuid = {\n"
         "  0x7a3c1e42, 0x9d55, 0x4c8b, { 0xb6, 0x21, 0x0f, 0x8a, 0x44, 0x2e, 0x91, 0x3d }\n"
         "};\n",
         "//\n"
         "// SAMURAI: where the mainline Linux kernel lives on a file system.  It used to be\n"
         "// an FFS file in this firmware volume; see SamuraiRegisterKernelBootOption() for why\n"
         "// that cannot work with a 30 MB kernel.  The name is 8.3 friendly on purpose, so the\n"
         "// volume does not depend on VFAT long name support.\n"
         "//\n"
         "#define SAMURAI_KERNEL_FILE  L\"\\\\Image\"\n"),
        # insert the scanner right before the #endif that closes the kernel block
        ("STATIC CHAR16  mSamuraiLinuxCmdLine[] =\n"
         "  L\"earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused\";\n"
         "#endif\n",
         "STATIC CHAR16  mSamuraiLinuxCmdLine[] =\n"
         "  L\"earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused\";\n"
         + SCANNER +
         "#endif\n"),
        # register the file system kernel instead of the FV file
        ("  //\n"
         "  // SAMURAI: the mainline Linux kernel built for this device.  BDS has already\n"
         "  // enabled EUD before the console is set up, so a host PC that ran \"eudtool\n"
         "  // com-up\" on the boot menu gets the complete kernel log from earlycon.\n"
         "  //\n"
         "  PlatformRegisterFvBootOption(\n"
         "      &mSamuraiLinuxKernelGuid, L\"Linux (mainline samurai)\", LOAD_OPTION_ACTIVE,\n"
         "      mSamuraiLinuxCmdLine);\n",
         "  //\n"
         "  // SAMURAI: find the mainline Linux kernel on a file system and register it.  BDS\n"
         "  // has already enabled EUD before the console is set up, so a host PC that ran\n"
         "  // \"eudtool com-up\" on the boot menu gets the complete kernel log from earlycon.\n"
         "  //\n"
         "  SamuraiRegisterKernelBootOption ();\n"),
    ])

# the kernel is no longer part of the firmware volume
edit(
    "Platform/Realme/sm8150/samurai.fdf.inc",
    [
        ("// SAMURAI: mainline Linux kernel (EFI stub) as a UEFI application in this FV.\n"
         "INF Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf\n",
         "// SAMURAI: the mainline Linux kernel is NOT in this firmware volume.  A 30 MiB\n"
         "// blob cannot be stored as an FFS file (24 bit size field) and the 62 MiB volume\n"
         "// that resulted did not fit the PrePi memory pool, so the DXE core was never\n"
         "// loaded.  The kernel lives on the FAT partition named \"logdump\" instead and\n"
         "// PlatformBm.c finds it there.  See HANDOVER-NEXT.md section 20.\n"),
    ])

# back to the known good FD size
edit(
    "configs/sm8150.conf",
    [("FD_SIZE=0x01400000", "FD_SIZE=0x00700000")])

edit(
    "Platform/Qualcomm/sm8150/sm8150.fdf",
    [("NumBlocks     = 0x1400", "NumBlocks     = 0x700"),
     ("0x00000000|0x01400000", "0x00000000|0x00700000")])

# leave a warning in the now unused INF
p = os.path.join(RK, "Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf")
s = open(p, encoding="utf-8").read()
warn = ("# DO NOT ADD THIS TO samurai.fdf.inc ANY MORE.\n"
        "#\n"
        "# The kernel is 30 MiB.  FFS files cannot exceed 16 MiB (the file header has a\n"
        "# 24 bit size field), so GenFfs silently truncated the size and corrupted FVMAIN;\n"
        "# the 62 MiB uncompressed volume then did not fit the PrePi memory pool at all.\n"
        "# The kernel now lives on the FAT \"logdump\" partition and PlatformBm.c finds it\n"
        "# there.  See HANDOVER-NEXT.md section 20.\n"
        "#\n")
if not s.startswith("# DO NOT ADD"):
    open(p, "w", encoding="utf-8").write(warn + s)
    print("warned", p)
print("all edits applied")