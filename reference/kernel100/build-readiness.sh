#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel100
test -f "$out/preparation.json"
test ! -e "$out/Image-readiness"
export KBUILD_BUILD_VERSION=99
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb
cp arch/arm64/boot/Image "$out/Image-readiness"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-readiness"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-readiness" "$out/dtb-readiness" "$out/cpio-after"
