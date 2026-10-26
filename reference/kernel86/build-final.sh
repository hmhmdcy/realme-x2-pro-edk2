#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel86
test ! -e "$out/Image-final"
cmp .config "$out/config-input"
cp '/mnt/e/RealmeX2Pro edk2/reference/kernel86/mp2650_charger.c' drivers/power/supply/mp2650_charger.c
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=87 Image >"$out/build-final.log" 2>&1
cmp .config "$out/config-input"
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-final"
sha256sum "$out/Image-final" .config usr/initramfs_data.cpio drivers/power/supply/mp2650_charger.c >"$out/final-build-hashes.txt"
cat "$out/final-build-hashes.txt"
