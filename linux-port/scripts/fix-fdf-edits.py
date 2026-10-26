#!/usr/bin/env python3
"""Redo the FDF edits without touching line endings (sm8150.fdf is CRLF)."""
import os
import subprocess

RK = "/home/cy122/edk2-samurai/repo"
os.chdir(RK)

subprocess.run(["git", "checkout", "--",
                "Platform/Qualcomm/sm8150/sm8150.fdf",
                "Platform/Realme/sm8150/samurai.fdf.inc"], check=True)

# sm8150.fdf keeps its CRLF line endings: edit at the byte level
p = "Platform/Qualcomm/sm8150/sm8150.fdf"
b = open(p, "rb").read()
for old, new in ((b"NumBlocks     = 0x1400", b"NumBlocks     = 0x700"),
                 (b"0x00000000|0x01400000", b"0x00000000|0x00700000")):
    assert b.count(old) == 1, old
    b = b.replace(old, new, 1)
open(p, "wb").write(b)
print("patched", p, "(byte level)")

# samurai.fdf.inc is LF
p = "Platform/Realme/sm8150/samurai.fdf.inc"
s = open(p, encoding="utf-8", newline="").read()
old = ("// SAMURAI: mainline Linux kernel (EFI stub) as a UEFI application in this FV.\n"
       "INF Platform/Realme/sm8150/LinuxKernel/SamuraiLinuxKernel.inf\n")
new = ("// SAMURAI: the mainline Linux kernel is NOT in this firmware volume.  A 30 MiB\n"
       "// blob cannot be stored as an FFS file (24 bit size field) and the 62 MiB volume\n"
       "// that resulted did not fit the PrePi memory pool, so the DXE core was never\n"
       "// loaded.  The kernel lives on the FAT partition named \"logdump\" instead and\n"
       "// PlatformBm.c finds it there.  See HANDOVER-NEXT.md section 20.\n")
assert s.count(old) == 1
open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
print("patched", p)