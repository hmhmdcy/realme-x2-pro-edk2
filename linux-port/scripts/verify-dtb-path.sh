#!/bin/bash
# 1) DtPlatformDxe 在没有"platform DTB"文件时是否仍然安装 EFI 配置表
# 2) FD 实际大小与 boot.img 结构
set -u
RK=/home/cy122/edk2-samurai/repo

echo "=== DtPlatformDxe 余下部分（120 行起）==="
sed -n '120,215p' "$RK/Common/edk2/EmbeddedPkg/Drivers/DtPlatformDxe/DtPlatformDxe.c"

echo
echo "=== DtPlatformLoadDtb 实现（DtPlatformDtbLoaderLib）==="
find "$RK/Common/edk2/EmbeddedPkg" -name 'DtPlatformDtbLoaderLib*' | head
sed -n '1,80p' "$RK/Common/edk2/EmbeddedPkg/Library/DtPlatformDtbLoaderLib/DxeDtPlatformDtbLoaderLib/DxeDtPlatformDtbLoaderLib.c" 2>/dev/null

echo
echo "=== FD / boot.img ==="
find "$RK" -maxdepth 3 -name '*.fd' 2>/dev/null | head
for f in $(find "$RK" -maxdepth 3 -name '*.fd' 2>/dev/null); do ls -la "$f"; done
ls -la "$RK/boot-samurai.img"
python3 - "$RK/boot-samurai.img" <<'PY'
import sys, struct
p = sys.argv[1]
b = open(p, 'rb').read()
magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page = struct.unpack_from('<8sIIIIIIII', b, 0)
print(f"magic={magic} kernel={ksize} @0x{kaddr:x} ramdisk={rsize} @0x{raddr:x} "
      f"second={ssize} tags=0x{tags:x} page={page}")
import gzip
print("kernel payload starts with gzip magic:", b[page*1:page*1+2] == b'\x1f\x8b')
print("总大小 %d 字节" % len(b))
PY
