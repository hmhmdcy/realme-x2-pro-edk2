#!/usr/bin/env python3
"""Only accept a file system whose \Image really is a PE kernel image.

The firmware's FAT driver mis-binds to the modem partition on this handset and
that bogus volume even "contains" a \Image, so opening the file is not enough:
BDS was told to boot a kernel from the modem partition and died with a fatal
BdsDxe error.  Require the PE signature instead.
"""
import os, sys
RK = "/home/cy122/edk2-samurai/repo"
p = os.path.join(RK, "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c")
s = open(p, encoding="utf-8").read()
old = ("    File->Close (File);\n"
       "    DevicePath = FileDevicePath (Handles[Index], SAMURAI_KERNEL_FILE);\n")
new = ("    //\n"
       "    // Do not trust the file name alone.  The FAT driver mis-binds to the modem\n"
       "    // partition on this handset and that bogus volume even exposes a \\Image, and\n"
       "    // booting a kernel that is not there makes BdsDxe die with a fatal error.  A\n"
       "    // kernel image starts with the PE signature \"MZ\".\n"
       "    //\n"
       "    {\n"
       "      UINT8    Magic[2] = { 0, 0 };\n"
       "      UINTN    MagicSize = sizeof (Magic);\n"
       "      BOOLEAN  LooksLikeKernel;\n"
       "\n"
       "      LooksLikeKernel = !EFI_ERROR (File->Read (File, &MagicSize, Magic)) &&\n"
       "                        (MagicSize == 2) && (Magic[0] == 'M') && (Magic[1] == 'Z');\n"
       "      File->Close (File);\n"
       "      if (!LooksLikeKernel) {\n"
       "        Print (L\"[SAMURAI] a file system has a \\\\Image that is not a kernel, skipped\\n\");\n"
       "        continue;\n"
       "      }\n"
       "    }\n"
       "\n"
       "    DevicePath = FileDevicePath (Handles[Index], SAMURAI_KERNEL_FILE);\n")
n = s.count(old)
if n != 1:
    sys.exit("anchor found %d times (want 1):\n%r" % (n, old[:200]))
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
print("patched", p)