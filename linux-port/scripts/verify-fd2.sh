#!/bin/bash
# 修正验证：找到 FD、从 boot.img 解出 BootShim+FD、核对 FD 尺寸与 FV 头
set -u
RK=/home/cy122/edk2-samurai/repo
OUT=/mnt/e/edk2-samurai-out

echo "=== 找到 FD 文件 ==="
find "$RK" -name '*.fd' 2>/dev/null | head
for f in $(find "$RK" -name '*.fd' 2>/dev/null); do ls -la "$f"; done

echo
echo "=== 从 boot.img 解出 BootShim + FD ==="
python3 - "$RK/boot-samurai.img" <<'PY'
import sys, struct, zlib, os
p = sys.argv[1]
b = open(p, 'rb').read()
magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page = struct.unpack_from('<8sIIIIIIII', b, 0)
payload = b[page:page+ksize]
d = zlib.decompressobj(16 + zlib.MAX_WBITS)
raw = d.decompress(payload)
print(f"解压出 {len(raw)} 字节 = BootShim + FD")
print("前 16 字节:", raw[:16].hex())
idx = raw.find(b'_FVH')
print("FV 头 '_FVH' 偏移:", idx)
if idx >= 0:
    fd_start = idx - 40  # _FVH 位于 EFI_FIRMWARE_VOLUME_HEADER 偏移 40
    fd = raw[fd_start:]
    fvlen = struct.unpack_from('<Q', raw, fd_start + 32)[0]  # FvLength
    print(f"FD 起始 {fd_start}, FvLength=0x{fvlen:x} ({fvlen}), 实际剩余 {len(fd)}")
    print(f"FD 文件尺寸应为 0x1400000 = {0x1400000}")
    open('/tmp/extracted.fd','wb').write(fd)
    print("已写出 /tmp/extracted.fd")
PY
if [ -f /tmp/extracted.fd ]; then
  ls -la /tmp/extracted.fd
  echo "--- 与构建目录里的 FD 对比 ---"
  for f in $(find "$RK" -name '*.fd' 2>/dev/null); do
    echo "$f: $(stat -c%s "$f")  $(sha256sum "$f" | cut -c1-16)"
  done
  echo "/tmp/extracted.fd: $(stat -c%s /tmp/extracted.fd)  $(sha256sum /tmp/extracted.fd | cut -c1-16)"
fi

echo
echo "=== 归档 FD ==="
for f in $(find "$RK" -name '*.fd' 2>/dev/null); do
  cp -f "$f" "$OUT/$(basename "$f" .fd)-linux.fd"
  ls -la "$OUT/$(basename "$f" .fd)-linux.fd"
done
