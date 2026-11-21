#!/usr/bin/env python3
"""Prove regulatory.db is inside the built kernel Image, not only in the
source archive (gen_initramfs.sh can silently produce an empty cpio)."""
import sys
import zlib

img = sys.argv[1]
data = open(img, "rb").read()
print(f"image bytes {len(data)}")

# A single ".cpio" CONFIG_INITRAMFS_SOURCE is embedded with compress-y :=
# copy, i.e. uncompressed, but with a gzip *footer* field left in the
# placeholder.  Search for the archive body directly, and fall back to a
# streaming inflate only if a real gzip member is present.
sys.path.insert(0, "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/_wsl-samurai")
import cpio  # noqa: E402

raw = None
cpio_at = -1
pos = 0
while True:
    i = data.find(b"070701", pos)
    if i < 0:
        break
    if data[i + 6:i + 14].isdigit() or data[i + 6:i + 14].isalpha():
        # A real header is followed by 13 printable hex fields.
        if all(48 <= c <= 57 or 65 <= c <= 70 or 97 <= c <= 102
               for c in data[i + 6:i + 110]):
            cpio_at = i
        break
    pos = i + 1
if cpio_at >= 0:
    raw = data[cpio_at:]
if raw is None or raw[:6] != b"070701":
    # Walk every gzip-looking offset: the Image also contains unrelated
    # compressed blobs, so only accept the one that inflates to a cpio.
    pos = 0
    while True:
        gz_at = data.find(b"\x1f\x8b\x08", pos)
        if gz_at < 0:
            break
        pos = gz_at + 1
        try:
            candidate = zlib.decompressobj(
                16 + zlib.MAX_WBITS).decompress(data[gz_at:])
        except Exception:
            continue
        if candidate[:6] == b"070701":
            raw = candidate
            print(f"  gzip initramfs at {gz_at}")
            break
if raw is None or raw[:6] != b"070701":
    raise SystemExit("could not locate the embedded initramfs archive")

names = [n for n, _, _ in cpio.entries(raw)]
print(f"initramfs: {len(raw)} bytes, {len(names)} members")
for probe in ("lib/firmware/regulatory.db",
              "lib/firmware/regulatory.db.p7s",
              "bin/busybox", "init", "usr/sbin/samurai-rootfs"):
    print(f"  {probe:<34} {'yes' if probe in names else 'NO'}")
for probe in (b"lib/firmware/regulatory.db",
              b"regulatory.db.p7s",
              b"usr/sbin/samurai-rootfs",
              b"bin/busybox"):
    pos = data.find(probe)
    print(f"  {probe.decode():<32} at {pos}")
    if pos > 0:
        print(f"    context {data[pos-20:pos+30]!r}")
