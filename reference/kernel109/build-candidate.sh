#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel109
stage=/home/cy122/pmos-samurai-kernel109
cd "$stage/kernel"
test ! -e "$out/Image-pmos"
export KBUILD_BUILD_VERSION=109
export PATH=/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- drivers/gpu/drm/panel/panel-samsung-sofef03f.o > "$out/panel-build.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-pmos"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-pmos"
cp usr/initramfs_data.cpio "$out/cpio-pmos"
cp .config "$out/config-after"
sha256sum "$out/Image-pmos" "$out/dtb-pmos" "$out/cpio-pmos" "$out/config-after" > "$out/kernel-candidate.sha256"
echo KERNEL109_BUILD_COMPLETE
