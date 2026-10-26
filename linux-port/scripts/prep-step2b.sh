#!/bin/bash
# FD 尺寸能不能放大：内存映射、FD_SIZE 来源、FD 区域布局
set -u
RK=/home/cy122/edk2-samurai/repo
DT=/tmp/live-dt

echo "=== 实机 /memory（ABL 修补后）==="
[ -d "$DT" ] || { mkdir -p "$DT"; tar -xf "/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar" -C "$DT"; }
for d in "$DT"/memory@*; do
  echo "-- $d"
  od -An -tx4 -N 32 "$d/reg" 2>/dev/null
done
ls "$DT" | grep -i '^memory' 

echo
echo "=== build.sh 里 FD_SIZE / FD_BASE 从哪来 ==="
grep -n -B6 -A6 'FD_SIZE' "$RK/build.sh" | head -50

echo
echo "=== sm8150.fdf 的 FD 区域布局（前面 60 行）==="
sed -n '1,60p' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf"

echo
echo "=== FVMAIN_COMPACT 的 FV 大小设置 ==="
sed -n '246,275p' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf"

echo
echo "=== LinuxSimpleMassStorage 在 DSC/FDF 里的包含条件 ==="
grep -rn -B4 -A4 'LinuxSimpleMassStorage' "$RK/Silicon/Qualcomm/QcomPkg/QcomCommonDsc.inc" | head -20
grep -rn -B2 -A2 'LinuxSimpleMassStorage\|ENABLE_LINUX_SIMPLE_MASS_STORAGE' "$RK/Platform/Qualcomm/sm8150/sm8150.fdf" "$RK/Platform/Realme/sm8150/samurai.dsc" "$RK/Platform/Realme/sm8150/samurai.fdf.inc" 2>/dev/null | head -20

echo
echo "=== LinuxSimpleMassStorage.inf 内容（照抄模板）==="
cat "$RK/Platform/EFI_Binaries/Applications/LinuxSimpleMassStorage/LinuxSimpleMassStorage.inf"
