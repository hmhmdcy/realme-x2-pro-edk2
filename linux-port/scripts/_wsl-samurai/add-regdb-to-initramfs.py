#!/usr/bin/env python3
"""Add regulatory.db(.p7s) to the kernel's embedded initramfs.

Why here: cfg80211 asks for the regulatory database at ~0.50 s, but the
F2FS rootfs (which carries /lib/firmware/regulatory.db) is only mounted at
~1.77 s and switch_root happens later.  During that window the firmware
search path is the initramfs, whose /lib/firmware has ath10k/qca/qcom but
no regdb.  Adding it there is what makes `iw reg get` report a real
country instead of country 00 (which leaves 5 GHz passive-scan only).
"""
import gzip
import sys

sys.path.insert(0, "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai")
import cpio  # noqa: E402


def main(src, regdb, p7s, dst):
    raw = gzip.decompress(open(src, "rb").read())
    parts = []
    ino = 0
    added = set()
    for name, hdr, data in cpio.entries(raw):
        ino += 1
        if name in ("lib/firmware/regulatory.db",
                    "lib/firmware/regulatory.db.p7s"):
            continue  # keep the operation idempotent
        hdr_ino = int(hdr[6:6 + 8], 16)
        parts.append(cpio.blob(name, data, hdr_ino,
                               int(hdr[14:14 + 8], 16)))

    for name, path in (("lib/firmware/regulatory.db", regdb),
                       ("lib/firmware/regulatory.db.p7s", p7s)):
        parts.append(cpio.blob(name, open(path, "rb").read(), 900000 + len(added)))
        added.add(name)

    parts.append(cpio.blob("TRAILER!!!", b"", 0, 0))
    raw_out = b"".join(parts)
    gz = gzip.compress(raw_out, 9)
    open(dst, "wb").write(gz)
    print(f"members={len(parts)} raw={len(raw_out)} gz={len(gz)} -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
