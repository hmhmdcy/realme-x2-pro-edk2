#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel110
stage=/home/cy122/pmos-samurai-kernel110
cd "$stage/kernel"
test ! -e "$out/Image-rescue"
export KBUILD_BUILD_VERSION=110
export PATH=/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-rescue"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-rescue"
cp usr/initramfs_data.cpio "$out/cpio-rescue"
cp .config "$out/config-after"
cmp "$out/dtb-rescue" /mnt/e/edk2-samurai-out/kernel109/dtb-pmos
sha256sum "$out/Image-rescue" "$out/dtb-rescue" "$out/cpio-rescue" > "$out/rescue-candidate.sha256"
echo RESCUE110_BUILD_COMPLETE_DTB_UNCHANGED
