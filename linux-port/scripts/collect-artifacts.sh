#!/bin/bash
# 收尾：整理补丁编号、把可复核的产物复制回 Windows 工作区。
set -eu
cd /home/cy122/x2pro-linux/linux
P=/home/cy122/x2pro-linux/patches
W="/mnt/e/RealmeX2Pro edk2/linux-port"
OUT="$W/artifacts"

mkdir -p "$W/patches" "$OUT"

echo "=== 1. 补丁编号整理 ==="
rm -f "$P/0001-eud-earlycon.patch"
EP=$(ls "$P"/0001-tty-serial-*.patch 2>/dev/null | head -1)
DP=$(ls "$P"/0001-arm64-dts-*.patch 2>/dev/null | head -1)
mv -f "$DP" "$P/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch" 2>/dev/null || true
cp -f "$P"/0001-tty-serial-*.patch "$W/patches/"
cp -f "$P"/0002-arm64-dts-*.patch "$W/patches/"
ls -la "$P" "$W/patches"

echo "=== 2. 新的 DTB 与反编译 ==="
DTB=arch/arm64/boot/dts/qcom/sm8150-samurai.dtb
scripts/dtc/dtc -I dtb -O dts -o "$OUT/sm8150-samurai.dts.decompiled" "$DTB"
cp -f "$DTB" "$OUT/sm8150-samurai.dtb"
cp -f arch/arm64/boot/dts/qcom/sm8150-samurai.dts "$W/dts/sm8150-samurai.dts"
sha256sum "$DTB" | tee "$OUT/sm8150-samurai.dtb.sha256"

echo "=== 3. reserved-memory 核对表 ==="
python3 - "$OUT/sm8150-samurai.dts.decompiled" "$OUT/reserved-memory.txt" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
lines = open(src).read().splitlines()
start = next(i for i, l in enumerate(lines) if l == '\treserved-memory {')
rows, cur, props, depth = [], None, [], 0
for l in lines[start:]:
    if l == '\treserved-memory {':
        depth = 1; continue
    if depth == 1:
        m = re.match(r'\t\t([^\s{]+) \{', l)
        if m:
            cur, props, depth = m.group(1), [], 2; continue
        if l == '\t};':
            break
        continue
    if depth == 2:
        if l == '\t\t};':
            rows.append((cur, props)); cur, props, depth = None, [], 1; continue
        props.append(l.strip())
with open(dst, 'w') as f:
    for name, props in rows:
        reg = next((p for p in props if p.startswith('reg =')), '')
        nomap = any('no-map' in p for p in props)
        comp = next((p for p in props if p.startswith('compatible =')), '')
        m = re.search(r'<(0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+) (0x[0-9a-f]+)>', reg)
        if m:
            line = f"{name:<24} 0x{int(m.group(2),16):09x} + 0x{int(m.group(4),16):<8x} no-map={str(nomap):<5} {comp}"
        else:
            line = f"{name:<24} {reg} {comp}"
        print(line); f.write(line + "\n")
PY

echo
echo "=== 4. git 状态 ==="
git log --oneline -3
git status --short
echo DONE
