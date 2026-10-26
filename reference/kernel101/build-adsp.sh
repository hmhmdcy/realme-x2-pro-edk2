#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel101
test -f "$out/preparation.json"
test ! -e "$out/Image-adsp"
export KBUILD_BUILD_VERSION=100
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb
cp arch/arm64/boot/Image "$out/Image-adsp"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-adsp"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-adsp" "$out/dtb-adsp" "$out/cpio-after"
