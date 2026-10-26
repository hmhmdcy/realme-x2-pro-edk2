#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel74
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel74'
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/kernel-build.log" 2>&1
cmp .config "$out/config-before"
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/dtb-before"
cp arch/arm64/boot/Image "$out/Image-handoff"
test ! -e "$out/logdump-k74-handoff.img"
cp "$out/logdump-before.img" "$out/logdump-k74-handoff.img"
mcopy -o -i "$out/logdump-k74-handoff.img" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$out/logdump-k74-handoff.img" ::Image -)
cmp "$out/dtb-before" <(mcopy -i "$out/logdump-k74-handoff.img" ::samurai.dtb -)
sha256sum "$out/Image-handoff" "$out/logdump-k74-handoff.img" .config > "$out/build-hashes.txt"
tail -8 "$out/kernel-build.log"
cat "$out/build-hashes.txt"
