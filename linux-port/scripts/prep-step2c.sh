#!/bin/bash
# 最后几项前置事实
set -u
RK=/home/cy122/edk2-samurai/repo
LK=/home/cy122/x2pro-linux/linux
DT=/tmp/live-dt

echo "=== 1. FD_SIZE / FD_BASE 定义 ==="
grep -rn 'FD_SIZE\|FD_BASE' "$RK"/build.sh | head -20
grep -rn 'FD_SIZE\|FD_BASE' "$RK"/*.cfg "$RK"/build_cfg/*.json 2>/dev/null | head -10

echo
echo "=== 2. 实机 memory 节点 ==="
ls "$DT" | head -5
for p in "$DT/memory/reg" "$DT"/memory@*/reg; do
  [ -f "$p" ] && { echo "-- $p"; od -An -tx4 -N 48 "$p"; }
done

echo
echo "=== 3. PlatformRegisterFvBootOption 实现 ==="
grep -n -B6 -A30 'PlatformRegisterFvBootOption (' "$RK/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c" | head -60

echo
echo "=== 4. gLinuxSimpleMassStorageGuid 定义处 ==="
grep -rn 'gLinuxSimpleMassStorageGuid' "$RK" --include='*.dec' --include='*.h' 2>/dev/null | grep -v workspace | head

echo
echo "=== 5. Image 压缩后大小（决定 FD 要长多少）==="
gzip -c "$LK/arch/arm64/boot/Image" | wc -c
ls -la "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.efi"
gzip -c "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.efi" | wc -c
