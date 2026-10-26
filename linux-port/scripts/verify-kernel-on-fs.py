#!/usr/bin/env python3
"""Verify the firmware that loads the kernel from a file system instead of its FV."""
import hashlib, os, struct, sys, zlib

RK = "/home/cy122/edk2-samurai/repo"
FD = os.path.join(RK, "workspace/Build/samurai/RELEASE_GCC5/FV/SM8150_UEFI.fd")
FVM = os.path.join(RK, "workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv")
BOOT = os.path.join(RK, "boot-samurai.img")
KERNEL_GUID = bytes.fromhex("421e3c7a559d8b4cb6210f8a442e913d")

problems = []
def check(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok: problems.append(msg)

fd = open(FD, "rb").read()
fvm = open(FVM, "rb").read()
print("FD size        :", len(fd), hex(len(fd)))
print("FVMAIN.Fv size :", len(fvm), "(%.1f MiB)" % (len(fvm)/1048576))
print("PrePi pool     : 0x4230000 = %.1f MiB" % (0x4230000/1048576))
check(len(fd) == 0x700000, "FD is back to 0x700000 (7 MiB)")
check(len(fvm) < 0x2200000, "uncompressed FVMAIN fits the PrePi pool with room to spare")

for s in ("[SAMURAI] kernel found, registered",
          "[SAMURAI] no \\Image on any file system",
          "[SAMURAI] no file system to look for the kernel on"):
    check(fvm.find(s.encode("utf-16-le")) >= 0, "scanner string present as UTF-16: %r" % s)

check(fvm.find(KERNEL_GUID) < 0, "kernel FFS file is gone from the volume")
check(fvm.count(b"realme,samurai") >= 1, "mainline device tree still present")
check(fvm.count(b"xiaomi,cepheus") == 0, "cepheus device tree still gone")

cmd = ("earlycon=eud,mmio,0x88e0000 console=tty0 loglevel=7 "
       "ignore_loglevel panic=15 clk_ignore_unused pd_ignore_unused regulator_ignore_unused")
check(fvm.find(cmd.encode("utf-16-le")) >= 0, "kernel command line still compiled in (LoadOptions)")

b = open(BOOT, "rb").read()
magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page = struct.unpack_from("<8sIIIIIIII", b, 0)
print("boot.img       :", len(b), "bytes, kernel_size", ksize)
raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(b[page:page+ksize])
i = raw.find(b"_FVH"); start = i - 40
check(raw[start:start+len(fd)] == fd, "FD embedded in boot.img is byte-identical to the build output")
print("boot.img sha256:", hashlib.sha256(b).hexdigest())
print("FD sha256      :", hashlib.sha256(fd).hexdigest())

print()
if problems:
    print("RESULT: %d problem(s)" % len(problems))
    sys.exit(1)
print("RESULT: all checks passed")