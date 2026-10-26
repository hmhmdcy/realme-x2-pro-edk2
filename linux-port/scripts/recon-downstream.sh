#!/bin/bash
# 检查旧工程留下的下游内核部分克隆，看能否直接提取安卓设备树
set -u
R="/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git"
echo "=== $R ==="
ls -la "$R" 2>&1 | head -20
echo "--- HEAD ---"; cat "$R/HEAD" 2>&1
echo "--- refs ---"; git --git-dir="$R" for-each-ref 2>&1 | head
echo "--- 仓库大小 ---"; du -sh "$R" 2>&1
echo "--- 能否列出文件 ---"; git --git-dir="$R" ls-tree -r --name-only HEAD 2>&1 | head -5
echo "--- 里面有没有 samurai/19781 的设备树 ---"
git --git-dir="$R" ls-tree -r --name-only HEAD 2>/dev/null | grep -iE 'dts/qcom/.*(samurai|19781|sm8150|msmnile)' | head -30
echo
echo "=== 旧工程 sources 目录其它线索 ==="
ls -la "/mnt/e/Realme X2 Pro移植主线Linux/sources/" 2>&1
find "/mnt/e/Realme X2 Pro移植主线Linux/sources/" -maxdepth 3 -iname '*dts*' 2>/dev/null | head -20
