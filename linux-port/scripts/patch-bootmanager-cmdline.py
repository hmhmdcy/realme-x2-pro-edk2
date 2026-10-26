#!/usr/bin/env python3
"""Hand the samurai kernel command line over as the boot option's LoadOptions.

PlatformRegisterFvBootOption() has no way to pass OptionalData, so every boot
option BDS registers here starts the image with empty LoadOptions.  That is
fine while the device tree carries /chosen/bootargs, but the arm64 EFI stub
*copies a non-empty EFI command line over* that property, so a device tree
that arrives without bootargs leaves the kernel with no console and no
earlycon - a silent black screen with nothing on EUD.

Passing the same string the device tree already contains changes nothing when
the normal path works and keeps the log channel alive when it does not.

The EFI stub reads LoadOptions as UTF-16 (libstub efi_convert_cmdline() formats
it with "%.*ls"), so the string must be CHAR16, not ASCII.
"""
import sys

PATH = ("/home/cy122/edk2-samurai/repo/Platform/RenegadePkg/"
        "Library/PlatformBootManagerLib/PlatformBm.c")

CMDLINE = ('earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 '
           'ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused '
           'regulator_ignore_unused')

s = open(PATH, encoding="utf-8").read()

if "mSamuraiLinuxCmdLine" in s:
    print("already applied, nothing to do")
    sys.exit(0)


def sub(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit("anchor found %d times (expected 1):\n%r" % (n, old[:200]))
    s = s.replace(old, new, 1)


# 1. the helper gains an optional command line
sub(
    "PlatformRegisterFvBootOption(\n"
    "    CONST EFI_GUID *FileGuid, CHAR16 *Description, UINT32 Attributes)\n"
    "{\n",

    "PlatformRegisterFvBootOption(\n"
    "    CONST EFI_GUID *FileGuid,\n"
    "    CHAR16 *Description,\n"
    "    UINT32 Attributes,\n"
    "    CHAR16 *CommandLine OPTIONAL)\n"
    "{\n")


# 2. declare the size of the optional data
sub(
    "  EFI_DEVICE_PATH_PROTOCOL *        DevicePath;\n"
    "  UINT16                            OptionNumber;\n",

    "  EFI_DEVICE_PATH_PROTOCOL *        DevicePath;\n"
    "  UINT16                            OptionNumber;\n"
    "  UINTN                             OptionalDataSize;\n")


# 3. pass it to the load option as OptionalData
sub(
    "  Status = EfiBootManagerInitializeLoadOption(\n"
    "      &NewOption, LoadOptionNumberUnassigned, LoadOptionTypeBoot, Attributes,\n"
    "      Description, DevicePath, NULL, 0);\n",

    "  //\n"
    "  // OptionalData becomes the loaded image's LoadOptions.  A kernel command\n"
    "  // line has to be a NUL terminated CHAR16 string, because the Linux EFI\n"
    "  // stub reads LoadOptions as UTF-16.\n"
    "  //\n"
    "  OptionalDataSize = 0;\n"
    "  if (CommandLine != NULL) {\n"
    "    OptionalDataSize = (StrLen(CommandLine) + 1) * sizeof(CHAR16);\n"
    "  }\n"
    "\n"
    "  Status = EfiBootManagerInitializeLoadOption(\n"
    "      &NewOption, LoadOptionNumberUnassigned, LoadOptionTypeBoot, Attributes,\n"
    "      Description, DevicePath, (UINT8 *)CommandLine, (UINT32)OptionalDataSize);\n")


# 4. the pre-existing callers keep their behaviour
sub('&gSimpleInitFileGuid, L"Simple Init", LOAD_OPTION_ACTIVE);',
    '&gSimpleInitFileGuid, L"Simple Init", LOAD_OPTION_ACTIVE, NULL);')
sub('&gUefiShellFileGuid, L"UEFI Shell", LOAD_OPTION_ACTIVE);',
    '&gUefiShellFileGuid, L"UEFI Shell", LOAD_OPTION_ACTIVE, NULL);')
sub('&gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE);',
    '&gLinuxSimpleMassStorageGuid, L"USB Attached SCSI (UAS) Storage", LOAD_OPTION_ACTIVE,\n'
    '      NULL);')
sub('&gSwitchSlotsAppFileGuid, L"Reboot to other slot", LOAD_OPTION_ACTIVE);',
    '&gSwitchSlotsAppFileGuid, L"Reboot to other slot", LOAD_OPTION_ACTIVE, NULL);')


# 5. the command line itself, next to the kernel GUID
sub(
    "STATIC CONST EFI_GUID  mSamuraiLinuxKernelGuid = {\n"
    "  0x7a3c1e42, 0x9d55, 0x4c8b, { 0xb6, 0x21, 0x0f, 0x8a, 0x44, 0x2e, 0x91, 0x3d }\n"
    "};\n"
    "#endif\n",

    "STATIC CONST EFI_GUID  mSamuraiLinuxKernelGuid = {\n"
    "  0x7a3c1e42, 0x9d55, 0x4c8b, { 0xb6, 0x21, 0x0f, 0x8a, 0x44, 0x2e, 0x91, 0x3d }\n"
    "};\n"
    "\n"
    "//\n"
    "// SAMURAI: same string as /chosen/bootargs of the device tree in\n"
    "// FdtBlob/samurai/.  It is passed as the LoadOptions of the boot option so\n"
    "// the log channel survives even if the device tree reaches the kernel\n"
    "// without bootargs.  CHAR16 on purpose: the EFI stub reads LoadOptions as\n"
    "// UTF-16 and an ASCII buffer would be decoded into garbage that *replaces*\n"
    "// the device tree's bootargs.\n"
    "//\n"
    'STATIC CHAR16  mSamuraiLinuxCmdLine[] =\n'
    '  L"' + CMDLINE + '";\n'
    "#endif\n")


# 6. hand it to the kernel boot option
sub('&mSamuraiLinuxKernelGuid, L"Linux (mainline samurai)", LOAD_OPTION_ACTIVE);',
    '&mSamuraiLinuxKernelGuid, L"Linux (mainline samurai)", LOAD_OPTION_ACTIVE,\n'
    '      mSamuraiLinuxCmdLine);')

open(PATH, "w", encoding="utf-8").write(s)
print("patched %s" % PATH)