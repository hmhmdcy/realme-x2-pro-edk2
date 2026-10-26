#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel88
test ! -e "$out/Image-wifi"
cmp .config "$out/config-wifi"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >"$out/olddefconfig.log" 2>&1
cmp .config "$out/config-wifi"
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=89 Image qcom/sm8150-samurai.dtb >"$out/build-wifi.log" 2>&1
cmp .config "$out/config-wifi"
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-wifi"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/samurai-wifi.dtb"
sha256sum "$out/Image-wifi" "$out/samurai-wifi.dtb" .config usr/initramfs_data.cpio >"$out/build-hashes.txt"
tail -n 12 "$out/build-wifi.log"
cat "$out/build-hashes.txt"
