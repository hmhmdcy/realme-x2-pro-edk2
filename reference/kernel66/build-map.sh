#!/bin/bash
set -euo pipefail
src=/home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel66
base=/mnt/e/edk2-samurai-out/logdump-k66-adc.img
dest=/mnt/e/edk2-samurai-out/logdump-k66-map.img
test ! -e "$dest"
test "$(sha256sum "$base" | cut -d' ' -f1)" = 38c35f641d48579b58c4aa9833efe0feafa7cabb0c32d99709e7fa731485c815
cd "$src"
cmp .config "$out/config-adc"
cmp arch/arm64/boot/Image "$out/Image-adc"
test "$(sha256sum drivers/tty/serial/eud_earlycon.c | cut -d' ' -f1)" = 34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9
make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image > "$out/map-build.log" 2>&1
if grep -Eq 'warning:|error:' "$out/map-build.log"; then tail -50 "$out/map-build.log"; exit 1; fi
cp "$base" "$dest"
mcopy -o -i "$dest" arch/arm64/boot/Image ::Image
cmp <(mcopy -i "$base" ::samurai.dtb -) <(mcopy -i "$dest" ::samurai.dtb -)
cmp arch/arm64/boot/Image <(mcopy -i "$dest" ::Image -)
cmp .config "$out/config-adc"
test "$(sha256sum drivers/tty/serial/eud.c | cut -d' ' -f1)" = 39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4
test "$(sha256sum /home/cy122/x2pro-linux/initramfs/init | cut -d' ' -f1)" = e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab
cp arch/arm64/boot/Image "$out/Image-map"
sha256sum "$dest" .config arch/arm64/boot/Image drivers/tty/serial/eud.c drivers/tty/serial/eud_earlycon.c /home/cy122/x2pro-linux/initramfs/init | tee "$out/map-hashes.txt"
