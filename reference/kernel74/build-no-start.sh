#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel74
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel74'
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/no-start-build.log" 2>&1
cmp .config "$out/config-before"
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-before"
cp arch/arm64/boot/Image "$out/Image-no-start"
test ! -e "$out/logdump-k74-no-start.img"
cp "$out/logdump-before.img" "$out/logdump-k74-no-start.img"
mcopy -o -i "$out/logdump-k74-no-start.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k74-no-start.img" ::Image -)
cmp "$out/dtb-before" <(mcopy -i "$out/logdump-k74-no-start.img" ::samurai.dtb -)
sha256sum "$out/Image-no-start" "$out/logdump-k74-no-start.img" .config > "$out/no-start-build-hashes.txt"
tail -8 "$out/no-start-build.log"
cat "$out/no-start-build-hashes.txt"
