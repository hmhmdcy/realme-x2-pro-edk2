#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel112
cd /home/cy122/pmos-samurai-kernel112/kernel
test ! -e "$out/Image-startup"
export KBUILD_BUILD_VERSION=112
export PATH=/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-startup"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-startup"
cp usr/initramfs_data.cpio "$out/cpio-startup"
cp .config "$out/config-after"
sha256sum "$out/Image-startup" "$out/dtb-startup" "$out/cpio-startup" > "$out/kernel-candidate.sha256"
echo KERNEL112_STARTUP_DIAGNOSTICS_BUILD_COMPLETE
