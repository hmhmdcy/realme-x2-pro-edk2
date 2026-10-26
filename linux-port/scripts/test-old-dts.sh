#!/bin/bash
# 核实旧工程：把 E:\Realme X2 Pro移植主线Linux\patches\0001-rmx1931-usb-bringup.patch
# 应用到 v7.3-rc6 树上，并编译它声明的设备树，看是否真的能编译通过。
set -u
cd /home/cy122/x2pro-linux/linux || exit 1

PATCH_SRC="/mnt/e/Realme X2 Pro移植主线Linux/patches/0001-rmx1931-usb-bringup.patch"
cp "$PATCH_SRC" /home/cy122/x2pro-linux/old-0001.patch || exit 1

echo "=== git status before ==="
git status --short

git apply --check /home/cy122/x2pro-linux/old-0001.patch && echo "APPLY_CHECK_OK" || { echo "APPLY_CHECK_FAILED"; exit 1; }
git apply /home/cy122/x2pro-linux/old-0001.patch || { echo "APPLY_FAILED"; exit 1; }
echo "APPLIED"

echo "=== build old dtb ==="
make -s ARCH=arm64 qcom/sm8150-realme-x2pro.dtb 2>&1 | tail -20
echo "MAKE_EXIT=${PIPESTATUS[0]}"
ls -la arch/arm64/boot/dts/qcom/sm8150-realme-x2pro.dtb 2>&1
