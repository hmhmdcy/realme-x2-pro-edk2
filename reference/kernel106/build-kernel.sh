#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel106
cd /home/cy122/x2pro-linux/linux
test ! -e "$out/target-build.log"
export KBUILD_BUILD_VERSION=105
export PATH=/home/cy122/.cargo/bin:$PATH
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
make -j8 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- net/qrtr/smd.o net/qrtr/af_qrtr.o net/qrtr/ns.o drivers/soc/qcom/qcom_pd_mapper.o sound/soc/qcom/qdsp6/q6core.o > "$out/target-build.log" 2>&1
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-radio"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-radio"
cp usr/initramfs_data.cpio "$out/cpio-after"
cp .config "$out/config-after"
sha256sum "$out/Image-radio" "$out/dtb-radio" "$out/cpio-after"
