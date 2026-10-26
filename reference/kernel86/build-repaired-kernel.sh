#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel86
test -f "$out/build-input-attempt1.log"
test ! -e "$out/Image-input"
cmp .config "$out/config-input"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=86 Image >"$out/build-input.log" 2>&1
cmp .config "$out/config-input"
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-input"
sha256sum "$out/Image-input" .config usr/initramfs_data.cpio drivers/power/supply/mp2650_charger.o >"$out/kernel-build-hashes.txt"
tail -n 10 "$out/build-input.log"
cat "$out/kernel-build-hashes.txt"
