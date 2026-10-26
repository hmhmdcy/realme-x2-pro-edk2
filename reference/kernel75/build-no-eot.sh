#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel75
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/no-eot-build.log" 2>&1
cmp .config "$out/config-before"
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp arch/arm64/boot/Image "$out/Image-no-eot"
test ! -e "$out/logdump-k75-no-eot.img"
cp "$out/logdump-k75-gpu.img" "$out/logdump-k75-no-eot.img"
mcopy -o -i "$out/logdump-k75-no-eot.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k75-no-eot.img" ::Image -)
sha256sum "$out/Image-no-eot" "$out/logdump-k75-no-eot.img" > "$out/no-eot-build-hashes.txt"
tail -8 "$out/no-eot-build.log"
