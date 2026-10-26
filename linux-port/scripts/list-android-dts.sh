#!/bin/bash
# 从本地下游内核克隆里盘点"安卓设备树"，看能拿到什么
set -u
R="/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git"
Q=arch/arm64/boot/dts/qcom

echo "=== 仓库信息 ==="
cat "$R/packed-refs" 2>/dev/null | head -5
git --git-dir="$R" log --oneline -3 2>&1 | head -5

echo
echo "=== qcom 目录下 dts/dtsi 总数 ==="
git --git-dir="$R" ls-tree -r --name-only HEAD "$Q" 2>/dev/null | wc -l

echo
echo "=== 名字里带 samurai / x2 / 19781 / rmx / oppo 的 ==="
git --git-dir="$R" ls-tree -r --name-only HEAD 2>/dev/null | grep -iE 'samurai|rmx1931|x2pro|x2_pro|19781|oppo' | head -40

echo
echo "=== 与 sm8150 相关的 dts/dtsi 前 60 个 ==="
git --git-dir="$R" ls-tree -r --name-only HEAD "$Q" 2>/dev/null | grep -iE 'sm8150|msmnile' | head -60

echo
echo "=== 厂商自有 dts 子目录 ==="
git --git-dir="$R" ls-tree -r --name-only HEAD arch/arm64/boot/dts/ 2>/dev/null | awk -F/ '{print $5}' | sort -u | head -30

echo
echo "=== 文件内容是否在本地（blob 检查）==="
git --git-dir="$R" cat-file -p HEAD:$Q/sm8150-mtp.dts 2>&1 | head -5
echo "---"
git --git-dir="$R" cat-file -t HEAD:$Q/sm8150.dtsi 2>&1
git --git-dir="$R" cat-file -s HEAD:$Q/sm8150.dtsi 2>&1
