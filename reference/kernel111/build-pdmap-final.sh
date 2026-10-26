#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel111
cd /home/cy122/pmos-samurai-kernel111/kernel
test ! -e "$out/Image-sensors"
export KBUILD_BUILD_VERSION=111
export PATH=/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- drivers/soc/qcom/qcom_pd_mapper.o > "$out/pdmap-build.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build-final.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-sensors"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-sensors"
cp usr/initramfs_data.cpio "$out/cpio-sensors"
sha256sum "$out/Image-sensors" "$out/dtb-sensors" "$out/cpio-sensors" "$out/config-after" > "$out/kernel-candidate.sha256"
echo KERNEL111_PD_MAP_FINAL_BUILD_COMPLETE
