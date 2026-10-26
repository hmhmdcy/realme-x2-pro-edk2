#!/bin/bash
# 从 19781 项目目录里找"机型 overlay"源文件，并抽取面板 dtsi 作为参考样本
set -u
R="/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git"
g() { git --git-dir="$R" "$@"; }
D=arch/arm64/boot/dts/19781
OUT=/home/cy122/x2pro-linux/refs/19781
mkdir -p "$OUT"

echo "=== 19781 目录里的 sm8150 相关文件 ==="
g ls-tree -r --name-only HEAD "$D" 2>/dev/null | sed "s|^$D/||" | grep -iE '^sm8150' | head -40

echo
echo "=== 含 overlay / project / 19781 的候选 ==="
g ls-tree -r --name-only HEAD "$D" 2>/dev/null | sed "s|^$D/||" | grep -iE 'overlay|project|oppo|realme' | head -20

echo
echo "=== 把整个 19781 目录导出到本地（只取 qcom/项目相关）==="
g archive HEAD "$D" 2>/dev/null | tar -x -C "$OUT" 2>/dev/null || echo "archive 失败（blob 可能不在本地）"
find "$OUT" -type f | wc -l
du -sh "$OUT" 2>/dev/null
