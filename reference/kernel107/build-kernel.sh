#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel107
cd /home/cy122/x2pro-linux/linux
test ! -e "$out/target-build.log"
export KBUILD_BUILD_VERSION=106
export PATH=/home/cy122/.cargo/bin:$PATH
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- net/qrtr/af_qrtr.o net/qrtr/ns.o > "$out/target-build.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-radio"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-radio"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-radio" "$out/dtb-radio" "$out/cpio-after"
