#!/bin/bash
set -euo pipefail
umask 077
export KBUILD_BUILD_VERSION=118
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py'
cd /home/cy122/pmos-samurai-kernel118/kernel
out=/mnt/e/edk2-samurai-out/kernel118
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/config-build.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/kernel-full-build.log" 2>&1
test -s arch/arm64/boot/Image
echo KERNEL118_FULL_IMAGE_MODULES_DTB_BUILD_PASS_NOT_DEPLOYED
