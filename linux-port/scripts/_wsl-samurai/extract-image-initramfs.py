#!/usr/bin/env python3
"""The built Image stores its initramfs compressed (gzip), so a plain byte
search for member names fails.  Locate the gzip blob, decompress it, and
verify the members that matter."""
import gzip
import sys

sys.path.insert(0, "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai")
import cpio  # noqa: E402

data = open(sys.argv[1], "rb").read()
print(f"image {len(data)} bytes")

found = 0
pos = 0
while True:
    i = data.find(b"\x1f\x8b\x08", pos)
    if i < 0:
        break
    pos = i + 1
    try:
        raw = gzip.decompress(data[i:])
    except Exception:
        continue
    if 116 <= len(raw) and raw[:6] in (b"070701", b"070702"):
        found += 1
        names = [n for n, _, _ in cpio.entries(raw)]
        print(f"  initramfs gzip at {i}: {len(raw)} bytes, "
              f"{len(names)} members")
        for probe in ("lib/firmware/regulatory.db",
                      "lib/firmware/regulatory.db.p7s",
                      "bin/busybox", "init"):
            print(f"    {probe:<34} {'yes' if probe in names else 'NO'}")
        if "lib/firmware/regulatory.db" in names:
            for n, _, body in cpio.entries(raw):
                if n == "lib/firmware/regulatory.db":
                    print(f"    regdb body {len(body)} bytes")
        break

if not found:
    print("  no embedded gzip initramfs found")
