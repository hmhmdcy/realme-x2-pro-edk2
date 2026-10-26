#!/bin/bash
# 校验新 DTB：反编译后按括号深度解析 reserved-memory，并识别 EDK2 现有占位 DTB。
set -eu
cd /home/cy122/x2pro-linux/linux
DTB=arch/arm64/boot/dts/qcom/sm8150-samurai.dtb
OUT="/mnt/e/RealmeX2Pro edk2/linux-port/artifacts"
EDK="/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb"
mkdir -p "$OUT"
scripts/dtc/dtc -I dtb -O dts -o "$OUT/sm8150-samurai.dts.decompiled" "$DTB" 2>/dev/null

echo "=== reserved-memory ==="
python3 - "$OUT/sm8150-samurai.dts.decompiled" <<'PY'
import re, sys
lines = open(sys.argv[1]).read().splitlines()
start = None
for i, l in enumerate(lines):
    if l == '\treserved-memory {':
        start = i
        break
depth = 0
cur, props = None, []
out = []
for l in lines[start:]:
    if l == '\treserved-memory {':
        depth = 1
        continue
    if depth == 1:
        m = re.match(r'\t\t([^\s{]+) \{', l)
        if m:
            cur, props = m.group(1), []
            depth = 2
            continue
        if l == '\t};':
            break
        continue
    if depth == 2:
        if l == '\t\t};':
            out.append((cur, props)); cur, props = None, []; depth = 1
            continue
        props.append(l.strip())
for name, props in out:
    reg = next((p for p in props if p.startswith('reg =')), '')
    nomap = 'no-map' in props
    comp = next((p for p in props if p.startswith('compatible =')), '')
    m = re.search(r'<(0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+)>', reg)
    if m:
        print(f"  {name:<24} 0x{int(m.group(2),16):09x} + 0x{int(m.group(4),16):<8x} no-map={str(nomap):<5} {comp}")
    else:
        print(f"  {name:<24} {reg} {comp}")
PY

echo
echo "=== EDK2 占位 DTB 的身份 ==="
scripts/dtc/dtc -I dtb -O dts -o /tmp/edk-placeholder.dts "$EDK" 2>/dev/null
echo "  size $(stat -c%s "$EDK")  sha256 $(sha256sum "$EDK" | cut -c1-16)"
grep -m2 -E '^\tmodel = |^\tcompatible = ' /tmp/edk-placeholder.dts | sed 's/^/  /'
echo "  reserved-memory 节点数: $(grep -c '^\t\tmemory@' /tmp/edk-placeholder.dts || true)"
grep -m3 '^\t\tmemory@' /tmp/edk-placeholder.dts | sed 's/^/  /'
echo "  memory 节点:"; grep -A2 -m1 '^\tmemory@' /tmp/edk-placeholder.dts | sed 's/^/  /'
