#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel75
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image qcom/sm8150-samurai.dtb > "$out/kernel-build.log" 2>&1
cmp .config "$out/config-before"
cp arch/arm64/boot/Image "$out/Image-gpu"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
test ! -e "$out/logdump-k75-gpu.img"
cp "$out/logdump-before.img" "$out/logdump-k75-gpu.img"
mcopy -o -i "$out/logdump-k75-gpu.img" arch/arm64/boot/Image ::Image
mcopy -o -i "$out/logdump-k75-gpu.img" arch/arm64/boot/dts/qcom/sm8150-samurai.dtb ::samurai.dtb
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k75-gpu.img" ::Image -)
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb <(mcopy -i "$out/logdump-k75-gpu.img" ::samurai.dtb -)
sha256sum "$out/Image-gpu" "$out/logdump-k75-gpu.img" .config > "$out/kernel-build-hashes.txt"
tail -8 "$out/kernel-build.log"
