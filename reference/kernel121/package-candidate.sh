#!/bin/bash
set -euo pipefail
umask 077
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py'
root=/home/cy122/pmos-samurai-kernel118/camera121
cd "$root/kernel"
out=/mnt/e/edk2-samurai-out/kernel121
test ! -e "$root/modules-root"
mkdir -m700 "$root/modules-root"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- INSTALL_MOD_PATH="$root/modules-root" INSTALL_MOD_STRIP=1 modules_install > "$out/modules-install-private.txt" 2>&1
release=$(cat include/config/kernel.release)
test -f "$root/modules-root/lib/modules/$release/modules.dep"
test -e "$root/modules-root/lib/modules/$release/build"
rm "$root/modules-root/lib/modules/$release/build"
depmod -e -F System.map -b "$root/modules-root" "$release" > "$out/depmod-check-private.txt" 2>&1
test ! -s "$out/depmod-check-private.txt"
tar -C "$root/modules-root" -czf "$out/modules-k121-private.tar.gz" lib/modules
cp arch/arm64/boot/Image "$out/Image-k121-private"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/sm8150-samurai-k121-private.dtb"
echo KERNEL121_MATCHING_MODULE_OVERLAY_DEPMOD_PASS_NOT_FULL_ROOTFS_NOT_DEPLOYED
