#!/bin/bash
set -euo pipefail
out=/mnt/e/edk2-samurai-out/kernel92
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel92'
cd /home/cy122/x2pro-linux/linux
test ! -e "$out/Image-connectivity"
while read -r entry; do
    key=${entry%%=*}; value=${entry#*=}
    if [ "$value" = y ]; then scripts/config --enable "${key#CONFIG_}"; else exit 1; fi
done < "$ref/connectivity-builtins.config"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
python3 "$ref/audit-config.py"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=91 Image qcom/sm8150-samurai.dtb > "$out/build-kernel.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-connectivity"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-connectivity"
cp .config "$out/config-after"
cp usr/initramfs_data.cpio "$out/cpio-after"
sha256sum "$out/Image-connectivity" "$out/dtb-connectivity" "$out/cpio-after" > "$out/build-hashes.txt"
python3 "$ref/audit-dtb.py"
tail -8 "$out/build-kernel.log"
cat "$out/build-hashes.txt"
