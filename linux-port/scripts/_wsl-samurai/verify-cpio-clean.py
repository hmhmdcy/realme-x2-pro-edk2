#!/usr/bin/env python3
"""End-to-end check: the archive parses cleanly to its trailer."""
import gzip
import sys

sys.path.insert(0, "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai")
import cpio  # noqa: E402

path = sys.argv[1]
raw = (gzip.decompress(open(path, "rb").read())
       if path.endswith(".gz") else open(path, "rb").read())
names = [n for n, _, _ in cpio.entries(raw)]
print(f"{path}: members={len(names)} last={names[-1]!r}")
print("has init:", "init" in names)
print("has regdb:", "lib/firmware/regulatory.db" in names)
