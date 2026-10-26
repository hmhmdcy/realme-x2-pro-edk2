#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel75
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/stalled-build.log" 2>&1
cmp .config "$out/config-before"
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp arch/arm64/boot/Image "$out/Image-stalled"
test ! -e "$out/logdump-k75-stalled.img"
cp "$out/logdump-k75-gpu.img" "$out/logdump-k75-stalled.img"
mcopy -o -i "$out/logdump-k75-stalled.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k75-stalled.img" ::Image -)
sha256sum "$out/Image-stalled" "$out/logdump-k75-stalled.img" > "$out/stalled-build-hashes.txt"
tail -8 "$out/stalled-build.log"
