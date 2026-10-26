#!/usr/bin/env python3
"""Offline verification of the samurai firmware image carrying the LoadOptions fix.

Read-only.  Everything is derived from the build tree under ~/edk2-samurai/repo,
so the whole result can be reproduced after a rebuild just by running it again:

    python3 verify-cmdline-firmware.py
"""
import hashlib
import os
import struct
import sys
import zlib

RK = "/home/cy122/edk2-samurai/repo"
BOOT = os.path.join(RK, "boot-samurai.img")
FD = os.path.join(RK, "workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd")
FVM = os.path.join(RK, "workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv")
MAIN_DTB = os.path.join(RK, "Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb")
COMPAT_DTB = os.path.join(RK, "Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb")
REF_FD = "/mnt/e/edk2-samurai-out/SM8150_UEFI-samurai-linux.fd"

CMDLINE = ("earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 "
           "ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused "
           "regulator_ignore_unused")
DESC = "Linux (mainline samurai)"

problems = []


def check(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


print("== 1. firmware device ==")
fd = open(FD, "rb").read()
check(len(fd) == 0x1400000, "FD size is 0x1400000 (got 0x%x)" % len(fd))
check(fd.count(b"_FVH") >= 1, "FD carries an FV header (_FVH)")
print("  FD sha256:", sha(FD))
if os.path.exists(REF_FD):
    old = sha(REF_FD)
    check(old != sha(FD), "FD changed vs the pre-fix archive (%s...)" % old[:16])

print("== 2. uncompressed FVMAIN ==")
fvm = open(FVM, "rb").read()
print("  FVMAIN size:", len(fvm))

u16 = CMDLINE.encode("utf-16-le")
off16 = fvm.find(u16)
check(off16 >= 0, "command line present as UTF-16 (offset %s)" % off16)
check(fvm.find(DESC.encode("utf-16-le")) >= 0,
      "boot option description 'Linux (mainline samurai)' present as UTF-16")

# An ASCII copy may only come from the device tree's own /chosen/bootargs.
# If the C code emitted one instead, the EFI stub would read ASCII as UTF-16,
# decode it into garbage and *overwrite* the device tree property with it.
ascii_ok = True
i = 0
while True:
    i = fvm.find(CMDLINE.encode("ascii"), i)
    if i < 0:
        break
    magic = fvm.rfind(b"\xd0\x0d\xfe\xed", max(0, i - 200000), i)
    size = struct.unpack_from(">I", fvm, magic + 4)[0] if magic >= 0 else 0
    inside_dtb = magic >= 0 and magic <= i < magic + size
    print("  ASCII copy at %d, inside device tree %s (fdt @ %s, %d bytes)"
          % (i, inside_dtb, magic, size))
    ascii_ok = ascii_ok and inside_dtb
    i += 1
check(ascii_ok, "no ASCII copy of the command line outside the device tree")

check(fvm.count(b"realme,samurai") >= 1, "samurai mainline device tree present")
check(fvm.count(b"xiaomi,cepheus") == 0, "cepheus (Mi 9) device tree is gone")

print("== 3. boot-samurai.img ==")
b = open(BOOT, "rb").read()
magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page = struct.unpack_from(
    "<8sIIIIIIII", b, 0)
print("  header: magic=%r kernel_size=%d kernel_addr=0x%x page=%d"
      % (magic, ksize, kaddr, page))
check(magic.rstrip(b"\0") in (b"ANDROID!", b"ANDROID"),
      "Android boot header v1 magic")
payload = b[page:page + ksize]

raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(payload)
print("  decompressed payload:", len(raw), "bytes")
idx = raw.find(b"_FVH")
fd_start = idx - 40
check(0 <= fd_start < len(raw), "FD located inside the BootShim payload")
extracted = raw[fd_start:]
check(len(extracted) == len(fd), "embedded payload is %d bytes like the FD" % len(fd))
check(extracted[:len(fd)] == fd, "embedded FD is byte-identical to the built FD")

compat = open(COMPAT_DTB, "rb").read()
appended = payload[-len(compat):]
check(appended == compat,
      "compat (vendor) device tree appended to the image is %s" % os.path.basename(COMPAT_DTB))
check(appended[:4] == b"\xd0\x0d\xfe\xed",
      "appended compat device tree has the FDT magic")

print("  boot.img size:", len(b))
print("  boot.img sha256:", sha(BOOT))
print("  mainline dtb sha256:", sha(MAIN_DTB))

print()
if problems:
    print("RESULT: %d problem(s)" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("RESULT: all checks passed")