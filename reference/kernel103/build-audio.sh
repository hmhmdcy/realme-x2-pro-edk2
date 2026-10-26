#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel103
test -f "$out/preparation.json"
test ! -e "$out/Image-audio"
export KBUILD_BUILD_VERSION=102
export PATH=/home/cy122/.cargo/bin:$PATH
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- sound/soc/codecs/max98937-samurai.o sound/soc/qcom/samurai-audio.o qcom/sm8150-samurai.dtb > "$out/audio-target-build.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-audio"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-audio"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-audio" "$out/dtb-audio" "$out/cpio-after"
