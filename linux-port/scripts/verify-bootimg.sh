#!/bin/bash
# 端到端验证 boot.img：BootShim + FD 尺寸 + 尾部追加 DTB + 归档
set -u
RK=/home/cy122/edk2-samurai/repo
OUT=/mnt/e/edk2-samurai-out

python3 - "$RK/boot-samurai.img" <<'PY'
import sys, struct, gzip, io
p = sys.argv[1]
b = open(p, 'rb').read()
magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page = struct.unpack_from('<8sIIIIIIII', b, 0)
print(f"header: magic={magic.decode()} kernel_size={ksize} kernel_addr=0x{kaddr:x} "
      f"page={page} ramdisk_size={rsize} tags_addr=0x{tags:x}")
payload = b[page:page+ksize]
# 尾部追加 DTB：payload 末尾的 450826 字节
vdtb = payload[-450826:]
print("尾部追加 DTB 魔数:", vdtb[:4].hex(), "(应为 d00dfeed)")
print("尾部 DTB 里的机型串:")
import re
print("  ", re.findall(rb'[\x20-\x7e]{6,40}', vdtb[:200000])[:6])
raw = gzip.decompress(payload)
print(f"解压后载荷 = BootShim + FD, 共 {len(raw)} 字节")
# BootShim.S 里 .quad UEFI_BASE / UEFI_SIZE 在开头附近
# 直接找 FD 签名 _FVH (0x4856465f)
idx = raw.find(b'_FVH')
print("FD 起始偏移:", idx)
if idx >= 0:
    fd = raw[idx-40:]
    hdr_len = struct.unpack_from('<I', raw, idx+48-40)[0] if False else None
    print("FD 头魔数:", raw[idx-40+40-12:idx-40+40-8].hex())
    print("FD 长度（文件里剩余部分）:", len(raw) - (idx - 40))
    fvlen = struct.unpack_from('<I', raw, (idx-40)+8+24)[0] if False else None
print("BootShim 头部 16 字节:", raw[:16].hex())
# 从 BootShim 里读 UEFI_BASE/UEFI_SIZE（.quad）
base, size = struct.unpack_from('<QQ', raw, 0x28) if len(raw) > 0x38 else (0,0)
print(f"BootShim 里推断 UEFI_BASE=0x{base:x} UEFI_SIZE=0x{size:x} ({size} 字节)")
PY

echo
echo "=== 归档新固件到 Windows ==="
mkdir -p "$OUT"
cp -f "$RK/boot-samurai.img" "$OUT/boot-samurai-linux.img"
for f in $(find "$RK" -maxdepth 3 -name 'SM8150_UEFI*.fd' 2>/dev/null); do
  cp -f "$f" "$OUT/$(basename "$f" .fd)-linux.fd"
done
ls -la "$OUT" | tail -12
sha256sum "$OUT/boot-samurai-linux.img"
