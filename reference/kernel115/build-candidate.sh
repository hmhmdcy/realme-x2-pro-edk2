#!/bin/bash
set -euo pipefail
umask 077
export PATH="/home/cy122/.cargo/bin:$PATH"
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_VERSION=115
cd /home/cy122/pmos-samurai-kernel115/kernel
out=/mnt/e/edk2-samurai-out/kernel115
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/kernel-config.log" 2>&1
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image modules qcom/sm8150-samurai.dtb > "$out/kernel-full-build.log" 2>&1
test -s drivers/net/ipa/ipa.ko
test -s drivers/block/zram/zram.ko
test -s arch/arm64/boot/Image
echo KERNEL115_OWN_IPA_ZRAM_IMAGE_MODULES_DTB_BUILD_PASS
