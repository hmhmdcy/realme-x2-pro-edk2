#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel73
cp .config "$out/config-first"
scripts/config --enable REGULATOR_QCOM_REFGEN --set-val DRIVER_DEFERRED_PROBE_TIMEOUT 60
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/clock-olddefconfig.log" 2>&1
grep -qx CONFIG_REGULATOR_QCOM_REFGEN=y .config
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/clock-build.log" 2>&1
cp arch/arm64/boot/Image "$out/Image-display-deps"
cp .config "$out/config-display-deps"
dest="$out/logdump-k73-display-deps.img"
test ! -e "$dest"
cp "$out/logdump-k73-display.img" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
cmp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb <(mcopy -i "$dest" ::samurai.dtb -)
sha256sum "$dest" arch/arm64/boot/Image .config > "$out/clock-build-hashes.txt"
tail -5 "$out/clock-build.log"
cat "$out/clock-build-hashes.txt"
