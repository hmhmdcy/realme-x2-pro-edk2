#!/bin/bash
# 决定性问题：FD 放大到 ~16MB 会不会踩到未映射内存 / FVMAIN 解压到哪里
set -u
RK=/home/cy122/edk2-samurai/repo
DT=/tmp/live-dt
mkdir -p "$DT"
tar -xf "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar" -C "$DT" 2>/dev/null

echo "=== 实机 /memory ==="
ls "$DT" | grep -i memory
for p in "$DT/memory/reg" "$DT"/memory*/reg "$DT"/memory@*/reg; do
  if [ -f "$p" ]; then echo "-- $p"; od -An -tx4 -N 48 "$p"; fi
done

echo
echo "=== EDK2 8G 档内存表（HAS_MLVM 下 0xC0000000 附近）==="
grep -n -A40 'Mem8G\|HAS_MLVM' "$RK/Silicon/Qualcomm/sm8150/Library/PlatformMemoryMapLib/PlatformMemoryMapLib.c" 2>/dev/null | grep -iE 'C0000000|CE000000|MLVM|Conv|0x[89ABCDEF][0-9A-Fa-f]{7}' | head -30

echo
echo "=== PrePi：FVMAIN 解压到哪里 ==="
grep -rn -iE 'PcdFvBaseAddress|FvBase|Decompress|0x9FC00000|PcdFvSize' "$RK/Silicon/Qualcomm/QcomPkg/PrePi/"*.c "$RK/Silicon/Qualcomm/QcomPkg/PrePi/"*.h 2>/dev/null | head -20
grep -rn 'PcdFvBaseAddress\|PcdFvSize' "$RK/Platform/Realme/sm8150/samurai.dsc" "$RK/Silicon/Qualcomm/QcomPkg/QcomCommonDsc.inc" 2>/dev/null | head

echo
echo "=== build.sh 头部：FD_SIZE 从哪来 ==="
sed -n '1,60p' "$RK/build.sh"

echo
echo "=== PlatformRegisterFvBootOption 在哪 ==="
grep -rn 'PlatformRegisterFvBootOption' "$RK/Platform/RenegadePkg/Library/PlatformBootManagerLib/"*.c | head
