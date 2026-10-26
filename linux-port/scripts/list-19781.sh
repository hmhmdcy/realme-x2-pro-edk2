#!/bin/bash
# 盘点 19781（= 本机 samurai）项目设备树，评估作为主线参考的价值
set -u
R="/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git"
g() { git --git-dir="$R" "$@"; }
D=arch/arm64/boot/dts/19781

echo "=== $D 下的文件 ==="
g ls-tree -r --name-only HEAD "$D" 2>&1 | sed "s|^$D/||" | head -60
echo "(共 $(g ls-tree -r --name-only HEAD "$D" 2>/dev/null | wc -l) 个)"

echo
echo "=== 19781/Makefile ==="
g cat-file -p HEAD:"$D/Makefile" 2>&1 | head -60

echo
echo "=== qcom 下与 19781/samurai 相关的机型 dts/dtsi ==="
g ls-tree -r --name-only HEAD arch/arm64/boot/dts/qcom 2>/dev/null | grep -iE '19781|samurai' | head -30

echo
echo "=== 触控 / 面板 / 充电 关键文件 ==="
for pat in s3706 synaptics sofef03f touch nt36 max989 bq27 mp2650; do
  echo "--- /$pat/"
  g ls-tree -r --name-only HEAD 2>/dev/null | grep -iE "$pat" | grep -iE '\.dts|\.dtsi' | head -6
done
