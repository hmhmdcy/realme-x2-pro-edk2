#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel75
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/noncontinuous-build.log" 2>&1
cmp .config "$out/config-before"
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp arch/arm64/boot/Image "$out/Image-noncontinuous"
test ! -e "$out/logdump-k75-noncontinuous.img"
cp "$out/logdump-k75-gpu.img" "$out/logdump-k75-noncontinuous.img"
mcopy -o -i "$out/logdump-k75-noncontinuous.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k75-noncontinuous.img" ::Image -)
sha256sum "$out/Image-noncontinuous" "$out/logdump-k75-noncontinuous.img" > "$out/noncontinuous-build-hashes.txt"
tail -8 "$out/noncontinuous-build.log"
