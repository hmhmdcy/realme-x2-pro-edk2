#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel87
test ! -e "$out/Image-watchdog"
cmp .config "$out/config-before"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=88 Image >"$out/build-watchdog.log" 2>&1
cmp .config "$out/config-before"
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-watchdog"
sha256sum "$out/Image-watchdog" .config usr/initramfs_data.cpio drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.o >"$out/build-hashes.txt"
cat "$out/build-hashes.txt"
