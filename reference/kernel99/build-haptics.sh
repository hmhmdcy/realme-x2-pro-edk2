#!/bin/bash
set -euo pipefail
kernel=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel99
cd "$kernel"
test -f "$out/driver-preparation.json"
test ! -e "$out/Image-haptics"
export KBUILD_BUILD_VERSION=98
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- W=1 drivers/input/misc/aw8697-samurai.o
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb
cp arch/arm64/boot/Image "$out/Image-haptics"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-haptics"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-haptics" "$out/dtb-haptics" "$out/cpio-after"
