#!/bin/bash
# The running kernel embeds an initramfs (CONFIG_INITRAMFS_SOURCE).  This
# decides where regulatory.db can be staged, because cfg80211 loads it at
# ~0.50s while the f2fs root only appears at ~1.77s.
set -eu
SRC=/mnt/e/edk2-samurai-out/kernel456/candidate-embedded-initramfs-private.gz
W=/root/irfs
mkdir -p "$W"
gzip -dc "$SRC" > "$W/initramfs.cpio"
ls -l "$W/initramfs.cpio"
cpio -it < "$W/initramfs.cpio" 2>/dev/null | head -40 ||
	python3 - "$W/initramfs.cpio" <<'PY'
import sys
d = open(sys.argv[1], "rb").read()
print("magic:", d[:6])
off = 0
n = 0
while off < len(d) and n < 40:
    if d[off:off+6] not in (b"070701", b"070702"):
        print("bad magic at", off)
        break
    def f(i):
        return int(d[off+6+i*4:off+6+(i+1)*4], 16)
    namesize = f(11)
    filesize = f(6)
    name = d[off+110:off+110+namesize-1].decode()
    print(f"  {name:40s} {filesize} bytes")
    hdr = 110 + namesize
    off += (hdr + filesize + 3) // 4 * 4
    n += 1
PY
