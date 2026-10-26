#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel91
test ! -e "$out/Image-rmtfs"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel91/audit-config.py'
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=90 Image qcom/sm8150-samurai.dtb > "$out/build-kernel.log" 2>&1
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-rmtfs"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp .config "$out/config-after"
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel91/audit-dtb.py'
sha256sum "$out/Image-rmtfs" "$out/firmware-after.dtb" .config usr/initramfs_data.cpio > "$out/build-hashes.txt"
tail -12 "$out/build-kernel.log"
cat "$out/build-hashes.txt"
